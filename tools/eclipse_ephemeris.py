#!/usr/bin/env python3
"""The real solar and lunar eclipses seen over the game's map, from the game's start (7 June 1926).

Writes src/eclipse_table.jo: for each eclipse, a small model the game evaluates at any minute and
any place on the map (src/eclipse.jo). Plain Python, no libraries.

The Moon: the main periodic terms of the ELP-2000/82 lunar theory as Meeus tabulates them
(Astronomical Algorithms, ch. 47; about 10" in longitude). The Sun: Meeus ch. 25 (about 0.01 deg at
worst, a few arcseconds usually). Topocentric positions for observers on the map, which the world
places on the real Aegean (MAP_LAT, MAP_LON at the world's origin; x east, z south, km).

  python3 tools/eclipse_ephemeris.py            # write src/eclipse_table.jo
  python3 tools/eclipse_ephemeris.py --check    # compare with well-known modern eclipses
"""
import math, sys, datetime, os

RAD = math.pi / 180.0
MAP_LAT = 38.3          # the world's origin on the real Aegean (degrees north, east)
MAP_LON = 25.2
MAP_HALF_X = 250.0      # the map's half size, km (x east, z south)
MAP_HALF_Z = 200.0
ZONE_HOURS = 2.0        # the game's clock: Eastern European Time (Greece from 1916)
START = datetime.datetime(1926, 6, 7, 7, 30)   # the world's minute 0 in UT (09:30 local)
END_YEAR = 1961
EARTH_R = 6378.14
MOON_R = 1737.4
SUN_R = 696000.0
AU = 149597870.7

def jd_of(dt):
    a = (14 - dt.month) // 12
    y = dt.year + 4800 - a
    m = dt.month + 12 * a - 3
    jdn = dt.day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045
    return jdn - 0.5 + (dt.hour + dt.minute / 60.0 + dt.second / 3600.0) / 24.0

def delta_t(year):
    # seconds, Espenak & Meeus polynomials for 1920-1986
    if year < 1941:
        t = year - 1920
        return 21.20 + 0.84493 * t - 0.076100 * t * t + 0.0020936 * t ** 3
    if year < 1961:
        t = year - 1950
        return 29.07 + 0.407 * t - t * t / 233 + t ** 3 / 2547
    if year < 1986:
        t = year - 1975
        return 45.45 + 1.067 * t - t * t / 260 - t ** 3 / 718
    if year < 2005:
        t = year - 2000
        return 63.86 + 0.3345 * t - 0.060374 * t * t + 0.0017275 * t ** 3 + 0.000651814 * t ** 4 + 0.00002373599 * t ** 5
    t = year - 2000
    return 62.92 + 0.32217 * t + 0.005589 * t * t

