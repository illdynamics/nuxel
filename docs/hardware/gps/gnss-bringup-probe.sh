#!/usr/bin/env bash
# =============================================================================
# Nuxel S10+ GNSS bring-up probe (read-only + bounded, safe to re-run)
#
# Records the evidence behind GPS-BLOCKERS.md B0: does the BCM4773 receiver /
# sensor hub answer at all?  It never writes a partition, never reboots and
# always restores the GPS_PWR_EN rail to its initial value.
#
# Usage (on the handset, as root):
#   docs/hardware/gps/gnss-bringup-probe.sh
# =============================================================================
set -u

RAIL=/sys/devices/virtual/sec/gps/GPS_PWR_EN/value
SSP=/sys/devices/virtual/sensors/ssp_sensor
[ -r "$RAIL" ] || { echo "SKIP: GPS_PWR_EN rail not exported (driver not probed)"; exit 3; }

INITIAL=$(cat "$RAIL")
cleanup() { printf '0' > "$RAIL" 2>/dev/null; [ "$INITIAL" = "1" ] && printf '1' > "$RAIL" 2>/dev/null; }
trap cleanup EXIT

echo "== nodes =="
for n in /dev/ttyBCM /dev/bbd_patch /dev/bbd_control /dev/bbd_sensor; do
  if [ -e "$n" ]; then printf '%-18s present\n' "$n"; else printf '%-18s MISSING\n' "$n"; fi
done

echo "== sensor hub state (before) =="
printf 'mcu_test   : %s\n' "$(cat "$SSP/mcu_test" 2>/dev/null || echo '?')"
printf 'mcu_name   : %s\n' "$(cat "$SSP/mcu_name" 2>/dev/null || echo '?')"
printf 'enable_irq : %s\n' "$(cat "$SSP/enable_irq" 2>/dev/null || echo '?')"
printf 'rail       : %s\n' "$(cat "$RAIL")"

echo "== rail on + raw receive window (no TX at all) =="
printf '1' > "$RAIL"; sleep 0.3
RX=$(python3 - <<'PY'
import os, select, time
fd = os.open("/dev/ttyBCM", os.O_RDWR | os.O_NONBLOCK)
n = 0
end = time.time() + 3.0
while time.time() < end:
    r, _, _ = select.select([fd], [], [], 0.2)
    if r:
        try:
            n += len(os.read(fd, 4096))
        except BlockingIOError:
            pass
os.close(fd)
print(n)
PY
)
echo "raw_rx_bytes_in_3s: $RX"
printf 'rail after window: %s\n' "$(cat "$RAIL")"

echo "== kernel claim check (does the driver reset the MCU?) =="
printf '1' > "$SSP/enable_irq" 2>/dev/null
sleep 2
printf 'enable_irq after write: %s\n' "$(cat "$SSP/enable_irq" 2>/dev/null || echo '?')"
printf 'mcu_test  after write: %s\n' "$(cat "$SSP/mcu_test" 2>/dev/null || echo '?')"

echo "== recent kernel evidence =="
dmesg 2>/dev/null | grep -E "SSPBBD|lhd is NULL|chip ID retry|fail to initialize mcu" | tail -8 || true

if [ "$RX" = "0" ]; then
  echo "VERDICT: receiver silent (0 bytes) -> see GPS-BLOCKERS.md B0"
else
  echo "VERDICT: receiver produced $RX byte(s) -> transport alive; decode is the next boundary (B1)"
fi
