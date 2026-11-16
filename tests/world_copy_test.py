"""The living world is changed in place, never through a copy: in Sloppy assignment copies, so a
function of aegean.jo that takes `w = living_world` and hands `w` to something that changes the
world (a `mut World` parameter) changes only its copy, which is thrown away. Rooms were taken, fish
sold, buckets bought, the barber paid and the boy sent for the band's players that way, and none of
it reached the world. Reading through `w` is fine; changing goes through `living_world` itself (or
the copy is written back with `living_world = w`)."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def mutating_functions():
    names = set()
    for path in [ROOT / 'aegean.jo', *sorted((ROOT / 'src').glob('*.jo'))]:
        for m in re.finditer(r'^([a-z_][a-z_0-9]*) = \([a-z_][a-z_0-9]*: mut (?:[a-z_]+\.)?World\b',
                             path.read_text(), re.M):
            names.add(m.group(1))
    return names


def lost_changes():
    lines = (ROOT / 'aegean.jo').read_text().split('\n')
    muts = mutating_functions()
    starts = [i for i, l in enumerate(lines) if re.match(r'^[a-z_][a-z_0-9]* = \(', l)] + [len(lines)]
    found = []
    for a, b in zip(starts, starts[1:]):
        body = lines[a:b]
        copies = {m.group(1) for l in body for m in [re.match(r'\s+([a-z_][a-z_0-9]*) = living_world\s*$', l)] if m}
        for v in copies:
            if any(re.search(r'\bliving_world = ' + v + r'\b', l) for l in body):
                continue
            for j, l in enumerate(body):
                for m in re.finditer(r'([a-z_][a-z_0-9.]*)\(' + v + r'\s*[,)]', l):
                    if m.group(1).split('.')[-1] in muts:
                        found.append(f"aegean.jo:{a + j + 1}: {m.group(1)}({v}, ...) changes a copy of living_world")
                if re.search(r'\b' + v + r'\.[a-z_\[\]().0-9]+\s*(=|\+=|-=)[^=]', l) or \
                        re.search(r'\b' + v + r'\.[a-z_\[\]().0-9]+\.(push|remove_at|pop|insert|extend)\(', l):
                    found.append(f"aegean.jo:{a + j + 1}: writes into a copy of living_world: {l.strip()}")
    return found


class WorldCopyTest(unittest.TestCase):
    def test_finds_mutating_functions(self):
        names = mutating_functions()
        self.assertIn('leisure_take_room', names)
        self.assertIn('transfer', names)

    def test_no_change_goes_to_a_copy_of_the_world(self):
        self.assertEqual(lost_changes(), [])


if __name__ == '__main__':
    unittest.main()
