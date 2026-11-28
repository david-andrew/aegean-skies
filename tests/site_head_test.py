#!/usr/bin/env python3
"""Check the web page's site head (site/head.html) and page files (site/web/).

Sloppy 0.45.0 builds the page directly from aegean.jo's `build:` block (`head = "site/head.html"`,
`page_files = "site/web"`): the head file's tags go after `<title>` (dropping the default `data:,`
icon because the head has `rel="icon"`), and every file under `site/web` is copied beside the page.

Run:
  python3 tests/site_head_test.py                  unit test (builds a minimal wasm page with
                                                   aegean.jo's head and page_files and checks it)
  python3 tests/site_head_test.py --check DIR      validate an already built site directory
                                                   (used on the real build in pages.yml)
"""
import argparse
import json
import os
import re
import struct
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
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


def png_size(path):
    data = Path(path).read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise ValueError(f"{path}: not a PNG")
    return struct.unpack(">II", data[16:24])


class _Head(HTMLParser):
    def __init__(self):
        super().__init__()
        self.metas, self.links, self.title = [], [], ""
        self._in_title, self.in_head = False, False

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


def parse_head(text):
    p = _Head()
    p.feed(text)
    return p


def check_text(text, base_url=BASE_URL):
    """Return a list of problems with a built page's head and runtime scripts."""
    p = parse_head(text)
    problems = []
    meta = {}
    for m in p.metas:
        key = m.get("name") or m.get("property")
        if key:
            if key in meta:
                problems.append(f"duplicate meta {key}")
            meta[key] = m.get("content", "")
    want = {
        "description": DESCRIPTION,
        "theme-color": THEME,
        "og:type": "website",
        "og:site_name": TITLE,
        "og:title": TITLE,
        "og:description": DESCRIPTION,
        "og:url": base_url,
        "og:image": base_url + PREVIEW,
        "og:image:type": "image/png",
        "og:image:width": str(PREVIEW_SIZE[0]),
        "og:image:height": str(PREVIEW_SIZE[1]),
        "og:image:alt": IMAGE_ALT,
        "twitter:card": "summary_large_image",
        "twitter:title": TITLE,
        "twitter:description": DESCRIPTION,
        "twitter:image": base_url + PREVIEW,
        "twitter:image:alt": IMAGE_ALT,
    }
    for k, v in want.items():
        if meta.get(k) != v:
            problems.append(f"meta {k}: {meta.get(k)!r}, wanted {v!r}")
    for k in ("og:url", "og:image", "twitter:image"):
        if not meta.get(k, "").startswith("https://"):
            problems.append(f"meta {k} is not an absolute https URL")
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
    if "<title>" in text and 'name="description"' in text:
        if text.index("<title>") > text.index('name="description"'):
            problems.append("head tags did not appear after <title>")
    if "<script" not in text or 'id="sloppy-wasm"' not in text:
        problems.append("the runtime's script tags are missing")
    return problems


def check_files(site, text=None, base_url=BASE_URL):
    """Return a list of problems with the files beside the built page."""
    site = Path(site)
    problems = []

    # Every relative href referenced in <head>, plus og:image/twitter:image under base_url
    if text is not None:
        p = parse_head(text)
        for l in p.links:
            href = l.get("href", "")
            if not href or href.startswith(("http://", "https://", "data:")):
                continue
            f = site / href
            if not f.is_file() or f.stat().st_size == 0:
                problems.append(f"referenced link file {href!r} is missing beside the page")
        for m in p.metas:
            key = m.get("name") or m.get("property")
            if key in ("og:image", "twitter:image"):
                val = m.get("content", "")
                if val.startswith(base_url):
                    rel_path = val[len(base_url):]
                    f = site / rel_path
                    if not f.is_file() or f.stat().st_size == 0:
                        problems.append(f"referenced {key} file {rel_path!r} is missing beside the page")

    for name, size in ICON_FILES.items():
        f = site / name
        if not f.is_file() or f.stat().st_size == 0:
            problems.append(f"{name} is missing")
        elif size:
            try:
                got = png_size(f)
                if got != size:
                    problems.append(f"{name} is {got}, wanted {size}")
            except ValueError as e:
                problems.append(str(e))
        elif name == "favicon.svg":
            if "<svg" not in f.read_text("utf-8"):
                problems.append("favicon.svg does not contain <svg")
        elif name == "favicon.ico":
            from PIL import Image
            with Image.open(f) as ico:
                if ico.info.get("sizes") != {(16, 16), (32, 32), (48, 48)}:
                    problems.append(f"favicon.ico sizes {ico.info.get('sizes')!r}, wanted 16/32/48")

    f = site / PREVIEW
    if not f.is_file():
        problems.append(f"{PREVIEW} is missing")
    else:
        try:
            got = png_size(f)
            if got != PREVIEW_SIZE:
                problems.append(f"{PREVIEW} is {got}, wanted {PREVIEW_SIZE}")
        except ValueError as e:
            problems.append(str(e))
        if f.stat().st_size > PREVIEW_MAX_BYTES:
            problems.append(f"{PREVIEW} is {f.stat().st_size} bytes, over {PREVIEW_MAX_BYTES}")

    mf = site / "site.webmanifest"
    if not mf.is_file():
        problems.append("site.webmanifest is missing")
    else:
        try:
            m = json.loads(mf.read_text("utf-8"))
        except ValueError as e:
            problems.append(f"site.webmanifest is invalid JSON: {e}")
            return problems
        for k in ("name", "short_name", "description", "start_url", "scope", "display",
                  "background_color", "theme_color", "icons"):
            if k not in m:
                problems.append(f"manifest lacks {k}")
        for icon in m.get("icons", []):
            src = icon.get("src", "")
            if not src or not (site / src).is_file():
                problems.append(f"manifest names {src!r}, which is missing")
        if {i.get("sizes") for i in m.get("icons", [])} < {"192x192", "512x512"}:
            problems.append("manifest lacks the 192 and 512 icons")
    return problems


