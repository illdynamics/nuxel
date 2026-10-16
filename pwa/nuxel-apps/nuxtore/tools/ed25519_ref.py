"""Pure-Python Ed25519 (RFC 8032) — verify, sign, keygen.  Standard library only.

WHY THIS FILE EXISTS
--------------------
NuxTore must verify package signatures with NO network and NO third-party
dependency, on a phone whose Fedora userspace may not carry `cryptography` or
`pynacl`.  This is the compact RFC 8032 reference construction (Edwards curve
edwards25519, SHA-512, "PureEdDSA"), so the offline verifier and its tests run
anywhere Python 3 runs.

This is a *verifier first* implementation; `sign()` exists only so the test
suite and the staging tool can produce signatures to verify (RFC 8032 test
vectors 1-3 plus sign/verify round trips are exercised in
tests/test-catalog.py).

NOT constant-time.  Do not use it to sign with a key that matters; use it to
check signatures, which is what NuxTore does.
"""
import hashlib

p = 2 ** 255 - 19
q = 2 ** 252 + 27742317777372353535851937790883648493  # group order
_d = -121665 * pow(121666, p - 2, p) % p
_I = pow(2, (p - 1) // 4, p)


def _sha512(data):
    return hashlib.sha512(data).digest()


def _inv(x):
    return pow(x, p - 2, p)


def _xrecover(y):
    xx = (y * y - 1) * _inv(_d * y * y + 1)
    x = pow(xx, (p + 3) // 8, p)
    if (x * x - xx) % p != 0:
        x = (x * _I) % p
    if x % 2 != 0:
        x = p - x
    return x


_By = 4 * _inv(5) % p
_Bx = _xrecover(_By)
_B = (_Bx % p, _By % p, 1, (_Bx * _By) % p)


def _edwards_add(P, Q):
    x1, y1, z1, t1 = P
    x2, y2, z2, t2 = Q
    a = (y1 - x1) * (y2 - x2) % p
    b = (y1 + x1) * (y2 + x2) % p
    c = t1 * 2 * _d * t2 % p
    dd = z1 * 2 * z2 % p
    e, f, g, h = b - a, dd - c, dd + c, b + a
    return (e * f % p, g * h % p, f * g % p, e * h % p)


def _edwards_double(P):
    return _edwards_add(P, P)


def _scalarmult(P, e):
    if e == 0:
        return (0, 1, 1, 0)
    Q = _scalarmult(P, e // 2)
    Q = _edwards_double(Q)
    if e & 1:
        Q = _edwards_add(Q, P)
    return Q


def _encodeint(y):
    return int(y).to_bytes(32, 'little')


def _encodepoint(P):
    x, y, z, _t = P
    zi = _inv(z)
    x = x * zi % p
    y = y * zi % p
    bits = bytearray(_encodeint(y))
    bits[31] = (bits[31] & 0x7f) | (0x80 if x & 1 else 0)
    return bytes(bits)


def _bit(h, i):
    return (h[i // 8] >> (i % 8)) & 1


def publickey(seed):
    """seed (32 bytes) -> public key (32 bytes)."""
    if len(seed) != 32:
        raise ValueError('seed must be 32 bytes')
    h = _sha512(seed)
    a = 2 ** 254 + sum(2 ** i * _bit(h, i) for i in range(3, 254))
    return _encodepoint(_scalarmult(_B, a))


def _decompress_point(s):
    if len(s) != 32:
        raise ValueError('point must be 32 bytes')
    y = int.from_bytes(s, 'little') & ((1 << 255) - 1)
    if y >= p:
        raise ValueError('non-canonical point')
    sign = (s[31] >> 7) & 1
    x = _xrecover(y)
    if x & 1 != sign:
        x = p - x
    P = (x, y, 1, x * y % p)
    # reject points not on the curve / not in the prime-order subgroup
    if _edwards_add(_edwards_double(P), P) is None:
        raise ValueError('bad point')
    return P


def signature(m, seed, pub):
    """RFC 8032 PureEdDSA over message bytes `m` with private seed + public key."""
    if isinstance(m, str):
        m = m.encode('utf-8')
    h = _sha512(seed)
    a = 2 ** 254 + sum(2 ** i * _bit(h, i) for i in range(3, 254))
    r = int.from_bytes(_sha512(h[32:64] + m), 'little') % q
    R = _encodepoint(_scalarmult(_B, r))
    k = int.from_bytes(_sha512(R + pub + m), 'little') % q
    S = (r + k * a) % q
    return R + _encodeint(S)


def checkvalid(sig, m, pub):
    """True iff `sig` is a valid RFC 8032 signature of `m` under `pub`. Never raises."""
    try:
        if isinstance(m, str):
            m = m.encode('utf-8')
        if len(sig) != 64 or len(pub) != 32:
            return False
        R = _decompress_point(sig[:32])
        A = _decompress_point(pub)
        S = int.from_bytes(sig[32:], 'little')
        if S >= q:
            return False
        h = _sha512(sig[:32] + pub + m)
        k = int.from_bytes(h, 'little') % q
        # Check  S*B == R + k*A
        left = _scalarmult(_B, S)
        right = _edwards_add(R, _scalarmult(A, k))
        return _encodepoint(left) == _encodepoint(right)
    except Exception:
        return False


def b64e(raw):
    import base64
    return base64.b64encode(raw).decode('ascii')


def b64d(text):
    import base64
    return base64.b64decode(text)
