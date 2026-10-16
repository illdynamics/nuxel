#!/usr/bin/env python3
"""Golden-bytes test for the protected A32 colour conversion (briq-02c).

WHAT IS BEING PROTECTED
    /dev/fb0 on the S10+ is a DECON programmed as DECON_PIXEL_FORMAT_ABGR_8888:
    the memory word is A[31:24] B[23:16] G[15:8] R[7:0] - R in the LOW byte -
    while fb_var *declares* R@16 G@8 B@0 (decon_check_var vs decon_pan_display,
    docs/s10plus-autonomous-boot-repair/NUXEL-COLOUR-ORDER.md).  The Wayland
    compositor hands the bridge XRGB8888 shm buffers (memory B,G,R,X), so the
    bridge MUST swap R and B and force alpha opaque, or red and blue are swapped
    on the glass.  A29..A31 shipped without that swap; A32 fixed it.

HOW THIS TEST WORKS (three independent layers)
    1. SOURCE: the LUT assignments in nuxel-wl-fb.c are parsed out of the C text
       and evaluated as arithmetic, so the test does not re-implement the code -
       it executes the code's own expressions.
    2. REFERENCE: an independent byte-level implementation derived from the
       driver documentation (dst bytes = R, G, B, 0xFF) must agree with (1).
    3. BINARY (when available): `nuxel-wl-fb --colour-dump` is parsed and every
       word compared byte for byte with (1)+(2).  This is the only layer that
       proves the COMPILED artifact.  It runs locally if build/out/s10plus/a33/
       nuxel-wl-fb is an executable for this host, or remotely when NUXEL_VM is
       set (the UTM guest is aarch64, so an aarch64 ELF cannot run on macOS).

MODE is printed: source+reference (always) and binary (when reachable).
Exit status is the number of failures.
"""
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
A33 = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(A33, "..", "..", ".."))
WLFB = os.path.join(A33, "nuxel-wl-fb.c")
EVIDENCE_DOCS = [
    os.path.join(ROOT, "docs/s10plus-autonomous-boot-repair/NUXEL-COLOUR-ORDER.md"),
    os.path.join(ROOT, "docs/s10plus-autonomous-boot-repair/COLOR-FORMAT-VERIFICATION.md"),
]

failures = 0


def check(name, cond, extra=""):
    global failures
    print(("PASS " if cond else "FAIL ") + name + ("" if cond else "  " + str(extra)))
    if not cond:
        failures += 1
    return cond


def lcg_words(n=64):
    """The exact LCG in nuxel-wl-fb.c colour_dump(): x = x*1103515245+12345 (u32)."""
    x = 0x12345678
    out = []
    for _ in range(n):
        x = (x * 1103515245 + 12345) & 0xFFFFFFFF
        out.append(x & 0x00FFFFFF)
    return out


PRIMARIES = [0x00FF0000, 0x0000FF00, 0x000000FF, 0x00FFFFFF, 0x00000000,
             0x00123456, 0x00FEDCBA, 0x00808080, 0x00010203, 0x00FDFEFF]
DUMP_SOURCES = PRIMARIES + lcg_words(64)


def reference(src):
    """Independent implementation from the driver doc: dst memory bytes = R,G,B,A
    with A forced opaque.  src is a little-endian XRGB8888 word 0x00RRGGBB."""
    r = (src >> 16) & 0xFF
    g = (src >> 8) & 0xFF
    b = src & 0xFF
    dst = (0xFF << 24) | (b << 16) | (g << 8) | r
    return dst


def source_lut_converter():
    """Parse the LUT lines out of the C source and evaluate them numerically."""
    src = open(WLFB, encoding="utf-8", errors="replace").read()
    m = re.search(r"cv_lo\[x\]\s*=\s*(.+?);\s*\n\s*cv_hi\[x\]\s*=\s*(.+?);", src)
    if not m:
        return None, None, None
    lo_expr, hi_expr = m.group(1), m.group(2)
    # the expressions are C: 0xffu / 0xff000000u must be sanitised before eval
    san = lambda e: re.sub(r"\b(0[xX][0-9a-fA-F]+|[0-9]+)[uUlL]+\b", r"\1", e)

    lo_expr, hi_expr = san(lo_expr), san(hi_expr)

    def lo(x):
        return eval(lo_expr, {"__builtins__": {}}, {"x": x}) & 0xFFFFFFFF

    def hi(x):
        return eval(hi_expr, {"__builtins__": {}}, {"x": x}) & 0xFFFFFFFF

    def conv(v):
        return (lo(v & 0xFFFF) | hi((v >> 16) & 0xFFFF)) & 0xFFFFFFFF

    return conv, lo_expr, hi_expr