def check_site(site, base_url=BASE_URL):
    site = Path(site)
    index = site / "index.html"
    if not index.is_file():
        return [f"{index} is missing"]
    text = index.read_text("utf-8")
    return check_text(text, base_url) + check_files(site, text=text, base_url=base_url)


class SiteHeadTest(unittest.TestCase):
    def test_aegean_build_block_wires_head_and_page_files(self):
        src = (ROOT / "aegean.jo").read_text("utf-8")
        m = re.search(r"^build:\n((?:    .*\n)+)", src, re.M)
        self.assertIsNotNone(m, "aegean.jo has no build: block")
        block = m.group(1)
        self.assertIn('name = "Aegean Skies"', block)
        self.assertIn('head = "site/head.html"', block)
        self.assertIn('page_files = "site/web"', block)
        self.assertTrue((ROOT / "site/head.html").is_file())
        self.assertTrue((ROOT / "site/web").is_dir())

    def test_description_is_one_plain_sentence(self):
        self.assertLessEqual(len(DESCRIPTION), 160)
        self.assertEqual(DESCRIPTION.count("."), 1)
        self.assertTrue(DESCRIPTION.endswith("."))

    def test_favicon_svg_matches_site_icons(self):
        sys.path.insert(0, str(ROOT / "tools"))
        import site_icons  # noqa: E402
        self.assertEqual((ROOT / "site/web/favicon.svg").read_text("utf-8"), site_icons.svg(True))

    def test_wasm_build_embeds_head_and_copies_page_files(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as tmp:
            tmp = Path(tmp)
            # Minimal program using the repo's exact site/head.html and site/web directory
            prog = tmp / "probe.jo"
            head_path = (ROOT / "site/head.html").as_posix()
            web_path = (ROOT / "site/web").as_posix()
            prog.write_text(
                f'build:\n'
                f'    name = "{TITLE}"\n'
                f'    head = "{head_path}"\n'
                f'    page_files = "{web_path}"\n'
                f'print("ok")\n',
                "utf-8",
            )
            out = tmp / "out"
            out.mkdir()
            r = subprocess.run(
                ["sloppy", "build", str(prog), "--target", "wasm", "--wasm-file", "-o", str(out / "index.html")],
                capture_output=True,
                text=True,
                timeout=120,
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue((out / "index.wasm").is_file())
            self.assertEqual(check_site(out), [])

            # Mutated checks fail as expected
            page = (out / "index.html").read_text("utf-8")
            bad_card = page.replace('content="summary_large_image"', 'content="summary"')
            self.assertTrue(any("twitter:card" in p for p in check_text(bad_card)))
            bad_icon = page.replace("</head>", '<link rel="icon" href="data:,"></head>')
            self.assertTrue(any("data:," in p for p in check_text(bad_icon)))
            bad_og = page.replace(BASE_URL + PREVIEW, PREVIEW)
            self.assertTrue(any("og:image" in p for p in check_text(bad_og)))

            (out / "icon-192.png").unlink()
            self.assertTrue(any("icon-192.png" in p for p in check_site(out)))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", metavar="SITE_DIR", help="check an already built web site directory")
    ap.add_argument("--base-url", default=BASE_URL)
    a, rest = ap.parse_known_args(argv)
    if a.check:
        problems = check_site(a.check, a.base_url)
        if problems:
            print(f"site_head_test: {'; '.join(problems)}", file=sys.stderr)
            return 1
        print(f"site_head_test: {Path(a.check) / 'index.html'} ok")
        return 0
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SiteHeadTest)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
