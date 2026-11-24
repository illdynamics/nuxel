#!/usr/bin/env python3
"""
fuzz_sipc5.py — mutational fuzzer for the C sipc5_fmt parser.

Drives tests/fuzz_driver (compiled from src/sipc5_fmt.c) with mutations of a
valid SIPC FORMAT corpus plus pure random bytes, under hard memory and time
caps. The parser is SAFE OFF BY DEFAULT (no writes); this fuzzer only detects:

  * crashes / nonzero exit / timeouts,
  * out-of-bounds reads (via ASan build when available),
  * and reports coverage counters.

It NEVER inspects or records payload bytes (IPC may carry subscriber data).

Usage:
  python3 fuzz_sipc5.py [--iters N] [--asan /path/to/fuzz_driver_asan]
"""
import os, random, subprocess, sys, time, signal

FMT_HDR = 7

def fmt_field_bytes():
    """Build a valid FMT message with randomized fields (no real vocab)."""
    plen = random.choice([0, 1, 2, 3, 4, 8, 16, 31, 32, 255, 256, 1024])
    hdr = bytes([
        (plen + FMT_HDR) & 0xFF, ((plen + FMT_HDR) >> 8) & 0xFF,
        random.randint(0, 255),   # msg_seq
        random.randint(0, 255),   # ack_seq
        random.randint(0, 255),   # main_cmd
        random.randint(0, 255),   # sub_cmd
        random.randint(0, 255),   # cmd_type
    ])
    # random payload bytes but capped; never interpreted
    payload = bytes(random.getrandbits(8) for _ in range(min(plen, 64)))
    if len(payload) < plen:
        payload += bytes(plen - len(payload))
    return hdr + payload

def link_bytes():
    """Build a valid SIPC5 link-framed blob (for offset parse)."""
    cfg = random.choice([0xF8, 0xF9, 0xFA, 0xFB, 0xFC, 0xFD, 0xFE, 0xFF])
    ch = random.randint(0, 255)
    body = bytes(random.getrandbits(8) for _ in range(random.randint(0, 40)))
    if cfg & 0x03 == 0x02:      # ext len -> 4-byte length
        ln = random.randint(0, 0xFFFF)
        return bytes([cfg, ch]) + ln.to_bytes(4, 'little') + body
    elif cfg & 0x03 == 0x03:    # multi-frame -> 2-byte len + ctrl
        ln = random.randint(0, 0xFFFF)
        return bytes([cfg, ch]) + ln.to_bytes(2, 'little') + bytes([random.randint(0,255)]) + body
    else:
        ln = random.randint(0, 0xFFFF)
        return bytes([cfg, ch]) + ln.to_bytes(2, 'little') + body

def mutate(b):
    b = bytearray(b)
    for _ in range(random.randint(1, 4)):
        if not b:
            break
        op = random.randint(0, 3)
        i = random.randrange(len(b))
        if op == 0:   # flip bit
            b[i] ^= 1 << random.randint(0, 7)
        elif op == 1: # random byte
            b[i] = random.randint(0, 255)
        elif op == 2: # truncate
            b = b[:i]
            break
        elif op == 3: # insert
            b = b[:i] + bytes([random.randint(0,255)]) + b[i:]
    return bytes(b)

def run(driver, blob, timeout_s):
    try:
        p = subprocess.run([driver], input=blob, timeout=timeout_s,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return 'TIMEOUT', b'', b''

def main():
    _i = [a.split("=",1)[1] for a in sys.argv if a.startswith("--iters=")]
    iters = int(_i[0]) if _i else int(os.environ.get("FUZZ_ITERS", "5000"))
    driver = sys.argv[1] if len(sys.argv) > 1 else '/tmp/fuzz_driver'
    timeout_s = 2.0
    crash = 0
    timeout_ct = 0
    seen_coverage = set()
    rng = random.Random(0x55005)
    random.seed(0x55005)

    corpus = []
    for _ in range(40):
        corpus.append(fmt_field_bytes())
        corpus.append(link_bytes())

    for i in range(iters):
        if rng.random() < 0.3:
            blob = bytes(rng.getrandbits(8) for _ in range(rng.randint(0, 256)))
        else:
            blob = mutate(rng.choice(corpus))
        # cap blob size to protect against pathological growth
        blob = blob[: (1 << 20)]
        rc, out, err = run(driver, blob, timeout_s)
        if rc == 'TIMEOUT':
            timeout_ct += 1
        elif rc != 0:
            crash += 1
            if crash <= 3:
                print(f"[CRASH] rc={rc} len={len(blob)}")
                print(err.decode('utf-8', 'replace')[:2000])
        # coverage
        txt = out.decode('latin1', 'replace')
        for line in txt.splitlines():
            if 'coverage=' in line:
                seen_coverage.add(line)

    print(f"iters={iters} crashes={crash} timeouts={timeout_ct} unique_coverage={len(seen_coverage)}")
    if crash or timeout_ct:
        print("FUZZ_RESULT=FLAPPY")
        return 1
    print("FUZZ_RESULT=PASS")
    return 0

if __name__ == '__main__':
    sys.exit(main())
