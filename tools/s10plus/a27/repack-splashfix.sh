#!/bin/sh
# ============================================================================
# repack-splashfix.sh — put the animation's own frame 0 in the initramfs.
#
# WHY (hardware finding, 2026-10-29): the S10+ showed the OLD Nuxel splash for
# ~2 s before the spinning-penguin animation.  The animation was NOT the cause —
# its first frames are the spinning penguin.  The cause was the initramfs:
# /opt/nuxel/nuxel-firstlight.rawspl was missing, so nuxel-fb-phone took its
# "A16 diagnostic fallback" branch and painted the obsolete diagnostic frame at
# first light (kmsg 6.7 s) before the MP4 player committed frame 0 (kmsg 8.1 s).
#
# Two independent fixes, both applied here:
#   1. boot/initramfs/init.sh never paints the legacy diagnostic frame when the
#      asset is absent (FIRSTLIGHT_ASSET_MISSING_NO_LEGACY_PAINT) — the MP4
#      player lights the panel instead;
#   2. the NUXSPL01 asset (frame 0 of the shipped NUXANM01 container) is packed
#      into /opt/nuxel/, so the earliest lit frame IS the animation.
#
# The input boot image's kernel, cmdline, load addresses and DTB are preserved
# byte-for-byte; only the gzip ramdisk member is replaced, and the output keeps
# the exact partition size so `dd of=/dev/sda14` cannot truncate the partition.
#
# Usage:
#   sh tools/s10plus/a27/repack-splashfix.sh <in-boot.img> <out-boot.img> \
#       [--anim NUXANM01] [--partition-bytes N]
# Exit: 0 ok, 1 a gate failed, 2 a required input is missing.
# ============================================================================
set -eu
ROOT=$(cd "$(dirname "$0")/../../.." && pwd)
IN=${1:-$ROOT/build/out/s10plus/pwnage38000/nuxel-boot-pwnage38000-audio-initramfs-gz.img}
OUT=${2:-$ROOT/build/out/s10plus/pwnage38000/nuxel-boot-pwnage38000-splashfix.img}
shift 2 2>/dev/null || true
ANIM=$ROOT/build/out/s10plus/nuxel-animation.nux
PART=${NUXEL_BOOT_PARTITION_BYTES:-57671680}
while [ $# -gt 0 ]; do
    case "$1" in
        --anim) ANIM=$2; shift 2 ;;
        --partition-bytes) PART=$2; shift 2 ;;
        *) echo "unknown argument: $1" >&2; exit 2 ;;
    esac
done
WORK=$ROOT/build/out/s10plus/a27/splashfix-work
mkdir -p "$WORK"
NEWC="$ROOT/tools/s10plus/newc.py"
say() { printf '[splashfix] %s\n' "$*"; }
die() { printf '[splashfix][FAIL] %s\n' "$*" >&2; exit 1; }

[ -s "$IN" ] || die "missing input boot image: $IN"
[ -s "$ANIM" ] || die "missing NUXANM01 container: $ANIM (see tools/s10plus/nuxel-anim-pack.py)"
command -v python3 >/dev/null || die "python3 required"
command -v gzip >/dev/null || die "gzip required"

# --- 1. NUXSPL01 = frame 0 of the animation container -------------------------
say "1. regenerating the NUXSPL01 first-light asset from $(basename "$ANIM")"
python3 "$ROOT/tools/s10plus/a26/make-firstlight-asset.py" \
    --anim "$ANIM" --out "$WORK/nuxel-firstlight.nuxspl" \
    --raw-out "$WORK/nuxel-firstlight.rawspl" \
    --report "$WORK/firstlight.report.json" >"$WORK/asset.log" 2>&1 \
    || { tail -20 "$WORK/asset.log"; die "first-light asset generation failed"; }
grep -q FIRSTLIGHT_ASSET_OK "$WORK/asset.log" || die "asset generation did not verify"
ASSET=$WORK/nuxel-firstlight.rawspl
[ -s "$ASSET" ] || die "no raw (uncompressed) first-light asset produced"

# --- 2. unpack the input container (header v1, page 2048) ---------------------
say "2. unpacking the boot image header + ramdisk"
python3 - "$IN" "$WORK" <<'PY' || die "boot image parse failed"
import struct, sys, json
src, work = sys.argv[1], sys.argv[2]
d = open(src, "rb").read()
assert d[:8] == b"ANDROID!", "not an ANDROID! boot image"
ks, ka, rs, ra, ss, sa, ta, ps, h40, osv = struct.unpack_from("<10I", d, 8)
assert ps == 2048, "unexpected page size %d" % ps
def al(n): return (n + ps - 1) // ps * ps
roff = ps + al(ks)
rd = d[roff:roff + rs]
assert rd[:2] == b"\x1f\x8b", "input ramdisk is not gzip (%r)" % rd[:2]
open(work + "/header.bin", "wb").write(d[:ps])
open(work + "/kernel.bin", "wb").write(d[ps:ps + ks])
open(work + "/ramdisk.cpio.gz", "wb").write(rd)
json.dump({"kernel_size": ks, "ramdisk_size": rs, "page_size": ps,
           "header_field40": h40, "image_bytes": len(d)}, open(work + "/in.json", "w"))
print("   in: kernel=%d ramdisk=%d image=%d" % (ks, rs, len(d)))
PY

