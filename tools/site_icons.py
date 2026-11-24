#!/usr/bin/env python3
"""Draw the site's favicon and app icons: a floatplane against a low sun over the sea.

Everything is geometry written here (polygons in a 512 x 512 box), emitted as SVG and rasterised
with Pillow at several sizes, so the vector and the bitmaps are the same drawing. No outside art.

  site_icons.py OUTDIR      writes favicon.svg, favicon.ico (16, 32, 48), apple-touch-icon.png (180),
                            icon-192.png and icon-512.png
  site_icons.py --sheet F   also writes a contact sheet of the sizes to F (for looking at)

The favicon (SVG, and the 16 and 32 px sizes of the .ico) is a bolder drawing, since it is seen tiny: a bigger
plane with a thicker wing and float, a bigger sun, no halo. The square icons (apple, 192, 512) fill the whole square, the content inside the central 80 % (the
safe zone a maskable icon needs); the favicon has rounded corners.
"""
import argparse
import math
import os
import sys

SIZE = 512
SKY_TOP = (0x1b, 0x4a, 0x68)
SKY_LOW = (0xf2, 0xa9, 0x5c)
SEA_TOP = (0x2e, 0x82, 0x96)
SEA_LOW = (0x15, 0x45, 0x5c)
SUN = (0xff, 0xe9, 0xb0)
HALO = (0xff, 0xcf, 0x7a)
PLANE = (0x12, 0x20, 0x2b)
GLINT = (0xff, 0xe2, 0xa0)
HORIZON = 336
SUN_AT = (292, 238, 108)  # x, y, radius


