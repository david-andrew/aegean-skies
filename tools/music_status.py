#!/usr/bin/env python3
"""Writes docs/music-status.md: every piece considered for the game, and where it stands.

The facts that come from the repository are derived here, so the page cannot drift from them:
  - the catalogue and its numbers: data/music/catalogue.json (the piece numbers are positions in
    MUSIC_PIECES, as src/radio_synth.jo and src/bar_band.jo use them);
  - the instruments in the game: decoded from each piece's packed events (data/music/<id>.z);
  - the instruments the source says: the General MIDI programs of the source file's tracks
    (data/music/source/<id>.mid);
  - the performance treatment: data/music/performance.json, levels from src/music_data.jo, the
    arranger's tables in tools/music_pack.py;
  - the source and its licence: data/music/source/licences.json and data/music/SOURCES.md;
  - where it is heard: the radio's stations, hours and rounds (src/radio.jo, src/radio_synth.jo),
    the hotel band's set (src/bar_band.jo) and the title music (src/title_music.jo).
What a person has to say lives in data/music/status-notes.json (the LOGH list's rows, a note per
catalogue piece, the requested pieces); it is merged in. Standard library only.

  python3 tools/music_status.py            write docs/music-status.md
  python3 tools/music_status.py --check    exit 1 if the page is out of date
"""
import json, re, struct, sys, zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'docs/music-status.md'
NOTES = ROOT / 'data/music/status-notes.json'
RATE = 16000                       # MUSIC_RATE
INSTRUMENTS = ['strings', 'brass', 'flute', 'oboe', 'clarinet', 'bassoon', 'piano', 'harp', 'bouzouki',
               'accordion', 'banjo', 'timpani', 'drums', 'bass', 'choir', 'trumpet']
# What a timbre of the synthesizer stands for in the arrangements (tools/music_pack.py).
TIMBRE_NOTE = {'bouzouki': 'island pluck (bouzouki, mandolin)', 'harp': 'harp', 'bass': 'double bass'}
GM = ['Acoustic Grand Piano', 'Bright Acoustic Piano', 'Electric Grand Piano', 'Honky-tonk Piano', 'Electric Piano 1', 'Electric Piano 2',
 'Harpsichord', 'Clavinet', 'Celesta', 'Glockenspiel', 'Music Box', 'Vibraphone', 'Marimba', 'Xylophone', 'Tubular Bells', 'Dulcimer',
 'Drawbar Organ', 'Percussive Organ', 'Rock Organ', 'Church Organ', 'Reed Organ', 'Accordion', 'Harmonica', 'Tango Accordion',
 'Nylon Guitar', 'Steel Guitar', 'Jazz Guitar', 'Clean Guitar', 'Muted Guitar', 'Overdriven Guitar', 'Distortion Guitar', 'Guitar Harmonics',
 'Acoustic Bass', 'Fingered Bass', 'Picked Bass', 'Fretless Bass', 'Slap Bass 1', 'Slap Bass 2', 'Synth Bass 1', 'Synth Bass 2',
 'Violin', 'Viola', 'Cello', 'Contrabass', 'Tremolo Strings', 'Pizzicato Strings', 'Orchestral Harp', 'Timpani',
 'String Ensemble 1', 'String Ensemble 2', 'Synth Strings 1', 'Synth Strings 2', 'Choir Aahs', 'Voice Oohs', 'Synth Voice', 'Orchestra Hit',
 'Trumpet', 'Trombone', 'Tuba', 'Muted Trumpet', 'French Horn', 'Brass Section', 'Synth Brass 1', 'Synth Brass 2',
 'Soprano Sax', 'Alto Sax', 'Tenor Sax', 'Baritone Sax', 'Oboe', 'English Horn', 'Bassoon', 'Clarinet',
 'Piccolo', 'Flute', 'Recorder', 'Pan Flute', 'Blown Bottle', 'Shakuhachi', 'Whistle', 'Ocarina',
 'Square Lead', 'Saw Lead', 'Calliope Lead', 'Chiff Lead', 'Charang Lead', 'Voice Lead', 'Fifths Lead', 'Bass and Lead',
 'New Age Pad', 'Warm Pad', 'Polysynth Pad', 'Choir Pad', 'Bowed Pad', 'Metallic Pad', 'Halo Pad', 'Sweep Pad',
 'Rain', 'Soundtrack', 'Crystal', 'Atmosphere', 'Brightness', 'Goblins', 'Echoes', 'Sci-fi',
 'Sitar', 'Banjo', 'Shamisen', 'Koto', 'Kalimba', 'Bag Pipe', 'Fiddle', 'Shanai',
 'Tinkle Bell', 'Agogo', 'Steel Drums', 'Woodblock', 'Taiko Drum', 'Melodic Tom', 'Synth Drum', 'Reverse Cymbal',
 'Guitar Fret Noise', 'Breath Noise', 'Seashore', 'Bird Tweet', 'Telephone Ring', 'Helicopter', 'Applause', 'Gunshot']
assert len(GM) == 128


# ---------------------------------------------------------------- readers

def packed_instruments(piece_id):
    """{timbre name: notes} of a packed piece (data/music/<id>.z), and the number of notes."""
    raw = zlib.decompressobj(-15).decompress((ROOT / 'data/music' / f'{piece_id}.z').read_bytes())
    magic = raw[:4]
    size = {b'MUS1': 12, b'MUS2': 14, b'MUS3': 16, b'MUS4': 16}[magic]
    count = struct.unpack_from('<I', raw, 4)[0]
    counts = {}
    for i in range(count):
        ins = raw[16 + i * size + 9] & 15
        counts[INSTRUMENTS[ins]] = counts.get(INSTRUMENTS[ins], 0) + 1
    return counts, count