# Meeus table 47.A: D, M, M', F, sigma l (1e-6 deg), sigma r (1e-3 km)
LR = [
    (0,0,1,0,6288774,-20905355),(2,0,-1,0,1274027,-3699111),(2,0,0,0,658314,-2955968),(0,0,2,0,213618,-569925),
    (0,1,0,0,-185116,48888),(0,0,0,2,-114332,-3149),(2,0,-2,0,58793,246158),(2,-1,-1,0,57066,-152138),
    (2,0,1,0,53322,-170733),(2,-1,0,0,45758,-204586),(0,1,-1,0,-40923,-129620),(1,0,0,0,-34720,108743),
    (0,1,1,0,-30383,104755),(2,0,0,-2,15327,10321),(0,0,1,2,-12528,0),(0,0,1,-2,10980,79661),
    (4,0,-1,0,10675,-34782),(0,0,3,0,10034,-23210),(4,0,-2,0,8548,-21636),(2,1,-1,0,-7888,24208),
    (2,1,0,0,-6766,30824),(1,0,-1,0,-5163,-8379),(1,1,0,0,4987,-16675),(2,-1,1,0,4036,-12831),
    (2,0,2,0,3994,-10445),(4,0,0,0,3861,-11650),(2,0,-3,0,3665,14403),(0,1,-2,0,-2689,-7003),
    (2,0,-1,2,-2602,0),(2,-1,-2,0,2390,10056),(1,0,1,0,-2348,6322),(2,-2,0,0,2236,-9884),
    (0,1,2,0,-2120,5751),(0,2,0,0,-2069,0),(2,-2,-1,0,2048,-4950),(2,0,1,-2,-1773,4130),
    (2,0,0,2,-1595,0),(4,-1,-1,0,1215,-3958),(0,0,2,2,-1110,0),(3,0,-1,0,-892,3258),
    (2,1,1,0,-810,2616),(4,-1,-2,0,759,-1897),(0,2,-1,0,-713,-2117),(2,2,-1,0,-700,2354),
    (2,1,-2,0,691,0),(2,-1,0,-2,596,0),(4,0,1,0,549,-1423),(0,0,4,0,537,-1117),
    (4,-1,0,0,520,-1571),(1,0,-2,0,-487,-1739),(2,1,0,-2,-399,0),(0,0,2,-2,-381,-4421),
    (1,1,1,0,351,0),(3,0,-2,0,-340,0),(4,0,-3,0,330,0),(2,-1,2,0,327,0),
    (0,2,1,0,-323,1165),(1,1,-1,0,299,0),(2,0,3,0,294,0),(2,0,-1,-2,0,8752),
]
# Meeus table 47.B: D, M, M', F, sigma b (1e-6 deg)
B = [
    (0,0,0,1,5128122),(0,0,1,1,280602),(0,0,1,-1,277693),(2,0,0,-1,173237),(2,0,-1,1,55413),
    (2,0,-1,-1,46271),(2,0,0,1,32573),(0,0,2,1,17198),(2,0,1,-1,9266),(0,0,2,-1,8822),
    (2,-1,0,-1,8216),(2,0,-2,-1,4324),(2,0,1,1,4200),(2,1,0,-1,-3359),(2,-1,-1,1,2463),
    (2,-1,0,1,2211),(2,-1,-1,-1,2065),(0,1,-1,-1,-1870),(4,0,-1,-1,1828),(0,1,0,1,-1794),
    (0,0,0,3,-1749),(0,1,-1,1,-1565),(1,0,0,1,-1491),(0,1,1,1,-1475),(0,1,1,-1,-1410),
    (0,1,0,-1,-1344),(1,0,0,-1,-1335),(0,0,3,1,1107),(4,0,0,-1,1021),(4,0,-1,1,833),
    (0,0,1,-3,777),(4,0,-2,1,671),(2,0,0,-3,607),(2,0,2,-1,596),(2,-1,1,-1,491),
    (2,0,-2,1,-451),(0,0,3,-1,439),(2,0,2,1,422),(2,0,-3,-1,421),(2,1,-1,1,-366),
    (2,1,0,1,-351),(4,0,0,1,331),(2,-1,1,1,315),(2,-2,0,-1,302),(0,0,1,3,-283),
    (2,1,1,-1,-229),(1,1,0,-1,223),(1,1,0,1,223),(0,1,-2,-1,-220),(2,1,-1,-1,-220),
    (1,0,1,1,-185),(2,-1,-2,-1,181),(0,1,2,1,-177),(4,0,-2,-1,176),(4,-1,-1,-1,166),
    (1,0,1,-1,-164),(4,0,1,-1,132),(1,0,-1,-1,-119),(4,-1,0,-1,115),(2,-2,0,1,107),
]

def moon_ecliptic(jde):
    """Geocentric ecliptic longitude, latitude (deg, mean equinox of date) and distance (km)."""
    T = (jde - 2451545.0) / 36525.0
    Lp = 218.3164477 + 481267.88123421 * T - 0.0015786 * T * T + T ** 3 / 538841 - T ** 4 / 65194000
    D = 297.8501921 + 445267.1114034 * T - 0.0018819 * T * T + T ** 3 / 545868 - T ** 4 / 113065000
    M = 357.5291092 + 35999.0502909 * T - 0.0001536 * T * T + T ** 3 / 24490000
    Mp = 134.9633964 + 477198.8675055 * T + 0.0087414 * T * T + T ** 3 / 69699 - T ** 4 / 14712000
    F = 93.2720950 + 483202.0175233 * T - 0.0036539 * T * T - T ** 3 / 3526000 + T ** 4 / 863310000
    A1 = 119.75 + 131.849 * T
    A2 = 53.09 + 479264.290 * T
    A3 = 313.45 + 481266.484 * T
    E = 1 - 0.002516 * T - 0.0000074 * T * T
    sl = sr = sb = 0.0
    for d, m, mp, f, l, r in LR:
        arg = (d * D + m * M + mp * Mp + f * F) * RAD
        e = E ** abs(m)
        sl += l * e * math.sin(arg)
        sr += r * e * math.cos(arg)
    for d, m, mp, f, b in B:
        arg = (d * D + m * M + mp * Mp + f * F) * RAD
        sb += b * (E ** abs(m)) * math.sin(arg)
    sl += 3958 * math.sin(A1 * RAD) + 1962 * math.sin((Lp - F) * RAD) + 318 * math.sin(A2 * RAD)
    sb += (-2235 * math.sin(Lp * RAD) + 382 * math.sin(A3 * RAD) + 175 * math.sin((A1 - F) * RAD)
           + 175 * math.sin((A1 + F) * RAD) + 127 * math.sin((Lp - Mp) * RAD) - 115 * math.sin((Lp + Mp) * RAD))
    return (Lp + sl / 1e6) % 360.0, sb / 1e6, 385000.56 + sr / 1000.0

