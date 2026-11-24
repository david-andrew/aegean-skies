#!/usr/bin/env python3
"""Give the built web page its site features: icons, description, link-card tags, manifest.

`sloppy build --target wasm` writes a bare <head> (title, an empty `data:,` icon, the viewport and
the style). This rewrites that head after the build (.github/workflows/pages.yml), leaving what the
build wrote and the runtime's scripts as they are:

  site_head.py SITE_DIR [--base-url URL]    rewrite SITE_DIR/index.html, write site.webmanifest
  site_head.py SITE_DIR --check             only validate an already rewritten site

SITE_DIR must already hold the files the head names (favicon.svg, favicon.ico, apple-touch-icon.png,
icon-192.png, icon-512.png from tools/site_icons.py, and preview.png, the 1200 x 630 link card).
It is idempotent: the tags sit between marker comments and a second run replaces them. It exits
with an error, writing nothing, when the head is not the one the build is known to write (no
`data:,` icon link and no markers, no <title>, no <head>) or a named file is missing or the wrong size.
"""
import argparse
import html
import json
import re
import struct
import sys
from html.parser import HTMLParser
from pathlib import Path

BASE_URL = "https://david-andrew.github.io/aegean-skies/"
TITLE = "Aegean Skies"
DESCRIPTION = "A seaplane game set over the Aegean in the 1920s–30s, playable in the browser."
IMAGE_ALT = "A biplane seaplane flying over a calm sea beside a hilly coast and a harbour town as the sun sets."
THEME = "#111111"
PREVIEW = "preview.png"
PREVIEW_SIZE = (1200, 630)
PREVIEW_MAX_BYTES = 1_000_000
ICON_FILES = {
    "favicon.svg": None,
    "favicon.ico": None,
    "apple-touch-icon.png": (180, 180),
    "icon-192.png": (192, 192),
    "icon-512.png": (512, 512),
}
BEGIN = "<!-- site-head:begin -->"
END = "<!-- site-head:end -->"
EMPTY_ICON = '<link rel="icon" href="data:,">'
MARKED = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END), re.S)


class SiteError(Exception):
    pass


def png_size(path):
    data = Path(path).read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise SiteError(f"{path}: not a PNG")
    return struct.unpack(">II", data[16:24])


def attr(value):
    return html.escape(value, quote=True)


def block(base_url):
    if not base_url.endswith("/"):
        raise SiteError("the base URL must end with a slash")
    page = base_url
    image = base_url + PREVIEW
    meta = [
        ('name', 'description', DESCRIPTION),
        ('name', 'theme-color', THEME),
        ('property', 'og:type', 'website'),
        ('property', 'og:site_name', TITLE),
        ('property', 'og:title', TITLE),
        ('property', 'og:description', DESCRIPTION),
        ('property', 'og:url', page),
        ('property', 'og:image', image),
        ('property', 'og:image:type', 'image/png'),
        ('property', 'og:image:width', str(PREVIEW_SIZE[0])),
        ('property', 'og:image:height', str(PREVIEW_SIZE[1])),
        ('property', 'og:image:alt', IMAGE_ALT),
        ('name', 'twitter:card', 'summary_large_image'),
        ('name', 'twitter:title', TITLE),
        ('name', 'twitter:description', DESCRIPTION),
        ('name', 'twitter:image', image),
        ('name', 'twitter:image:alt', IMAGE_ALT),
    ]
    lines = [BEGIN]
    for kind, name, content in meta[:2]:
        lines.append(f'<meta {kind}="{name}" content="{attr(content)}">')
    lines += [
        f'<link rel="canonical" href="{attr(page)}">',
        '<link rel="icon" href="favicon.svg" type="image/svg+xml">',
        '<link rel="icon" href="favicon.ico" sizes="16x16 32x32 48x48">',
        '<link rel="apple-touch-icon" href="apple-touch-icon.png">',
        '<link rel="manifest" href="site.webmanifest">',
    ]
    for kind, name, content in meta[2:]:
        lines.append(f'<meta {kind}="{name}" content="{attr(content)}">')
    lines.append(END)
    return "\n".join(lines)


