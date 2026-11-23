"""docs/music-status.md: current with the repository, every catalogue piece and LOGH row present, tables and links valid."""
import json, re, sys, unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import music_status

PAGE = ROOT / 'docs/music-status.md'


class MusicStatusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text, cls.notes = music_status.build()
        cls.catalogue = json.loads((ROOT / 'data/music/catalogue.json').read_text())

    def test_page_is_current(self):
        self.assertEqual(PAGE.read_text(), self.text, 'docs/music-status.md is out of date: run python3 tools/music_status.py')

    def test_tables_are_valid(self):
        lines = self.text.split('\n')
        i = 0
        tables = 0
        while i < len(lines):
            if lines[i].startswith('|') and i + 1 < len(lines) and lines[i + 1].startswith('|---'):
                tables += 1
                width = len(re.findall(r'(?<!\\)\|', lines[i]))
                j = i
                while j < len(lines) and lines[j].startswith('|'):
                    self.assertEqual(len(re.findall(r'(?<!\\)\|', lines[j])), width, f'line {j + 1}: {lines[j][:80]}')
                    j += 1
                i = j
            else:
                i += 1
        self.assertGreaterEqual(tables, 7)

    def test_links_resolve(self):
        anchors = set(re.findall(r'<a id="([^"]+)"></a>', self.text))
        # (GitHub's slug of a heading: lower case, punctuation dropped, spaces to hyphens)
        anchors |= {re.sub(r'[^a-z0-9 -]', '', h.lower()).replace(' ', '-') for h in re.findall(r'^#+ (.*)$', self.text, re.M)}
        for target in re.findall(r'\]\(#([^)]+)\)', self.text):
            self.assertIn(target, anchors, f'a link to #{target} has no anchor')

    def test_every_catalogue_piece_has_one_row(self):
        for i in range(len(self.catalogue)):
            self.assertEqual(self.text.count(f'<a id="p{i}"></a>'), 1, i)
        self.assertEqual(set(self.notes['pieces']) - {e['id'] for e in self.catalogue}, set())

    def test_logh_rows(self):
        rows = self.notes['logh']
        self.assertEqual(len(rows), 211)      # the user's list: one row per work
        counts = Counter(r['status'] for r in rows)
        self.assertEqual(sum(counts.values()), 211)
        for r in rows + self.notes['logh_extra']:
            self.assertIn(r['status'], music_status.STATUS)
            self.assertEqual(r['status'] in ('in the game', 'partly'), bool(r['pieces']), r['work'])
            self.assertTrue(r['work'] and r['composer'])
        for k in range(len(rows)):
            self.assertEqual(self.text.count(f'<a id="L{k + 1}"></a>'), 1)

    def test_every_piece_is_heard_somewhere_or_says_so(self):
        self.assertNotIn('| ? |', self.text.split('## Every piece in the catalogue')[1].split('## Where the music is heard')[0])


if __name__ == '__main__':
    unittest.main()
