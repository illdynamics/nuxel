#!/usr/bin/env bash
# =============================================================================
# build-candidate.sh — fail-closed builder for S10+ (beyond2lte) BOOT candidates
#
# Supersedes the legacy boot/s10plus/build-debug-candidate.sh +
# tools/s10plus/patch-boot-from-upload.py path, which could reintroduce the two
# hardware-proven regressions:
#   * a GZIP kernel payload (S-Boot executes it as code: seven silent loads), and
#   * a legacy header with the DTB size written at offset 40 (S-Boot reads that
#     as `header_version` and logs "BOOT IMG HDR V376101").
#
# Everything this script emits is checked by tools/s10plus/verify-boot-image.py
# before it is reported as buildable.  The script never overwrites an existing
# candidate unless --force is given, so hardware-tested images stay intact.
#
# Usage:
#   boot/s10plus/build-candidate.sh \
#       --base build/out/s10plus/debug-candidates/nuxel-beyond2lte-boot-A5-dtb-fix.img \
#       --compress lzma \
#       --out   build/out/s10plus/debug-candidates/A6/boot.img
#
# Options:
#   --base IMG            hardware-proven boot image supplying kernel + DTB
#                         (default: the A5 candidate)
#   --kernel IMAGE        override the kernel payload (must be a raw arm64 Image)
#   --dtb DTB             override the appended device tree (default: from --base)
#   --initramfs-cpio F    uncompressed newc cpio to use (default: from --base)
#   --init SHELL_SCRIPT   replace /init with this file (default boot/initramfs/init.sh;
#                         pass '--init none' to keep the base's /init)
#   --no-dev-nodes        do NOT insert /dev/console + /dev/null
#   --compress MODE       ramdisk container: lzma | gzip | none  (default lzma)
#   --pad-cpio BYTES      zero padding appended inside the compressed stream
#                         (default 65536; keeps TRAILER!!! well inside the stream)
#   --align-ramdisk N     zero-pad the COMPRESSED ramdisk up to a multiple of N
#                         bytes (default 65536).  S-Boot's delivered initrd length
#                         is container-derived and has been observed both rounded
#                         up (TWRP: +23B) and floored to 4 KiB (A2/A3); an aligned
#                         size makes every rounding rule a no-op, and the extra
#                         bytes are zeros that the LZMA end-of-stream marker
#                         already protects against (proven by the TWRP ramdisk).
#   --out IMG             output candidate (required)
#   --report FILE         write the validation report here (default <out>.report.txt)
#   --partition-bytes N   BOOT partition size used for the capacity gate
#   --force               allow overwriting an existing --out
#   -h|--help
#
# Exit codes: 0 ok, 1 gate/build failure (nothing is reported as flashable),
#             2 usage/input error.
# =============================================================================
set -euo pipefail

HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../.." && pwd)
PY=python3
GATE="$ROOT/tools/s10plus/verify-boot-image.py"
UNPACK="$ROOT/tools/s10plus/unpack-boot-image.py"
NEWC="$ROOT/tools/s10plus/newc.py"

BASE="$ROOT/build/out/s10plus/debug-candidates/nuxel-beyond2lte-boot-A5-dtb-fix.img"
KERNEL=""; DTB=""; CPIO=""; INIT="$ROOT/boot/initramfs/init.sh"
DEV_NODES=1; MODE=lzma; PAD=65536; ALIGN=65536; OUT=""; REPORT=""
PARTITION_BYTES="${NUXEL_BOOT_PARTITION_BYTES:-57671680}"; FORCE=0

while [ $# -gt 0 ]; do
  case "$1" in
    --base) BASE="$2"; shift 2 ;;
    --kernel) KERNEL="$2"; shift 2 ;;
    --dtb) DTB="$2"; shift 2 ;;
    --initramfs-cpio) CPIO="$2"; shift 2 ;;
    --init) INIT="$2"; shift 2 ;;
    --no-dev-nodes) DEV_NODES=0; shift ;;
    --compress) MODE="$2"; shift 2 ;;
    --pad-cpio) PAD="$2"; shift 2 ;;
    --align-ramdisk) ALIGN="$2"; shift 2 ;;
    --out) OUT="$2"; shift 2 ;;
    --report) REPORT="$2"; shift 2 ;;
    --partition-bytes) PARTITION_BYTES="$2"; shift 2 ;;
    --force) FORCE=1; shift ;;
    -h|--help) sed -n '2,45p' "$0"; exit 0 ;;
    *) echo "build-candidate: unknown argument: $1" >&2; exit 2 ;;
  esac
done

