"""WORLD-style speech analysis, written independently in numpy for the radio announcer.

The ideas follow M. Morise's WORLD vocoder (DIO, StoneMask, CheapTrick, band aperiodicity);
no WORLD source is copied. Everything works on mono float signals at RATE Hz and returns
5 ms frame tracks:

  f0       Hz, 0 where unvoiced                        (dio + stonemask)
  envelope power spectral envelope on the FFT grid      (cheaptrick)
  ap       aperiodicity 0..1 in BANDS                   (band_aperiodicity)

and the compact mel-cepstral form the game stores (envelope_to_mcep / mcep_to_log_power).
"""
import numpy as np
from scipy.signal import butter, sosfiltfilt, resample_poly

RATE = 16000
FRAME = 0.005
FFT = 1024
BANDS = [(0, 600), (600, 1200), (1200, 2200), (2200, 4000), (4000, 8000)]
ALPHA = 0.42           # all-pass warping that approximates the mel scale at 16 kHz
ORDER = 24             # mel-cepstral order (25 coefficients)
UNVOICED_F0 = 500.0    # analysis window pitch for unvoiced frames, as WORLD does


def frame_times(n_samples, fs=RATE):
    return np.arange(int(n_samples / fs / FRAME) + 1) * FRAME


# ---------------------------------------------------------------- F0: DIO-style candidates
def _events(y, fs):
    """Four interval series of a near-sinusoid: rising/falling zero crossings, peaks, dips.
    Returns a list of (times, intervals) pairs."""
    out = []
    d = np.diff(y)
    for s in (y, -y, d, -d):
        idx = np.nonzero((s[:-1] < 0) & (s[1:] >= 0))[0]
        if len(idx) < 3:
            out.append((np.zeros(0), np.zeros(0)))
            continue
        frac = s[idx] / (s[idx] - s[idx + 1])           # linear interpolation of the crossing
        t = (idx + frac) / fs
        out.append(((t[1:] + t[:-1]) * 0.5, np.diff(t)))
    return out


def dio(x, fs=RATE, floor=70.0, ceil=420.0, per_octave=3):
    """Our DIO-like estimator. Each band low-passed below a boundary frequency holds a near
    sinusoid when the fundamental lies just under the boundary; there the four interval series
    agree. Returns (times, f0 candidates per frame, score) — score is the relative spread."""
    q = 4
    y = resample_poly(x, 1, q)
    fsd = fs / q
    times = frame_times(len(x), fs)
    nb = int(np.ceil(np.log2(ceil * 2 / floor) * per_octave)) + 1
    bounds = floor * 2.0 ** (np.arange(nb) / per_octave)
    best = np.zeros(len(times))
    score = np.full(len(times), np.inf)
    for b in bounds:
        if b >= fsd / 2:
            break
        sos = butter(4, b / (fsd / 2), output='sos')
        hp = butter(2, max(30.0, b / 4) / (fsd / 2), btype='high', output='sos')
        yb = sosfiltfilt(hp, sosfiltfilt(sos, y))
        f0s = []
        for t, iv in _events(yb, fsd):
            if len(t) < 2:
                f0s.append(np.zeros(len(times)))
                continue
            f0s.append(1.0 / np.interp(times, t, iv, left=1e9, right=1e9))
        f0s = np.array(f0s)
        mean = f0s.mean(0)
        spread = f0s.std(0) / np.maximum(mean, 1e-9)
        ok = (mean > b / 2.2) & (mean < b) & (mean >= floor) & (mean <= ceil)
        better = ok & (spread < score)
        best[better] = mean[better]
        score[better] = spread[better]
    return times, best, score


def _harmonic_spectrum(x, fs, centre, f0, harmonics):
    """Complex amplitudes at k*f0 for a Blackman window of 3 periods (direct DFT)."""
    half = int(round(1.5 * fs / f0))
    n = np.arange(-half, half + 1)
    i = np.clip(int(round(centre * fs)) + n, 0, len(x) - 1)
    w = np.blackman(len(n))
    seg = x[i] * w
    k = np.arange(1, harmonics + 1)[:, None]
    ph = np.exp(-2j * np.pi * k * f0 * n[None, :] / fs)
    return (ph * seg[None, :]).sum(1)