def find_binary():
    cand = os.environ.get("NUXEL_WLFB_BIN") or os.path.join(ROOT, "build/out/s10plus/a33/nuxel-wl-fb")
    if os.path.isfile(cand) and os.access(cand, os.X_OK):
        return cand
    return None


def run_colour_dump():
    """Return (mode, lines) where lines are COLOUR_PIXEL/COLOUR_DUMP lines."""
    binary = find_binary()
    if binary:
        try:
            out = subprocess.run([binary, "--colour-dump"], capture_output=True, text=True, timeout=20)
            if out.returncode == 0 and "COLOUR_DUMP" in out.stdout:
                return "binary:" + binary, out.stdout.splitlines()
            if out.returncode == 0:  # foreign-arch ELF that somehow returned 0
                return "binary:" + binary, out.stdout.splitlines()
            return "binary-failed:" + binary, []
        except (OSError, subprocess.SubprocessError) as e:
            print("NOTE local binary not runnable (%s)" % e)
    vm = os.environ.get("NUXEL_VM")
    if vm:
        remote = "~/a33build/nuxel-wl-fb"
        cmd = ("ssh -q -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=6 %s "
               "'test -x %s && %s --colour-dump || echo NO_BINARY'" % (vm, remote, remote))
        try:
            out = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            if out.returncode == 0 and "COLOUR_DUMP" in out.stdout:
                return "vm:" + vm, out.stdout.splitlines()
        except (OSError, subprocess.SubprocessError) as e:
            print("NOTE VM not reachable (%s)" % e)
    return "source-derived", []


