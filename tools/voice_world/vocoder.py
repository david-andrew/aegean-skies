"""Reference model of the in-game announcer synthesizer (src/voice_synth.jo), in numpy.

WORLD's source/filter model in time-domain form: a fractionally placed impulse train (amplitude
sqrt(T0), the same power as unit white noise) and white noise are mixed per band by the
aperiodicity, then shaped by an all-pole lattice filter fitted to the frame's mel-cepstral
envelope. Used offline to check the analysis by copy synthesis and to test the game's port.
"""
import numpy as np
from scipy.signal import lfilter
from world_analysis import RATE, FRAME, ALPHA, BANDS, warp

GRID = 128          # linear-frequency points for envelope -> autocorrelation
LPC = 24            # all-pole order
SUB = 16            # samples between interpolated filter updates (1 ms)
CROSS = [b[1] for b in BANDS[:-1]]


def tables(order_m, alpha=ALPHA, grid=GRID, lpc=LPC):
    om = (np.arange(grid) + 0.5) * np.pi / grid
    basis = np.cos(np.outer(warp(om, alpha), np.arange(order_m + 1)))   # grid x M
    cosk = np.cos(np.outer(np.arange(lpc + 1), om)) / grid              # p+1 x grid
    return basis, cosk


def levinson(r, p):
    """Autocorrelation -> reflection coefficients k[1..p] and prediction error.
    A(z) = 1 + sum a_i z^-i ; k_i is the last coefficient of the order-i predictor."""
    a = np.zeros(p + 1)
    a[0] = 1.0
    k = np.zeros(p)
    e = r[0] * (1 + 1e-9) + 1e-30
    for i in range(1, p + 1):
        acc = r[i] + np.dot(a[1:i], r[i - 1:0:-1])
        ki = -acc / e
        ki = max(-0.9995, min(0.9995, ki))
        a_new = a.copy()
        a_new[1:i] = a[1:i] + ki * a[i - 1:0:-1]
        a_new[i] = ki
        a = a_new
        k[i - 1] = ki
        e *= (1 - ki * ki)
    return k, e, a


def frame_filter(mcep, basis, cosk, lpc=LPC):
    logp = basis @ mcep
    p = np.exp(np.clip(logp, -60, 60))
    r = cosk @ p
    k, e, _ = levinson(r, lpc)
    return k, e


def _biquad_lp(hz):
    w = 2 * np.pi * hz / RATE
    c = np.cos(w)
    a = np.sin(w) / (2 * 0.70710678)
    d = 1 + a
    b0 = (1 - c) / 2 / d
    return np.array([b0, 2 * b0, b0, -2 * c / d, (1 - a) / d])


def synthesize(f0, mcep, ap, seed=1, lpc=LPC, sinc_taps=8, phases=32):
    """f0 [n] Hz (0 unvoiced), mcep [n, M+1], ap [n, bands] -> float signal at RATE."""
    n = len(f0)
    hop = int(FRAME * RATE)
    total = (n - 1) * hop
    basis, cosk = tables(mcep.shape[1] - 1)
    ks = np.zeros((n, lpc))
    gains = np.zeros(n)
    for j in range(n):
        k, e = frame_filter(mcep[j], basis, cosk, lpc)
        ks[j] = k
        gains[j] = np.sqrt(max(e, 0))
    # fractional-delay impulse kernels (Hann-windowed sinc)
    taps = np.arange(-sinc_taps // 2 + 1, sinc_taps // 2 + 1)
    kern = []
    for ph in range(phases):
        fr = ph / phases
        t = taps - fr
        kern.append(np.sinc(t) * (0.5 + 0.5 * np.cos(np.pi * t / (sinc_taps / 2 + 1))))
    kern = np.array(kern)
    rng = np.random.default_rng(seed)
    pulse = np.zeros(total + sinc_taps * 2)
    voiced = np.zeros(total)
    # pulse placement by integrating f0 per sample
    t = np.arange(total) / hop
    fi = np.interp(t, np.arange(n), f0)
    vi = np.interp(t, np.arange(n), (f0 > 0).astype(float))
    phase = 0.0
    for s in range(total):
        if fi[s] <= 0 or vi[s] < 0.5:
            phase = 0.999 if phase < 0.999 else phase
            continue
        voiced[s] = 1
        step = fi[s] / RATE
        if phase + step >= 1.0:
            frac = (1.0 - phase) / step          # fraction of this sample before the pulse
            phase = phase + step - 1.0
            pos = s + frac
            ip = int(np.floor(pos))
            ph = int((pos - ip) * phases) % phases
            amp = np.sqrt(RATE / fi[s])
            lo = ip + taps[0] + sinc_taps
            pulse[lo:lo + sinc_taps] += amp * kern[ph]
        else:
            phase += step
    pulse = pulse[sinc_taps:sinc_taps + total]
    noise = rng.standard_normal(total)
    # band mixing with telescoping low-pass crossovers
    lps = [_biquad_lp(h) for h in CROSS]

    def lp_run(x, c):
        return lfilter(c[:3], [1.0, c[3], c[4]], x)
    lp_p = [np.zeros(total)] + [lp_run(pulse, c) for c in lps] + [pulse]
    lp_n = [np.zeros(total)] + [lp_run(noise, c) for c in lps] + [noise]
    api = np.array([np.interp(t, np.arange(n), ap[:, b]) for b in range(ap.shape[1])])
    exc = np.zeros(total)
    for b in range(ap.shape[1]):
        a_b = np.clip(api[b], 0, 1)
        exc += np.sqrt(1 - a_b) * (lp_p[b + 1] - lp_p[b]) * voiced
        # unvoiced frames: all noise regardless of the stored value
        exc += np.where(voiced > 0, np.sqrt(a_b), 1.0) * (lp_n[b + 1] - lp_n[b])
    # lattice all-pole with interpolated reflection coefficients and gain
    y = np.zeros(total)
    b = np.zeros(lpc + 1)
    for s0 in range(0, total, SUB):
        u = (s0 + SUB / 2) / hop
        j = min(int(u), n - 2)
        fr = u - j
        k = ks[j] * (1 - fr) + ks[j + 1] * fr
        g = gains[j] * (1 - fr) + gains[j + 1] * fr
        for s in range(s0, min(s0 + SUB, total)):
            f = exc[s] * g
            for i in range(lpc, 0, -1):
                f = f - k[i - 1] * b[i - 1]
                b[i] = b[i - 1] + k[i - 1] * f
            b[0] = f
            y[s] = f
    return y
