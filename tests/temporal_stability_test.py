#!/usr/bin/env python3
"""Automated flicker, morphing, horizon-steadiness and plane-ghosting gate.

Runs tools/temporal_stability_check.jo headless (software-rendered with SLOPPY_SOFT_SCALE=1 so
the full terrain, canopy, crown, aircraft and screen-space outline pipeline runs identically on
CI's GPU-less runners and locally; pass --gpu for a desktop GPU run), computes per-clip temporal
metrics, compares them against tests/baselines/temporal_stability.json, prints a summary table,
and saves the worst frame pairs (prev, cur, warped-diff) as PNGs.

Run locally:
    python3 tests/temporal_stability_test.py
    python3 tests/temporal_stability_test.py --out ~/dev/tmp/aegean-skies/stability-out
    python3 tests/temporal_stability_test.py --gpu
"""
import argparse
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from PIL import Image, ImageChops

try:
    import numpy as np
except ImportError:
    np = None

ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = ROOT / 'tests' / 'baselines' / 'temporal_stability.json'


def cam_basis(yaw, pitch):
    cy, sy = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(pitch), math.sin(pitch)
    fwd = (-sy * cp, sp, -cy * cp)
    right = (cy, 0.0, -sy)
    up = (sy * sp, cp, cy * sp)
    return right, up, fwd