def sun_ecliptic(jde):
    """Apparent geocentric longitude (deg, mean equinox of date, with aberration) and distance (km)."""
    T = (jde - 2451545.0) / 36525.0
    L0 = 280.46646 + 36000.76983 * T + 0.0003032 * T * T
    M = 357.52911 + 35999.05029 * T - 0.0001537 * T * T
    e = 0.016708634 - 0.000042037 * T - 0.0000001267 * T * T
    C = ((1.914602 - 0.004817 * T - 0.000014 * T * T) * math.sin(M * RAD)
         + (0.019993 - 0.000101 * T) * math.sin(2 * M * RAD) + 0.000289 * math.sin(3 * M * RAD))
    nu = M + C
    R = 1.000001018 * (1 - e * e) / (1 + e * math.cos(nu * RAD))
    lon = L0 + C - 20.4898 / 3600.0 / R
    return lon % 360.0, R * AU

def obliquity(jde):
    T = (jde - 2451545.0) / 36525.0
    return (23.0 + 26.0 / 60 + 21.448 / 3600 - 46.8150 / 3600 * T) * RAD

def ecl_to_eq(lon, lat, dist, eps):
    l = lon * RAD; b = lat * RAD
    x = math.cos(b) * math.cos(l); y = math.cos(b) * math.sin(l); z = math.sin(b)
    return (dist * x, dist * (y * math.cos(eps) - z * math.sin(eps)), dist * (y * math.sin(eps) + z * math.cos(eps)))

def gmst(jd_ut):
    T = (jd_ut - 2451545.0) / 36525.0
    return (280.46061837 + 360.98564736629 * (jd_ut - 2451545.0) + 0.000387933 * T * T - T ** 3 / 38710000) % 360.0

def sub(a, b): return (a[0] - b[0], a[1] - b[1], a[2] - b[2])
def add(a, b): return (a[0] + b[0], a[1] + b[1], a[2] + b[2])
def mul(a, k): return (a[0] * k, a[1] * k, a[2] * k)
def dot(a, b): return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
def cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def norm(a): return math.sqrt(dot(a, a))
def unit(a): n = norm(a); return (a[0] / n, a[1] / n, a[2] / n)

class Bodies:
    """Sun and Moon at a moment (UT julian day): geocentric equatorial vectors (km) and the sidereal angle."""
    def __init__(self, jd_ut):
        year = 2000 + (jd_ut - 2451545.0) / 365.25
        jde = jd_ut + delta_t(year) / 86400.0
        eps = obliquity(jde)
        ml, mb, md = moon_ecliptic(jde)
        sl, sd = sun_ecliptic(jde)
        self.moon = ecl_to_eq(ml, mb, md, eps)
        self.sun = ecl_to_eq(sl, 0.0, sd, eps)
        self.theta = gmst(jd_ut) * RAD

def site(lat, lon, theta):
    """An observer's geocentric vector (km) and their zenith and north directions."""
    phi = lat * RAD
    u = math.atan(0.99664719 * math.tan(phi))
    rs = 0.99664719 * math.sin(u); rc = math.cos(u)
    lst = theta + lon * RAD
    pos = (EARTH_R * rc * math.cos(lst), EARTH_R * rc * math.sin(lst), EARTH_R * rs)
    up = (math.cos(phi) * math.cos(lst), math.cos(phi) * math.sin(lst), math.sin(phi))
    return pos, up

