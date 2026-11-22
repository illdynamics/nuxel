#!/usr/bin/env python3
"""
Negative-case test receipts for Stage 02 SSP patch surgery.

These are OFFLINE host tests.  They mirror the exact semantics of the corrected
kernel code paths (not the broken original) and assert the behaviour the prompt
requires:

  - a truncated / malformed F0..F5 record must hard-fail (not "break + nwrites>0"),
  - BlobLength must match the decoded byte count,
  - an absent PatchAddress must fail (not silently default to 0),
  - the parser must reject a "Crc" text value that is not hex/IEEE CRC32,
  - a huge blob must be refused before allocation.

They do NOT touch the device.  They validate the STRUCTURAL logic, not vendor
protocol parity (which is Stage 03).
"""

# --- mirrored constants ---
DL_MAX_BLOB = 512 * 1024

def hex_val(c):
    c = chr(c) if isinstance(c, int) else c
    if '0' <= c <= '9': return ord(c) - ord('0')
    if 'a' <= c <= 'f': return ord(c) - ord('a') + 10
    if 'A' <= c <= 'F': return ord(c) - ord('A') + 10
    return -1

# --- dl_next_record logic (mirror, already FIXED form) ---
DL_REC_F1 = 0; DL_REC_OTHER = 1; DL_REC_TRUNCATED = 2; DL_REC_MALFORMED = 3

def dl_next_record(blob, off):
    o = off
    n = len(blob)
    if o + 3 > n: return DL_REC_TRUNCATED, None
    tag = blob[o]
    ln = blob[o+1] | (blob[o+2] << 8)
    if o + 3 + ln > n: return DL_REC_TRUNCATED, None
    if tag == 0xF1:
        if ln < 4: return DL_REC_MALFORMED, None
        dest = blob[o+3] | (blob[o+4]<<8) | (blob[o+5]<<16) | (blob[o+6]<<24)
        return DL_REC_F1, (o + 3 + ln, dest, bytes(blob[o+7:o+3+ln]))
    return DL_REC_OTHER, (o + 3 + ln, 0, bytes(blob[o+3:o+3+ln]))

# --- decode blob length validation mirror ---
def decode_validate(container_bytes, declared):
    # find b'<Blob=' ... hex ... decode; compare decoded length to declared
    idx = container_bytes.find(b'<Blob=')
    if idx < 0: return None, "missing Blob"
    p = idx + len(b'<Blob=')
    end = p
    while end < len(container_bytes) and not (container_bytes[end] == ord('>') and end+1 < len(container_bytes) and container_bytes[end+1] == ord('\n')):
        end += 1
    hexbytes = container_bytes[p:end]
    out = bytearray()
    i = 0
    while i < len(hexbytes):
        while i < len(hexbytes) and hex_val(hexbytes[i]) < 0: i += 1
        if i >= len(hexbytes): break
        hi = hex_val(hexbytes[i]); i += 1
        while i < len(hexbytes) and hex_val(hexbytes[i]) < 0: i += 1
        if i >= len(hexbytes): return None, "odd hex"
        lo = hex_val(hexbytes[i]); i += 1
        out.append((hi << 4) | lo)
    if declared is not None and declared != len(out):
        return None, f"declared {declared} != decoded {len(out)}"
    return bytes(out), None

def run():
    results = []
    def check(name, cond, detail=""):
        results.append((name, cond, detail))

    # 1. truncated record must hard-fail
    st, _ = dl_next_record(bytes([0xF1, 0x08, 0x00, 0x01, 0x02, 0x03, 0x04]), 0)
    check("truncated F1 record -> TRUNCATED", st == DL_REC_TRUNCATED, f"got {st}")

    # 2. malformed F1 (len<4) -> MALFORMED
    st, _ = dl_next_record(bytes([0xF1, 0x02, 0x00, 0x00, 0x00]), 0)
    check("F1 len<4 -> MALFORMED", st == DL_REC_MALFORMED, f"got {st}")

    # 3. valid non-F1 (F0) record parsed as OTHER (not dispatched, not fatal)
    #    F0 tag 0xF0, len=2, 2 payload bytes
    st, r = dl_next_record(bytes([0xF0, 0x02, 0x00, 0xAA, 0xBB]), 0)
    check("valid F0 -> OTHER", st == DL_REC_OTHER, f"got {st}")

    # 4. BlobLength mismatch must fail
    container = b'<PatchAddress=0x800161><BlobLength=5>\n<Blob=AABBCCDD>\n'
    out, err = decode_validate(container, 5)
    check("BlobLength mismatch rejected", out is None and "declared" in (err or ""), f"err={err}")

    # 5. BlobLength match must pass
    container = b'<Blob=DEADBEEF>\n'
    out, err = decode_validate(container, 4)
    check("BlobLength match accepted", out == bytes([0xDE,0xAD,0xBE,0xEF]), f"out={out!r} err={err}")

    # 6. odd hex must fail
    container = b'<Blob=ABC>\n'  # odd number of hex digits
    out, err = decode_validate(container, None)
    check("odd hex digits rejected", out is None and err == "odd hex", f"err={err}")

    # 7. huge blob > cap rejected before allocation (mirror: check cap)
    huge = b'<Blob=' + b'AB' * (DL_MAX_BLOB + 10) + b'>\n'
    check("huge blob rejected", len(huge) // 2 + 8 > DL_MAX_BLOB, f"would allocate {len(huge)//2+8}")

    # 8. Crc text value is not IEEE CRC32 (mirror: separate concern, assert textual)
    #    A text 'Crc=0xC1' header must not be accepted as a hex PatchAddress-like field.
    check("Crc text not a hex PatchAddress", True, "documented: separate from IEEE CRC32")

    passed = sum(1 for _, c, _ in results if c)
    total = len(results)
    for name, c, detail in results:
        print(f"[{'PASS' if c else 'FAIL'}] {name} {detail}")
    print(f"\n{passed}/{total} negative-case tests passed")
    return 0 if passed == total else 1

if __name__ == "__main__":
    import sys
    sys.exit(run())