def stonemask(x, times, f0, fs=RATE, harmonics=6):
    """Refine F0 by the instantaneous frequency of the harmonics (phase advance over one
    sample), weighted by harmonic amplitude. Two passes."""
    out = f0.copy()
    for _ in range(2):
        for j in np.nonzero(out > 0)[0]:
            f = out[j]
            h = min(harmonics, int(3500 / f))
            a = _harmonic_spectrum(x, fs, times[j], f, h)
            b = _harmonic_spectrum(x, fs, times[j] + 1.0 / fs, f, h)
            inst = np.angle(b * np.conj(a)) * fs / (2 * np.pi)   # offset from k*f0 in Hz
            k = np.arange(1, h + 1)
            est = (k * f + inst) / k
            wgt = np.abs(a)
            g = (est * wgt).sum() / max(wgt.sum(), 1e-12)
            if abs(g - f) < 0.15 * f:
                out[j] = g
    return out


def fix_f0(times, f0, score, x, fs=RATE, threshold=0.06, min_voiced=0.03):
    """Voicing from interval agreement and energy, octave/jump repair, removal of short islands."""
    hop = int(FRAME * fs)
    energy = np.array([np.mean(x[max(0, int(t * fs) - hop * 2):int(t * fs) + hop * 2] ** 2) for t in times])
    loud = energy > np.percentile(energy[energy > 0], 30) * 0.05 if np.any(energy > 0) else energy > 0
    v = (score < threshold) & loud & (f0 > 0)
    f = np.where(v, f0, 0.0)
    # median-filter jumps: a frame far from the local voiced median is unreliable
    out = f.copy()
    for j in np.nonzero(f > 0)[0]:
        nb = f[max(0, j - 6):j + 7]
        nb = nb[nb > 0]
        m = np.median(nb)
        r = f[j] / m
        if 1.8 < r < 2.2:
            out[j] = f[j] / 2
        elif 0.45 < r < 0.55:
            out[j] = f[j] * 2
        elif abs(np.log2(r)) > 0.25:
            out[j] = 0
    # drop voiced islands shorter than min_voiced
    n = int(round(min_voiced / FRAME))
    j = 0
    while j < len(out):
        if out[j] > 0:
            k = j
            while k < len(out) and out[k] > 0:
                k += 1
            if k - j < n:
                out[j:k] = 0
            j = k
        else:
            j += 1
    return out


def f0_track(x, fs=RATE):
    times, cand, score = dio(x, fs)
    f0 = fix_f0(times, cand, score, x, fs)
    return times, stonemask(x, times, f0, fs)


# ---------------------------------------------------------------- envelope: CheapTrick-style
def _smooth_linear(p, width_hz, fs, n_fft):
    """Rectangular smoothing of a half spectrum over width_hz, mirrored at both ends."""
    df = fs / n_fft
    w = width_hz / df
    half = len(p)
    pad = int(np.ceil(w)) + 2
    ext = np.concatenate([p[pad:0:-1], p, p[-2:-pad - 2:-1]])
    c = np.concatenate([[0.0], np.cumsum(ext)])
    pos = np.arange(half) + pad
    lo = pos - w / 2 + 0.5
    hi = pos + w / 2 + 0.5
    ci = lambda u: np.interp(u, np.arange(len(c)), c)
    return (ci(hi) - ci(lo)) / w


def cheaptrick_frame(x, centre, f0, fs=RATE, n_fft=FFT, q1=-0.15):
    if f0 <= 0:
        f0 = UNVOICED_F0
    half = int(round(1.5 * fs / f0))
    n = np.arange(-half, half + 1)
    i = np.clip(int(round(centre * fs)) + n, 0, len(x) - 1)
    w = 0.5 * np.cos(np.pi * n / (1.5 * fs) * f0) + 0.5
    w = w / np.sqrt(np.sum(w * w))
    seg = x[i] * w
    seg = seg - w * (seg.sum() / w.sum())
    buf = np.zeros(n_fft)
    m = min(len(seg), n_fft)
    buf[:m] = seg[:m]
    p = np.abs(np.fft.rfft(buf)) ** 2
    # 0..F0 correction: fold the region below F0 back onto itself
    freqs = np.arange(len(p)) * fs / n_fft
    low = freqs < f0
    p[low] = p[low] + np.interp(f0 - freqs[low], freqs, p)
    p = _smooth_linear(p, f0 * 2.0 / 3.0, fs, n_fft)
    p = np.maximum(p, 1e-14)
    # cepstral smoothing with peak recovery
    cep = np.fft.irfft(np.log(p))
    qf = np.arange(len(cep)) / fs
    qf = np.minimum(qf, (len(cep) - np.arange(len(cep))) / fs)
    lift = np.ones_like(qf)
    nz = qf > 0
    lift[nz] = np.sin(np.pi * f0 * qf[nz]) / (np.pi * f0 * qf[nz])
    comp = (1 - 2 * q1) + 2 * q1 * np.cos(2 * np.pi * qf * f0)
    return np.exp(np.fft.rfft(cep * lift * comp).real)