def map_site(x_km, z_km):
    lat = MAP_LAT - z_km / 111.13
    lon = MAP_LON + x_km / (111.32 * math.cos(MAP_LAT * RAD))
    return lat, lon

def overlap(d, r1, r2):
    """The share of disc 1 (radius r1) covered by disc 2 (radius r2), centres d apart."""
    if d >= r1 + r2: return 0.0
    if d <= abs(r2 - r1): return 1.0 if r2 >= r1 else (r2 * r2) / (r1 * r1)
    a1 = math.acos(max(-1.0, min(1.0, (d * d + r1 * r1 - r2 * r2) / (2 * d * r1))))
    a2 = math.acos(max(-1.0, min(1.0, (d * d + r2 * r2 - r1 * r1) / (2 * d * r2))))
    area = r1 * r1 * (a1 - math.sin(2 * a1) / 2) + r2 * r2 * (a2 - math.sin(2 * a2) / 2)
    return area / (math.pi * r1 * r1)

def solar_local(b, lat, lon):
    """Local circumstances: the Moon's offset from the Sun (in the Sun's radii: x to the viewer's right
    as they face the Sun, y toward the zenith), the Moon's radius over the Sun's, the Sun's height (deg)."""
    pos, up = site(lat, lon, b.theta)
    s = sub(b.sun, pos); m = sub(b.moon, pos)
    sh = unit(s); mh = unit(m)
    rs = math.asin(SUN_R / norm(s)); rm = math.asin(MOON_R / norm(m))
    right = unit(cross(sh, up)); upp = cross(right, sh)
    # gnomonic offset on the plane at the Sun
    k = 1.0 / dot(mh, sh)
    ox = dot(mh, right) * k; oy = dot(mh, upp) * k
    alt = math.asin(dot(sh, up)) / RAD
    return ox / rs, oy / rs, rm / rs, alt, rs

def gamma_of(b):
    """The shadow axis's least distance from the Earth's centre (Earth radii), signed by its side."""
    d = unit(sub(b.moon, b.sun))
    m = b.moon
    perp = sub(m, mul(d, dot(m, d)))
    return norm(perp) / EARTH_R * (1 if perp[2] >= 0 else -1), perp

def axis_point(b):
    """Where the shadow axis meets the Earth (lat, lon) or None."""
    d = unit(sub(b.moon, b.sun)); m = b.moon
    # solve |m + t d| = R (sphere, flattening ignored for the check)
    bq = 2 * dot(m, d); c = dot(m, m) - EARTH_R ** 2
    disc = bq * bq - 4 * c
    if disc < 0: return None
    t = (-bq - math.sqrt(disc)) / 2
    p = add(m, mul(d, t))
    lat = math.asin(p[2] / EARTH_R) / RAD
    lon = (math.atan2(p[1], p[0]) - b.theta) / RAD
    lon = (lon + 540) % 360 - 180
    # geodetic latitude, near enough
    lat = math.atan(math.tan(lat * RAD) / 0.99330562) / RAD
    return lat, lon

def new_moons(jd0, jd1):
    """Julian days (UT, to a minute) of new and full moons between jd0 and jd1: (jd, 'new'|'full')."""
    out = []
    jd = jd0
    def elong(j):
        b = Bodies(j)
        sl = math.atan2(b.sun[1], b.sun[0]); ml = math.atan2(b.moon[1], b.moon[0])
        # (right ascension difference is fine for finding syzygies roughly; refined later by separation)
        return (ml - sl) % (2 * math.pi)
    prev = elong(jd)
    while jd < jd1:
        nxt = jd + 0.25
        e = elong(nxt)
        if prev > 5.5 and e < 0.8: out.append((nxt, 'new'))
        if prev < math.pi <= e: out.append((nxt, 'full'))
        prev = e; jd = nxt
    return out

def minimise(f, a, b, steps=60):
    best = None
    for i in range(steps + 1):
        t = a + (b - a) * i / steps
        v = f(t)
        if best is None or v < best[1]: best = (t, v)
    lo = max(a, best[0] - (b - a) / steps); hi = min(b, best[0] + (b - a) / steps)
    for _ in range(60):
        m1 = lo + (hi - lo) / 3; m2 = hi - (hi - lo) / 3
        if f(m1) < f(m2): hi = m2
        else: lo = m1
    t = (lo + hi) / 2
    return t, f(t)

