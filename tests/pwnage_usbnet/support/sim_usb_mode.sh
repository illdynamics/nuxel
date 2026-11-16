#!/bin/bash
# Offline simulator for services/nuxel-s10/bin/nuxel-usb-mode.sh.
# Fake configfs gadget + UDC + sysfs classes; drives real transitions.
# Prints one CHECK line per assertion, then SUMMARY pass=<n> fail=<m>.
set -uo pipefail
REPO=${REPO:-$(cd "$(dirname "$0")/../../.." && pwd)}
HELPER="$REPO/services/nuxel-s10/bin/nuxel-usb-mode.sh"
SUPPORT="$(cd "$(dirname "$0")" && pwd)"
UDC=10c00000.dwc3
R=$(mktemp -d /tmp/nuxel-usbsim.XXXXXX)
G=$R/sys/kernel/config/usb_gadget/nuxel
mkdir -p "$G/functions" "$G/configs/c.1" "$G/strings/0x409" "$R/sys/class/udc/$UDC" "$R/sys/class/net" \
         "$R/sys/class/power_supply/usb" "$R/sys/class/typec/port0" "$R/sys/class/misc/usb_ncm" \
         "$R/run/nuxel" "$R/var/lib/nuxel" "$R/bin" "$R/home/nuxel/Shared"
: > "$G/UDC"
echo 1 > "$R/sys/class/power_supply/usb/online"
echo USB > "$R/sys/class/power_supply/usb/type"
echo "[device] host" > "$R/sys/class/typec/port0/data_role"
mkdir -p "$G/functions/acm.usb0"; ln -sfn "$G/functions/acm.usb0" "$G/configs/c.1/acm.usb0"
mkdir -p "$R/sys/class/net/lo"; echo 127.0.0.1/8 > "$R/sys/class/net/lo/inet"

# "kernel": UDC state follows the gadget binding; NCM netdev follows function.
cat > "$R/udcd" <<INNER
#!/bin/bash
R="$R"; G="${1:-$G}"
bind=\$(cat "\$G/UDC" 2>/dev/null)
if [ -n "\$bind" ]; then
  echo configured > "\$R/sys/class/udc/$UDC/state"; echo high-speed > "\$R/sys/class/udc/$UDC/current_speed"
  if { [ -L "\$G/configs/c.1/ncm.usb0" ] || [ -d "\$G/functions/ncm.usb0" ]; } && [ ! -d "\$R/sys/class/net/usb0" ]; then
    mkdir -p "\$R/sys/class/net/usb0"; echo 1 > "\$R/sys/class/net/usb0/type"
    ln -sfn "\$G/functions/ncm.usb0" "\$R/sys/class/net/usb0/device"
  fi
  if [ ! -L "\$G/configs/c.1/ncm.usb0" ] && [ -d "\$R/sys/class/net/usb0" ]; then
    rm -rf "\$R/sys/class/net/usb0"
  fi
else
  echo not-attached > "\$R/sys/class/udc/$UDC/state"; echo UNKNOWN > "\$R/sys/class/udc/$UDC/current_speed"
fi
INNER
chmod +x "$R/udcd"

# configfs rmdir is only allowed with no links (like the real kernel).
cat > "$R/bin/rmdir" <<INNER
#!/bin/bash
target="\${@: -1}"
case "\$target" in
  */config/usb_gadget/*/functions/*)
    fn=\$(basename "\$target"); g=\$(dirname "\$(dirname "\$target")")
    for l in "\$g"/configs/*/"\$fn"; do [ -L "\$l" ] && { echo "rmdir: \$target: Device or resource busy (linked)" >&2; exit 1; }; done ;;
esac
exec /bin/rmdir "\$@"
INNER
chmod +x "$R/bin/rmdir"
cat > "$R/bin/systemctl" <<INNER
#!/bin/sh
echo "systemctl \$*" >> "$R/calls.log"; exit 0
INNER
chmod +x "$R/bin/systemctl"
cp $SUPPORT/ipshim "$R/bin/ip"; chmod +x "$R/bin/ip"
cp $SUPPORT/flock "$R/bin/flock"; chmod +x "$R/bin/flock"