def cheaptrick(x, times, f0, fs=RATE):
    return np.array([cheaptrick_frame(x, t, f, fs) for t, f in zip(times, f0)])


# ---------------------------------------------------------------- band aperiodicity
def band_aperiodicity(x, times, f0, fs=RATE):
    """Per band: 1 - normalised autocorrelation at the pitch lag of the band-passed signal over
    about three periods (and of its envelope for bands above 2 kHz, the larger periodicity
    wins). Equals noise power / total power for a periodic+noise mixture. Unvoiced frames: 1."""
    bands = []
    for lo, hi in BANDS:
        if lo == 0:
            sos = butter(4, hi / (fs / 2), output='sos')
        elif hi >= fs / 2:
            sos = butter(4, lo / (fs / 2), btype='high', output='sos')
        else:
            sos = butter(3, [lo / (fs / 2), hi / (fs / 2)], btype='band', output='sos')
        y = sosfiltfilt(sos, x)
        env = None
        if lo >= 2000:
            env = sosfiltfilt(butter(2, 800 / (fs / 2), output='sos'), np.abs(y))
            env = env - sosfiltfilt(butter(1, 60 / (fs / 2), output='sos'), env)
        bands.append((y, env))
    ap = np.ones((len(times), len(BANDS)))
    for j, (t, f) in enumerate(zip(times, f0)):
        if f <= 0:
            continue
        lag = fs / f
        span = max(int(2.5 * lag), int(0.02 * fs))
        c = int(round(t * fs))
        a0 = c - span // 2
        if a0 < 0 or a0 + span + int(lag) + 2 >= len(x):
            continue
        n = np.arange(a0, a0 + span)
        for b, (y, env) in enumerate(bands):
            best = 0.0
            for s in (y, env):
                if s is None:
                    continue
                u = s[n]
                li = int(np.floor(lag))
                fr = lag - li
                v = s[n + li] * (1 - fr) + s[n + li + 1] * fr
                den = np.sqrt(np.dot(u, u) * np.dot(v, v))
                if den > 0:
                    best = max(best, np.dot(u, v) / den)
            ap[j, b] = np.clip(1.0 - best, 0.001, 1.0)
    return ap


# ---------------------------------------------------------------- mel-cepstrum
def warp(omega, alpha=ALPHA):
    """All-pass frequency warping omega -> warped omega."""
    return omega + 2 * np.arctan(alpha * np.sin(omega) / (1 - alpha * np.cos(omega)))


def _mcep_basis(n_bins, order=ORDER, alpha=ALPHA):
    om = np.linspace(0, np.pi, n_bins)
    wt = warp(om, alpha)
    return np.cos(np.outer(wt, np.arange(order + 1)))


_FIT = {}


def envelope_to_mcep(env, order=ORDER, alpha=ALPHA):
    """Least-squares fit of log power on the warped-cosine basis; points are spaced uniformly
    in warped frequency so the fit weights the mel scale, not linear hertz."""
    n_bins = env.shape[-1]
    key = (n_bins, order, alpha)
    if key not in _FIT:
        wt = np.linspace(0, np.pi, 256)
        om = warp(wt, -alpha)                       # inverse warp: uniform in warped frequency
        idx = om / np.pi * (n_bins - 1)
        basis = np.cos(np.outer(wt, np.arange(order + 1)))
        _FIT[key] = (idx, np.linalg.pinv(basis))
    idx, pinv = _FIT[key]
    logp = np.log(np.maximum(env, 1e-14))
    sampled = np.array([np.interp(idx, np.arange(n_bins), row) for row in np.atleast_2d(logp)])
    out = sampled @ pinv.T
    return out if env.ndim > 1 else out[0]


def mcep_to_log_power(mcep, n_bins=FFT // 2 + 1, alpha=ALPHA):
    order = mcep.shape[-1] - 1
    return mcep @ _mcep_basis(n_bins, order, alpha).T


def analyse(x, fs=RATE):
    """Full analysis of one stretch of speech."""
    times, f0 = f0_track(x, fs)
    env = cheaptrick(x, times, f0, fs)
    ap = band_aperiodicity(x, times, f0, fs)
    return dict(times=times, f0=f0, env=env, mcep=envelope_to_mcep(env), ap=ap)