def greatest(jd):
    """Greatest eclipse: the moment the shadow axis passes nearest the Earth's centre."""
    t, g = minimise(lambda j: abs(gamma_of(Bodies(j))[0]), jd - 0.4, jd + 0.4)
    return t, gamma_of(Bodies(t))[0]

def check():
    known = [  # (name, UT of greatest eclipse (TD minus delta T taken loosely), gamma, lat, lon)
        ("1999-08-11", datetime.datetime(1999, 8, 11, 11, 2), 0.5062, 45.1, 24.3),
        ("2006-03-29", datetime.datetime(2006, 3, 29, 10, 10), 0.3843, 23.2, 16.7),
        ("2017-08-21", datetime.datetime(2017, 8, 21, 18, 25), 0.4367, 37.0, -87.7),
        ("2024-04-08", datetime.datetime(2024, 4, 8, 18, 17), 0.3431, 25.3, -104.1),
        ("1936-06-19", datetime.datetime(1936, 6, 19, 5, 20), 0.5389, 56.1, 105.2),
    ]
    for name, dt, g_ref, lat_ref, lon_ref in known:
        t, g = greatest(jd_of(dt))
        p = axis_point(Bodies(t))
        when = START + datetime.timedelta(days=t - jd_of(START))
        print(f"{name}: greatest {when:%H:%M:%S} UT gamma {g:+.4f} (ref {g_ref:.4f}) at {p[0]:.1f}N {p[1]:.1f}E (ref {lat_ref}, {lon_ref})")

def fit(rows, cols):
    """Least squares: rows of (features..., value) -> coefficients."""
    n = cols
    A = [[0.0] * n for _ in range(n)]; y = [0.0] * n
    for r in rows:
        f, v = r[:n], r[n]
        for i in range(n):
            y[i] += f[i] * v
            for j in range(n): A[i][j] += f[i] * f[j]
    # Gauss-Jordan
    for i in range(n):
        p = max(range(i, n), key=lambda k: abs(A[k][i]))
        A[i], A[p] = A[p], A[i]; y[i], y[p] = y[p], y[i]
        piv = A[i][i]
        for j in range(n): A[i][j] /= piv
        y[i] /= piv
        for k in range(n):
            if k != i and A[k][i] != 0.0:
                fct = A[k][i]
                for j in range(n): A[k][j] -= fct * A[i][j]
                y[k] -= fct * y[i]
    return y

def minute_of(jd):
    return (jd - jd_of(START)) * 1440.0

def solar_features(t, x, z):
    # t in hours from the reference, x and z in hundreds of km
    return [1.0, t, t * t, t ** 3, t ** 4, x, z, x * t, z * t, x * t * t, z * t * t, x * x, z * z, x * z]

GRID = [(-250, -200), (0, -200), (250, -200), (-250, 0), (0, 0), (250, 0), (-250, 200), (0, 200), (250, 200),
        (-125, -100), (125, -100), (-125, 100), (125, 100)]

