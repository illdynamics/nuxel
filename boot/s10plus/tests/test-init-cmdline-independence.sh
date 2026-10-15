#!/bin/sh
# Regression test for the S10+ cmdline-independence repair (2026-10-15).
#
# Reproduces the condition captured from the handset: Samsung S-Boot wrote its own
# /chosen/bootargs, so the Android boot image header cmdline ("nuxel.device=s10plus
# root=...") never reached the kernel. The Nuxel initramfs /init then saw an empty
# nuxel.device= and fell into the generic branch, which cannot resolve this root.
#
# The test extracts the functions under test from the shipped
# boot/initramfs/init.sh, so it fails if that file regresses.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../../.." && pwd)
INIT="$ROOT/boot/initramfs/init.sh"
TMP=$(mktemp -d "${TMPDIR:-/tmp}/nuxel-init-test.XXXXXX")
trap 'rm -rf "$TMP"' EXIT INT TERM
pass=0; fail=0; skip=0
ok()  { printf '  PASS  %s\n' "$1"; pass=$((pass+1)); }
bad() { printf '  FAIL  %s\n' "$1"; fail=$((fail+1)); }
skp() { printf '  SKIP  %s\n' "$1"; skip=$((skip+1)); }
check(){ if [ "$2" = "$3" ]; then ok "$1 = $2"; else bad "$1: got '$2', want '$3'"; fi; }

[ -f "$INIT" ] || { echo "init.sh not found at $INIT" >&2; exit 2; }

awk '/^block_by_partname\(\) \{/,/^\}$/'       "$INIT" > "$TMP/f_blocks.inc"
awk '/^s10plus_userdata_device\(\) \{/,/^\}$/' "$INIT" > "$TMP/f_ud.inc"
awk '/^diag_raw_slot\(\) \{/,/^\}$/'           "$INIT" > "$TMP/f_slot.inc"
awk '/^# --- device identity without the kernel cmdline/,/^# Dispatch on nuxel.device=/' "$INIT" \
  | sed '$d' > "$TMP/f_detect.inc"
for f in f_blocks f_ud f_slot f_detect; do
  [ -s "$TMP/$f.inc" ] || { echo "extraction of $f.inc failed" >&2; exit 2; }
done

# Fake device tree carrying the real handset values.
mkdir -p "$TMP/dt" "$TMP/blk"
printf 'Samsung BEYOND2LTE EUR OPEN 26 board based on EXYNOS9820\000' > "$TMP/dt/model"
printf 'samsung,armv8\000samsung,exynos9820\000' > "$TMP/dt/compatible"

# Real block special devices are needed for the -b checks (macOS: disk0/disk0s1).
DEVDIR=""; NODE1=""; NODE2=""
for cand in /dev/disk0 /dev/sda /dev/mmcblk0 /dev/vda; do
  if [ -b "$cand" ]; then DEVDIR=$(dirname "$cand"); NODE1=$(basename "$cand"); break; fi
done
if [ -n "$NODE1" ]; then
  for cand in /dev/disk0s1 /dev/disk1 /dev/sda1 /dev/vdb; do
    [ -b "$cand" ] && { NODE2=$(basename "$cand"); break; }
  done
  mkdir -p "$TMP/blk/$NODE1"; printf 'PARTNAME=userdata\n' > "$TMP/blk/$NODE1/uevent"; printf '232669184\n' > "$TMP/blk/$NODE1/size"
  if [ -n "$NODE2" ]; then
    mkdir -p "$TMP/blk/$NODE2"; printf 'PARTNAME=boot\n' > "$TMP/blk/$NODE2/uevent"; printf '112640\n' > "$TMP/blk/$NODE2/size"
  fi
fi

cat > "$TMP/probe.sh" <<'EOH'
#!/bin/sh
D="$1"; DEVDIR="$2"
NUXEL_DT="$D/dt"; NUXEL_BLOCK_SYS="$D/blk"; NUXEL_DEV="$DEVDIR"
export NUXEL_DT NUXEL_BLOCK_SYS NUXEL_DEV
. "$D/f_blocks.inc"
. "$D/f_ud.inc"
. "$D/f_slot.inc"
printf 'bypartname=%s\n' "$(block_by_partname userdata)"
printf 'rootdev=%s\n'    "$(s10plus_userdata_device)"
printf 'rawslot=%s\n'    "$(diag_raw_slot)"
EOH

run_detect() { # $1 dt dir  $2 block dir  $3 dev dir
  NUXEL_DT="$1" NUXEL_BLOCK_SYS="$2" NUXEL_DEV="$3" D4="$TMP" sh -c '
     export NUXEL_DT NUXEL_BLOCK_SYS NUXEL_DEV
     log(){ :; }; warn(){ :; }; err(){ :; }; diag(){ :; }; diag_environment(){ :; }
     DEVICE=""
     . "$D4/f_detect.inc"
     printf "%s" "${DEVICE}"'
}
probe() { sh "$TMP/probe.sh" "$TMP" "$1" 2>/dev/null | sed -n "s/^$2=//p"; }

echo "Nuxel S10+ init cmdline-independence test"
echo "  init.sh: $INIT"

r=$(run_detect "$TMP/dt" "$TMP/blk" "${DEVDIR:-/dev}")
check "T1 real S-Boot cmdline + beyond2lte DTB => s10plus" "$r" "s10plus"

mkdir -p "$TMP/dt2"; printf '\000' > "$TMP/dt2/model"
printf 'samsung,armv8\000samsung,exynos9820\000' > "$TMP/dt2/compatible"
r=$(run_detect "$TMP/dt2" "$TMP/blk" "${DEVDIR:-/dev}")
check "T2 detection from compatible only" "$r" "s10plus"

mkdir -p "$TMP/dt3"; printf 'Google Mustang\000' > "$TMP/dt3/model"
printf 'google,gs501\000' > "$TMP/dt3/compatible"
r=$(run_detect "$TMP/dt3" "$TMP/blk" "${DEVDIR:-/dev}")
check "T3 foreign DTB not claimed as s10plus" "$r" ""

if [ -n "$NODE1" ]; then
  check "T4 PARTNAME=userdata resolved by identity" "$(probe "$DEVDIR" bypartname)" "$DEVDIR/$NODE1"
  check "T5 s10plus root resolver uses PARTNAME"     "$(probe "$DEVDIR" rootdev)"    "$DEVDIR/$NODE1"
  if [ -n "$NODE2" ]; then
    check "T6 BOOT-slack diagnostic offset" "$(probe "$DEVDIR" rawslot)" "$DEVDIR/$NODE2 $(( (112640 - 128) * 512 ))"
  else
    skp "T6 (no second block device for the BOOT-slack probe)"
  fi
else
  skp "T4/T5/T6 (no block special device available on this host)"
fi

grep -q 'auto-detected device=' "$INIT" && grep -q 'nuxel-boot-diag.log' "$INIT" \
  && ok "T7 init.sh has device auto-detection + persistent diagnostics" \
  || bad "T7 init.sh missing auto-detection / diagnostics"

if awk '/fail_boot "s10plus: USERDATA not found/,/reboot -f/' "$INIT" | grep -q 'reboot -f'; then
  ok "T8 USERDATA-not-found path persists then reboots (no silent hang)"
else
  bad "T8 USERDATA-not-found path does not persist+reboot"
fi

echo "  ---- $pass passed, $fail failed, $skip skipped ----"
[ "$fail" -eq 0 ]
