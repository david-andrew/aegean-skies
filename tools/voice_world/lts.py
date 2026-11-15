"""Letter-to-sound rules for words the lexicon lacks (mostly the game's invented names), and the
stress guess for them. Written for this project; the rule format is the classic context form

    (left context, letters, right context, phones)

Contexts, read outward from the letters:
    ' '  word edge        '#'  one or more vowels     ':'  zero or more consonants
    '^'  one consonant    '+'  E, I or Y              '.'  a voiced consonant
    '%'  a suffix: E, ER, ES, ED, ING, ELY then the word edge
    anything else: those letters
Rules for a letter are tried in order; the first whose contexts match wins. The same table is
exported to the game, which runs the same matcher (src/voice_text.jo).
"""

VOWEL = set('AEIOUY')
VOICED = set('BDGJLMNRVWZ')
SUFFIXES = ['ELY', 'ING', 'ER', 'ES', 'ED', 'E']

R = []


def rule(letter, *rows):
    for row in rows:
        left, mid, right, out = row
        R.append((left, mid, right, out))


rule('A',
     (' ', 'A', ' ', 'AH'), ('', 'AR', '#', 'EH R'), ('', 'AR', '', 'AA R'), ('', 'AIR', '', 'EH R'),
     ('', 'AI', '', 'EY'), ('', 'AY', '', 'EY'), ('', 'AU', '', 'AO'), ('', 'AW', '', 'AO'),
     ('', 'ALL', '', 'AO L'), ('', 'ALK', '', 'AO K'), ('', 'AL', '^', 'AE L'),
     ('', 'A', '^E ', 'EY'), ('', 'A', '^%', 'EY'), ('', 'A', '^+#', 'EY'),
     ('', 'A', ' ', 'AH'), ('', 'A', '', 'AE'))
rule('B', ('', 'BB', '', 'B'), ('M', 'B', ' ', ''), ('', 'B', '', 'B'))
rule('C', ('', 'CH', '', 'CH'), ('', 'CK', '', 'K'), ('', 'CC', '+', 'K S'), ('', 'CC', '', 'K'),
     ('', 'C', '+', 'S'), ('', 'C', '', 'K'))
rule('D', ('', 'DD', '', 'D'), ('', 'DG', '+', 'JH'), ('#:', 'DED', ' ', 'D IH D'), ('', 'D', '', 'D'))
rule('E',
     (' ', 'E', ' ', 'IY'), ('#:', 'E', ' ', ''), (' :', 'E', ' ', 'IY'), ('', 'EAU', '', 'OW'),
     ('', 'EA', 'SUR', 'EH'), ('', 'EA', 'THER', 'EH'), ('', 'EA', 'LTH', 'EH'), ('', 'EA', 'R', 'IY'), ('', 'EA', '', 'IY'), ('', 'EE', '', 'IY'), ('', 'EI', '', 'EY'),
     ('', 'EY', ' ', 'IY'), ('', 'EY', '', 'EY'), ('', 'EU', '', 'Y UW'), ('', 'EW', '', 'Y UW'),
     ('', 'ER', '#', 'EH R'), ('', 'ER', '', 'ER'), ('#:', 'ES', ' ', 'IH Z'), ('#:', 'ED', ' ', 'D'),
     ('', 'E', '^E ', 'IY'), ('', 'E', '', 'EH'))
rule('F', ('', 'FF', '', 'F'), ('', 'F', '', 'F'))
rule('G', ('', 'GG', '', 'G'), ('', 'GH', ' ', ''), ('', 'GH', '', 'G'), ('', 'GN', ' ', 'N'),
     (' ', 'G', '+', 'JH'), ('', 'GE', ' ', 'JH'), ('', 'G', '', 'G'))
rule('H', (' ', 'HOUR', '', 'AW ER'), ('', 'H', '#', 'HH'), ('', 'H', '', ''))
rule('I',
     ('', 'IGH', '', 'AY'), ('', 'IE', ' ', 'IY'), ('', 'IER', '', 'IY ER'), ('', 'IE', '', 'IY'),
     ('', 'IRR', '', 'IH R'), ('', 'IR', '#', 'AY R'), ('', 'IR', '', 'ER'), ('', 'ION', '', 'Y AH N'),
     ('', 'I', '^E ', 'AY'), ('', 'I', '^%', 'AY'), (' ', 'I', ' ', 'AY'), ('', 'I', ' ', 'IY'),
     ('', 'I', '#', 'IY'), ('', 'I', '', 'IH'))