def solar_eclipse(jd_new):
    """A new moon's eclipse over the map, or None."""
    tg, g = greatest(jd_new)
    if abs(g) > 1.6: return None
    # the window: when any of the map's points sees a bite with the Sun up
    seen = []
    j = tg - 0.25
    while j < tg + 0.25:
        b = Bodies(j)
        best = 0.0
        for x, z in GRID:
            lat, lon = map_site(x, z)
            ox, oy, k, alt, rs = solar_local(b, lat, lon)
            if alt < -1.2: continue
            best = max(best, overlap(math.hypot(ox, oy), 1.0, k))
        if best > 0.0: seen.append((j, best))
        j += 2.0 / 1440.0
    if not seen: return None
    j0 = seen[0][0] - 4.0 / 1440.0; j1 = seen[-1][0] + 4.0 / 1440.0
    ref = (j0 + j1) / 2
    hours = (j1 - j0) * 24.0
    rows_x = []; rows_y = []; rows_k = []
    steps = 40
    for i in range(steps + 1):
        j = j0 + (j1 - j0) * i / steps
        b = Bodies(j)
        t = (j - ref) * 24.0
        for gx in range(-2, 3):
            for gz in range(-2, 3):
                x = gx * MAP_HALF_X / 2; z = gz * MAP_HALF_Z / 2
                lat, lon = map_site(x, z)
                ox, oy, k, alt, rs = solar_local(b, lat, lon)
                f = solar_features(t, x / 100.0, z / 100.0)
                rows_x.append(f + [ox]); rows_y.append(f + [oy]); rows_k.append(f[:1] + [k])
    n = len(solar_features(0, 0, 0))
    cx = fit(rows_x, n); cy = fit(rows_y, n)
    k = sum(r[1] for r in rows_k) / len(rows_k)
    # the fit's worst error (in the Sun's radii) and the map's best view
    err = 0.0; best = (0.0, 0, 0, 0, 0)
    for i in range(steps * 3 + 1):
        j = j0 + (j1 - j0) * i / (steps * 3)
        b = Bodies(j)
        t = (j - ref) * 24.0
        for x, z in GRID:
            lat, lon = map_site(x, z)
            ox, oy, kk, alt, rs = solar_local(b, lat, lon)
            f = solar_features(t, x / 100.0, z / 100.0)
            px = sum(a * c for a, c in zip(f, cx)); py = sum(a * c for a, c in zip(f, cy))
            err = max(err, math.hypot(px - ox, py - oy))
            if alt > -1.0:
                o = overlap(math.hypot(ox, oy), 1.0, kk)
                if o > best[0]: best = (o, x, z, j, alt)
    if best[0] < 0.005: return None
    when = START + datetime.timedelta(days=ref - jd_of(START))
    return dict(kind='solar', ref=ref, minute=minute_of(ref), hours=hours, cx=cx, cy=cy, k=k, gamma=g,
                err=err, best=best, date=when, greatest=tg)

def lunar_eclipse(jd_full):
    """A full moon's eclipse seen from the map, or None. The Moon's offset from the shadow's centre in the
    Moon's radii (x to the viewer's right facing the Moon, y toward the zenith at the map's origin), and
    the umbra's and the penumbra's radii in the Moon's radii."""
    def sep(j):
        b = Bodies(j)
        anti = mul(unit(b.sun), -1.0)
        return math.acos(max(-1.0, min(1.0, dot(unit(b.moon), anti))))
    tg, s = minimise(sep, jd_full - 0.5, jd_full + 0.5)
    b = Bodies(tg)
    pm = math.asin(EARTH_R / norm(b.moon)); ps = math.asin(EARTH_R / norm(b.sun)); ss = math.asin(SUN_R / norm(b.sun))
    rm = math.asin(MOON_R / norm(b.moon))
    pen = 1.02 * (0.998340 * pm + ss + ps); umb = 1.02 * (0.998340 * pm - ss + ps)
    if s > pen + rm: return None
    # the span of the penumbral eclipse
    def inside(j): return sep(j) < pen + rm
    j0 = tg
    while inside(j0): j0 -= 2.0 / 1440.0
    j1 = tg
    while inside(j1): j1 += 2.0 / 1440.0
    # seen from the map: the Moon up at some part of it
    lat, lon = map_site(0, 0)
    visible = False
    rows_x = []; rows_y = []
    steps = 40
    ref = (j0 + j1) / 2
    for i in range(steps + 1):
        j = j0 + (j1 - j0) * i / steps
        b = Bodies(j)
        pos, up = site(lat, lon, b.theta)
        mh = unit(sub(b.moon, pos))
        if math.asin(dot(mh, up)) / RAD > 0.0: visible = True
        # geocentric offset of the Moon from the shadow's centre, in the zenith frame at the map
        mg = unit(b.moon); anti = mul(unit(b.sun), -1.0)
        right = unit(cross(mg, up)); upp = cross(right, mg)
        kk = 1.0 / dot(anti, mg)
        # (the shadow's centre seen from the Moon's place: offset of the Moon = -(offset of the shadow))
        ox = -dot(anti, right) * kk; oy = -dot(anti, upp) * kk
        t = (j - ref) * 24.0
        f = [1.0, t, t * t]
        rows_x.append(f + [ox / rm]); rows_y.append(f + [oy / rm])
    if not visible: return None
    umag = (umb + rm - s) / (2 * rm)
    if umag < -0.45: return None        # (a penumbral eclipse too slight to see)
    cx = fit(rows_x, 3); cy = fit(rows_y, 3)
    umag = (umb + rm - s) / (2 * rm)
    when = START + datetime.timedelta(days=ref - jd_of(START))
    return dict(kind='lunar', ref=ref, minute=minute_of(ref), hours=(j1 - j0) * 24.0, cx=cx, cy=cy,
                umb=umb / rm, pen=pen / rm, umag=umag, date=when, greatest=tg)

