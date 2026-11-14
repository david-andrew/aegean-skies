"""Read an announcer data file (format AVX1, written by pack.py) back into Python: the phone set,
the diphone units (dequantised), the lexicon, the rules and the model section."""
import struct, zlib
import numpy as np


def read(path):
    b = zlib.decompress(open(path, 'rb').read(), -15)
    assert b[:4] == b'AVX1'
    at = 4
    n = struct.unpack_from('<H', b, at)[0]; at += 2
    phones = []
    for i in range(n):
        k = b[at]; phones.append(b[at + 1:at + 1 + k].decode()); at += 1 + k
    M, B, H, alpha = struct.unpack_from('<HHHf', b, at); at += 10
    scale = np.array(struct.unpack_from('<%df' % M, b, at)); at += 4 * M
    nu = struct.unpack_from('<H', b, at)[0]; at += 2
    W = M + B + 1
    units = {}
    for u in range(nu):
        a, c, count, left, right = struct.unpack_from('<BBHHH', b, at); at += 8
        f = np.zeros((2 * H, W))
        for j in range(2 * H):
            f[j, :M] = np.frombuffer(b, np.int8, M, at) * scale; at += M
            f[j, M:M + B] = np.frombuffer(b, np.uint8, B, at) / 255.0; at += B
            f[j, M + B] = b[at] / 255.0; at += 1
        units[(phones[a], phones[c])] = dict(frames=f, count=count, left=left / 1000.0, right=right / 1000.0)
    lex = {}
    nw = struct.unpack_from('<I', b, at)[0]; at += 4
    for i in range(nw):
        k = b[at]; w = b[at + 1:at + 1 + k].decode(); at += 1 + k
        k = b[at]; codes = list(b[at + 1:at + 1 + k]); at += 1 + k
        lex[w] = [phones[c & 63] + (str(c >> 6) if phones[c & 63] in VOWEL_SET else '') for c in codes]
    nr = struct.unpack_from('<H', b, at)[0]; at += 2
    for i in range(nr):
        for p in range(3):
            k = b[at]; at += 1 + k
        k = b[at]; at += 1 + k
    model = {}
    if at + 2 <= len(b):
        nm = struct.unpack_from('<H', b, at)[0]; at += 2
        for i in range(nm):
            k = b[at]; name = b[at + 1:at + 1 + k].decode(); at += 1 + k
            k = struct.unpack_from('<H', b, at)[0]; at += 2
            model[name] = list(struct.unpack_from('<%df' % k, b, at)); at += 4 * k
    return dict(phones=phones, M=M, B=B, H=H, alpha=alpha, units=units, lexicon=lex, model=model)


VOWEL_SET = {'AA', 'AE', 'AH', 'AO', 'AW', 'AY', 'EH', 'ER', 'EY', 'IH', 'IY', 'OW', 'OY', 'UH', 'UW'}
