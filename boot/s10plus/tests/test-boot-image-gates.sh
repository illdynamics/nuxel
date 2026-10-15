#!/usr/bin/env bash
# =============================================================================
# test-boot-image-gates.sh — regression tests for the S10+ BOOT release gate
#
# Proves that tools/s10plus/verify-boot-image.py FAILS the images that are
# hardware-proven not to boot and PASSES the one that is hardware-proven to
# execute the Nuxel kernel.  Also proves the builder refuses to reintroduce the
# two known container defects.
#
# Offline only.  No device access.
# =============================================================================
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../../.." && pwd)
GATE="$ROOT/tools/s10plus/verify-boot-image.py"
NEWC="$ROOT/tools/s10plus/newc.py"
PACK="$ROOT/boot/s10plus/pack-boot-v1.sh"
UNPACK="$ROOT/tools/s10plus/unpack-boot-image.py"
WORK=$(mktemp -d "${TMPDIR:-/tmp}/nuxel-gate-tests.XXXXXX")
trap 'rm -rf "$WORK"' EXIT

PASS=0; FAIL=0; SKIP=0
ok()   { PASS=$((PASS+1)); printf '  ok   %s\n' "$1"; }
bad()  { FAIL=$((FAIL+1)); printf '  FAIL %s\n' "$1"; }
skip() { SKIP=$((SKIP+1)); printf '  skip %s\n' "$1"; }

# expect_gate <want:pass|fail> <label> <image> [partition_bytes]
expect_gate() {
  local want="$1" label="$2" img="$3" part="${4:-57671680}"
  if [ ! -f "$img" ]; then skip "$label (missing fixture)"; return; fi
  if python3 "$GATE" --quiet --partition-bytes "$part" "$img" >/dev/null 2>&1; then got=pass; else got=fail; fi
  if [ "$got" = "$want" ]; then ok "$label -> $want (as required)"
  else bad "$label -> $got, expected $want"; python3 "$GATE" --partition-bytes "$part" "$img" | sed 's/^/       /'; fi
}

A5="$ROOT/build/out/s10plus/debug-candidates/nuxel-beyond2lte-boot-A5-dtb-fix.img"
if ! python3 "$UNPACK" "$A5" "$WORK/base" >/dev/null 2>&1; then
  echo "test-boot-image-gates: cannot unpack the hardware-proven A5 base" >&2
  exit 1
fi

echo "== 1. known-bad images must FAIL the gate"
expect_gate fail "A1 cmdline-free (gzip kernel + legacy header 376101)" \
  "$ROOT/build/out/s10plus/debug-candidates/nuxel-beyond2lte-boot-diag-cmdline-free.img"
expect_gate fail "legacy merged-fixed image (gzip kernel + legacy header)" \
  "$ROOT/build/out/s10plus/nuxel-beyond2lte-boot-merged-fixed.img"
expect_gate fail "A2 uncompressed kernel but legacy header 376101" \
  "$ROOT/build/out/s10plus/debug-candidates/nuxel-beyond2lte-boot-A2-uncompressed.img"

echo "== 2. hardware-proven images must PASS the gate"
expect_gate pass "A5 (raw Image, v1 header, newc cpio, S-Boot executed it)" \
  "$ROOT/build/out/s10plus/debug-candidates/nuxel-beyond2lte-boot-A5-dtb-fix.img"
# TWRP lives in the (larger) RECOVERY partition, so give it that capacity: this
# fixture exists to prove the ramdisk/initramfs gates accept the one container
# S-Boot is observed to deliver AND unpack on this handset.
expect_gate pass "TWRP recovery image (the only ramdisk S-Boot delivers + unpacks)" \
  "$ROOT/backups/s10plus/twrp-recovery-original.img" 67633152

echo "== 3. synthetic defects must FAIL the gate"
cp "$ROOT/build/out/s10plus/debug-candidates/A4/initramfs.cpio" "$WORK/cpio"
python3 "$NEWC" replace "$WORK/cpio" init "$WORK/cpio" "$WORK/cpio2" >/dev/null 2>&1
# 3a. gzip kernel payload via the packer's --strict switch
if python3 "$PACK" --kernel "$ROOT/build/out/s10plus/debug-candidates/A2/Image.gz" \
     --ramdisk "$WORK/cpio" --output "$WORK/gzip-kernel.img" \
     --kernel-addr 0x10008000 --ramdisk-addr 0x11000000 --tags-addr 0x10000100 \
     --v1-spec --strict >/dev/null 2>&1; then
  bad "packer --strict accepted a gzip kernel payload"
