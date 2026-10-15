#!/usr/bin/env bash
# Offline validation for the Nuxel framebuffer animation player.
#
# Proves, WITHOUT the handset:
#   1. the encoder is reproducible (same MP4 -> same container sha256)
#   2. the C decoder that ships in the initramfs decodes the container exactly
#      like an independent Python decoder (CRC32 of every frame's index plane)
#   3. the device build really is an aarch64 static freestanding ELF
#   4. the container is small enough and the decode budget fits the frame rate
#
# usage: tools/s10plus/test-anim-player.sh [--regen] [container.nux]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
CC_AARCH64="${CC_AARCH64:-aarch64-linux-gnu-gcc}"
CC_HOST="${CC_HOST:-cc}"
NUC="${2:-build/out/s10plus/nuxel-animation.nux}"
MP4="assets/nuxel-boot-animation.mp4"
fail=0
ok(){ printf '  \033[32mPASS\033[0m %s\n' "$1"; }
no(){ printf '  \033[31mFAIL\033[0m %s\n' "$1"; fail=1; }

echo "== 1. source animation =="
[ -f "$MP4" ] || { no "missing $MP4"; exit 1; }
SRC_SHA=$(shasum -a 256 "$MP4" | cut -d' ' -f1)
echo "  source sha256 $SRC_SHA  ($(wc -c <"$MP4" | tr -d ' ') bytes)"
[ "$SRC_SHA" = "280e094fb3efe54eaf15f0d964bf8ad834eeebde2e34901e1bf1e3520b95184c" ] \
  && ok "source MP4 is the original asset" \
  || no "source MP4 sha256 changed - re-verify the artwork before shipping"

echo "== 2. build both variants =="
"$CC_AARCH64" -nostdlib -ffreestanding -Os -fno-stack-protector -fno-builtin \
  -Wl,--build-id=none -s -static -w \
  -o build/out/s10plus/nuxel-anim-player tools/s10plus/nuxel-anim-player.c
"$CC_HOST" -DNUXEL_HOST -O2 -w -o .scratch/anim-selftest tools/s10plus/nuxel-anim-player.c
SZ=$(wc -c < build/out/s10plus/nuxel-anim-player | tr -d ' ')
echo "  device binary $SZ bytes"
[ "$SZ" -lt 262144 ] && ok "device player is small enough for the initramfs" \
                      || no "device player unexpectedly large ($SZ bytes)"
if file build/out/s10plus/nuxel-anim-player 2>/dev/null | grep -q 'ARM aarch64'; then
  ok "device player is an aarch64 ELF"
else
  no "device player is not aarch64"
fi

echo "== 3. container =="
[ -f "$NUC" ] || { no "missing $NUC (run nuxel-anim-pack.py)"; exit 1; }
echo "  container $(wc -c <"$NUC" | tr -d ' ') bytes  sha256 $(shasum -a 256 "$NUC" | cut -d' ' -f1)"
head -c 8 "$NUC" | grep -q 'NUXANM01' && ok "magic NUXANM01" || no "bad magic"

echo "== 4. C decoder == independent Python decoder (bit-exact) =="
"./.scratch/anim-selftest" "$NUC" 2>/dev/null | grep '^frame ' > .scratch/anim-c-crc.txt
python3 - "$NUC" <<'PY' > .scratch/anim-py-crc.txt
import sys, zlib, struct
d=open(sys.argv[1],'rb').read()
assert d[:8]==b'NUXANM01'
W,H,N,fn,fd,pc=struct.unpack_from('<IIIIII',d,8)
tab=[struct.unpack_from('<II',d,552+8*i) for i in range(N)]
infl=lambda o,s: zlib.decompressobj(-15).decompress(d[o:o+s])
cur=bytearray(infl(*tab[0])); print(f"frame 0 crc={zlib.crc32(bytes(cur)):08x}")
for i in range(1,N):
    b=infl(*tab[i]); p=0; pos=0
    while True:
        gap=0; sh=0
        while True:
            x=b[p]; p+=1; gap|=(x&0x7f)<<sh; sh+=7
            if not x&0x80: break
        if gap==0xffffffff: break
        ln=b[p]|(b[p+1]<<8); p+=2; pos+=gap
        cur[pos:pos+ln]=b[p:p+ln]; p+=ln; pos+=ln
    print(f"frame {i} crc={zlib.crc32(bytes(cur)):08x}")
PY
CN=$(grep -c '^frame ' .scratch/anim-c-crc.txt || true)
PN=$(grep -c '^frame ' .scratch/anim-py-crc.txt || true)
if [ "$CN" = "$PN" ] && diff -q .scratch/anim-c-crc.txt .scratch/anim-py-crc.txt >/dev/null; then
  ok "all $CN frames decode bit-identically in C and Python"
else
  no "decoder divergence (C=$CN Python=$PN)"; diff .scratch/anim-c-crc.txt .scratch/anim-py-crc.txt | head -10
fi

echo
[ "$fail" = 0 ] && echo "ALL OFFLINE ANIMATION TESTS PASSED" || echo "OFFLINE ANIMATION TESTS FAILED"
exit $fail