def _varlen(b, i):
    v = 0
    while True:
        c = b[i]; i += 1
        v = (v << 7) | (c & 0x7F)
        if not c & 0x80:
            return v, i


def midi_programs(path):
    """The General MIDI instrument names of the tracks that play notes, in track order (a track with
    no program change takes the previous track's, as tools/music_pack.py does); percussion as such."""
    b = Path(path).read_bytes()
    ntrks = struct.unpack('>H', b[10:12])[0]
    i = 14
    names = []
    previous = None
    for _ in range(ntrks):
        n = struct.unpack('>I', b[i + 4:i + 8])[0]
        j = i + 8; stop = j + n; status = 0
        program = {}; first = None; notes = False; drums = False
        while j < stop:
            _, j = _varlen(b, j)
            c = b[j]
            if c == 0xFF:
                ln, j = _varlen(b, j + 2); j += ln
            elif c in (0xF0, 0xF7):
                ln, j = _varlen(b, j + 1); j += ln
            else:
                if c & 0x80:
                    status = c; j += 1
                hi, ch = status & 0xF0, status & 15
                if hi == 0xC0:
                    program[ch] = b[j]
                    if first is None:
                        first = b[j]
                    j += 1
                elif hi == 0xD0:
                    j += 1
                else:
                    if hi == 0x90 and b[j + 1]:
                        notes = True
                        if ch == 9:
                            drums = True
                    j += 2
        i = stop
        if first is not None:
            previous = first
        if notes:
            used = sorted(set(program.values())) or [previous or 0]
            if drums and not program:
                names.append('percussion')
            else:
                for p in used:
                    names.append(GM[p])
                if drums:
                    names.append('percussion')
    return list(dict.fromkeys(names))


def catalogue():
    return json.loads((ROOT / 'data/music/catalogue.json').read_text())


def music_data_levels():
    """Each piece's level in the mix, in catalogue order, from src/music_data.jo (1.0 when absent)."""
    out = []
    for line in (ROOT / 'src/music_data.jo').read_text().splitlines():
        if line.startswith('    MusicPiece('):
            m = re.search(r'level = ([0-9.]+)', line)
            out.append(float(m.group(1)) if m else 1.0)
    return out


def table_rows(path):
    """The rows of the first markdown table of SOURCES.md: lists of cells."""
    rows = []
    for line in Path(path).read_text().splitlines():
        if line.startswith('| ') and not line.startswith('| Piece') and not line.startswith('|---'):
            rows.append([c.strip() for c in line.strip().strip('|').split(' | ')])
    return rows


def pack_tables():
    """The arranger's tables from tools/music_pack.py: SOURCE, APPLY_MOOD, ANNOTATED, EXPRESSIVE,
    GENTLE, HAND_SET_BALANCE, AS_ARRANGED, GRACE_SKIP, SUNG (read as text; no mido needed)."""
    t = (ROOT / 'tools/music_pack.py').read_text()

    def keys(name):
        a = t.index(name + ' = ') + len(name) + 3
        depth = 0
        for end in range(a, len(t)):
            depth += (t[end] == '{') - (t[end] == '}')
            if depth == 0:
                break
        return set(re.findall(r"'([a-z0-9-]+)'\s*:", t[a:end]))
    out = {n: keys(n) for n in ('APPLY_MOOD', 'ANNOTATED', 'EXPRESSIVE', 'GENTLE', 'HAND_SET_BALANCE', 'SUNG')}
    out['AS_ARRANGED'] = set(re.findall(r"'([a-z0-9-]+)'", t[t.index('AS_ARRANGED = '):].split('\n')[0]))
    out['GRACE_SKIP'] = set(re.findall(r"'([a-z0-9-]+)'", t[t.index('GRACE_SKIP = '):].split('\n')[0]))
    a = t.index('SOURCE = {')
    out['SOURCE'] = dict(re.findall(r"'([\w-]+)': '([\w-]+)'", t[a:t.index('}', a)]))
    return out


# ---------------------------------------------------------------- where it is heard

def radio_model():
    """Stations, blocks and the pool of each round, read from src/radio.jo and src/radio_synth.jo."""
    r = (ROOT / 'src/radio.jo').read_text()
    stations = {}
    for m in re.finditer(r'RadioStation\((\d+),"([^"]+)","(\w+)",(\d+),vec3\([^)]*\),(\d+),(-?\d+),(-?\d+),\.(\w+)\)', r):
        stations[int(m.group(1))] = dict(id=int(m.group(1)), name=m.group(2), khz=int(m.group(4)), style=m.group(8))
    blocks = {}
    body = r[r.index('radio_blocks = '):r.index('_in_block = ')]
    for m in re.finditer(r'^\s+(\d+): \[(.*)\]\s*$', body, re.M):
        blocks[int(m.group(1))] = [dict(frm=int(a), to=int(b), style=s, talk=int(tk or 0), dance=bool(dance))
                                   for a, b, s, tk, dance in re.findall(r'RadioBlock\((\d+), (\d+), \.(\w+)(?:, (\d))?(?:, (true))?\)', m.group(2))]
    s = (ROOT / 'src/radio_synth.jo').read_text()
    pool = s[s.index('radio_pool = '):s.index('struct RadioCue')]
    pools = {}
    for style in ('classical', 'foxtrot', 'tango', 'march', 'waltz', 'choir'):
        m = re.search(r'\.' + style + r': \[([\d,]+)\]', pool)
        pools[style] = [int(x) for x in m.group(1).split(',')]
    m = re.search(r'if station == 11: \[([\d,]+)\] else: if station >= 7: \[([\d,]+)\] else: \[([\d,]+)\]', pool)
    pools['cafe-aman'] = [int(x) for x in m.group(1).split(',')]
    pools['cafe'] = [int(x) for x in m.group(2).split(',')]
    pools['island'] = [int(x) for x in m.group(3).split(',')]
    return stations, blocks, pools


