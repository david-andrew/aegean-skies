"""Expressive timing from the score itself: an intensity curve, and a tempo that follows it.

Not hand-tuned bars. For any piece:

1. Intensity, on a grid of half beats, from what the notes are doing:
   * density: notes per beat around the moment (thick chords count every note);
   * motion: distinct onsets per beat (how continuously something is moving: runs, arpeggios);
   * register and range: how high the sounding notes sit and how wide they spread;
   * tension: how dissonant the sounding pitch classes are (seconds, sevenths, tritones);
   * dynamics: the score's dynamic markings when given (a curve in dB), else the notes'
     velocities, when the score has any variety in them;
   * contour: whether the top voice is climbing.
   Each is normalised against the piece itself (its 10th and 90th percentiles), weighted, and
   smoothed over about a bar.

2. Tempo (performed seconds per score second, a "rate": below 1 is faster), in the log domain:
   * forward motion where the texture flows (motion, more so as intensity rises) and where
     intensity is building;
   * broadening at intensity peaks and lingering at phrase ends (cadences);
   * a final ritard;
   * a bounded, seeded variation (slow, smooth wanderings and a small offset per phrase), so
     the same score never sounds machined, yet every rebuild is identical;
   * smoothed over half a beat and clamped to the piece's range.

Each piece gives a few parameters (`ExpressiveTiming`): the overall pace, the range, the
sensitivity and the weights, and optionally the score's own tempo markings (a factor per marked
section, from the printed score: "Un poco mosso", "Calmato", "Tempo I"...), which set each
section's pace; the intensity then shapes the motion within it. `timing_map` returns score-time -> performed-time points (the
`time_map` of a performance annotation) and the curves, for plotting and checking.
"""
from bisect import bisect_right
from dataclasses import dataclass, field
import math, random


@dataclass
class ExpressiveTiming:
    base: float = 1.0               # overall pace (performed / score); below 1 is faster
    min_rate: float = 0.75          # the fastest it may go
    max_rate: float = 1.35          # and the slowest (not counting the final ritard)
    sensitivity: float = 1.0        # how strongly intensity moves the tempo
    flow: float = 0.22              # forward motion where the texture flows
    build: float = 0.10             # forward motion where intensity rises
    peak: float = 0.10              # broadening at intensity peaks
    cadence: float = 0.22           # lingering into phrase ends
    final_ritard: float = 0.45      # the last bars
    variation: float = 0.03         # the seeded wandering, as a fraction of the tempo
    seed: int = 1
    phrase_bars: int = 2
    melody_tracks: tuple = (1,)
    tempo_marks: list = field(default_factory=list)   # [(bar, rate factor)] from the score's markings
    weights: dict = field(default_factory=lambda: dict(density=0.22, motion=0.1, register=0.1, range=0.1, tension=0.16, dynamics=0.26, contour=0.06))


def _percentile(xs, q):
    s = sorted(xs)
    if not s: return 0.0
    k = min(len(s) - 1, max(0, int(round(q * (len(s) - 1)))))
    return s[k]


def _normalise(xs):
    lo, hi = _percentile(xs, 0.1), _percentile(xs, 0.9)
    if hi - lo < 1e-9: return [0.5 for _ in xs]
    return [min(1.0, max(0.0, (x - lo) / (hi - lo))) for x in xs]


def _smooth(xs, sigma):
    if sigma <= 0: return list(xs)
    r = int(math.ceil(sigma * 3))
    kernel = [math.exp(-0.5 * (k / sigma) ** 2) for k in range(-r, r + 1)]
    out = []
    for i in range(len(xs)):
        total = weight = 0.0
        for k, w in zip(range(-r, r + 1), kernel):
            j = i + k
            if 0 <= j < len(xs):
                total += xs[j] * w; weight += w
        out.append(total / weight)
    return out


# how much each interval class (in semitones, folded to 0..6) grates
DISSONANCE = [0.0, 1.0, 0.45, 0.12, 0.08, 0.05, 0.8]


def _curve_at(points, t):
    times = [p[0] for p in points]
    i = max(0, min(len(points) - 2, bisect_right(times, t) - 1))
    (a, x), (b, y) = points[i], points[i + 1]
    return x + (y - x) * max(0.0, min(1.0, (t - a) / (b - a))) if b > a else x


