"""The web page's site head (tools/site_head.py) and icons (tools/site_icons.py).
Run: python3 tests/site_head_test.py   Needs Pillow; no Sloppy.
Also run on the real build in .github/workflows/pages.yml (`site_head.py site --check`).
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import site_head  # noqa: E402

# the head `sloppy build --target wasm` writes (v0.44.0), and the start of its body
PAGE = """<!doctype html>
<html><head><meta charset="utf-8"><title>Aegean Skies</title>
<link rel="icon" href="data:,">
<meta name="viewport" content="width=device-width,initial-scale=1,minimum-scale=1,maximum-scale=1,viewport-fit=cover">
<style>html,body{margin:0;height:100%;background:#111;color:#ddd;font:14px monospace}</style>
</head><body><canvas id="sloppy-canvas" tabindex="1" width="0" height="0"></canvas><div id="log"></div>
<script type="application/wasm" id="sloppy-wasm" data-src="index.wasm?v=3c52b0dcfc73"></script>
<script>
"use strict";
const x = "<link rel=\\"icon\\" href=\\"data:,\\">";
</script>
</body></html>
"""


def site_dir(tmp, page=PAGE):
    d = Path(tmp)
    (d / "index.html").write_text(page, "utf-8")
    subprocess.run([sys.executable, str(ROOT / "tools/site_icons.py"), str(d)], check=True)
    from PIL import Image
    Image.new("RGB", site_head.PREVIEW_SIZE, (40, 90, 120)).save(d / "preview.png")
    return d


class SiteHead(unittest.TestCase):
    def test_rewrite_keeps_the_build_and_adds_the_tags(self):
        out = site_head.rewrite(PAGE)
        self.assertEqual(site_head.check_text(out), [])
        for kept in ('<meta charset="utf-8">', "<title>Aegean Skies</title>", 'name="viewport"', "<style>html,body",
                     '<script type="application/wasm" id="sloppy-wasm"', 'const x = "<link rel=\\"icon\\" href=\\"data:,\\">";'):
            self.assertIn(kept, out)
        self.assertNotIn('<link rel="icon" href="data:,">\n', out)
        self.assertTrue(out.startswith("<!doctype html>"))
        self.assertEqual(out[out.index("</head>"):], PAGE[PAGE.index("</head>"):])

    def test_idempotent(self):
        once = site_head.rewrite(PAGE)
        self.assertEqual(site_head.rewrite(once), once)
        self.assertEqual(once.count(site_head.BEGIN), 1)

    def test_other_base_url_replaces_the_block(self):
        once = site_head.rewrite(PAGE)
        other = site_head.rewrite(once, "https://example.org/g/")
        self.assertEqual(site_head.check_text(other, "https://example.org/g/"), [])
        self.assertNotIn("david-andrew", other)

    def test_fails_when_the_head_is_not_the_expected_one(self):
        for bad in (PAGE.replace('<link rel="icon" href="data:,">\n', ""),
                    PAGE.replace('<link rel="icon" href="data:,">', '<link rel="icon" href="data:,"><link rel="icon" href="data:,">'),
                    PAGE.replace("<title>Aegean Skies</title>", "<title>Other</title>"),
                    PAGE.replace("<head>", "<body>").replace("</head>", ""),
                    "<html></html>"):
            with self.assertRaises(site_head.SiteError):
                site_head.rewrite(bad)
        with self.assertRaises(site_head.SiteError):
            site_head.rewrite(site_head.rewrite(PAGE).replace(site_head.END, ""))

    def test_description_is_one_plain_sentence(self):
        d = site_head.DESCRIPTION
        self.assertLessEqual(len(d), 160)
        self.assertEqual(d.count("."), 1)
        self.assertTrue(d.endswith("."))

    def test_checker_catches_a_changed_tag(self):
        out = site_head.rewrite(PAGE).replace('content="summary_large_image"', 'content="summary"')
        self.assertTrue(any("twitter:card" in p for p in site_head.check_text(out)))

    def test_manifest(self):
        m = site_head.manifest()
        self.assertEqual(m["background_color"], "#111111")
        self.assertIn(m["display"], ("fullscreen", "standalone"))
        self.assertEqual({i["sizes"] for i in m["icons"]}, {"192x192", "512x512"})
        json.dumps(m)


class WholeSite(unittest.TestCase):
    def test_script_writes_everything_and_check_passes(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as tmp:
            d = site_dir(tmp)
            script = str(ROOT / "tools/site_head.py")
            self.assertEqual(subprocess.run([sys.executable, script, str(d)]).returncode, 0)
            first = (d / "index.html").read_text("utf-8")
            self.assertEqual(subprocess.run([sys.executable, script, str(d)]).returncode, 0)
            self.assertEqual((d / "index.html").read_text("utf-8"), first)
            self.assertEqual(subprocess.run([sys.executable, script, str(d), "--check"]).returncode, 0)
            self.assertEqual(site_head.check_files(d), [])
            from PIL import Image
            with Image.open(d / "favicon.ico") as ico:
                self.assertEqual(ico.info["sizes"], {(16, 16), (32, 32), (48, 48)})
            for name, size in (("apple-touch-icon.png", 180), ("icon-192.png", 192), ("icon-512.png", 512)):
                with Image.open(d / name) as im:
                    self.assertEqual(im.size, (size, size))
            self.assertIn("<svg", (d / "favicon.svg").read_text())

    def test_missing_or_wrong_files_fail_without_changing_the_page(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as tmp:
            d = site_dir(tmp)
            (d / "icon-192.png").unlink()
            self.assertEqual(subprocess.run([sys.executable, str(ROOT / "tools/site_head.py"), str(d)],
                                            stderr=subprocess.DEVNULL).returncode, 1)
            self.assertEqual((d / "index.html").read_text("utf-8"), PAGE)
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as tmp:
            d = site_dir(tmp)
            from PIL import Image
            Image.new("RGB", (600, 315)).save(d / "preview.png")
            self.assertEqual(subprocess.run([sys.executable, str(ROOT / "tools/site_head.py"), str(d)],
                                            stderr=subprocess.DEVNULL).returncode, 1)

    def test_unrewritten_page_fails_the_check(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get("TMPDIR")) as tmp:
            d = site_dir(tmp)
            self.assertEqual(subprocess.run([sys.executable, str(ROOT / "tools/site_head.py"), str(d), "--check"],
                                            stderr=subprocess.DEVNULL).returncode, 1)


if __name__ == "__main__":
    unittest.main()
