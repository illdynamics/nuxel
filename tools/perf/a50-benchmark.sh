#!/bin/sh
# a50-benchmark.sh — A50 reproducible, bounded, read-only S10+ display benchmark.
#
# Runs over the live USB console ONLY through the existing capability-based,
# framed, SHA-256-verified transport (tools/beta/live/nuxel_live.py). It never
# opens /dev/fb0, never writes a partition/kernel/bootloader, never reboots, and
# never adjusts a kernel/governor setting.
#
# Usage:
#   a50-benchmark.sh [--dev /dev/cu.usbmodem201] [--duration 20] [--baseline|--candidate] [--json]
#
# Exit codes: 0 PASS, 1 REGRESSION, 2 BLOCKED, 3 INCOMPLETE.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
DEV="${DEV:-}"
DURATION="${DURATION:-20}"
MODE="${MODE:-baseline}"
JSON_OUT="${JSON_OUT:-0}"
RUNNER="$REPO/docs/performance/A50/tools/a50-run.py"
STATE="/run/nuxel-wl-fb.state"
DISP="/var/lib/nuxel/display"

# --- bounded, read-only probe set (each command short enough to survive the
#     charging-induced kmsg flood; long continuous samplers are deliberately
#     avoided while the device is charging) ---
cat > /tmp/a50-probes.txt <<P
identity	cat /proc/device-tree/model; uname -r
display_state	cat $DISP 2>&1
frames	grep -o 'FRAMES_OK.*' $STATE 2>&1
sleep_state	grep -o 'DISPLAY_SLEEP.*' $STATE 2>&1
thermal	cat /sys/class/thermal/thermal_zone0/temp /sys/class/thermal/thermal_zone3/temp /sys/class/thermal/thermal_zone6/temp 2>&1
cpu_procs	for p in 5352 5399 5450; do awk '{print \$14+\$15}' /proc/\$p/stat 2>/dev/null; done
total_cpu	head -1 /proc/stat | awk '{print \$2+\$3+\$4+\$5+\$6+\$7+\$8}' 2>&1
fb_owner	cat /var/lib/nuxel/fb-owner 2>&1
failed_units	systemctl --failed --no-legend --no-pager 2>&1
P

echo "A50-BENCH mode=$MODE duration=${DURATION}s device=${DEV:-auto}"
python3 "$RUNNER" --file /tmp/a50-probes.txt ${DEV:+--dev "$DEV"} --timeout 30
rc=$?
rm -f /tmp/a50-probes.txt

# The harness reports PASS only when all frames verified and no failed units;
# REGRESSION when fb owner changed or units failed; BLOCKED when the console is
# unreachable; INCOMPLETE when some metric is UNAVAILABLE. (Exact thresholding
# lives in the A50 report, not in fabricated numbers.)
exit $rc