def manifest():
    return {
        "name": TITLE,
        "short_name": TITLE,
        "description": DESCRIPTION,
        "start_url": "./",
        "scope": "./",
        "display": "fullscreen",
        "background_color": THEME,
        "theme_color": THEME,
        "icons": [
            {"src": "icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
            {"src": "icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any"},
            {"src": "icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
    }


def rewrite(text, base_url=BASE_URL):
    """The page's text with the site tags in its head; raises SiteError if the head is not the build's."""
    head = re.search(r"<head[ >].*?</head>", text, re.S)
    if not head:
        raise SiteError("no <head> found")
    if "<title>" + TITLE + "</title>" not in head.group(0):
        raise SiteError(f"the head has no <title>{TITLE}</title>")
    new = block(base_url)
    h = head.group(0)
    if BEGIN in h:
        if h.count(BEGIN) != 1 or h.count(END) != 1 or EMPTY_ICON in h:
            raise SiteError("the head has damaged site markers")
        h2 = MARKED.sub(lambda _m: new, h)
    else:
        if h.count(EMPTY_ICON) != 1:
            raise SiteError(f"expected the head to hold {EMPTY_ICON} exactly once, found {h.count(EMPTY_ICON)}")
        h2 = h.replace(EMPTY_ICON, new)
    return text[:head.start()] + h2 + text[head.end():]


class _Head(HTMLParser):
    def __init__(self):
        super().__init__()
        self.metas, self.links, self.title, self._in_title, self.in_head, self.scripts = [], [], "", False, False, 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "head":
            self.in_head = True
        if not self.in_head:
            return
        if tag == "meta":
            self.metas.append(a)
        elif tag == "link":
            self.links.append(a)
        elif tag == "title":
            self._in_title = True

    def handle_endtag(self, tag):
        if tag == "head":
            self.in_head = False
        if tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._in_title:
            self.title += data


def check_text(text, base_url=BASE_URL):
    """A list of problems with the head of an already rewritten page (empty: it is right)."""
    p = _Head()
    p.feed(text)
    problems = []
    meta = {}
    for m in p.metas:
        key = m.get("name") or m.get("property")
        if key:
            if key in meta:
                problems.append(f"duplicate meta {key}")
            meta[key] = m.get("content", "")
    want = {
        "description": DESCRIPTION, "theme-color": THEME, "og:type": "website", "og:site_name": TITLE,
        "og:title": TITLE, "og:description": DESCRIPTION, "og:url": base_url, "og:image": base_url + PREVIEW,
        "og:image:width": "1200", "og:image:height": "630", "og:image:alt": IMAGE_ALT,
        "twitter:card": "summary_large_image", "twitter:title": TITLE, "twitter:description": DESCRIPTION,
        "twitter:image": base_url + PREVIEW,
    }
    for k, v in want.items():
        if meta.get(k) != v:
            problems.append(f"meta {k}: {meta.get(k)!r}, wanted {v!r}")
    if len(meta.get("description", "")) > 160:
        problems.append("description is over 160 characters")
    if p.title != TITLE:
        problems.append(f"title is {p.title!r}")
    if not any(m.get("charset") for m in p.metas):
        problems.append("charset meta lost")
    if not any(m.get("name") == "viewport" for m in p.metas):
        problems.append("viewport meta lost")
    rel = {}
    for l in p.links:
        rel.setdefault(l.get("rel"), []).append(l)
    if any(l.get("href") == "data:," for l in p.links):
        problems.append("the empty data:, icon is still there")
    for r, n in (("canonical", 1), ("icon", 2), ("apple-touch-icon", 1), ("manifest", 1)):
        if len(rel.get(r, [])) != n:
            problems.append(f"{len(rel.get(r, []))} link rel={r}, wanted {n}")
    if rel.get("canonical") and rel["canonical"][0].get("href") != base_url:
        problems.append("canonical is not the page's URL")
    if "<script" not in text or 'id="sloppy-wasm"' not in text:
        problems.append("the runtime's script tags are missing")
    return problems


def check_files(site, with_manifest=True):
    site = Path(site)
    problems = []
    for name, size in ICON_FILES.items():
        f = site / name
        if not f.is_file() or f.stat().st_size == 0:
            problems.append(f"{name} is missing")
        elif size and png_size(f) != size:
            problems.append(f"{name} is {png_size(f)}, wanted {size}")
    f = site / PREVIEW
    if not f.is_file():
        problems.append(f"{PREVIEW} is missing")
    else:
        if png_size(f) != PREVIEW_SIZE:
            problems.append(f"{PREVIEW} is {png_size(f)}, wanted {PREVIEW_SIZE}")
        if f.stat().st_size > PREVIEW_MAX_BYTES:
            problems.append(f"{PREVIEW} is {f.stat().st_size} bytes, over {PREVIEW_MAX_BYTES}")
    mf = site / "site.webmanifest"
    if not with_manifest:
        return problems
    if not mf.is_file():
        problems.append("site.webmanifest is missing")
    else:
        m = json.loads(mf.read_text("utf-8"))
        for k in ("name", "short_name", "start_url", "display", "background_color", "theme_color", "icons"):
            if k not in m:
                problems.append(f"manifest lacks {k}")
        for icon in m.get("icons", []):
            if not (site / icon["src"]).is_file():
                problems.append(f"manifest names {icon['src']}, which is missing")
        if {i["sizes"] for i in m.get("icons", [])} < {"192x192", "512x512"}:
            problems.append("manifest lacks the 192 and 512 icons")
    return problems


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("site")
    ap.add_argument("--base-url", default=BASE_URL)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args(argv)
    site = Path(a.site)
    index = site / "index.html"
    try:
        if not a.check:
            problems = check_files(site, with_manifest=False)
            if problems:
                raise SiteError("; ".join(problems))
            text = rewrite(index.read_text("utf-8"), a.base_url)
            (site / "site.webmanifest").write_text(json.dumps(manifest(), indent=2, ensure_ascii=False) + "\n", "utf-8")
            index.write_text(text, "utf-8")
        problems = check_files(site) + check_text(index.read_text("utf-8"), a.base_url)
        if problems:
            raise SiteError("; ".join(problems))
    except (SiteError, OSError, ValueError, KeyError) as e:
        print(f"site_head: {e}", file=sys.stderr)
        return 1
    print(f"site_head: {index} ok")
    return 0


if __name__ == "__main__":
    sys.exit(main())