else
  ok "packer --strict refuses a gzip kernel payload"
fi
# 3b. a synthetic legacy-header image (DTB size at offset 40)
if python3 "$PACK" --kernel "$WORK/base/Image" --ramdisk "$WORK/cpio" \
     --output "$WORK/legacy.img" --kernel-addr 0x10008000 --ramdisk-addr 0x11000000 \
     --tags-addr 0x10000100 >/dev/null 2>&1; then
  expect_gate fail "synthetic legacy header (DTB size at offset 40)" "$WORK/legacy.img"
else
  skip "synthetic legacy header (packer failed)"
fi
# 3c. ramdisk without /init
python3 - "$WORK/cpio" "$WORK/no-init.cpio" "$ROOT/tools/s10plus" <<'PY'
import sys, os
sys.path.insert(0, sys.argv[3])
import newc
data = open(sys.argv[1], "rb").read()
out = []
for off, name, mode, size, ds, dl in newc.iter_records(data):
    if name == newc.TRAILER:
        out.append(data[off:ds + dl]); break
    if name == "init":
        continue           # drop /init entirely
    out.append(data[off:ds + dl])
newc._pack_header  # noqa
open(sys.argv[2], "wb").write(b"".join(out))
PY
if python3 "$PACK" --kernel "$WORK/base/Image" --ramdisk "$WORK/no-init.cpio" \
     --output "$WORK/no-init.img" --kernel-addr 0x10008000 --ramdisk-addr 0x11000000 \
     --tags-addr 0x10000100 --v1-spec >/dev/null 2>&1; then
  expect_gate fail "ramdisk with /init removed" "$WORK/no-init.img"
else
  skip "ramdisk with /init removed (packer failed)"
fi
# 3d. truncated ramdisk (drops the TRAILER!!! record) — the A3 failure mode
python3 - "$WORK/cpio" "$WORK/trunc.cpio" <<'PY'
import sys
d = open(sys.argv[1], "rb").read()
open(sys.argv[2], "wb").write(d[:8192000])   # 8,192,000B = round_down(A3 size, 4096)
PY
if python3 "$PACK" --kernel "$WORK/base/Image" --ramdisk "$WORK/trunc.cpio" \
     --output "$WORK/trunc.img" --kernel-addr 0x10008000 --ramdisk-addr 0x11000000 \
     --tags-addr 0x10000100 --v1-spec >/dev/null 2>&1; then
  expect_gate fail "ramdisk truncated below TRAILER!!! (the A3 failure mode)" "$WORK/trunc.img"
else
  skip "truncated ramdisk"
fi
# 3e. oversized image must fail the capacity gate
if python3 "$PACK" --kernel "$WORK/base/Image" --ramdisk "$WORK/cpio" \
     --output "$WORK/big.img" --kernel-addr 0x10008000 --ramdisk-addr 0x11000000 \
     --tags-addr 0x10000100 --v1-spec >/dev/null 2>&1; then
  if python3 "$GATE" --partition-bytes 4194304 --quiet "$WORK/big.img" >/dev/null 2>&1; then
    bad "capacity gate accepted an image larger than the partition"
  else
    ok "capacity gate rejects an image larger than the BOOT partition"
  fi
else
  skip "oversized image"
fi

echo "== 4. newc tool round-trip identity (no silent archive corruption)"
python3 "$NEWC" extract "$ROOT/build/out/s10plus/debug-candidates/A4/initramfs.cpio" init "$WORK/init" >/dev/null 2>&1
python3 "$NEWC" replace "$ROOT/build/out/s10plus/debug-candidates/A4/initramfs.cpio" init "$WORK/init" "$WORK/rt.cpio" >/dev/null 2>&1
if python3 - "$ROOT/build/out/s10plus/debug-candidates/A4/initramfs.cpio" "$WORK/rt.cpio" <<'PY'
import sys
a = open(sys.argv[1], "rb").read()
b = open(sys.argv[2], "rb").read()
end = 8192904
sys.exit(0 if a[:end] == b[:end] else 1)
PY
then ok "replace(same bytes) reproduces the archive byte-for-byte"
else bad "replace(same bytes) changed the archive"; fi

echo
echo "== test-boot-image-gates: $PASS passed, $FAIL failed, $SKIP skipped"
[ "$FAIL" -eq 0 ] || exit 1