def hhmm(minutes):
    minutes %= 1440
    return f'{minutes // 60:02d}:{minutes % 60:02d}'


def span(frm, to):
    return f'{hhmm(frm)}–{"24:00" if to % 1440 == 0 and to else hhmm(to)}'


def round_stations(stations, blocks):
    """For each round (a pool): [(station name, khz, hours text)]. A later station's hours come from its
    blocks (src/radio.jo radio_blocks); the first six stations play their own style all day (Archipelago
    Radio's choir at 06:00, the Night Gull's evening hours, the Blue Lantern's half-hour rotation)."""
    rounds = {k: [] for k in ('classical', 'foxtrot', 'tango', 'march', 'waltz', 'choir', 'cafe-aman', 'cafe', 'island')}

    def add(rd, sid, hours):
        st = stations[sid]
        rounds[rd].append((st['name'], st['khz'], hours))
    add('island', 0, 'all day except the 06:00 hour')
    add('choir', 0, 'the 06:00 hour (wordless choir)')
    add('classical', 1, 'all day')
    add('march', 2, 'all day')
    add('foxtrot', 3, 'every third half hour, in rotation with the tango and the waltz')
    add('tango', 3, 'every third half hour, in rotation with the foxtrot and the waltz')
    add('waltz', 3, 'every third half hour, in rotation with the foxtrot and the tango')
    add('tango', 5, '19:00–03:00')
    for sid, bl in sorted(blocks.items()):
        for b in bl:
            hours = span(b['frm'], b['to'])
            name = {'classical': 'classical', 'march': 'march', 'waltz': 'waltz', 'choir': 'choir', 'tango': 'tango', 'foxtrot': 'foxtrot', 'bouzouki': None}[b['style']] if not b['dance'] else None
            if b['dance']:
                for rd, text in (('foxtrot', 'dance hour'), ('tango', 'dance hour'), ('waltz', 'dance hour')):
                    add(rd, sid, f'{hours}, every third half hour (the dance hour rotation)')
            elif b['style'] == 'bouzouki':
                if sid == 11:
                    add('cafe-aman', sid, hours + ' (minus its tango hours)')
                elif sid >= 7:
                    add('cafe', sid, hours)
                else:
                    add('island', sid, hours)
            else:
                add(name, sid, hours)
    return rounds


def bar_model():
    """The hotel band's set (src/bar_band.jo BAR_SET), its line-up names and its hours."""
    t = (ROOT / 'src/bar_band.jo').read_text()
    names = {}
    comment = re.search(r'lineup: int\s+# ([^\n]*)', t).group(1)
    for k, name in re.findall(r'(\d) ([a-z ]+?)(?:,|$)', comment):
        names[int(k)] = name.strip()
    body = t[t.index('BAR_SET: SetPiece[] = ['):]
    body = body[:body.index('\n]')]
    sung = {}
    for m in re.finditer(r'MUSIC_PIECES\[(\d+)\]\.sung', body):
        sung[int(m.group(1))] = None
    items = []
    for m in re.finditer(r'SetPiece\((\d+), (\d), (\d+), (\d+), (\[[^\]]*\]|MUSIC_PIECES\[\d+\]\.sung)(?:, (\d+))?(?:, ([\d.]+))?\)', body):
        items.append(dict(piece=int(m.group(1)), lineup=names[int(m.group(2))], lead=INSTRUMENTS[int(m.group(3))],
                          sung=m.group(5) if m.group(5) != '[]' else '', nights=int(m.group(6) or 1), level=float(m.group(7) or 1.0)))
    start = int(re.search(r'BAR_START = (\d+)', t).group(1)); end = int(re.search(r'BAR_END = (\d+)', t).group(1))
    gap = float(re.search(r'BAR_GAP = ([\d.]+)', t).group(1))
    return items, start, end, gap


def title_piece():
    return int(re.search(r'TITLE_MUSIC_PIECE = (\d+)', (ROOT / 'src/title_music.jo').read_text()).group(1))


def piece_flags():
    """Per catalogue piece, from src/music_data.jo: hall, upright piano, level, harshness shelf, sung."""
    out = []
    for line in (ROOT / 'src/music_data.jo').read_text().splitlines():
        if not line.startswith('    MusicPiece('):
            continue
        shelf = re.search(r',(\d+\.\d+),\[([^\]]*)\]', line)
        shelves = {}
        if shelf:
            for k, v in enumerate(shelf.group(2).split(',')):
                if float(v) != 0.0:
                    shelves[INSTRUMENTS[k]] = float(v)
        out.append(dict(hall='hall = true' in line, upright='piano = 1' in line, shelf=shelves,
                        shelf_hz=float(shelf.group(1)) if shelf else 0.0, sung='sung = [' in line))
    return out