def main():
    if '--check' in sys.argv:
        check()
        return
    jd0 = jd_of(START) - 1; jd1 = jd_of(datetime.datetime(END_YEAR, 1, 1))
    found = []
    for jd, kind in new_moons(jd0, jd1):
        e = solar_eclipse(jd) if kind == 'new' else lunar_eclipse(jd)
        if e: found.append(e)
    found.sort(key=lambda e: e['ref'])
    lines = []
    lines.append("# The real eclipses seen over the map from the game's start, written by tools/eclipse_ephemeris.py")
    lines.append("# (do not edit: run it again). Each row: the reference minute of the world's clock, the span")
    lines.append("# either side of it (minutes), and the model src/eclipse.jo evaluates:")
    lines.append("#   solar: the Moon's offset from the Sun in the Sun's radii (x to the right facing the Sun, y up),")
    lines.append("#          x and y each a polynomial in t (hours from the reference) and the place (x east, z")
    lines.append("#          south, hundreds of km): 1 t t2 t3 t4 x z xt zt xt2 zt2 xx zz xz; then the Moon's radius over the Sun's.")
    lines.append("#   lunar: the Moon's offset from the Earth's shadow in the Moon's radii, 1 t t2 for x and y; then")
    lines.append("#          the umbra's and the penumbra's radii in the Moon's radii.")
    lines.append("")
    lines.append("struct EclipseRow:")
    lines.append("    solar: bool")
    lines.append("    minute: f64                     # the reference minute (world clock)")
    lines.append("    span: f64                       # minutes either side of it with any eclipse on the map")
    lines.append("    cx: f64[]")
    lines.append("    cy: f64[]")
    lines.append("    k: f64                          # solar: the Moon's radius over the Sun's; lunar: the umbra's radius")
    lines.append("    pen: f64 = 0.0                  # lunar: the penumbra's radius (Moon radii)")
    lines.append("    seed: int = 0                   # the corona's own pattern")
    lines.append("    label: str = \"\"")
    lines.append("")
    lines.append("ECLIPSE_ROWS = [")
    for i, e in enumerate(found):
        lt = e['date'] + datetime.timedelta(hours=ZONE_HOURS)
        if e['kind'] == 'solar':
            o, bx, bz, bj, alt = e['best']
            gl = START + datetime.timedelta(days=bj - jd_of(START), hours=ZONE_HOURS)
            kind = 'total' if e['k'] > 1.0 and o >= 0.9999 else ('annular' if o > 0.0 and e['k'] < 1.0 and o > (e['k'] ** 2) * 0.999 else 'partial')
            label = f"{lt:%d %b %Y} solar, {kind} at best on the map ({o*100:.0f}% of the Sun at {gl:%H:%M}, sun {alt:.0f} deg up)"
            cx = ", ".join(f"{c:.6g}" for c in e['cx']); cy = ", ".join(f"{c:.6g}" for c in e['cy'])
            lines.append(f"    EclipseRow(true, {e['minute']:.2f}, {e['hours']*30:.1f}, [{cx}], [{cy}], {e['k']:.6f}, seed = {i * 7919 % 9973}, label = \"{label}\"),")
            print(label, f"best at x {bx} z {bz} km;", f"fit err {e['err']:.4f} sun radii, gamma {e['gamma']:+.3f}")
        else:
            label = f"{lt:%d %b %Y} lunar, umbral magnitude {e['umag']:.2f}"
            cx = ", ".join(f"{c:.6g}" for c in e['cx']); cy = ", ".join(f"{c:.6g}" for c in e['cy'])
            lines.append(f"    EclipseRow(false, {e['minute']:.2f}, {e['hours']*30:.1f}, [{cx}], [{cy}], {e['umb']:.5f}, pen = {e['pen']:.5f}, seed = {i * 7919 % 9973}, label = \"{label}\"),")
            print(label)
    lines.append("]")
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src', 'eclipse_table.jo')
    with open(out, 'w') as fh:
        fh.write("\n".join(lines) + "\n")
    print(f"wrote {len(found)} eclipses to {os.path.normpath(out)}")

if __name__ == '__main__':
    main()