[ -n "$OUT" ] || { echo "build-candidate: --out is required" >&2; exit 2; }
case "$MODE" in lzma|gzip|none) ;; *) echo "build-candidate: bad --compress '$MODE'" >&2; exit 2 ;; esac
[ -f "$BASE" ] || { echo "build-candidate: base image not found: $BASE" >&2; exit 2; }
if [ -e "$OUT" ] && [ "$FORCE" -ne 1 ]; then
  echo "build-candidate: refusing to overwrite $OUT (use --force)" >&2; exit 2
fi
[ -n "$REPORT" ] || REPORT="$OUT.report.txt"

WORK=$(mktemp -d "${TMPDIR:-/tmp}/nuxel-cand.XXXXXX")
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$(dirname "$OUT")"
LOG="$WORK/build.log"
exec 3>&1
: > "$LOG"

say() { echo "$@" | tee -a "$LOG" >&3; }

say "### build-candidate: base $(basename "$BASE")"
say "### sha256(base) = $(shasum -a 256 "$BASE" | awk '{print $1}')"
say "### ramdisk container mode = $MODE, dev nodes = $DEV_NODES, init = $INIT"

# --- 1. take the proven container apart --------------------------------------
"$UNPACK" "$BASE" "$WORK/base" >>"$LOG" 2>&1 || { echo "build-candidate: cannot unpack base" >&2; exit 1; }
[ -n "$KERNEL" ] || KERNEL="$WORK/base/Image"
[ -n "$DTB" ]    || DTB="$WORK/base/appended.dtb"
[ -n "$CPIO" ]   || CPIO="$WORK/base/initramfs.cpio"
for f in "$KERNEL" "$DTB" "$CPIO"; do [ -f "$f" ] || { echo "build-candidate: missing input $f" >&2; exit 1; }; done

# The base's ramdisk must be a usable cpio even if the base container is legacy.
"$NEWC" trailer "$CPIO" >>"$LOG" 2>&1 || { echo "build-candidate: base initramfs is not a newc cpio" >&2; exit 1; }

# --- 2. initramfs surgery ----------------------------------------------------
STAGE="$WORK/initramfs.cpio"
cp "$CPIO" "$STAGE"
cpio_sha() { shasum -a 256 "$1" | awk '{print $1}'; }
BEFORE_CPIO=$(cpio_sha "$STAGE")

if [ "$INIT" != "none" ]; then
  [ -f "$INIT" ] || { echo "build-candidate: --init file not found: $INIT" >&2; exit 1; }
  sh -n "$INIT" 2>/dev/null || { echo "build-candidate: --init is not valid shell" >&2; exit 1; }
  say "### /init <- $INIT ($(wc -c <"$INIT" | tr -d ' ') bytes, sha256 $(cpio_sha "$INIT"))"
  "$NEWC" replace "$STAGE" init "$INIT" "$STAGE.new" --mode=0100755 >>"$LOG" 2>&1
  mv "$STAGE.new" "$STAGE"
fi

if [ "$DEV_NODES" -eq 1 ]; then
  # prepare_namespace() is skipped when the initramfs supplies /init, so the
  # kernel never mounts devtmpfs: /dev/console MUST come from the archive or
  # kernel_init prints "Warning: unable to open an initial console" and the
  # initramfs can never emit any console evidence.
  "$NEWC" insert "$STAGE" "$STAGE.d1" --after dev --name dev/console \
      --mode 0100600 --type char --major 5 --minor 1 >>"$LOG" 2>&1
  mv "$STAGE.d1" "$STAGE"
  "$NEWC" insert "$STAGE" "$STAGE.d2" --after dev/console --name dev/null \
      --mode 0100666 --type char --major 1 --minor 3 >>"$LOG" 2>&1
  mv "$STAGE.d2" "$STAGE"
fi

if [ "$PAD" -gt 0 ]; then
  # Padding must live INSIDE the compressed stream: S-Boot rounds the delivered
  # ramdisk length, and the kernel's initramfs parser needs the bytes up to the
  # end of the TRAILER!!! record to exist.
  python3 - "$STAGE" "$PAD" <<'PY'
import sys
p, pad = sys.argv[1], int(sys.argv[2])
d = open(p, "rb").read()
open(p, "wb").write(d + b"\x00" * pad)
PY
fi
AFTER_CPIO=$(cpio_sha "$STAGE")
say "### initramfs cpio: $BEFORE_CPIO -> $AFTER_CPIO ($(wc -c <"$STAGE" | tr -d ' ') bytes incl. padding)"