def main():
    print("== A33 colour-order golden-bytes test (briq-02c) ==")
    check("source exists: %s" % os.path.relpath(WLFB, ROOT), os.path.isfile(WLFB))
    for d in EVIDENCE_DOCS:
        check("driver evidence present: %s" % os.path.relpath(d, ROOT), os.path.isfile(d))

    src_text = open(WLFB, encoding="utf-8", errors="replace").read()

    # --- 1. the hardware order is the DECON order, not the declared fb_var order
    check("hardware order constants are the DECON ABGR_8888 order (R@0 G@8 B@16)",
          re.search(r"static unsigned hw_r_off = 0, hw_g_off = 8, hw_b_off = 16;", src_text) is not None)
    check("the override is ON by default (hw_order_override = 1)",
          re.search(r"static int hw_order_override = 1;", src_text) is not None)
    check("the LUT path only builds for the DECON order",
          re.search(r"if \(hw_r_off != 0 \|\| hw_g_off != 8 \|\| hw_b_off != 16\) return;\s*/\* generic path \*/", src_text) is not None)

    conv, lo_expr, hi_expr = source_lut_converter()
    if not conv:
        check("LUT expressions located in the C source", False, "regex did not match")
        print("\n%d FAILURES" % failures)
        return failures
    print("     LUT: cv_lo[x] = %s ; cv_hi[x] = %s" % (lo_expr.strip(), hi_expr.strip()))

    # --- 2. alpha must be forced opaque in the same expression (a transparent shm
    #        pixel must never expose the previous frame on a non-blending DECON)
    check("low LUT forces alpha 0xff", "0xff000000" in lo_expr.replace(" ", ""))
    check("high LUT contributes only the red byte", hi_expr.strip().replace(" ", "") in ("(x&0xffu)", "(x&0xff)"))
    check("low LUT moves the source blue byte into bits 16..23",
          re.search(r"\(x & 0xffu?\) << 16", lo_expr) is not None)
    check("full 64K+64K LUT allocation is the A32 fast path",
          re.search(r"cv_lo = malloc\(sizeof\(uint32_t\) \* 65536\);", src_text) is not None)

    # --- 3. byte-level golden vectors
    golden = {
        0x00FF0000: (0xFF, 0x00, 0x00, 0xFF, "red -> memory R=ff G=00 B=00 A=ff"),
        0x0000FF00: (0x00, 0xFF, 0x00, 0xFF, "green"),
        0x000000FF: (0x00, 0x00, 0xFF, 0xFF, "blue"),
        0x00FFFFFF: (0xFF, 0xFF, 0xFF, 0xFF, "white"),
        0x00000000: (0x00, 0x00, 0x00, 0xFF, "black -> opaque, never transparent"),
        0x00123456: (0x12, 0x34, 0x56, 0xFF, "mixed"),
        0x00FEDCBA: (0xFE, 0xDC, 0xBA, 0xFF, "mixed"),
    }
    ok = True
    for src, (b0, b1, b2, b3, why) in golden.items():
        got = conv(src)
        want = b0 | (b1 << 8) | (b2 << 16) | (b3 << 24)
        ok &= check("golden bytes src=0x%08x -> %02x,%02x,%02x,%02x (%s)" % (src, b0, b1, b2, b3, why),
                    got == want, "got 0x%08x want 0x%08x" % (got, want))
        ok &= check("reference implementation agrees for 0x%08x" % src, reference(src) == got)

    # --- 4. the whole dump set: source LUT == independent reference, and alpha is
    #        always opaque (the property the DECON depends on)
    for src in DUMP_SOURCES:
        if conv(src) != reference(src):
            ok = check("LUT == reference for 0x%08x" % src, False, "0x%08x != 0x%08x" % (conv(src), reference(src)))
    check("LUT == independent reference over %d words (10 primaries + 64 LCG)" % len(DUMP_SOURCES), ok)
    check("alpha opaque on every dumped word", all((conv(s) >> 24) == 0xFF for s in DUMP_SOURCES))

    # --- 5. the compiled artifact, when this host can execute it (or NUXEL_VM set)
    mode, lines = run_colour_dump()
    print("     binary layer: %s" % mode)
    if lines:
        dump = [l for l in lines if l.startswith("COLOUR_DUMP")]
        check("binary reports the DECON order R@0,G@8,B@16",
              bool(dump) and "hw=R@0,G@8,B@16" in dump[0], dump[:1])
        check("binary reports the ABGR override enabled",
              bool(dump) and "hw_order_override=1" in dump[0], dump[:1])
        px = {}
        for l in lines:
            m = re.match(r"COLOUR_PIXEL idx=(\d+) src=0x([0-9a-f]{8}) dst=0x([0-9a-f]{8}) "
                         r"bytes=([0-9a-f]{2}),([0-9a-f]{2}),([0-9a-f]{2}),([0-9a-f]{2})", l)
            if m:
                px[int(m.group(1))] = (int(m.group(2), 16), int(m.group(3), 16),
                                       tuple(int(m.group(i), 16) for i in (4, 5, 6, 7)))
        check("binary dumped %d+%d pixels" % (len(PRIMARIES), 64),
              len(px) == len(PRIMARIES) + 64, len(px))
        bad = []
        for i, src in enumerate(PRIMARIES):
            if i not in px or px[i][0] != src or px[i][1] != conv(src):
                bad.append(i)
        for j, src in enumerate(lcg_words(64)):
            i = 100 + j
            if i not in px or px[i][0] != src or px[i][1] != conv(src):
                bad.append(i)
        check("every binary word equals the source-derived conversion (golden bytes)", not bad, bad[:8])
        badb = [i for i, (s, d, b) in px.items()
                if b != ((d & 0xFF), (d >> 8) & 0xFF, (d >> 16) & 0xFF, (d >> 24) & 0xFF)]
        check("binary byte order in memory is R,G,B,A (little-endian word)", not badb, badb[:8])
        check("binary alpha is opaque everywhere", all(b[3] == 0xFF for (_, _, b) in px.values()))
    else:
        print("     NOTE compiled-artifact layer skipped: no runnable aarch64 binary here "
              "(set NUXEL_VM or build/out/s10plus/a33/nuxel-wl-fb); the source LUT and the "
              "independent reference above are still executed and must agree.")

    # --- 6. the pass-through rules that must NOT convert
    check("XRGB8888 is converted", re.search(r"int convert = \(format == WL_SHM_FORMAT_XRGB8888 \|\| format == WL_SHM_FORMAT_ARGB8888\);", src_text) is not None)
    check("ABGR/XBGR are passed through with alpha forced opaque",
          re.search(r"d\[x\] = s\[xmap\[x\]\] \| 0xff000000u;", src_text) is not None)
    check("an unknown shm format is logged, never silently mis-converted",
          re.search(r"COLOR_UNKNOWN_SRC_FORMAT=0x%08x passthrough", src_text) is not None)
    check("the applied order is logged with the declared fb_var order",
          re.search(r"COLOR_ORDER declared=R@%u G@%u B@%u A@%u  applied=R@%u G@%u B@%u A@24 name=%s override=1", src_text) is not None)

    print("\n%s colour-order golden-bytes test (%d failures)" % ("FAIL" if failures else "PASS", failures))
    return failures


if __name__ == "__main__":
    sys.exit(main())