def intensity(notes, clock, params: ExpressiveTiming, step=0.5, markings=None):
    """Notes are [start, duration, pitch, instrument, g0, g1, track, ...] in score seconds."""
    beats = [clock.beat(n[0]) for n in notes]
    ends = [clock.beat(n[0] + n[1]) for n in notes]
    last = max(ends)
    grid = [i * step for i in range(int(math.ceil(last / step)) + 1)]
    onsets = sorted(beats)
    velocities = [n[4] for n in notes]
    dynamic = max(velocities) - min(velocities) > 0.05
    order = sorted(range(len(notes)), key=lambda i: beats[i])
    distinct = sorted(set(round(x, 3) for x in onsets))
    density, motion, register, spread, tension, loud, top = [], [], [], [], [], [], []
    for b in grid:
        a = bisect_right(onsets, b - 1.0); z = bisect_right(onsets, b + 1.0)
        density.append((z - a) / 2.0)
        motion.append((bisect_right(distinct, b + 1.0) - bisect_right(distinct, b - 1.0)) / 2.0)
        sounding = [i for i in order if beats[i] <= b + 0.25 and ends[i] > b - 0.25]
        pitches = [notes[i][2] for i in sounding]
        register.append(sum(pitches) / len(pitches) if pitches else 0.0)
        spread.append(max(pitches) - min(pitches) if pitches else 0.0)
        classes = sorted(set(p % 12 for p in pitches))
        pairs = [(x, y) for i, x in enumerate(classes) for y in classes[i + 1:]]
        tension.append(sum(DISSONANCE[min((y - x) % 12, 12 - (y - x) % 12)] for x, y in pairs) / max(1, len(pairs)) if pairs else 0.0)
        near = [notes[i][4] for i in sounding if abs(beats[i] - b) < 1.0]
        loud.append(sum(near) / len(near) if near else 0.0)
        melody = [notes[i][2] for i in sounding if notes[i][6] in params.melody_tracks]
        top.append(max(melody) if melody else (top[-1] if top else 0.0))
    top = _smooth(top, 2.0 / step)
    contour = [0.0] + [max(0.0, top[i] - top[i - 1]) for i in range(1, len(top))]
    features = dict(density=_normalise(density), motion=_normalise(_smooth(motion, clock.meter * 0.6 / step)), register=_normalise(register), range=_normalise(spread),
                    tension=_normalise(tension), contour=_normalise(_smooth(contour, 1.0 / step)))
    if markings: features['dynamics'] = _normalise([_curve_at(markings, clock.time(b)) for b in grid])
    elif dynamic: features['dynamics'] = _normalise(loud)
    weights = {k: v for k, v in params.weights.items() if k in features}
    total = sum(weights.values())
    raw = [sum(features[k][i] * w for k, w in weights.items()) / total for i in range(len(grid))]
    bar = clock.meter
    return grid, _smooth(raw, bar / step * 0.5), features


def _phrase_bounds(notes, clock, params, last):
    """Phrase ends every few bars, moved to a nearby rest or long note in the melody."""
    bar = clock.meter
    top = {}
    for n in notes:
        if n[6] not in params.melody_tracks: continue
        b = round(clock.beat(n[0]), 4)
        if b not in top or n[2] > top[b][2]: top[b] = n
    melody = sorted((b, n) for b, n in top.items())
    candidates = []
    for (b, n), (c, _) in zip(melody, melody[1:]):
        finish = clock.beat(n[0] + n[1])
        if c - finish > 0.25 or finish - b > 1.4 * bar / 3: candidates.append(c)
    bounds = []
    target = params.phrase_bars * bar
    while target < last - bar * 0.5:
        near = [c for c in candidates if abs(c - target) < bar * 0.6]
        bounds.append(min(near, key=lambda c: abs(c - target)) if near else target)
        target = bounds[-1] + params.phrase_bars * bar
    return bounds