def linked_title(i, cat):
    return f'[{cat[i]["title"]}](#p{i})'


# ---------------------------------------------------------------- rendering

STATUS = {'in the game': 'in the game', 'partly': 'partly', 'found': 'source found, not arranged', 'wanted': 'wanted',
          'blocked': 'blocked', 'not planned': 'not planned', 'requested': 'requested'}
ORDER = ['in the game', 'partly', 'found', 'wanted', 'blocked', 'not planned', 'requested']
ROUND_NAMES = {'classical': 'Classical', 'foxtrot': 'Foxtrot', 'tango': 'Tango', 'march': 'March', 'waltz': 'Waltz',
               'choir': 'Choir', 'island': 'Island', 'cafe': 'Café', 'cafe-aman': 'Café Aman'}
ROUND_ORDER = ['classical', 'foxtrot', 'tango', 'march', 'waltz', 'island', 'cafe', 'cafe-aman', 'choir']


def cell(text):
    return str(text).replace('|', '\\|').replace('\n', '<br>').strip() or '—'


def parse_year(composition_cell):
    m = re.search(r'\(\d{4}[–-]\d{4}\),\s*(\d{4})', composition_cell) or re.search(r',\s*(\d{4})\b', composition_cell)
    return m.group(1) if m else ''


def build():
    cat = catalogue()
    notes = json.loads(NOTES.read_text())
    perf = json.loads((ROOT / 'data/music/performance.json').read_text())
    levels_json = json.loads((ROOT / 'data/music/levels.json').read_text())
    tables = pack_tables()
    flags = piece_flags()
    levels = music_data_levels()
    assert len(flags) == len(cat) == len(levels)
    rows = table_rows(ROOT / 'data/music/SOURCES.md')
    licences = {e['file'][:-4]: e for e in json.loads((ROOT / 'data/music/source/licences.json').read_text())}
    stations, blocks, pools = radio_model()
    rounds = round_stations(stations, blocks)
    bar, bar_start, bar_end, bar_gap = bar_model()
    title = title_piece()
    index = {e['id']: i for i, e in enumerate(cat)}
    gaps = list(notes.get('gaps', []))

    # --- where each piece is heard
    heard = {i: [] for i in range(len(cat))}          # tokens for the short form
    rounds_of = {i: [] for i in range(len(cat))}
    for rd, members in pools.items():
        for i in members:
            rounds_of[i].append(rd)
    def stations_of(rd):
        return list(dict.fromkeys(n for n, _, _ in rounds[rd]))
    bar_of = {}
    for k, b in enumerate(bar):
        bar_of.setdefault(b['piece'], []).append((k, b))

    # --- which LOGH row holds each piece (the rows are the one source of the link)
    logh_link = {}
    for prefix, rows_ in (('L', notes['logh']), ('LX', notes['logh_extra'])):
        for k, r in enumerate(rows_):
            for pid in r['pieces']:
                assert pid not in logh_link, f'{pid} is in two LOGH rows'
                logh_link[pid] = f'[{prefix}{k + 1}](#{prefix}{k + 1})'

    # --- the catalogue rows
    piece_info = []
    manual = {'mahler-opening': 'Symphony No. 5, I: opening trumpet call', 'magnetic': 'Magnetic Rag', 'bethena': 'Bethena, a concert waltz'}
    for i, e in enumerate(cat):
        pid = e['id']
        n = notes['pieces'].get(pid, {})
        src = tables['SOURCE'].get(pid, pid)
        lic = licences.get(src)
        srow = None
        for r in rows:
            if (lic and r[0] == lic['title'].split(' (')[0].strip()) or pid in manual and r[0] == manual[pid]:
                srow = r
        if srow is None and lic:
            u = lic['url'].rstrip('/')
            matches = [r for r in rows if u in r[2]]
            srow = matches[0] if len(matches) == 1 else None
        if srow is None and lic:
            for r in rows:
                if lic['title'][:30] in r[0]:
                    srow = r
        if srow is None:
            gaps.append(f'#{i} {e["title"]}: no row in data/music/SOURCES.md was matched')
        year = n.get('year') or (parse_year(srow[1]) if srow else '')
        if not year:
            year = '?'; gaps.append(f'#{i} {e["title"]}: year of composition or publication')
        # instruments
        counts, total = packed_instruments(pid)
        shares = sorted(counts.items(), key=lambda kv: -kv[1])
        main = [k for k, v in shares if v * 100 >= total * 2] or [shares[0][0]]
        minor = [k for k, v in shares if k not in main]
        game = ', '.join(TIMBRE_NOTE.get(k, k) for k in main) + (f' (and a few {", ".join(minor)} notes)' if minor else '')
        mid = ROOT / 'data/music/source' / f'{src}.mid'
        if mid.exists():
            programs = midi_programs(mid)
            programs = [p for p in programs if p not in ('Tremolo Strings', 'Pizzicato Strings')] + (['strings: tremolo and pizzicato variants'] if any(p in ('Tremolo Strings', 'Pizzicato Strings') for p in programs) else [])
            source = ', '.join(programs)
        else:
            source = 'no MIDI: our own transcription' if pid == 'mahler-opening' else '?'
            if source == '?':
                gaps.append(f'#{i} {e["title"]}: the source file\'s instruments')
        # treatment
        p = perf.get(pid, {})
        treat = []
        if pid in tables['ANNOTATED']:
            treat.append(f'annotated performance ({tables["ANNOTATED"] and "data/music/" + {"adagietto": "adagietto-performance.json", "clair-de-lune": "clair-de-lune-performance.json"}[pid]})')
        elif pid == 'mahler-opening':
            treat.append('annotated solo (data/music/opening-performance.json)')
        elif pid in tables['AS_ARRANGED']:
            treat.append('played as arranged: no interpretation pass')
        elif pid in tables['APPLY_MOOD']:
            treat.append(f'expressive timing in its mood ({p.get("mood", "?")})' + ('; gentle touch' if pid in tables['GENTLE'] else ''))
        elif pid in tables['EXPRESSIVE']:
            treat.append('expressive timing (tools/expressive_timing.py)')
        elif pid == 'schubert-ave-maria':
            treat.append('own tempo map with ritardandi, then the generic phrase rules')
        else:
            treat.append('generic phrase rules')
        if p.get('duration_before') and p.get('duration_after'):
            r = p['duration_after'] / p['duration_before']
            if abs(r - 1) > 0.03:
                treat.append(f'tempo ×{r:.2f} (as played against the score\'s clock)')
        if pid == 'magnetic':
            treat.append('tempo scaled to 116 to the minute')
        pb = p.get('part_balance', {})
        if isinstance(pb, str):
            pb = {}
        st = pb.get('status', '?')
        if st == 'hand-set':
            treat.append('balance hand-set (' + pb.get('reason', '') + ')')
        elif st == 'kept':
            treat.append('balance kept from the first pass (per-instrument gains)')
        elif st == 'balanced':
            parts = pb.get('parts', {})
            big = max(parts.items(), key=lambda kv: abs(kv[1]['gain_db'])) if parts else None
            treat.append('automatic part balance' + (f' (largest move {big[1]["gain_db"]:+.1f} dB on {big[0]})' if big and abs(big[1]['gain_db']) >= 3 else ''))
        elif st == 'one part':
            treat.append('one pitched part: nothing to balance')
        elif st == 'in balance':
            treat.append('automatic balance: already in balance')
        else:
            treat.append(f'balance: {st}')
        if flags[i]['shelf']:
            treat.append('harshness shelf ' + ', '.join(f'{k} {v:+.0f} dB' for k, v in flags[i]['shelf'].items()) + f' above {flags[i]["shelf_hz"]:.0f} Hz')
        g = p.get('grace_notes', {})
        if g.get('notes'):
            treat.append(f'grace notes: {g.get("acciaccatura", 0)} acciaccature, {g.get("appoggiatura", 0)} appoggiature')
        lv = levels[i]
        treat.append(f'level {lv:g} ({"measured, levels.json" if pid in levels_json else "set by ear"})' if lv != 1.0 else 'level 1')
        if flags[i]['hall']:
            treat.append('concert-hall reverberation')
        if flags[i]['sung']:
            treat.append('sung by the singer (src/singer.jo)')
        # source
        if srow:
            lic_text = 'CC0 1.0' if 'CC0' in srow[3] and 'new transcription' not in srow[3] and 'Public-domain edition' not in srow[3] else ('Public Domain (Mutopia)' if 'Mutopia' in srow[3] else srow[3])
            sourcecell = f'{srow[2]}. Licence: {lic_text}.'
        else:
            sourcecell = '?'
        # where heard
        where = []
        for rd in ROUND_ORDER:
            if rd in rounds_of[i]:
                where.append(f'[{ROUND_NAMES[rd]} round](#round-{rd}): ' + ', '.join(stations_of(rd)))
        for k, b in bar_of.get(i, []):
            when = 'every evening' if b['nights'] == 1 else 'every other evening' if b['nights'] == 2 else f'one evening in {b["nights"]}'
            where.append(f'[Hotel Ancora band](#the-hotel-band) ({b["lineup"]}{", sung" if b["sung"] else ""}; {when})')
        if i == title:
            where.append('the title music')
        if not where:
            where.append('not on air or at the bar (debug menu audition only)')
        piece_info.append(dict(i=i, id=pid, title=e['title'], composer=e['composer'], year=year, game=game, source=source, treat=treat,
                               sourcecell=sourcecell, where=where, rounds=rounds_of[i], bar=bar_of.get(i, []), notes=n,
                               minutes=e['frames'] / RATE / 60, status='in the game' + (' (title music)' if i == title else '')))

    # --- the LOGH rows
    def logh_heard(piece_ids):
        toks = []
        for pid in piece_ids:
            pi = piece_info[index[pid]]
            for rd in pi['rounds']:
                toks.append(f'{ROUND_NAMES[rd]} round')
            if pi['bar']:
                toks.append('hotel band')
            if pi['i'] == title:
                toks.append('title')
        return ', '.join(dict.fromkeys(toks)) or ('debug menu only' if piece_ids else '')

    for r in notes['logh'] + notes['logh_extra']:
        for pid in r['pieces']:
            assert pid in index, pid
        assert (r['status'] in ('in the game', 'partly')) == bool(r['pieces']), r['work']
        assert r['status'] in STATUS, r['status']
    for pid, n in notes['pieces'].items():
        assert pid in index, f'status-notes.json names an unknown piece: {pid}'
    for c in notes['candidates'] + notes['requested']:
        assert c.get('status', 'requested') in STATUS

    lines = []
    out = lines.append
    out('<!-- Generated by tools/music_status.py from the repository and data/music/status-notes.json; do not edit by hand. -->')
    out('# Music status: every piece considered for the game')
    out('')
    out('One living page for the music: every work on the *Legend of the Galactic Heroes* (LOGH) list, every other piece in the game\'s catalogue, and any piece the user wants considered. '
        'The facts that come from the repository (catalogue numbers, instruments, treatment, sources, where each piece is heard) are derived by `tools/music_status.py`; what a person knows (the LOGH rows, notes on a piece) is in `data/music/status-notes.json`. '
        'To add a piece, see [Adding a piece](#adding-a-piece).')
    out('')
    # counts
    all_logh = notes['logh']
    from collections import Counter
    cl = Counter(r['status'] for r in all_logh)
    cx = Counter(r['status'] for r in notes['logh_extra'])
    cc = Counter(c.get('status', 'requested') for c in notes['candidates'] + notes['requested'])
    out('## Counts')
    out('')
    out('| Status | LOGH list (%d works) | More LOGH works from earlier research (%d) | Other candidates (%d) | Catalogue pieces |' % (len(all_logh), len(notes['logh_extra']), len(notes['candidates']) + len(notes['requested'])))
    out('|---|---:|---:|---:|---:|')
    for s_ in ORDER:
        out(f'| {STATUS[s_]} | {cl.get(s_, 0)} | {cx.get(s_, 0)} | {cc.get(s_, 0)} | {len(cat) if s_ == "in the game" else 0} |')
    out('')
    pieces_in = sum(len(r['pieces']) for r in all_logh)
    out(f'The catalogue has {len(cat)} pieces (numbers 0–{len(cat) - 1}, their positions in `MUSIC_PIECES`): '
        f'{len({p for r in all_logh + notes["logh_extra"] for p in r["pieces"]})} of them are pieces of LOGH works and {len(cat) - len({p for r in all_logh + notes["logh_extra"] for p in r["pieces"]})} are not.')
    out('')
    out('## Reading this page')
    out('')
    out('**Status** (one of):')
    out('')
    out('- **in the game**: the piece (or every movement LOGH uses) is in the catalogue, with its catalogue number(s);')
    out('- **partly**: some movements or an excerpt are in the game; the notes say which are not;')
    out('- **source found, not arranged**: a note source that passes our rules exists (a Mutopia public-domain edition, a staged CC0 PDMX row) but nothing is in the catalogue yet;')
    out('- **wanted**: no public-domain source found yet (or not yet researched; the note says which);')
    out('- **blocked**: something stops it. Either the work is not public domain and needs the user\'s explicit approval, or only a public-domain *scan* exists (an IMSLP edition), so our own transcription waits on the OMR reader. A wider PDMX search has not been done for the scan-only works, so some of them may move to "source found";')
    out('- **not planned**: cannot be identified as one work, or deliberately left out;')
    out('- **requested**: added by the user for consideration, not yet researched.')
    out('')
    out('**The rule for music.** The user\'s ruling (2026-11-20): anything public domain is fine; anything that is not needs their explicit approval. For a composition that means public domain in the US (published 1930 or earlier, in 2026) and in the EU (every author died 70 or more years ago). The note data must come from a CC0 or public-domain transcription (Mutopia "Public Domain", a PDMX/MuseScore row marked CC0 with no licence conflict) or from our own transcription of a public-domain scan, which is dedicated to CC0 (data/music/SOURCES.md has every record and permission). Nothing here is a recording.')
    out('')
    out('**Instruments.** "In the game" is read from the packed events: the synthesizer\'s timbres, with a share of the notes; a timbre under 2% of the notes is called a few notes. "Source file" is the General MIDI program names of the source file\'s tracks (percussion as such); Mutopia\'s LilyPond files often carry a default piano program whatever the score\'s instruments, so the "scoring" line says what the work and the source really are. '
        'The packer maps programs to timbres: pianos to piano; harp; accordions; choir and voices to choir; guitars, banjo and sitars to banjo; basses to bass; timpani; strings to strings; brass to brass; clarinets and all saxophones to clarinet; oboe and English horn to oboe; bassoon; flutes, piccolo and recorders to flute; anything else to strings. '
        'The *island pluck* ("bouzouki") stands for the bouzouki, mandolin and guitar, and the harp model also stands for the guitar in several arrangements. The piano follows the venue: the concert grand on the classical programme, the honky-tonk upright at the bar and on the popular and dance programmes ([docs/music-orchestra.md](music-orchestra.md)).')
    out('')
    out('**Treatment** is the performance given on top of the notes ([docs/music-performance.md](music-performance.md)): the generic phrase rules, the automatic part balance (tools/music_part_balance.py), the level in the mix, grace notes (tools/music_grace.py), tempo against the score (tools/music_tempo.py), plus anything done by hand. The level is 1 unless shown: measured to a common loudness by tools/music_level.py (levels.json) or set by ear. Voice stealing (which note gives way when the 64 voices are all busy: `music_steal` in src/music_synth.jo) is one rule for every piece; no piece sets its own. No piece is transposed, and the packer cuts nothing except the Greek songs\' introductions and interludes.')
    out('')
    out('**Catalogue numbers** are positions in `MUSIC_PIECES` (data/music/catalogue.json), the numbers the radio, the band and the title use. The `L` numbers are positions in the LOGH list (from 1, in the list\'s order: composer, then work).')
    out('')

    # --- the LOGH list
    def logh_table(rows_, prefix, start=1):
        out('| # | Work | Composer | Year (first published unless marked) | Status | Used in LOGH | In the game | Source, or what stops it | Heard |')
        out('|---|---|---|---|---|---|---|---|---|')
        for k, r in enumerate(rows_):
            anchor = f'<a id="{prefix}{k + start}"></a>{prefix}{k + start}'
            use = (r['use'] or '—').replace(' (film)', '')
            if r.get('film'):
                use += ('<br>' if use != '—' else '') + r['film']
            inc = ', '.join(f'[#{index[p]}](#p{index[p]}) {cat[index[p]]["title"]}' for p in r['pieces']) or '—'
            src_ = r['source'] or ''
            note = r['note'] or ''
            if r['pieces']:
                srccell = note or 'see the catalogue rows'
            else:
                srccell = (note + (' ' if note and src_ else '') + (('Source: ' + src_) if src_ else '')).strip()
            out('| ' + ' | '.join(cell(x) for x in [anchor, r['work'], r['composer'], r['year'], STATUS[r['status']], use, inc, srccell, logh_heard(r['pieces'])]) + ' |')
    out('## The LOGH list, work by work')
    out('')
    out(f'Every one of the {len(all_logh)} works on the user\'s list (the original 110-episode OVA, the films *My Conquest Is the Sea of Stars* and *Overture to a New War*, and *Gaiden*; not *Die Neue These*). One row per work; "Used in LOGH" names the movements the earlier research (a scrape of Gineipaedia\'s per-episode music sections) found, with the films\' cues from the list; the list is a work-level catalogue, not a cue sheet. *Golden Wings* has no pre-existing classical cue. The list\'s "entries requiring closer identification" are folded into the rows they concern (the Shostakovich "Symphony No. 2, III" is not counted).')
    out('')
    logh_table(all_logh, 'L')
    out('')
    out('### More LOGH works from the earlier research, not on the list')
    out('')
    out('Works the earlier scrape found that the list does not name (marked LX).')
    out('')
    logh_table(notes['logh_extra'], 'LX')
    out('')

    # --- the catalogue
    out('## Every piece in the catalogue')
    out('')
    out('One row per catalogue number, in catalogue order. "LOGH" links to the row above; "—" means the piece is not on the LOGH list (an extra: the Greek songs, the dance band and café numbers, the period repertoire, the title music).')
    out('')
    out('| # | Piece and composer | LOGH | Year | Status | Instruments: in the game, and the source file | Scoring, versions | Performance treatment | Source and licence | Where it is heard | Minutes as played |')
    out('|---|---|---|---|---|---|---|---|---|---|---:|')
    for pi in piece_info:
        n = pi['notes']
        lcell = logh_link.get(pi['id'], '—')
        scoring = n.get('scoring', '')
        if n.get('versions'):
            scoring += ('<br>' if scoring else '') + '**Versions:** ' + n['versions']
        treat = '; '.join(pi['treat'])
        if n.get('note'):
            treat += '<br>' + n['note']
        instr = f'**Game:** {pi["game"]}<br>**Source file:** {pi["source"]}'
        out('| ' + ' | '.join(cell(x) for x in [f'<a id="p{pi["i"]}"></a>{pi["i"]}', f'**{pi["title"]}**<br>{pi["composer"]}<br>`{pi["id"]}`', lcell, pi['year'], pi['status'], instr, scoring, treat, pi['sourcecell'], '<br>'.join(pi['where']), f'{pi["minutes"]:.1f}']) + ' |')
    out('')

    # --- where it is heard
    out('## Where the music is heard')
    out('')
    out('### Radio rounds')
    out('')
    out('Each station plays its programme\'s round of pieces, one after another, each heard whole from its start, on the saved world clock (`radio_pool`, `radio_cue` in src/radio_synth.jo); every station joins the round at its own place (an offset of 1913 s times its number), so two stations on the same round are not on the same piece. The programme clock takes the news, weather, editorial and quiz minutes from the music ([docs/radio.md](radio.md)); hours are local time (the world\'s minute 0 is 09:30). The Blue Lantern and the dance-hour blocks turn between foxtrot, tango and waltz every half hour, so each of those three rounds airs a third of the time there. The first six stations are on the air by their own rules; the later stations by their blocks (`radio_blocks` in src/radio.jo).')
    out('')
    out('| Round | Stations and hours | Pieces | Length of the round | The round, in order (catalogue numbers) |')
    out('|---|---|---:|---:|---|')
    for rd in ROUND_ORDER:
        by_station = {}
        for name, khz, hours in rounds[rd]:
            by_station.setdefault((name, khz), []).append(hours)
        st_text = '<br>'.join(f'{name} {khz} kHz: ' + ', '.join(hs) for (name, khz), hs in by_station.items())
        members = pools[rd]
        total = sum(cat[m]['frames'] for m in members) / RATE
        out(f'| <a id="round-{rd}"></a>{ROUND_NAMES[rd]} | {cell(st_text)} | {len(members)} | {int(total // 3600)} h {int(total % 3600 // 60):02d} min | ' + ', '.join(f'[{m}](#p{m})' for m in members) + ' |')
    out('')
    out('The island round is also Archipelago Radio\'s and Radio Dawn\'s: Ikariotikos and the first eight Greek songs. The Café round is the lighter mixed list of Radio Porto Vecchio\'s mornings, Radio Mandolinata\'s mornings and the Meltemi Weather Wireless\'s tunes; the Café Aman round adds the two Hotel Ancora Greek songs. The spoken stations\' news and weather are read aloud by the announcer, not music; the Aegean Maritime Service plays no music (Morse, weather and shipping).')
    out('')
    out('### The hotel band')
    out('')
    out(f'The Hotel Ancora\'s band plays in the evening, from {hhmm(bar_start)} to {hhmm(bar_end)} (local time), the numbers of its set in order, round again until it stops, {bar_gap:g} seconds between numbers, in the open air of the terrace (the upright piano always). Its request list is the whole set: a number asked of the band (and tipped) is played next, then the evening goes on where it was. A number plays when its players are in their places (`src/band_life.jo`). The set (`BAR_SET` in src/bar_band.jo):')
    out('')
    out('| Order | Piece | Line-up | Evenings | Sung |')
    out('|---:|---|---|---|---|')
    for k, b in enumerate(bar):
        when = 'every evening' if b['nights'] == 1 else 'every other evening' if b['nights'] == 2 else f'one evening in {b["nights"]}'
        sung = 'yes' if b['sung'] else ''
        extra = f' (level {b["level"]:g})' if b['level'] != 1.0 else ''
        out(f'| {k + 1} | {linked_title(b["piece"], cat)} | {b["lineup"]}, the tune on the {b["lead"]}{extra} | {when} | {sung} |')
    out('')
    out('### The title music, and everything else')
    out('')
    out(f'- **Title music:** {linked_title(title, cat)} (src/title_music.jo): 19 bars, about 77 s, with a gain curve after the receiver.')
    out('- **Café Aman** is a radio station (1360 kHz, 21:00–05:00 local), not a place in the game: plucked strings, tangos round midnight.')
    out('- **Street musicians** play a generated plucked phrase (src/street_phrase.jo: a scale, a theme and its variations on a bouzouki part), not a catalogue piece; only the nearest musician is heard (src/life_audio.jo).')
    out('- **Scenarios:** no scenario cue uses a catalogue piece (the only users of `MUSIC_PIECES` are the radio, the hotel band, the title and the debug menu\'s audition list).')
    out('- **The announcer, Morse, the engine and the ambience** are not music and are not listed.')
    out('')

    # --- other candidates
    out('## Other candidates, not in the catalogue')
    out('')
    out('Pieces considered for a 1920s–30s Mediterranean radio (the earlier research; the ones now in the catalogue are not repeated here), and anything the user has requested. Same statuses.')
    out('')
    out('| Work | Composer | Year | Status | Source, or what stops it |')
    out('|---|---|---|---|---|')
    for c in notes['candidates'] + notes['requested']:
        srcc = (c.get('note', '') + (' ' if c.get('note') and c.get('source') else '') + (('Source: ' + c['source']) if c.get('source') else '')).strip()
        out('| ' + ' | '.join(cell(x) for x in [c['work'], c.get('composer', ''), c.get('year', '?'), STATUS[c.get('status', 'requested')], srcc]) + ' |')
    out('')
    out('## Adding a piece')
    out('')
    out('To put a new piece on the page, add a row with the status `requested`: a work, its composer, and anything you know (a year, a link, why). Either:')
    out('')
    out('- run `python3 tools/music_status.py --add "Composer; Work; year; a note or link"` (year, note and link are optional), which appends the row to `requested` in `data/music/status-notes.json` and rewrites this page; or')
    out('- edit `data/music/status-notes.json` yourself: add an object `{"composer": "...", "work": "...", "year": "...", "source": "...", "note": "..."}` to `requested`, then run `python3 tools/music_status.py`.')
    out('')
    out('An agent researching it changes `status` (to wanted, source found, blocked or not planned) and fills `source` and `note` in the same row; when the piece enters the catalogue (tools/music_pack.py `PIECES`, then `python3 tools/music_pack.py`) its row moves to the pieces\' notes (`pieces`, keyed by catalogue id) and, if it is on the LOGH list, its list row gains its `pieces`. The rest of the page is regenerated from the repository by `python3 tools/music_status.py`; `tests/music_status_test.py` fails when the page is out of date. A piece not public domain needs the user\'s explicit approval before anything is committed (see the rule above).')
    out('')
    out('## Gaps')
    out('')
    out('Fields that could not be determined are marked `?` on the page. They are:')
    out('')
    for g_ in dict.fromkeys(gaps):
        out(f'- {g_}')
    for r in all_logh + notes['logh_extra']:
        if r['year'] == '?':
            out(f'- {r["composer"]}, {r["work"]}: year')
    out('')
    return '\n'.join(lines) + '\n', notes


def add_request(spec):
    notes = json.loads(NOTES.read_text())
    parts = [x.strip() for x in spec.split(';')]
    if len(parts) < 2:
        sys.exit('usage: --add "Composer; Work; year; note"')
    row = dict(composer=parts[0], work=parts[1], year=parts[2] if len(parts) > 2 and parts[2] else '?', status='requested',
               source='', note=parts[3] if len(parts) > 3 else '')
    notes['requested'].append(row)
    NOTES.write_text(json.dumps(notes, indent=1, ensure_ascii=False) + '\n')


def main():
    args = sys.argv[1:]
    if args[:1] == ['--add']:
        add_request(args[1])
    text, _ = build()
    if args[:1] == ['--check']:
        if not OUT.exists() or OUT.read_text() != text:
            print('docs/music-status.md is out of date: run python3 tools/music_status.py')
            return 1
        return 0
    OUT.write_text(text)
    print(f'wrote {OUT} ({len(text.splitlines())} lines)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