rule('J', ('', 'J', '', 'JH'))
rule('K', (' ', 'KN', '', 'N'), ('', 'KK', '', 'K'), ('', 'K', '', 'K'))
rule('L', ('', 'LL', '', 'L'), ('', 'L', '', 'L'))
rule('M', ('', 'MM', '', 'M'), ('', 'M', '', 'M'))
rule('N', ('I', 'NGER', ' ', 'NG ER'), ('I', 'NGER', 'S ', 'NG ER'), ('O', 'NGER', '', 'NG G ER'), ('U', 'NGER', '', 'NG G ER'),
     ('', 'NG', '+', 'N JH'), ('', 'NG', '', 'NG'), ('', 'NK', '', 'NG K'), ('', 'NN', '', 'N'), ('', 'N', '', 'N'))
rule('O',
     (' ', 'O', ' ', 'OW'), ('', 'OO', 'R', 'AO'), ('', 'OO', 'K', 'UH'), ('', 'OO', '', 'UW'),
     ('', 'OA', '', 'OW'), ('', 'OI', '', 'OY'), ('', 'OY', '', 'OY'), ('', 'OU', 'GHT', 'AO'),
     ('', 'OU', '', 'AW'), ('', 'OW', ' ', 'OW'), ('', 'OW', '', 'AW'), ('#:', 'OR', ' ', 'ER'), ('#:', 'OR', 'S ', 'ER'), ('', 'OR', '', 'AO R'),
     ('', 'O', '^E ', 'OW'), ('', 'O', '^%', 'OW'), ('', 'O', ' ', 'OW'), ('', 'O', '#', 'OW'),
     ('', 'O', '', 'AA'))
rule('P', ('', 'PH', '', 'F'), ('', 'PP', '', 'P'), ('', 'P', '', 'P'))
rule('Q', ('', 'QU', '', 'K W'), ('', 'Q', '', 'K'))
rule('R', ('', 'RR', '', 'R'), ('', 'RH', '', 'R'), ('', 'R', '', 'R'))
rule('S',
     ('', 'SCH', '', 'S K'), ('', 'SH', '', 'SH'), ('', 'SS', '', 'S'), ('', 'SION', '', 'ZH AH N'), ('#', 'SURE', '', 'ZH ER'),
     ('#', 'S', '#', 'Z'), ('.', 'S', ' ', 'Z'), ('#', 'S', ' ', 'Z'), ('', 'S', '', 'S'))
rule('T',
     ('', 'TCH', '', 'CH'), ('#', 'TH', 'ER', 'DH'), ('', 'TH', '', 'TH'), ('', 'TION', '', 'SH AH N'), ('', 'TT', '', 'T'),
     ('', 'T', '', 'T'))
rule('U',
     ('', 'UR', '#', 'Y UH R'), ('', 'UR', '', 'ER'), ('', 'U', '^E ', 'UW'), ('', 'U', '^%', 'UW'),
     ('', 'U', ' ', 'UW'), ('', 'U', '#', 'UW'), ('', 'U', '', 'AH'))
rule('V', ('', 'V', '', 'V'))
rule('W', ('', 'WH', '', 'W'), (' ', 'WR', '', 'R'), ('', 'W', '', 'W'))
rule('X', (' ', 'X', '', 'Z'), ('', 'X', '', 'K S'))
rule('Y',
     (' ', 'Y', '#', 'Y'), ('', 'Y', '#', 'Y'), (' :', 'Y', ' ', 'AY'), ('#:', 'Y', ' ', 'IY'),
     ('^', 'Y', '^', 'IH'), ('', 'Y', '', 'IY'))
rule('Z', ('', 'ZZ', '', 'Z'), ('', 'Z', '', 'Z'))
rule("'", ('', "'", '', ''))

RULES = R