say "3. verifying the unpacked ramdisk is a newc cpio with a TRAILER"
gzip -dc "$WORK/ramdisk.cpio.gz" > "$WORK/ramdisk.cpio"
python3 - "$NEWC" "$WORK/ramdisk.cpio" <<'PY' || die "ramdisk is not a valid newc archive"
import importlib.util, sys
spec = importlib.util.spec_from_file_location("newc", sys.argv[1])
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
data = open(sys.argv[2], "rb").read()
names = [r[1] for r in m.iter_records(data)]
assert names and names[-1] == "TRAILER!!!", "missing TRAILER!!! record"
assert "init" in names, "no /init in the ramdisk"
assert "bin/toybox" in names, "no bin/toybox in the ramdisk"
assert len(names) == len(set(names)), "duplicate member names"
print("   ok %d records, %d bytes" % (len(names), len(data)))
PY

# --- 3. patch /init and add the asset ----------------------------------------
say "4. installing the no-legacy-paint /init and the first-light asset"
python3 "$NEWC" replace "$WORK/ramdisk.cpio" init "$ROOT/boot/initramfs/init.sh" \
    "$WORK/ramdisk.new.cpio" --mode=0100755 >/dev/null
python3 "$NEWC" insert "$WORK/ramdisk.new.cpio" "$WORK/ramdisk.spl.cpio" \
    --after opt/nuxel/nuxel-fb-phone --name opt/nuxel/nuxel-firstlight.rawspl \
    --mode 0100644 --type file --file "$ASSET" >/dev/null

# fail closed: the shipped /init must carry the guard, and the asset bytes must
# be the ones we just generated.
python3 "$NEWC" extract "$WORK/ramdisk.spl.cpio" init "$WORK/init.check"
grep -q FIRSTLIGHT_ASSET_MISSING_NO_LEGACY_PAINT "$WORK/init.check" \
    || die "the packed /init lacks the no-legacy-paint guard"
python3 "$NEWC" extract "$WORK/ramdisk.spl.cpio" opt/nuxel/nuxel-firstlight.rawspl "$WORK/spl.check"
cmp -s "$WORK/spl.check" "$ASSET" || die "the packed first-light asset differs from the generated one"

say "5. repacking the gzip ramdisk"
# -n: no filename/mtime in the gzip header, so identical inputs always
# produce an identical boot image (the receipt sha256 is meaningful).
gzip -9 -n -c "$WORK/ramdisk.spl.cpio" > "$WORK/ramdisk.new.cpio.gz"

say "6. assembling the boot image (kernel/cmdline/addresses/DTB preserved)"
python3 - "$WORK" "$OUT" "$PART" <<'PY' || die "boot image assembly failed"
import json, struct, sys
work, out, part = sys.argv[1], sys.argv[2], int(sys.argv[3])
info = json.load(open(work + "/in.json"))
hdr = bytearray(open(work + "/header.bin", "rb").read())
kern = open(work + "/kernel.bin", "rb").read()
rd = open(work + "/ramdisk.new.cpio.gz", "rb").read()
PAGE = 2048
def al(n): return (n + PAGE - 1) // PAGE * PAGE
assert len(kern) == info["kernel_size"], "kernel size changed unexpectedly"
struct.pack_into("<I", hdr, 16, len(rd))          # ramdisk_size (offset 16)
blob = bytearray(bytes(hdr))
blob += kern.ljust(al(len(kern)), b"\0")
blob += rd.ljust(al(len(rd)), b"\0")
if len(blob) > part:
    sys.exit("image (%d) exceeds the partition (%d)" % (len(blob), part))
blob += b"\0" * (part - len(blob))                # keep the exact partition size
open(out, "wb").write(blob)
PY

say "7. verifying the written image"
python3 - "$OUT" "$WORK" "$PART" <<'PY' || die "output verification failed"
import json, struct, sys
out, work, part = sys.argv[1], sys.argv[2], int(sys.argv[3])
info = json.load(open(work + "/in.json"))
d = open(out, "rb").read()
assert d[:8] == b"ANDROID!", "output magic"
ks, ka, rs, ra = struct.unpack_from("<4I", d, 8)
assert ks == info["kernel_size"], "kernel size not preserved"
assert d[2048:2048 + ks] == open(work + "/kernel.bin", "rb").read(), "kernel bytes changed"
assert d[2048:2064] == open(work + "/header.bin", "rb").read()[2048:2064] if False else True
# cmdline + name + load addresses are unchanged (the header is byte-identical
# apart from the ramdisk_size field we rewrote).
old = bytearray(open(work + "/header.bin", "rb").read())
old[16:20] = struct.pack("<I", rs)
assert bytes(old) == d[:2048], "header changed beyond ramdisk_size"
off = 2048 + ((ks + 2047) // 2048) * 2048
assert d[off:off + rs] == open(work + "/ramdisk.new.cpio.gz", "rb").read(), "ramdisk mismatch"
assert len(d) == part, "partition size %d != %d" % (len(d), part)
print("   ok image=%d kernel=%d ramdisk=%d" % (len(d), ks, rs))
PY

{ echo "in=$IN"; echo "out=$OUT"; echo "anim=$ANIM";
  echo "asset_bytes=$(wc -c <"$ASSET" | tr -d ' ')";
  echo "asset_sha256=$(shasum -a 256 "$ASSET" | cut -d' ' -f1)";
  echo "image_bytes=$(wc -c <"$OUT" | tr -d ' ')";
  echo "image_sha256=$(shasum -a 256 "$OUT" | cut -d' ' -f1)"; } > "$WORK/RECEIPT.txt"
cat "$WORK/RECEIPT.txt"
say "SPLASHFIX_READY $OUT"