def dot3(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def load_rgb_img(path):
    with Image.open(path) as im:
        return im.convert('RGB')


def load_depth_metres(path):
    with Image.open(path) as im:
        rgb = im.convert('RGB')
        w, h = rgb.size
        raw = rgb.tobytes()
    if np is not None:
        arr = np.frombuffer(raw, dtype=np.uint8).reshape((h, w, 3))
        valid = arr[:, :, 2] >= 128
        q = arr[:, :, 0].astype(np.float64) * 256.0 + arr[:, :, 1].astype(np.float64)
        out = np.where(valid, np.power(2.0, 20.0 * q / 65535.0) - 1.0, 0.0)
        return out
    n = w * h
    out = [0.0] * n
    for i in range(n):
        if raw[i * 3 + 2] >= 128:
            q = raw[i * 3] * 256 + raw[i * 3 + 1]
            out[i] = (2.0 ** (20.0 * q / 65535.0)) - 1.0
    return out


def border_mask(w, h):
    """L-mode mask with 255 inside [1..w-2, 1..h-2] and 0 on the 1px outer border."""
    m = Image.new('L', (w, h), 0)
    m.paste(255, (1, 1, w - 1, h - 1))
    return m


def rotation_coeffs(w, h, src_meta, dst_meta):
    """PIL PERSPECTIVE coefficients mapping dst (x+0.5, y+0.5) -> src (sx+0.5, sy+0.5)."""
    r_s, u_s, f_s = cam_basis(src_meta['yaw'], src_meta['pitch'])
    r_d, u_d, f_d = cam_basis(dst_meta['yaw'], dst_meta['pitch'])
    tan_y = math.tan(math.radians(dst_meta['fov']) * 0.5)
    tan_x = tan_y * (w / h)
    m_rr = dot3(r_s, r_d); m_ru = dot3(r_s, u_d); m_rf = dot3(r_s, f_d)
    m_ur = dot3(u_s, r_d); m_uu = dot3(u_s, u_d); m_uf = dot3(u_s, f_d)
    m_fr = dot3(f_s, r_d); m_fu = dot3(f_s, u_d); m_ff = dot3(f_s, f_d)

    kx = 2.0 * tan_x / w
    ky = -2.0 * tan_y / h
    px_c = -m_rr * tan_x + m_ru * tan_y + m_rf
    py_c = -m_ur * tan_x + m_uu * tan_y + m_uf
    pz_c = -m_fr * tan_x + m_fu * tan_y + m_ff

    inv_kx = w / (2.0 * tan_x)
    inv_ky = -h / (2.0 * tan_y)
    half_w = 0.5 * w
    half_h = 0.5 * h

    a = (inv_kx * m_rr * kx + half_w * m_fr * kx) / pz_c
    b = (inv_kx * m_ru * ky + half_w * m_fu * ky) / pz_c
    c = (inv_kx * px_c + half_w * pz_c) / pz_c
    d = (inv_ky * m_ur * kx + half_h * m_fr * kx) / pz_c
    e = (inv_ky * m_uu * ky + half_h * m_fu * ky) / pz_c
    f = (inv_ky * py_c + half_h * pz_c) / pz_c
    g = (m_fr * kx) / pz_c
    hh = (m_fu * ky) / pz_c
    return (a, b, c, d, e, f, g, hh)


def warp_frame(src_im, src_meta, dst_meta, dst_depth=None, bmask=None):
    """Warp src RGB Image into dst camera frame. Returns (warped_rgb_im, valid_L_im)."""
    w, h = src_im.size
    ex_s, ey_s, ez_s = src_meta['eye']
    ex_d, ey_d, ez_d = dst_meta['eye']
    dx_eye, dy_eye, dz_eye = ex_d - ex_s, ey_d - ey_s, ez_d - ez_s
    has_trans = (dx_eye * dx_eye + dy_eye * dy_eye + dz_eye * dz_eye) > 1e-6

    if not has_trans or dst_depth is None:
        coeffs = rotation_coeffs(w, h, src_meta, dst_meta)
        warped = src_im.transform((w, h), Image.Transform.PERSPECTIVE, coeffs, resample=Image.Resampling.BILINEAR)
        if bmask is None:
            bmask = border_mask(w, h)
        valid = bmask.transform((w, h), Image.Transform.PERSPECTIVE, coeffs, resample=Image.Resampling.NEAREST)
        return warped, valid

    # 3D depth-assisted reprojection for camera translation (flight_300)
    r_s, u_s, f_s = cam_basis(src_meta['yaw'], src_meta['pitch'])
    r_d, u_d, f_d = cam_basis(dst_meta['yaw'], dst_meta['pitch'])
    tan_y = math.tan(math.radians(dst_meta['fov']) * 0.5)
    tan_x = tan_y * (w / h)
    inv_tan_x = 1.0 / tan_x
    inv_tan_y = 1.0 / tan_y
    m_rr = dot3(r_s, r_d); m_ru = dot3(r_s, u_d); m_rf = dot3(r_s, f_d)
    m_ur = dot3(u_s, r_d); m_uu = dot3(u_s, u_d); m_uf = dot3(u_s, f_d)
    m_fr = dot3(f_s, r_d); m_fu = dot3(f_s, u_d); m_ff = dot3(f_s, f_d)
    tr_s = dx_eye * r_s[0] + dy_eye * r_s[1] + dz_eye * r_s[2]
    tu_s = dx_eye * u_s[0] + dy_eye * u_s[1] + dz_eye * u_s[2]
    tf_s = dx_eye * f_s[0] + dy_eye * f_s[1] + dz_eye * f_s[2]

    if np is not None:
        src_arr = np.asarray(src_im, dtype=np.float32)
        xs = (((np.arange(w, dtype=np.float64) + 0.5) / w) * 2.0 - 1.0) * tan_x
        ys = (1.0 - ((np.arange(h, dtype=np.float64) + 0.5) / h) * 2.0) * tan_y
        nx, ny = np.meshgrid(xs, ys)
        px = nx * m_rr + ny * m_ru + m_rf
        py = nx * m_ur + ny * m_uu + m_uf
        pz = nx * m_fr + ny * m_fu + m_ff
        z = dst_depth
        has_z = z > 0.0
        px = np.where(has_z, px * z + tr_s, px)
        py = np.where(has_z, py * z + tu_s, py)
        pz = np.where(has_z, pz * z + tf_s, pz)
        ok = pz > 0.01
        safe_pz = np.where(ok, pz, 1.0)
        sx = (px / safe_pz * inv_tan_x + 1.0) * (0.5 * w) - 0.5
        sy = (1.0 - py / safe_pz * inv_tan_y) * (0.5 * h) - 0.5
        ok = ok & (sx >= 1.0) & (sx <= w - 2.0) & (sy >= 1.0) & (sy <= h - 2.0)
        sx_c = np.clip(sx, 0.0, w - 2.0)
        sy_c = np.clip(sy, 0.0, h - 2.0)
        x0 = sx_c.astype(np.int32)
        y0 = sy_c.astype(np.int32)
        fx = (sx_c - x0)[:, :, None].astype(np.float32)
        fy = (sy_c - y0)[:, :, None].astype(np.float32)
        out = (
            src_arr[y0, x0] * ((1.0 - fx) * (1.0 - fy))
            + src_arr[y0, x0 + 1] * (fx * (1.0 - fy))
            + src_arr[y0 + 1, x0] * ((1.0 - fx) * fy)
            + src_arr[y0 + 1, x0 + 1] * (fx * fy)
        )
        out = np.where(ok[:, :, None], np.clip(np.rint(out), 0, 255), 0).astype(np.uint8)
        valid_arr = np.where(ok, 255, 0).astype(np.uint8)
        return Image.fromarray(out, 'RGB'), Image.fromarray(valid_arr, 'L')

    src = src_im.tobytes()
    warped = bytearray(w * h * 3)
    valid = bytearray(w * h)
    ndc_xs = [(((x + 0.5) / w) * 2.0 - 1.0) * tan_x for x in range(w)]
    ndc_ys = [(1.0 - ((y + 0.5) / h) * 2.0) * tan_y for y in range(h)]
    wm1 = w - 2.0
    hm1 = h - 2.0
    half_w = 0.5 * w
    half_h = 0.5 * h
    for y in range(h):
        ny = ndc_ys[y]
        row_off = y * w
        ry_r = ny * m_ru + m_rf
        ry_u = ny * m_uu + m_uf
        ry_f = ny * m_fu + m_ff
        for x in range(w):
            nx = ndc_xs[x]
            px = nx * m_rr + ry_r
            py = nx * m_ur + ry_u
            pz = nx * m_fr + ry_f
            idx = row_off + x
            z = dst_depth[idx]
            if z > 0.0:
                px = px * z + tr_s
                py = py * z + tu_s
                pz = pz * z + tf_s
            if pz <= 0.01:
                continue
            inv_z = 1.0 / pz
            sx = (px * inv_z * inv_tan_x + 1.0) * half_w - 0.5
            sy = (1.0 - py * inv_z * inv_tan_y) * half_h - 0.5
            if sx < 1.0 or sx > wm1 or sy < 1.0 or sy > hm1:
                continue
            x0 = int(sx)
            y0 = int(sy)
            fx = sx - x0
            fy = sy - y0
            w00 = (1.0 - fx) * (1.0 - fy)
            w10 = fx * (1.0 - fy)
            w01 = (1.0 - fx) * fy
            w11 = fx * fy
            i00 = (y0 * w + x0) * 3
            i10 = i00 + 3
            i01 = i00 + w * 3
            i11 = i01 + 3
            o = idx * 3
            warped[o] = int(src[i00] * w00 + src[i10] * w10 + src[i01] * w01 + src[i11] * w11 + 0.5)
            warped[o + 1] = int(src[i00 + 1] * w00 + src[i10 + 1] * w10 + src[i01 + 1] * w01 + src[i11 + 1] * w11 + 0.5)
            warped[o + 2] = int(src[i00 + 2] * w00 + src[i10 + 2] * w10 + src[i01 + 2] * w01 + src[i11 + 2] * w11 + 0.5)
            valid[idx] = 255
    return Image.frombytes('RGB', (w, h), bytes(warped)), Image.frombytes('L', (w, h), bytes(valid))


def max_channel_img(rgb_im):
    r, g, b = rgb_im.split()
    return ImageChops.lighter(ImageChops.lighter(r, g), b)


def pair_diff_stats(cur_im, pw_im, valid_im):
    """Return (sum_err, count_valid, count_gt12, max_err) using C-accelerated PIL ops."""
    diff = max_channel_img(ImageChops.difference(cur_im, pw_im))
    masked = ImageChops.darker(diff, valid_im)
    vh = valid_im.histogram()
    cnt = vh[255]
    if cnt == 0:
        return 0.0, 0, 0, 0
    dh = masked.histogram()
    s = sum(v * c for v, c in enumerate(dh))
    gt12 = sum(dh[13:])
    mx = 0
    for v in range(255, 0, -1):
        if dh[v]:
            mx = v
            break
    return float(s), cnt, gt12, mx


def triplet_osc_image(pw_im, cur_im, nw_im, valid_im):
    """Per-pixel max-channel sign-flip oscillation image (L-mode), masked by valid_im."""
    d_prev_pos = ImageChops.subtract(cur_im, pw_im)
    d_prev_neg = ImageChops.subtract(pw_im, cur_im)
    d_next_pos = ImageChops.subtract(nw_im, cur_im)
    d_next_neg = ImageChops.subtract(cur_im, nw_im)
    osc_hi = ImageChops.darker(d_prev_pos, d_next_neg)
    osc_lo = ImageChops.darker(d_prev_neg, d_next_pos)
    osc_max = max_channel_img(ImageChops.lighter(osc_hi, osc_lo))
    return ImageChops.darker(osc_max, valid_im)


def hist_stats(l_im, valid_im, gt_thresh):
    cnt = valid_im.histogram()[255]
    if cnt == 0:
        return 0.0, 0, 0
    h = l_im.histogram()
    s = sum(v * c for v, c in enumerate(h))
    gt = sum(h[gt_thresh + 1:])
    return float(s), cnt, gt


def horizon_profile(rgb_im):
    """Return y_top[x] for each column: first row differing from sky color (top-left pixel)."""
    w, h = rgb_im.size
    rgb = rgb_im.tobytes()
    sr, sg, sb = rgb[0], rgb[1], rgb[2]
    tops = [h] * w
    for x in range(w):
        for y in range(h):
            o = (y * w + x) * 3
            if max(abs(rgb[o] - sr), abs(rgb[o + 1] - sg), abs(rgb[o + 2] - sb)) > 8:
                tops[x] = y
                break
    return tops


def reproject_column_x(x, y, w, h, src_meta, dst_meta):
    r_s, u_s, f_s = cam_basis(src_meta['yaw'], src_meta['pitch'])
    r_d, u_d, f_d = cam_basis(dst_meta['yaw'], dst_meta['pitch'])
    tan_y = math.tan(math.radians(dst_meta['fov']) * 0.5)
    tan_x = tan_y * (w / h)
    nx = (((x + 0.5) / w) * 2.0 - 1.0) * tan_x
    ny = (1.0 - ((y + 0.5) / h) * 2.0) * tan_y
    d = (nx * r_d[0] + ny * u_d[0] + f_d[0],
         nx * r_d[1] + ny * u_d[1] + f_d[1],
         nx * r_d[2] + ny * u_d[2] + f_d[2])
    pz = dot3(d, f_s)
    if pz <= 0.01:
        return None
    sx = (dot3(d, r_s) / (pz * tan_x) + 1.0) * 0.5 * w - 0.5
    sy = (1.0 - dot3(d, u_s) / (pz * tan_y)) * 0.5 * h - 0.5
    if sx < 1.0 or sx > w - 2.0 or sy < 1.0 or sy > h - 2.0:
        return None
    return sx, sy


def interp_profile(prof, sx):
    x0 = int(sx)
    f = sx - x0
    return prof[x0] * (1.0 - f) + prof[x0 + 1] * f


def save_worst_pair(out_path, im_a, im_b, diff_scale=6):
    w, h = im_a.size
    diff = ImageChops.difference(im_a, im_b).point(lambda v: min(255, v * diff_scale))
    strip = Image.new('RGB', (w * 3, h))
    strip.paste(im_a, (0, 0))
    strip.paste(im_b, (w, 0))
    strip.paste(diff, (w * 2, 0))
    strip.save(out_path)


def evaluate_clip(clip, items, cap_dir, worst_dir):
    items = sorted(items, key=lambda it: it['index'])
    w, h = items[0]['w'], items[0]['h']
    bmask = border_mask(w, h)
    full_valid = Image.new('L', (w, h), 255)
    frames = []
    depths = []
    offs = []
    masks = []
    for it in items:
        pad = f"{it['index']:03d}"
        frames.append(load_rgb_img(cap_dir / f"{clip}-f{pad}.png"))
        depths.append(load_depth_metres(cap_dir / f"{clip}-d{pad}.png") if it['has_depth'] else None)
        offs.append(load_rgb_img(cap_dir / f"{clip}-off{pad}.png") if it['has_off'] else None)
        masks.append(load_rgb_img(cap_dir / f"{clip}-mask{pad}.png") if it['has_mask'] else None)

    reproj_sum = 0.0
    reproj_gt12 = 0
    reproj_cnt = 0
    worst_pair_err = -1.0
    worst_pair_imgs = None

    flick_sum = 0.0
    flick_gt6 = 0
    flick_cnt = 0
    still_max = 0

    horizon_jitter_sum = 0.0
    horizon_step_sum = 0.0
    horizon_cols = 0
    horizon_flick_sum = 0.0
    horizon_flick_cnt = 0
    off_horizon_flick_sum = 0.0
    off_horizon_flick_cnt = 0
    outline_horizon_px_sum = 0

    groups = {}
    for k, it in enumerate(items):
        groups.setdefault(it['group'], []).append(k)

    for grp, idxs in groups.items():
        # Cache prev-warped frames so pair and triplet loops share the work
        warped_prev = {}
        for j in range(1, len(idxs)):
            i0, i1 = idxs[j - 1], idxs[j]
            if clip == 'still':
                pw, vm = frames[i0], full_valid
            else:
                pw, vm = warp_frame(frames[i0], items[i0], items[i1], depths[i1], bmask)
            warped_prev[j] = (pw, vm)
            pair_sum, pair_n, gt12, mx = pair_diff_stats(frames[i1], pw, vm)
            reproj_gt12 += gt12
            if mx > still_max:
                still_max = mx
            if pair_n > 0:
                reproj_sum += pair_sum
                reproj_cnt += pair_n
                mean_e = pair_sum / pair_n
                if mean_e > worst_pair_err:
                    worst_pair_err = mean_e
                    worst_pair_imgs = (pw, frames[i1])

        profiles = None
        if clip == 'horizon_woods':
            profiles = {idx: horizon_profile(frames[idx]) for idx in idxs}

        for j in range(1, len(idxs) - 1):
            i0, i1, i2 = idxs[j - 1], idxs[j], idxs[j + 1]
            pw, v1 = warped_prev[j]
            if clip == 'still':
                nw, v2 = frames[i2], full_valid
            else:
                nw, v2 = warp_frame(frames[i2], items[i2], items[i1], depths[i1], bmask)
            vboth = ImageChops.darker(v1, v2)
            osc_im = triplet_osc_image(pw, frames[i1], nw, vboth)
            fs, fc, fgt = hist_stats(osc_im, vboth, 6)
            flick_sum += fs
            flick_cnt += fc
            flick_gt6 += fgt

            if clip == 'horizon_woods':
                p0, p1, p2 = profiles[i0], profiles[i1], profiles[i2]
                for x in range(8, w - 8):
                    y1 = p1[x]
                    if y1 <= 2 or y1 >= h - 4:
                        continue
                    r0 = reproject_column_x(x, y1, w, h, items[i0], items[i1])
                    r2 = reproject_column_x(x, y1, w, h, items[i2], items[i1])
                    if r0 is None or r2 is None:
                        continue
                    y0 = interp_profile(p0, r0[0]) + (y1 - r0[1])
                    y2 = interp_profile(p2, r2[0]) + (y1 - r2[1])
                    d1 = y1 - y0
                    d2 = y2 - y1
                    horizon_step_sum += abs(d1)
                    if d1 * d2 < 0.0:
                        horizon_jitter_sum += min(abs(d1), abs(d2))
                    horizon_cols += 1

                # Horizon band mask (+/- 10 px around horizon profile)
                band_bytes = bytearray(w * h)
                for x in range(w):
                    lo = max(0, p1[x] - 10)
                    hi = min(h - 1, p1[x] + 10)
                    for y in range(lo, hi + 1):
                        band_bytes[y * w + x] = 255
                band_im = Image.frombytes('L', (w, h), bytes(band_bytes))
                hv = ImageChops.darker(vboth, band_im)
                hs, hc, _ = hist_stats(ImageChops.darker(osc_im, band_im), hv, 6)
                horizon_flick_sum += hs
                horizon_flick_cnt += hc

                if offs[i0] is not None and offs[i1] is not None and offs[i2] is not None:
                    opw, ov1 = warp_frame(offs[i0], items[i0], items[i1], None, bmask)
                    onw, ov2 = warp_frame(offs[i2], items[i2], items[i1], None, bmask)
                    ovb = ImageChops.darker(ImageChops.darker(ov1, ov2), band_im)
                    oosc = triplet_osc_image(opw, offs[i1], onw, ovb)
                    os_sum, os_cnt, _ = hist_stats(oosc, ovb, 6)
                    off_horizon_flick_sum += os_sum
                    off_horizon_flick_cnt += os_cnt

    if clip == 'horizon_woods':
        for k in range(len(items)):
            if offs[k] is None:
                continue
            d = max_channel_img(ImageChops.difference(frames[k], offs[k]))
            outline_horizon_px_sum += sum(d.histogram()[7:])

    plane_ghost_px = 0
    plane_ghost_max = 0
    worst_ghost_imgs = None
    if clip == 'chase_dusk':
        for k in range(len(items)):
            if offs[k] is None or masks[k] is None:
                continue
            a = frames[k].tobytes()
            b = offs[k].tobytes()
            m = masks[k].tobytes()
            on_plane = bytearray(w * h)
            halo = bytearray(w * h)
            for p in range(w * h):
                o = p * 3
                if max(m[o], m[o + 1], m[o + 2]) > 4:
                    on_plane[p] = 1
            for y in range(h):
                for x in range(w):
                    if on_plane[y * w + x]:
                        halo[y * w + x] = 1
                        if y == 0 or not on_plane[(y - 1) * w + x]:
                            for dy in range(1, 9):
                                if y - dy >= 0:
                                    halo[(y - dy) * w + x] = 1
            g_px = 0
            g_max = 0
            for y in range(h):
                for x in range(w):
                    p = y * w + x
                    if not halo[p]:
                        continue
                    o = p * 3
                    e = max(abs(a[o] - b[o]), abs(a[o + 1] - b[o + 1]), abs(a[o + 2] - b[o + 2]))
                    if e <= 6:
                        continue
                    if on_plane[p]:
                        g_px += 1
                        if e > g_max:
                            g_max = e
                    else:
                        has_bg_ridge = False
                        # At 19:00 dusk, a wooded hill-over-hill ridge step in `b` can be 5-7 RGB levels.
                        for dy in range(1, 9):
                            yy = y + dy
                            if yy >= h or on_plane[yy * w + x]:
                                break
                            oo = (yy * w + x) * 3
                            oo_up = ((yy - 1) * w + x) * 3
                            if max(abs(b[oo] - b[oo_up]), abs(b[oo + 1] - b[oo_up + 1]), abs(b[oo + 2] - b[oo_up + 2])) > 5:
                                has_bg_ridge = True
                                break
                        if not has_bg_ridge:
                            g_px += 1
                            if e > g_max:
                                g_max = e
            if g_px > plane_ghost_px or (g_px == plane_ghost_px and g_max > plane_ghost_max):
                plane_ghost_px = g_px
                plane_ghost_max = g_max
                worst_ghost_imgs = (offs[k], frames[k])

    if worst_dir is not None:
        if clip == 'chase_dusk' and worst_ghost_imgs is not None:
            save_worst_pair(worst_dir / f'worst-{clip}.png', worst_ghost_imgs[0], worst_ghost_imgs[1])
        elif worst_pair_imgs is not None:
            save_worst_pair(worst_dir / f'worst-{clip}.png', worst_pair_imgs[0], worst_pair_imgs[1])

    metrics = {
        'flicker_mean': round(flick_sum / max(flick_cnt, 1), 4),
        'flicker_pct': round(100.0 * flick_gt6 / max(flick_cnt, 1), 3),
        'reproj_mae': round(reproj_sum / max(reproj_cnt, 1), 4),
        'reproj_pct': round(100.0 * reproj_gt12 / max(reproj_cnt, 1), 3),
    }
    if clip == 'still':
        metrics['still_max_diff'] = int(still_max)
    if clip == 'horizon_woods':
        h_fl = horizon_flick_sum / max(horizon_flick_cnt, 1)
        off_fl = off_horizon_flick_sum / max(off_horizon_flick_cnt, 1)
        metrics['horizon_jitter_px'] = round(horizon_jitter_sum / max(horizon_cols, 1), 4)
        metrics['horizon_step_px'] = round(horizon_step_sum / max(horizon_cols, 1), 4)
        metrics['horizon_flicker'] = round(h_fl, 4)
        metrics['outline_flicker_added'] = round(max(0.0, h_fl - off_fl), 4)
        metrics['outline_pixels_mean'] = round(outline_horizon_px_sum / max(len(items), 1), 1)
    if clip == 'chase_dusk':
        metrics['plane_ghost_px'] = int(plane_ghost_px)
        metrics['plane_ghost_max'] = int(plane_ghost_max)
    return metrics


def make_thresholds(results):
    """Build baseline thresholds from a clean reference run with documented margins."""
    out = {}
    for clip, m in results.items():
        t = {}
        if clip == 'still':
            t['still_max_diff'] = 0
            t['flicker_mean'] = 0.0
            t['flicker_pct'] = 0.0
            t['reproj_mae'] = 0.0
            t['reproj_pct'] = 0.0
        else:
            t['flicker_mean'] = round(max(m['flicker_mean'] * 1.35 + 0.12, 0.25), 4)
            t['flicker_pct'] = round(max(m['flicker_pct'] * 1.40 + 0.35, 0.50), 3)
            t['reproj_mae'] = round(max(m['reproj_mae'] * 1.35 + 0.30, 0.60), 4)
            t['reproj_pct'] = round(max(m['reproj_pct'] * 1.40 + 0.60, 1.00), 3)
        if clip == 'horizon_woods':
            t['horizon_jitter_px'] = round(max(m['horizon_jitter_px'] * 1.35 + 0.06, 0.15), 4)
            t['horizon_step_px'] = round(max(m['horizon_step_px'] * 1.35 + 0.10, 0.25), 4)
            t['horizon_flicker'] = round(max(m['horizon_flicker'] * 1.35 + 0.15, 0.35), 4)
            t['outline_flicker_added'] = round(max(m['outline_flicker_added'] * 1.35 + 0.04, 0.20), 4)
            t['min_outline_pixels'] = max(20.0, round(m['outline_pixels_mean'] * 0.4, 1))
        if clip == 'chase_dusk':
            t['plane_ghost_px'] = max(4, int(m['plane_ghost_px']) + 4)
            t['plane_ghost_max'] = max(12, int(m['plane_ghost_max']) + 8)
        out[clip] = t
    return out


def run_capture(repo_root, cap_dir, use_gpu=False, clips=None):
    cap_dir.mkdir(parents=True, exist_ok=True)
    env = {k: v for k, v in os.environ.items() if k not in ('DISPLAY', 'WAYLAND_DISPLAY', 'AEGEAN_OUTLINE', 'AEGEAN_PAINTED_LAYERS')}
    env.update(
        SLOPPY_NO_AUDIO='1',
        SLOPPY_THREADS='1',
        SLOPPY_WINDOW='384x216',
        SLOPPY_FRAMES='500',
        SLOPPY_SCREENSHOT=str(cap_dir / 'last.png'),
        AEGEAN_STABILITY_OUT=str(cap_dir),
    )
    if use_gpu:
        env.pop('SLOPPY_SOFTWARE', None)
        env.pop('SLOPPY_SOFT_SCALE', None)
    else:
        env['SLOPPY_SOFTWARE'] = '1'
        env['SLOPPY_SOFT_SCALE'] = '1'
    if clips:
        env['AEGEAN_STABILITY_CLIPS'] = clips
    done = subprocess.run(
        ['sloppy', '--release', 'tools/temporal_stability_check.jo'],
        cwd=repo_root,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if done.returncode != 0:
        print(done.stdout[-3000:], file=sys.stderr)
        raise RuntimeError(f'temporal_stability_check.jo failed with exit code {done.returncode}')
    return done.stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', type=str, default=os.environ.get('AEGEAN_STABILITY_OUT', ''))
    ap.add_argument('--from-dir', type=str, default='')
    ap.add_argument('--repo', type=str, default=str(ROOT))
    ap.add_argument('--clips', type=str, default='')
    ap.add_argument('--gpu', action='store_true', default=os.environ.get('AEGEAN_STABILITY_GPU') == '1')
    ap.add_argument('--write-baseline', action='store_true')
    ap.add_argument('--no-fail', action='store_true')
    args = ap.parse_args()

    tmp_ctx = None
    if args.from_dir:
        cap_dir = Path(args.from_dir)
        worst_dir = Path(args.out) if args.out else cap_dir / 'worst'
    elif args.out:
        cap_dir = Path(args.out)
        worst_dir = cap_dir / 'worst'
    else:
        scratch = Path.home() / 'dev/tmp/aegean-skies/temporal-stability'
        if scratch.parent.exists():
            scratch.mkdir(parents=True, exist_ok=True)
            tmp_ctx = tempfile.TemporaryDirectory(dir=scratch)
        else:
            tmp_ctx = tempfile.TemporaryDirectory(prefix='aegean-stability-')
        cap_dir = Path(tmp_ctx.name)
        worst_dir = cap_dir / 'worst'

    worst_dir.mkdir(parents=True, exist_ok=True)

    if not args.from_dir:
        run_capture(Path(args.repo), cap_dir, use_gpu=args.gpu, clips=args.clips)

    manifest = json.loads((cap_dir / 'manifest.json').read_text())
    by_clip = {}
    for it in manifest:
        by_clip.setdefault(it['clip'], []).append(it)

    results = {}
    for clip in ('still', 'pan_150', 'pan_800', 'flight_300', 'chase_dusk', 'horizon_woods'):
        if clip in by_clip:
            results[clip] = evaluate_clip(clip, by_clip[clip], cap_dir, worst_dir)

    if args.write_baseline:
        data = {
            'mode': 'gpu' if args.gpu else 'software',
            'size': [manifest[0]['w'], manifest[0]['h']],
            'reference': results,
            'thresholds': make_thresholds(results),
        }
        BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
        BASELINE_PATH.write_text(json.dumps(data, indent=2) + '\n')
        print(f'Wrote baseline to {BASELINE_PATH}')

    baseline = json.loads(BASELINE_PATH.read_text()) if BASELINE_PATH.exists() else {'thresholds': {}}
    thresholds = baseline.get('thresholds', {})

    print(f"\n{'CLIP':<15} {'METRIC':<23} {'VALUE':>9} {'LIMIT':>9} {'STATUS':>8}")
    print('-' * 68)
    failures = []
    for clip, m in results.items():
        lim = thresholds.get(clip, {})
        for k, v in m.items():
            if k == 'outline_pixels_mean':
                lo = lim.get('min_outline_pixels')
                if lo is not None:
                    ok = v >= lo
                    status = 'OK' if ok else 'FAIL'
                    print(f'{clip:<15} {k:<23} {v:>9.2f} {f">={lo:.1f}":>9} {status:>8}')
                    if not ok:
                        failures.append(f'{clip}.{k}={v} < {lo}')
                else:
                    print(f'{clip:<15} {k:<23} {v:>9.2f} {"-":>9} {"INFO":>8}')
                continue
            hi = lim.get(k)
            if hi is None:
                print(f'{clip:<15} {k:<23} {v:>9.4f} {"-":>9} {"INFO":>8}')
            else:
                ok = v <= hi
                status = 'OK' if ok else 'FAIL'
                print(f'{clip:<15} {k:<23} {v:>9.4f} {hi:>9.4f} {status:>8}')
                if not ok:
                    failures.append(f'{clip}.{k}={v} > {hi}')

    (worst_dir / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
    print(f'\nWorst frame pairs saved in: {worst_dir}')

    if failures and not args.no_fail:
        print('\nTEMPORAL STABILITY FAIL:')
        for f in failures:
            print('  -', f)
        if tmp_ctx is not None:
            keep = Path.home() / 'dev/tmp/aegean-skies/temporal-stability-fail'
            if keep.parent.exists():
                keep.mkdir(parents=True, exist_ok=True)
                for p in worst_dir.glob('*.png'):
                    (keep / p.name).write_bytes(p.read_bytes())
                (keep / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
                print(f'Copied failure worst-frame pairs to: {keep}')
        sys.exit(1)

    print('\nTEMPORAL STABILITY PASS')


if __name__ == '__main__':
    main()