# --- 3. container --------------------------------------------------------------
case "$MODE" in
  lzma)
    # Same container shape as the only ramdisk proven to be delivered AND
    # unpacked on this handset (TWRP 3.7.0_9-2): LZMA-alone, lc=3 lp=0 pb=2
    # (properties byte 0x5d), 8 MiB dictionary, uncompressed size unknown
    # (0xFFFFFFFFFFFFFFFF) so the stream carries an end-of-stream marker.
    python3 - "$STAGE" "$WORK/ramdisk.lzma" <<'PY'
import lzma, sys
src, dst = sys.argv[1], sys.argv[2]
data = open(src, "rb").read()
filters = [{"id": lzma.FILTER_LZMA1, "preset": 6, "dict_size": 1 << 23}]
comp = lzma.compress(data, format=lzma.FORMAT_ALONE, filters=filters)
# FORMAT_ALONE with a known size writes the real size; the device's own ramdisk
# carries 0xFFFFFFFFFFFFFFFF.  Rewrite the size field so the stream is shaped
# exactly like the working recovery ramdisk.
assert comp[:1] == b"\x5d", comp[:1].hex()
comp = comp[:5] + b"\xff" * 8 + comp[13:]
open(dst, "wb").write(comp)
print("lzma-alone: %d -> %d bytes, props=0x%02x dict=0x%x size=0x%s"
      % (len(data), len(comp), comp[0], int.from_bytes(comp[1:5], "little"),
         comp[5:13].hex()))
PY
    ;;
  gzip) gzip -9 -n -c "$STAGE" > "$WORK/ramdisk.gz" && cp "$WORK/ramdisk.gz" "$WORK/ramdisk.raw" ;;
  none) cp "$STAGE" "$WORK/ramdisk.raw" ;;
esac
[ -f "$WORK/ramdisk.raw" ] || cp "$WORK/ramdisk.lzma" "$WORK/ramdisk.raw"
RAMDISK="$WORK/ramdisk.raw"
if [ "$ALIGN" -gt 1 ]; then
  python3 - "$RAMDISK" "$ALIGN" <<'PYX'
import sys
p, align = sys.argv[1], int(sys.argv[2])
d = open(p, "rb").read()
if len(d) % align:
    d += b"\x00" * (align - len(d) % align)
    open(p, "wb").write(d)
    print("ramdisk aligned to %d -> %d bytes" % (align, len(d)))
else:
    print("ramdisk already %d-aligned at %d bytes" % (align, len(d)))
PYX
fi
say "### ramdisk container ($MODE): $(wc -c <"$RAMDISK" | tr -d ' ') bytes, sha256 $(cpio_sha "$RAMDISK")"

# --- 4. repack with the proven load addresses and a spec v1 header -------------
python3 "$ROOT/boot/s10plus/pack-boot-v1.sh" \
  --kernel "$KERNEL" --ramdisk "$RAMDISK" --dtb "$DTB" \
  --cmdline "$(python3 - "$BASE" <<'PY'
import struct, sys
d = open(sys.argv[1], 'rb').read(576)
print(d[64:576].split(b'\0')[0].decode('ascii', 'replace'))
PY
)" --kernel-addr 0x10008000 --ramdisk-addr 0x11000000 --tags-addr 0x10000100 \
  --v1-spec --strict --output "$OUT" >>"$LOG" 2>&1 \
  || { echo "build-candidate: packer refused the container (see $LOG)" >&2; cat "$LOG" >&2; exit 1; }

# --- 5. the gate ---------------------------------------------------------------
say "### release gate"
if ! "$GATE" --partition-bytes "$PARTITION_BYTES" "$OUT" 2>&1 | tee -a "$LOG"; then
  echo "build-candidate: GATE FAILED — $OUT must not be flashed" >&2
  exit 1
fi

{
  echo "build-candidate report"
  echo "  base            = $BASE"
  echo "  base sha256     = $(cpio_sha "$BASE")"
  echo "  kernel          = $KERNEL  sha256 $(cpio_sha "$KERNEL")"
  echo "  dtb             = $DTB  size $(wc -c <"$DTB" | tr -d ' ')  sha256 $(cpio_sha "$DTB")"
  echo "  initramfs cpio  = $BEFORE_CPIO -> $AFTER_CPIO"
  echo "  ramdisk mode    = $MODE (aligned to $ALIGN)"
  echo "  ramdisk sha256  = $(cpio_sha "$RAMDISK")"
  echo "  out             = $OUT"
  echo "  out size        = $(wc -c <"$OUT" | tr -d ' ')"
  echo "  out sha256      = $(cpio_sha "$OUT")"
} > "$WORK/report.txt"
cat "$WORK/report.txt"
cp "$LOG" "$REPORT" 2>/dev/null || true
cat "$WORK/report.txt" >> "$REPORT" 2>/dev/null || true
say "### candidate built and gated: $OUT"
say "### report: $REPORT"
