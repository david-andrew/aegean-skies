"""Grace notes: finding them in a piece's notes and playing them as grace notes.

The sources write a grace note in one of three ways, and none of them plays well as it comes:

* MuseScore's export gives a real short note ending where the main note begins (about an eighth of
  a beat, or a few ticks for a run of them), with the note before it left running under it;
* LilyPond's export gives it a fixed 10 or 21 ticks whatever the tempo (27 ms at a quick tempo: a
  click, not a pitch), before the beat;
* LilyPond 2.6's export (Mutopia's older pieces) gives it its written length, started a little
  before the main note and left sounding through it: a smear, not a grace note.

None of them says whether the score's small note was an acciaccatura or an appoggiatura. So the
kind is decided as a player would from the notes: a quick note before a long one, a step away,
is leaned on (an appoggiatura, on the beat); anything else is crushed in before the beat
(an acciaccatura).

* acciaccatura: a quick note (ACCIACCATURA_S, 40-70 ms) ending where the main note begins, so it
  sounds just before the beat; the note it follows is cut short to make room.
* appoggiatura: sounds on the beat and takes its time from the start of the main note (a quarter of
  the main note's length, between APPOGGIATURA_MIN and APPOGGIATURA_MAX seconds); the main note
  ends where it was written to end.

A group of up to GROUP_MAX quick notes (a turn, {re32 do32}) is played as one grace, the notes
sharing the time. The graces' levels are set against the main note so they are heard without
standing out. Pure functions on [start, duration, pitch, instrument, gain0, gain1, track, ...]
notes in seconds: nothing here reads a file.
"""
from collections import defaultdict

GRACE_BEATS = 0.10        # a grace note is shorter than this many beats (a written 32nd is 0.125: that is a rhythm)
SHORT_MAX_S = 0.25        # ...and than this many seconds, in the slowest pieces
SHORT_S = 0.16            # a note in a group is shorter than this when no clock says what a beat is
CONTIG_S = 0.012          # ...and ends no more than this before the main note's start
OVERRUN_S = 0.040         # ...or no more than this after it (the performance pass stretches short notes)
OVERLAP_S = 0.10          # a LilyPond 2.6 grace starts up to this long before its main note
GROUP_MAX = 4
MAIN_RATIO = 2.2          # the main note is this many times its length (or more)
MAIN_MIN_S = 0.10
ACCIACCATURA_S = (0.040, 0.070)
GROUP_NOTE_S = (0.032, 0.048)   # each note of a grace group
# An instrument whose note takes a while to speak a pitch (measured with the synthesizer: a grace
# note's pitch is held about as long as the note lasts for a piano, harp, brass, flute, oboe,
# bassoon and plucked strings at 55 ms, but not for the violin (nothing at 55 ms, 50 ms at 90) or
# much for the clarinet, accordion and banjo): an acciaccatura on one of them is longer.
# (instrument number from music_pack: STRINGS 0, CLARINET 4, ACCORDION 9, BANJO 10)
SLOW_START_S = {0: 0.12, 4: 0.09, 9: 0.075, 10: 0.075}
APPOGGIATURA_MIN, APPOGGIATURA_MAX = 0.09, 0.30
APPOGGIATURA_SHARE = 0.25
APPOGGIATURA_MAIN_MIN = 0.45   # the main note is at least this long (seconds) to be leaned on
GRACE_GAIN = 0.9                # of the main note's level (clear, not forward)

START, DUR, PITCH, INS, G0, G1, TRACK = range(7)


def _parts(notes):
    parts = defaultdict(list)
    for i, n in enumerate(notes):
        parts[(n[TRACK], n[INS])].append(i)
    for key in parts:
        parts[key].sort(key=lambda i: (notes[i][START], notes[i][PITCH]))
    return parts


def _meets(a, b):
    """Does note a end where note b begins (a little short of it, or running a little into it)?"""
    return -OVERRUN_S <= b[START] - (a[START] + a[DUR]) <= CONTIG_S