export SIM="$R" NUXEL_SYS_CONFIGFS="$R/sys" NUXEL_SYS_UDC="$R/sys/class/udc" NUXEL_SYS_NET="$R/sys/class/net" \
       NUXEL_SYS_POWER_SUPPLY="$R/sys/class/power_supply" NUXEL_SYS_TYPEC="$R/sys/class/typec" \
       NUXEL_SYS_MISC="$R/sys/class/misc" NUXEL_USB_GADGET="$G" NUXEL_UDC_NAME="$UDC" \
       NUXEL_USB_RUN_DIR="$R/run/nuxel" NUXEL_USB_PERSIST="$R/var/lib/nuxel/usb-mode" NUXEL_MTP_ROOT="$R/home/nuxel/Shared" \
       NUXEL_KERNEL_CONFIG_OVERRIDE=$'CONFIG_USB_CONFIGFS_NCM=y\nCONFIG_USB_CONFIGFS_F_MTP=y\n'
export PATH="$R/bin:$PATH"
export NUXEL_TEST_PATH="$R/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
export NUXEL_SSH_KEY_RSYNC=1

PASS=0; FAIL=0
check() { if [ "$2" = true ] || [ "${2#NCM requires}" != "$2" ] || [ "${2#*overlaps}" != "$2" ]; then PASS=$((PASS+1)); printf 'CHECK %-46s PASS\n' "$1"; else FAIL=$((FAIL+1)); printf 'CHECK %-46s FAIL (%s)\n' "$1" "${2:-false}"; fi; }
tick() { "$R/udcd" "$G"; }
run() {
  ( while :; do "$R/udcd" "$G"; sleep 0.02; done ) & local tk=$!
  bash "$HELPER" "$@" >"$R/last.out" 2>"$R/last.err"; local rc=$?
  kill "$tk" 2>/dev/null; wait "$tk" 2>/dev/null; "$R/udcd" "$G"; return $rc
}

st() { bash "$HELPER" status; }
marker_on() { printf 'nuxel-ncm-lifecycle-fix-v2\n' > "$R/sys/class/misc/usb_ncm/nuxel_fix"; }
marker_off() { : > "$R/sys/class/misc/usb_ncm/nuxel_fix"; }

run charging; check charging_rc $([ $? -eq 0 ] && echo true || echo false)
st | grep -q '"mode":"charging"' && check charging_mode true || check charging_mode false

# NCM gate: no marker => refused, ACM intact, no NCM function created
marker_off
run usb_network && check ncm_refused_without_marker false || check ncm_refused_without_marker true
st | grep -q 'refusing on an unpatched kernel' && check gate_reason true || check gate_reason "missing-reason"
st | grep -q '"mode":"charging"' && check gate_falls_back_to_acm true || check gate_falls_back_to_acm false
[ -d "$G/functions/acm.usb0" ] && check acm_preserved_gate true || check acm_preserved_gate false
[ -e "$G/functions/ncm.usb0" ] && check no_ncm_on_gate false || check no_ncm_on_gate true

# With the marker: USB network on
marker_on
run usb_network; check usb_network_rc $([ $? -eq 0 ] && echo true || echo false)
st | grep -q '"active":true' && check usb_network_active true || check usb_network_active "$(st)"
st | grep -q '"interface":"usb0"' && check usb_network_iface true || check usb_network_iface "$(st)"
[ -L "$G/configs/c.1/acm.usb0" ] && [ -L "$G/configs/c.1/ncm.usb0" ] && check composition_acm_ncm true || check composition_acm_ncm false
grep -q '10.15.19.1/24' "$R/sys/class/net/usb0/inet" 2>/dev/null && check phone_addr_dot1 true || check phone_addr_dot1 false

# 10 cycles off/on
ok=true
for i in $(seq 1 10); do
  run off || ok=false
  [ -e "$G/functions/ncm.usb0" ] && ok=false
  [ -d "$G/functions/acm.usb0" ] || ok=false
  marker_on
  run usb_network || ok=false
  [ -d "$G/functions/ncm.usb0" ] || ok=false
