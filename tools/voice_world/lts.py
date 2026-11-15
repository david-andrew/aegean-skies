"""Letter-to-sound rules for words the lexicon lacks (the world's names and other foreign words,
read Greek-style), and the stress guess for them. Written for this project; the rule format is the classic context form

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


# Greek-style values (the user's decision, 2026-11-15): the rules read the world's names and
# other words the dictionary lacks; ordinary English words come from the dictionary.
#   a = ah, e = eh, i/y = ee, o = oh, ou = oo; ai = eh, ei/oi = ee, au/eu = av/ev; every vowel
#   letter is its own syllable; no silent letters but h and doubled consonants; s stays s.
rule('A', ('', 'AI', '', 'EH'), ('', 'AU', '', 'AA V'), ('', 'AY', '#', 'AA Y'), ('', 'AY', '', 'AY'), ('', 'A', '', 'AA'))
rule('B', ('', 'BB', '', 'B'), ('', 'B', '', 'B'))
rule('C', ('', 'CH', '', 'CH'), ('', 'CK', '', 'K'), ('', 'CC', '+', 'K S'), ('', 'CC', '', 'K'),
     ('', 'C', '+', 'S'), ('', 'C', '', 'K'))
rule('D', ('', 'DD', '', 'D'), ('', 'D', '', 'D'))
rule('E', ('', 'EI', '', 'IY'), ('', 'EU', '', 'EH V'), ('', 'EY', '', 'EH Y'), ('', 'EE', '', 'IY'), ('', 'E', '', 'EH'))
rule('F', ('', 'FF', '', 'F'), ('', 'F', '', 'F'))
rule('G', ('', 'GG', '', 'G'), ('', 'GH', '', 'G'), ('', 'G', '', 'G'))
rule('H', ('', 'H', '#', 'HH'), ('', 'H', '', ''))
rule('I', ('', 'I', '', 'IY'))
rule('J', ('', 'J', '', 'JH'))
rule('K', ('', 'KK', '', 'K'), ('', 'K', '', 'K'))
rule('L', ('', 'LL', '', 'L'), ('', 'L', '', 'L'))
rule('M', ('', 'MM', '', 'M'), ('', 'M', '', 'M'))
rule('N', ('', 'NG', '', 'NG G'), ('', 'NK', '', 'NG K'), ('', 'NN', '', 'N'), ('', 'N', '', 'N'))
rule('O', ('', 'OU', '', 'UW'), ('', 'OI', '', 'IY'), ('', 'OO', '', 'UW'), ('', 'OY', '', 'OY'), ('', 'O', '', 'OW'))
rule('P', ('', 'PH', '', 'F'), ('', 'PP', '', 'P'), ('', 'P', '', 'P'))
rule('Q', ('', 'QU', '', 'K W'), ('', 'Q', '', 'K'))
rule('R', ('', 'RR', '', 'R'), ('', 'RH', '', 'R'), ('', 'R', '', 'R'))
rule('S', ('', 'SH', '', 'SH'), ('', 'SS', '', 'S'), ('', 'S', '', 'S'))
rule('T', ('', 'TH', '', 'TH'), ('', 'TT', '', 'T'), ('', 'T', '', 'T'))
rule('U', ('', 'U', '', 'UW'))
rule('V', ('', 'V', '', 'V'))
rule('W', ('', 'WH', '', 'W'), ('', 'W', '', 'W'))
rule('X', ('', 'X', '', 'K S'))
rule('Y', (' ', 'Y', '#', 'Y'), ('', 'Y', '', 'IY'))
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
    """Which vowel phone carries the stress: the penultimate (a name's Greek pattern; the name
    list overrides it where the name says otherwise), the only one in a one-vowel word."""
    n = sum(1 for p in letters_to_phones(word) if p in VOW)
    return max(0, n - 2)


def pronounce(word):
    phones = letters_to_phones(word)
    target = stress_syllable(word)
    out = []
    k = 0
    for p in phones:
        if p in VOW:
            out.append(p + ('1' if k == target else '0'))
            k += 1
        else:
            out.append(p)
    if k and not any(p.endswith('1') for p in out):
        for i, p in enumerate(out):
            if p[:-1] in VOW:
                out[i] = p[:-1] + '1'
                break
    return out