def mix(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def hexc(c):
    return "#%02x%02x%02x" % c


def ellipse(cx, cy, rx, ry, n=48):
    return [(cx + rx * math.cos(2 * math.pi * k / n), cy + ry * math.sin(2 * math.pi * k / n)) for k in range(n)]


def rotate(points, about, angle):
    s, c = math.sin(angle), math.cos(angle)
    ax, ay = about
    return [(ax + (x - ax) * c - (y - ay) * s, ay + (x - ax) * s + (y - ay) * c) for x, y in points]


def plane_parts(bold=False):
    """The floatplane, flying to the right and climbing a little: a list of polygons.
    bold: for the 16 and 32 px icons, larger, with the wing and float thickened so they survive."""
    cx, cy = 256, 232
    parts = []
    # fuselage: a long tapering body, nose to the right
    body = [(112, 214), (170, 212), (300, 202), (372, 214), (404, 232), (372, 254),
            (300, 262), (170, 250), (112, 236)]
    parts.append(body)
    # fin and tailplane
    parts.append([(112, 214), (150, 208), (138, 158), (116, 160)])
    parts.append([(116, 226), (186, 224), (186, 238), (112, 238)])
    # the wing, high above the body, on two struts
    parts.append([(214, 170), (352, 164), (352, 186), (214, 192)])
    parts.append([(250, 190), (262, 190), (276, 212), (262, 212)])
    parts.append([(310, 186), (322, 186), (330, 206), (318, 206)])
    # one float under the body on two struts
    parts.append([(204, 276), (366, 276), (384, 292), (196, 292)])
    parts.append([(236, 252), (248, 252), (250, 278), (238, 278)])
    parts.append([(318, 254), (330, 254), (332, 278), (320, 278)])
    # the propeller disc, edge on
    parts.append(ellipse(412, 232, 9, 46, 24))
    if bold:
        k = 1.28
        parts = [[(cx + (x - cx) * k, cy + (y - cy) * k) for x, y in p] for p in parts]
        parts.append([(214 - 20, 160), (352 + 20, 150), (352 + 20, 190), (214 - 20, 200)])
        parts.append([(196 - 24, 270), (384 + 24, 270), (384 + 24, 300), (196 - 24, 300)])
    return [rotate(p, (cx, cy), math.radians(-7)) for p in parts]


def glints():
    """Short bars of sun on the water, under the sun, widening toward the viewer."""
    sx = SUN_AT[0]
    return [(sx - 54, 354, 108, 11), (sx - 78, 384, 156, 12), (sx - 40, 416, 80, 11), (sx - 62, 442, 124, 10)]


def svg(bold=False):
    sx, sy, sr = SUN_AT
    if bold:
        sr = 140
    out = []
    w = out.append
    w('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d">' % (SIZE, SIZE, SIZE, SIZE))
    w('<defs>')
    w('<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="%s"/><stop offset="1" stop-color="%s"/></linearGradient>' % (hexc(SKY_TOP), hexc(SKY_LOW)))
    w('<linearGradient id="sea" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="%s"/><stop offset="1" stop-color="%s"/></linearGradient>' % (hexc(SEA_TOP), hexc(SEA_LOW)))
    w('<clipPath id="r"><rect width="%d" height="%d" rx="%d"/></clipPath>' % (SIZE, SIZE, 64 if bold else 96))
    w('</defs>')
    w('<g clip-path="url(#r)">')
    w('<rect width="%d" height="%d" fill="url(#sky)"/>' % (SIZE, HORIZON + 1))
    if not bold:
        w('<circle cx="%d" cy="%d" r="%d" fill="%s" fill-opacity="0.35"/>' % (sx, sy, sr + 52, hexc(HALO)))
    w('<circle cx="%d" cy="%d" r="%d" fill="%s"/>' % (sx, sy, sr, hexc(SUN)))
    w('<rect y="%d" width="%d" height="%d" fill="url(#sea)"/>' % (HORIZON, SIZE, SIZE - HORIZON))
    for x, y, bw, bh in (glints()[:2] if not bold else [(sx - 70, 372, 140, 22)]):
        w('<rect x="%d" y="%d" width="%d" height="%d" rx="%d" fill="%s" fill-opacity="0.85"/>' % (x, y, bw, bh, bh // 2, hexc(GLINT)))
    for p in plane_parts(bold):
        w('<polygon points="%s" fill="%s"/>' % (" ".join("%.1f,%.1f" % q for q in p), hexc(PLANE)))
    w('</g></svg>')
    return "\n".join(out) + "\n"


def raster(px, rounded, bold=False):
    """The icon at px x px with Pillow, drawn at 4x and reduced."""
    from PIL import Image, ImageDraw
    k = 4
    big = px * k
    f = big / SIZE
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for y in range(big):
        v = y / f
        if v < HORIZON:
            c = mix(SKY_TOP, SKY_LOW, v / HORIZON)
        else:
            c = mix(SEA_TOP, SEA_LOW, (v - HORIZON) / (SIZE - HORIZON))
        d.line([(0, y), (big, y)], fill=c + (255,))
    sx, sy, sr = SUN_AT
    if bold:
        sr = 140
    layer = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    r = (sr + 52) * f
    if not bold:
        ld.ellipse([sx * f - r, sy * f - r, sx * f + r, sy * f + r], fill=HALO + (89,))
    ld.rectangle([0, HORIZON * f, big, big], fill=(0, 0, 0, 0))
    img = Image.alpha_composite(img, layer)
    d = ImageDraw.Draw(img)
    r = sr * f
    # the sun sets behind the horizon line: the sea is drawn over its foot
    sun = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    ImageDraw.Draw(sun).ellipse([sx * f - r, sy * f - r, sx * f + r, sy * f + r], fill=SUN + (255,))
    img = Image.alpha_composite(img, sun)
    d = ImageDraw.Draw(img)
    for y in range(int(HORIZON * f), big):
        c = mix(SEA_TOP, SEA_LOW, (y / f - HORIZON) / (SIZE - HORIZON))
        d.line([(0, y), (big, y)], fill=c + (255,))
    for x, y, bw, bh in (glints()[:2] if not bold else [(sx - 70, 372, 140, 22)]):
        glint = Image.new("RGBA", (big, big), (0, 0, 0, 0))
        ImageDraw.Draw(glint).rounded_rectangle([x * f, y * f, (x + bw) * f, (y + bh) * f], radius=bh * f / 2, fill=GLINT + (217,))
        img = Image.alpha_composite(img, glint)
    d = ImageDraw.Draw(img)
    for p in plane_parts(bold):
        d.polygon([(a * f, b * f) for a, b in p], fill=PLANE + (255,))
    if rounded:
        mask = Image.new("L", (big, big), 0)
        ImageDraw.Draw(mask).rounded_rectangle([0, 0, big - 1, big - 1], radius=(64 if bold else 96) * f, fill=255)
        img.putalpha(mask)
    return img.resize((px, px), Image.LANCZOS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("outdir")
    ap.add_argument("--sheet")
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)
    with open(os.path.join(a.outdir, "favicon.svg"), "w") as f:
        f.write(svg(True))
    sizes = [raster(s, True, s < 48) for s in (16, 32, 48)]
    sizes[2].save(os.path.join(a.outdir, "favicon.ico"), format="ICO", sizes=[(16, 16), (32, 32), (48, 48)],
                  append_images=sizes[:2])
    raster(180, False).save(os.path.join(a.outdir, "apple-touch-icon.png"), optimize=True)
    raster(192, False).save(os.path.join(a.outdir, "icon-192.png"), optimize=True)
    raster(512, False).save(os.path.join(a.outdir, "icon-512.png"), optimize=True)
    if a.sheet:
        from PIL import Image
        shown = [16, 32, 48, 64, 128, 192, 256]
        sheet = Image.new("RGBA", (sum(shown) + 20 * (len(shown) + 1), 300), (17, 17, 17, 255))
        x = 20
        for s in shown:
            sheet.alpha_composite(raster(s, True, s < 48), (x, 20))
            x += s + 20
        sheet.save(a.sheet)


if __name__ == "__main__":
    sys.exit(main())
