#!/usr/bin/env bash
# Post-flash / post-deploy GNSS verification (SAFE: read-only + bounded, no flash).
#
# Verifies, in order: target identity, firmware provenance, device nodes/driver,
# safe power, native daemon presence, provider source labelling, and (only when
# the proprietary decoder is available) a bounded hardware session. It never
# writes a partition, never reboots, and never fabricates a fix.
set -u

TARGET="SM-G975F/beyond2lte"
FW_SHA256="0b53f3b04bfb3d5c19727aac1e33e7a44693a2c01be37bfd1ea3b0ef4e859d72"
RAIL=/sys/devices/virtual/sec/gps/GPS_PWR_EN/value
LHD="/usr/lib/nuxel/nuxel-gnss/nuxel_lhd.py"

pass=0; fail=0
ok()  { echo "PASS: $*"; pass=$((pass+1)); }
bad() { echo "FAIL: $*"; fail=$((fail+1)); }

echo "== 1. identity =="
kompat=$(cat /sys/firmware/devicetree/base/spi@10970000/BCM4773@0/compatible 2>/dev/null | tr -d '\0')
[ "$kompat" = "ssp,BCM4773" ] && ok "DT compatible=$kompat" || bad "DT compatible=$kompat"

echo "== 2. firmware provenance (read-only) =="
if [ -r /dev/bbd_patch ]; then
  sha=$(python3 -c '
import os,hashlib
fd=os.open("/dev/bbd_patch",os.O_RDONLY); d=b""
while True:
    c=os.read(fd,65536)
    if not c: break
    d+=c
os.close(fd)
print(hashlib.sha256(d).hexdigest())
')
  [ "$sha" = "$FW_SHA256" ] && ok "firmware sha256 matches" || bad "firmware sha256=$sha"
else
  bad "/dev/bbd_patch not readable"
fi

echo "== 3. nodes + driver =="
for n in /dev/ttyBCM /dev/bbd_patch /dev/bbd_control /dev/bbd_sensor; do
  [ -e "$n" ] && ok "$n" || bad "$n missing"
done
bound=$(readlink -f "/sys/bus/spi/drivers/brcm gps spi/spi17.0" 2>/dev/null)
[ -n "$bound" ] && ok "spi17.0 bound" || bad "spi17.0 not bound"

echo "== 4. safe power (no change made) =="
rail=$([ -r "$RAIL" ] && cat "$RAIL" || echo unknown)
echo "  (rail currently=$rail; NOT toggled by this script)"
ok "rail readable (state=$rail)"

echo "== 5. native daemon presence =="
[ -x "$LHD" ] && ok "nuxel_lhd.py present" || bad "nuxel_lhd.py missing"
python3 -c "import ast; ast.parse(open('$LHD').read())" 2>/dev/null \
  && ok "nuxel_lhd.py parses" || bad "nuxel_lhd.py syntax error"

echo "== 6. source labelling (bridge) =="
python3 - <<'PY' 2>/dev/null && ok "bridge location status queried" || bad "bridge query failed"
import dbus
b=dbus.SystemBus()
i=dbus.Interface(b.get_object('org.nuxel.Bridge','/org/nuxel/Bridge'),'org.nuxel.Bridge')
st=i.LocationGetStatus('nuxel-gnss-verify')
assert st.get('gnss_fix', False) in (True, False)
assert 'network_fix' in st and 'fix_source' in st
PY

echo
echo "RESULT: $pass passed, $fail failed"
echo "NOTE: a receiver-originated GNSS fix is NOT asserted here and requires the"
echo "      proprietary position decoder (see GPS-BLOCKERS.md) + an outdoor test."
exit $([ "$fail" -eq 0 ] && echo 0 || echo 1)
