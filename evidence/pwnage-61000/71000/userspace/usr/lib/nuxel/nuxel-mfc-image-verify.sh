#!/usr/bin/env bash
# PWNAGE-61000 — rootfs/image MFC invariants.
#
# Usage:
#   nuxel-mfc-image-verify.sh --rootfs DIR [--profile software|mfc] [--require-proof]
#
# software profile: MFC firmware/helper may be absent; software fallback and
#                   the guard MUST be present.
# mfc profile:      exact mfc_fw.bin hash, diagnostic, helper and proof receipt
#                   must be present.
set -euo pipefail

ROOTFS=""
PROFILE="software"
REQUIRE_PROOF=0
while [ $# -gt 0 ]; do
    case "$1" in
        --rootfs) ROOTFS="$2"; shift 2 ;;
        --profile) PROFILE="$2"; shift 2 ;;
        --require-proof) REQUIRE_PROOF=1; shift ;;
        --help|-h) sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
        *) echo "unknown: $1" >&2; exit 2 ;;
    esac
done
[ -n "$ROOTFS" ] && [ -d "$ROOTFS" ] || { echo "error: --rootfs DIR required" >&2; exit 2; }
case "$PROFILE" in software|mfc) ;; *) echo "error: --profile software|mfc" >&2; exit 2 ;; esac

pass=0; fail=0
ok()   { echo "PASS  $*"; pass=$((pass+1)); }
bad()  { echo "FAIL  $*"; fail=$((fail+1)); }
note() { echo "NOTE  $*"; }

# 1. Diagnostic is installed and defaults to inventory-only.
if [ -x "$ROOTFS/usr/lib/nuxel/nuxel-mfc-diag" ]; then
    ok "nuxel-mfc-diag installed"
    if grep -q 'Default mode is INVENTORY' "$ROOTFS/usr/lib/nuxel/nuxel-mfc-diag"; then
        ok "diag documents inventory-only default"
    else
        bad "diag does not document inventory-only default"
    fi
else
    bad "nuxel-mfc-diag missing"
fi

# 2. Software fallback and boot/preload safety.
for f in "$ROOTFS/usr/bin/mpv" "$ROOTFS/usr/lib/nuxel/nuxel-gstreamer-guard.sh"; do
    [ -e "$f" ] && ok "present: ${f#$ROOTFS}" || bad "missing: ${f#$ROOTFS}"
done
if grep -Rqs -- '--hwdec=no' "$ROOTFS/usr/lib/nuxel" 2>/dev/null; then
    ok "software-safe --hwdec=no path present"
else
    note "no /usr/lib/nuxel preload script carrying --hwdec=no in this rootfs"
fi

# 3. Guard: V4L2/KMS/OpenGL plugins must not be active by default.
base="$ROOTFS/usr/lib64/gstreamer-1.0"
if [ -d "$base" ]; then
    for p in libgstvideo4linux2.so libgstv4l2codecs.so libgstkms.so libgstopengl.so; do
        if [ -e "$base/$p" ] && [ ! -e "$base/$p.nuxel-disabled" ]; then
            bad "guard not applied to $p"
        else
            ok "guard state for $p"
        fi
    done
else
    note "GStreamer plugin dir absent (minimal rootfs)"
fi

# 4. WirePlumber: camera capture disabled, audio/BT kept.
wp="$ROOTFS/etc/wireplumber/wireplumber.conf.d/99-nuxel-no-v4l2.conf"
if [ -f "$wp" ]; then
    grep -q 'hardware.video-capture = disabled' "$wp" && ok "WirePlumber video-capture disabled" || bad "WirePlumber video-capture not disabled"
    grep -q 'hardware.audio = required' "$wp" && ok "WirePlumber audio required" || bad "WirePlumber audio lost"
    grep -q 'hardware.bluetooth = required' "$wp" && ok "WirePlumber bluetooth required" || bad "WirePlumber bluetooth lost"
else
    bad "WirePlumber 99-nuxel-no-v4l2.conf missing"
fi

# 5. No boot/login/autostart MFC test.
hits="$(grep -Rls -- 'nuxel-mfc-decode\|--allow-hardware-open' "$ROOTFS/etc/systemd" "$ROOTFS/etc/xdg/autostart" 2>/dev/null || true)"
if [ -n "$hits" ]; then
    bad "MFC hardware test referenced from boot/login: $hits"
else
    ok "no boot/login MFC hardware test"
fi

# 6. Profile-specific firmware/diagnostic/proof.
mfc_fw="$ROOTFS/lib/firmware/mfc_fw.bin"
if [ "$PROFILE" = "mfc" ]; then
    [ -x "$ROOTFS/usr/lib/nuxel/nuxel-mfc-decode" ] && ok "nuxel-mfc-decode installed" || bad "nuxel-mfc-decode missing"
    if [ -f "$mfc_fw" ]; then
        sum="$(sha256sum "$mfc_fw" | awk '{print $1}')"
        [ "$sum" = "f3802d34524f5919c16505c03b4cbfe184963f98787feed6232b643bda68b55f" ] \
            && ok "mfc_fw.bin hash matches" || bad "mfc_fw.bin hash mismatch: $sum"
    else
        bad "mfc_fw.bin missing in mfc profile"
    fi
    if [ "$REQUIRE_PROOF" -eq 1 ]; then
        receipt="$ROOTFS/etc/nuxel/mfc/safety-receipt.json"
        if python3 - "$receipt" <<'PY'
import json, sys
try:
    d = json.load(open(sys.argv[1]))
except Exception:
    raise SystemExit(1)
raise SystemExit(0 if d.get("decode_verified") is True and d.get("owner_approved") is True else 1)
PY
        then ok "decode proof receipt present"; else bad "decode proof receipt missing/unverified"; fi
    fi
else
    [ -e "$mfc_fw" ] && note "mfc_fw.bin present in software profile (allowed)" || ok "mfc_fw.bin absent in software profile (allowed)"
fi

echo "summary: profile=$PROFILE pass=$pass fail=$fail"
[ "$fail" -eq 0 ]