def find_graces(notes, overlapped=False, beat_s=None):
    """Grace notes in `notes`: a list of (kind, [grace indices], main index) where kind is
    'acciaccatura' or 'appoggiatura'. `overlapped`: the source (LilyPond 2.6) leaves the grace
    note sounding through its main note."""
    found, taken = [], set()
    # how long a note may be and still be a grace note, from where it stands in the piece's tempo
    def short(n):
        return n[DUR] <= (min(SHORT_MAX_S, GRACE_BEATS * beat_s(n[START])) if beat_s else SHORT_S)
    for key, idx in _parts(notes).items():
        # the top note at each onset: the line a grace note belongs to
        top = {}
        for i in idx:
            t = round(notes[i][START], 4)
            if t not in top or notes[i][PITCH] > notes[top[t]][PITCH]:
                top[t] = i
        line = sorted(top.values(), key=lambda i: notes[i][START])
        for k, g in enumerate(line):
            n = notes[g]
            if g in taken or k + 1 >= len(line):
                continue
            if not short(n):
                # (a LilyPond 2.6 grace note keeps its written length: it is found by where it starts)
                m = notes[line[k + 1]]
                if overlapped and 0.012 < m[START] - n[START] <= OVERLAP_S and n[START] + n[DUR] > m[START] \
                        and abs(m[PITCH] - n[PITCH]) <= 2 and m[PITCH] != n[PITCH] and n[DUR] >= 0.08 \
                        and m[DUR] >= 0.9 * n[DUR] and not (k > 0 and _meets(notes[line[k - 1]], n)
                                                             and notes[line[k - 1]][DUR] < 0.9 * n[DUR]):
                    found.append(('acciaccatura', [g], line[k + 1]))
                    taken.add(g)
                continue
            # the group: this note and the contiguous quick notes after it, then the main note
            group = [g]
            j = k + 1
            while j < len(line) and len(group) <= GROUP_MAX:
                nxt = notes[line[j]]
                last = notes[group[-1]]
                if _meets(last, nxt) and nxt[START] > last[START] + 1e-4 and short(nxt):
                    group.append(line[j]); j += 1
                else:
                    break
            if j >= len(line) or len(group) > GROUP_MAX:
                continue
            # an alternation of two notes (a written trill or mordent) is the composer's own figure
            if len(group) >= 3 and all(notes[group[x]][PITCH] == notes[group[x + 2]][PITCH] for x in range(len(group) - 2)):
                continue
            main = line[j]
            m = notes[main]
            last = notes[group[-1]]
            if m[DUR] < max(MAIN_MIN_S, MAIN_RATIO * last[DUR]) or m[PITCH] == last[PITCH]:
                continue
            contiguous = _meets(last, m) and m[START] > last[START] + 0.012
            smear = (overlapped and len(group) == 1 and 0.012 < m[START] - last[START] <= OVERLAP_S
                     and last[START] + last[DUR] > m[START] and abs(m[PITCH] - last[PITCH]) <= 2
                     and last[DUR] >= 0.08)
            if not (contiguous or smear):
                continue
            # not the tail of a fast run: the note before the group, in this line, is not quick too
            if k > 0 and short(notes[line[k - 1]]) and \
                    _meets(notes[line[k - 1]], n):
                continue
            if any(x in taken for x in group):
                continue
            step = abs(m[PITCH] - last[PITCH]) <= 2
            kind = 'appoggiatura' if (step and m[DUR] >= APPOGGIATURA_MAIN_MIN and len(group) == 1) else 'acciaccatura'
            found.append((kind, group, main))
            taken.update(group)
    return found


def regrace(notes, overlapped=False, clock=None):
    """The notes with every grace note played as one (see the module's text): (notes, counts)."""
    out = [list(n) for n in notes]
    beat_s = None
    if clock is not None:
        def beat_s(t):
            b = max(0.0, clock.beat(t))
            return max(0.05, clock.time(b + 1) - clock.time(b))
    found = find_graces(out, overlapped, beat_s)
    counts = dict(acciaccatura=0, appoggiatura=0, notes=0)
    if not found:
        return out, counts
    parts = _parts(out)
    # the notes before a grace: the line's top notes, to be cut short where a grace needs the time
    line_of = {}
    for key, idx in parts.items():
        for i in idx:
            line_of[i] = key
    for kind, group, main in sorted(found, key=lambda f: out[f[2]][START]):
        m = out[main]
        count = len(group)
        counts[kind] += 1
        counts['notes'] += count
        main_start = m[START]
        main_end = m[START] + m[DUR]
        if kind == 'acciaccatura':
            if count == 1:
                total = min(max(out[group[0]][DUR] if ACCIACCATURA_S[0] <= out[group[0]][DUR] <= ACCIACCATURA_S[1] else 0.055,
                                ACCIACCATURA_S[0]), ACCIACCATURA_S[1])
                total = min(max(total, SLOW_START_S.get(out[group[0]][INS], 0.0)), m[DUR] * 0.4)
            else:
                total = min(GROUP_NOTE_S[1] * count, max(GROUP_NOTE_S[0] * count, 0.1), m[DUR] * 0.4)
                slow = SLOW_START_S.get(out[group[0]][INS], 0.0)
                total = min(max(total, slow * (1 + 0.5 * (count - 1))), 0.25, m[DUR] * 0.4)
            each = total / count
            at = main_start - total
            # the note it follows gives up the time
            for i in parts[line_of[main]]:
                p = out[i]
                if i in group or i == main:
                    continue
                if p[START] < at - 1e-9 and p[START] + p[DUR] > at:
                    # only the line's own earlier note (the top note where it began)
                    tops = [x for x in parts[line_of[main]] if abs(out[x][START] - p[START]) < 1e-4]
                    if i == max(tops, key=lambda x: out[x][PITCH]):
                        p[DUR] = max(0.03, at - p[START])
            for q, g in enumerate(group):
                out[g][START] = at + q * each
                out[g][DUR] = each
        else:
            total = min(max(m[DUR] * APPOGGIATURA_SHARE, APPOGGIATURA_MIN), APPOGGIATURA_MAX, m[DUR] * 0.5)
            g = group[0]
            out[g][START] = main_start
            out[g][DUR] = total
            m[START] = main_start + total
            m[DUR] = main_end - m[START]
        # the grace is heard: GRACE_GAIN of the main note's level, whatever the source gave it
        for g in group:
            out[g][G0] = GRACE_GAIN * m[G0]
            out[g][G1] = GRACE_GAIN * m[G1]
    return sorted(out, key=lambda n: (n[START], n[PITCH])), counts