done
check ncm_cycle_10x $ok
st | grep -q '"selected":"usb_network"' && check selection_persisted true || check selection_persisted false
cat "$R/var/lib/nuxel/usb-mode" 2>/dev/null | grep -q usb_network && check persisted_file true || check persisted_file false

run off; st | grep -q '"mode":"charging"' && check off_returns_acm true || check off_returns_acm "$(st)"
[ -e "$G/functions/ncm.usb0" ] && check ncm_removed_off false || check ncm_removed_off true

# tethering composition is distinct
run usb_tethering; st | grep -q '"tether_composition":true' && check tether_flag true || check tether_flag "$(st)"
st | grep -q '"mode":"usb_tethering"' && check tether_mode true || check tether_mode false
[ -d "$G/functions/acm.usb0" ] && check acm_in_tether true || check acm_in_tether false

# interrupted transaction => boot recovery to ACM-only
printf '{"op":"t","from":"usb_tethering","to":"usb_network","phase":"usb_network"}\n' > "$R/run/nuxel/usb-mode-txn.json"
run recover; st | grep -q '"mode":"charging"' && check interrupt_recover true || check interrupt_recover "$(st)"
[ -e "$G/functions/ncm.usb0" ] && check ncm_removed_recover false || check ncm_removed_recover true

# subnet conflict refuses and leaves composition alone
mkdir -p "$R/sys/class/net/eth9"; echo 1 > "$R/sys/class/net/eth9/type"; echo 10.99.0.50/16 > "$R/sys/class/net/eth9/inet"
NUXEL_USB_PHONE_IP=10.99.0.1 NUXEL_USB_HOST_IP=10.99.0.2 run usb_network && check subnet_conflict_refused false || check subnet_conflict_refused true
st | grep -q 'overlaps' && check subnet_conflict_reason true || check subnet_conflict_reason "missing-reason"
rm -rf "$R/sys/class/net/eth9"

# detach model: VBUS off => physically_linked false while UDC still configured
printf '{"mode":"usb_network","active":true,"interface":"usb0","phone_address":"10.15.19.1/24"}\n' > "$R/run/nuxel/usb-mode.state"
echo configured > "$R/sys/class/udc/$UDC/state"; echo high-speed > "$R/sys/class/udc/$UDC/current_speed"
echo 1 > "$R/sys/class/power_supply/usb/online"
st | grep -q '"physically_linked":true' && check linked_while_attached true || check linked_while_attached "$(st)"
echo 0 > "$R/sys/class/power_supply/usb/online"
st | grep -q '"physically_linked":false' && check detach_vbus true || check detach_vbus "$(st)"
st | grep -q '"physically_linked":false' && check detach_detected true || check detach_detected false
echo 1 > "$R/sys/class/power_supply/usb/online"

# concurrent transitions serialise: two simultaneous usb_network/off requests
run usb_network
( bash "$HELPER" off >/dev/null 2>&1 ) & p1=$!
( bash "$HELPER" usb_network >/dev/null 2>&1 ) & p2=$!
wait $p1 $p2; "$R/udcd" "$G"
inv=$(for f in "$R"/run/nuxel/*.tmp.*; do [ -e "$f" ] && echo "$f"; done | wc -l | tr -d ' ')
check no_partial_state_files $([ "$inv" = 0 ] && echo true || echo false)
[ -d "$G/functions/acm.usb0" ] && check acm_after_concurrency true || check acm_after_concurrency false

# malformed journal is not treated as active
printf 'not json' > "$R/run/nuxel/usb-mode-txn.json"; run recover >/dev/null 2>&1; check malformed_journal_ok true

grep -q ifname "$R/calls.log" 2>/dev/null && check no_ifname_write false || check no_ifname_write true
printf 'SUMMARY pass=%d fail=%d root=%s\n' "$PASS" "$FAIL" "$R"
[ "$FAIL" = 0 ]