def _left(ctx, word, i):
    """Does ctx match the letters ending just before word[i]? Matched right to left."""
    j = i - 1
    for c in reversed(ctx):
        if c == ' ':
            if j >= 0:
                return False
        elif c == '#':
            if j < 0 or word[j] not in VOWEL:
                return False
            while j >= 0 and word[j] in VOWEL:
                j -= 1
            continue
        elif c == ':':
            while j >= 0 and word[j].isalpha() and word[j] not in VOWEL:
                j -= 1
            continue
        elif c == '^':
            if j < 0 or word[j] in VOWEL or not word[j].isalpha():
                return False
        elif c == '+':
            if j < 0 or word[j] not in 'EIY':
                return False
        elif c == '.':
            if j < 0 or word[j] not in VOICED:
                return False
        else:
            if j < 0 or word[j] != c:
                return False
        j -= 1
    return True


def _right(ctx, word, i):
    j = i
    n = len(word)
    k = 0
    while k < len(ctx):
        c = ctx[k]
        if c == ' ':
            if j < n:
                return False
        elif c == '#':
            if j >= n or word[j] not in VOWEL:
                return False
            while j < n and word[j] in VOWEL:
                j += 1
            k += 1
            continue
        elif c == ':':
            while j < n and word[j] not in VOWEL:
                j += 1
            k += 1
            continue
        elif c == '^':
            if j >= n or word[j] in VOWEL:
                return False
        elif c == '+':
            if j >= n or word[j] not in 'EIY':
                return False
        elif c == '.':
            if j >= n or word[j] not in VOICED:
                return False
        elif c == '%':
            rest = word[j:]
            return any(rest == s for s in SUFFIXES)
        else:
            if j >= n or word[j] != c:
                return False
        j += 1
        k += 1
    return True


def letters_to_phones(word):
    w = ''.join(c for c in word.upper() if c.isalpha() or c == "'")
    out = []
    i = 0
    while i < len(w):
        for left, mid, right, ph in RULES:
            if w.startswith(mid, i) and _left(left, w, i) and _right(right, w, i + len(mid)):
                out.extend(ph.split())
                i += len(mid)
                break
        else:
            i += 1
    return out


VOW = {'AA', 'AE', 'AH', 'AO', 'AW', 'AY', 'EH', 'ER', 'EY', 'IH', 'IY', 'OW', 'OY', 'UH', 'UW'}
LONG = {'AA', 'AO', 'AW', 'AY', 'EY', 'IY', 'OW', 'OY', 'UW'}


def stress_syllable(word):
    """Which vowel group of the spelling carries the stress. Two groups: the first. Longer:
    the penultimate if it is a digraph or is closed by two consonant letters (the Latin/Greek
    habit most invented names follow), else the antepenultimate. A final silent E is no group."""
    w = ''.join(c for c in word.upper() if c.isalpha())
    groups = []
    i = 0
    while i < len(w):
        if w[i] in VOWEL and not (w[i] == 'Y' and i + 1 < len(w) and w[i + 1] in VOWEL and i == 0):
            j = i
            while j < len(w) and w[j] in VOWEL:
                j += 1
            groups.append((i, j))
            i = j
        else:
            i += 1
    if len(groups) > 1 and groups[-1][0] == len(w) - 1 and w[-1] == 'E':
        groups.pop()
    n = len(groups)
    if n <= 2:
        return 0
    a, b = groups[-2]
    nxt = groups[-1][0]
    if b - a >= 2 or nxt - b >= 2:
        return n - 2
    return n - 3


# Unstressed full vowels from the rules reduce to schwa, as an English reader would say them
# ("compass", "balcony"); long vowels and diphthongs keep their quality. The game does the same.
REDUCE = {'AE', 'AA', 'EH', 'AO', 'UH'}


def pronounce(word):
    phones = letters_to_phones(word)
    target = stress_syllable(word)
    out = []
    k = 0
    for p in phones:
        if p in VOW:
            out.append(p + '1' if k == target else ('AH' if p in REDUCE else p) + '0')
            k += 1
        else:
            out.append(p)
    if k and not any(p.endswith('1') for p in out):
        for i, p in enumerate(out):
            if p[:-1] in VOW:
                out[i] = p[:-1] + '1'
                break
    return out