def timing_map(notes, clock, params: ExpressiveTiming, step=0.5, markings=None):
    """Score seconds -> performed seconds, and the curves (beats, intensity, rate) behind it.
    `markings`: the score's dynamics as [score seconds, dB] points, when known."""
    grid, level, features = intensity(notes, clock, params, step, markings)
    last = grid[-1]
    bar = clock.meter
    rising = [0.0] + [(level[i] - level[i - 1]) / step for i in range(1, len(level))]
    rising = _smooth(rising, bar / step * 0.5)
    # the peaks: local maxima standing out from their neighbourhood by a fifth of the range
    peaks = []
    span = int(bar / step * 1.5)
    for i in range(1, len(level) - 1):
        window = level[max(0, i - span): i + span + 1]
        if level[i] == max(window) and level[i] - min(window) > 0.2: peaks.append(grid[i])
    bounds = _phrase_bounds(notes, clock, params, last)
    rng = random.Random(params.seed)
    waves = [(rng.uniform(3, 9) * bar, rng.uniform(0, math.tau), rng.uniform(0.5, 1.0)) for _ in range(3)]
    phrase_offsets = [rng.uniform(-1, 1) for _ in range(len(bounds) + 2)]
    log_rate = []
    for i, b in enumerate(grid):
        # (flowing motion presses on, the more so the more is happening)
        loudness = features['dynamics'][i] if 'dynamics' in features else level[i]
        flow = (features['motion'][i] - 0.4) * (0.15 + 0.85 * loudness)
        x = -params.sensitivity * (params.flow * flow + params.build * max(-0.5, min(1.0, rising[i] * bar)))
        x += params.peak * sum(math.exp(-((b - p) / (bar * 0.6)) ** 2) for p in peaks)
        # lingering into each phrase's end, and a breath after it
        for e in bounds + [last]:
            u = (b - e) / (bar * 0.35)
            if -2.5 < u < 1.0: x += params.cadence * math.exp(-(u + 0.6) ** 2)
        k = bisect_right(bounds, b)
        wander = sum(a * math.sin(math.tau * b / period + phase) for period, phase, a in waves) / 2.0
        x += params.variation * (0.6 * wander + 0.4 * phrase_offsets[k])
        ending = max(0.0, 1.0 - (last - b) / (bar * 2.0))
        x += params.final_ritard * ending ** 2
        # the marked sections' own pace (eased over half a bar at each change)
        if params.tempo_marks:
            marked = 0.0
            for k, (bar_no, factor) in enumerate(params.tempo_marks):
                start = (bar_no - 1) * bar
                previous = math.log(params.tempo_marks[k - 1][1]) if k > 0 else 0.0
                u = max(0.0, min(1.0, (b - start + bar * 0.25) / (bar * 0.5)))
                if b >= start - bar * 0.25: marked = previous + (math.log(factor) - previous) * u * u * (3 - 2 * u)
            x += marked
        log_rate.append(x)
    log_rate = _smooth(log_rate, 1.0 / step)
    low, high = math.log(params.min_rate / params.base), math.log(params.max_rate / params.base)
    rates = []
    for i, x in enumerate(log_rate):
        ending = max(0.0, 1.0 - (last - grid[i]) / (bar * 2.0))
        top = high + (params.final_ritard if ending > 0 else 0.0)
        # (a soft limit: approaching the range's ends it eases in, never a flat ceiling)
        mid = (low + top) * 0.5; half = (top - low) * 0.5
        rates.append(params.base * math.exp(mid + half * math.tanh((x - mid) / half)))
    points = [[0.0, 0.0]]
    for i in range(1, len(grid)):
        a, z = clock.time(grid[i - 1]), clock.time(grid[i])
        points.append([round(z, 6), round(points[-1][1] + (z - a) * (rates[i - 1] + rates[i]) * 0.5, 6)])
    # (on past the last note's end at the final pace, so ringing notes and the hall are kept)
    tail = clock.time(last + bar * 2) - clock.time(last)
    points.append([round(points[-1][0] + tail, 6), round(points[-1][1] + tail * rates[-1], 6)])
    return points, dict(beats=grid, intensity=level, rate=rates, peaks=peaks, bounds=bounds, features=features)


def warp(notes, points):
    """Apply a time map to notes ([start, duration, ...]) directly (pieces with no annotation)."""
    times = [p[0] for p in points]
    def at(t):
        i = max(0, min(len(points) - 2, bisect_right(times, t) - 1))
        (a, x), (b, y) = points[i], points[i + 1]
        return x + (y - x) * max(0.0, min(1.0, (t - a) / (b - a))) if b > a else x
    out = []
    for n in notes:
        s = at(n[0]); e = at(n[0] + n[1])
        out.append([s, max(0.02, e - s)] + list(n[2:]))
    return out
