#!/usr/bin/env bash
# nuxel-touch-capture.sh — bounded, self-terminating touch capture for the S10+ (briq-01d).
#
# WHAT IT DOES
#   1. takes an owner-test lock so the boot-mode guard cannot reboot under the test;
#   2. calls nuxel-touch-trace.py --live --expect-finger, which:
#        - classifies the boot (charger/LPM) first,
#        - selects the touch node BY CAPABILITY (never by a node number),
#        - arms it with the measured open/close/open trick,
#        - records raw evdev bytes + per-event decode inside the window,
#        - snapshots /proc/interrupts before/after,
#        - collects libinput shim state, compositor input fds, Wayland seat state,
#        - runs the bounded DOM collector for touch-probe.html;
#   3. adds the operator-facing diagnostics (the verify-touch / final-verify
#      command set) to the same bundle so one directory is the whole evidence;
#   4. applies the machine gate and prints exactly one verdict.
#
# THE GATE (this is the only thing that may print CAPTURE_GATE=PASS)
#   >=1 BTN_TOUCH down AND >=1 up, with ABS_MT coordinates inside the device's own
#   reported range, AND those coordinates observed at the TOP layer (DOM).
#   Anything else prints CAPTURE_GATE=FAIL or CAPTURE_GATE=BLOCKED, and the
#   terminal verdict for the item stays NEEDS_OWNER_TEST:
#   a passing script on a desk is not a finger test.
#
# BOUNDED BY CONSTRUCTION
#   --seconds is enforced by the tracer's own alarm AND by `timeout` when present,
#   so the live console can never hang on this script.
#
# NO FLASHING, EVER
#   Nothing here writes a partition, a bootloader, a DTB, a modem, an EFS or a
#   partition table. There is no device-node write outside the read-only input
#   nodes, and no bootloader interface is invoked.
#
# USAGE (on the phone, as root, finger ready)
#   nuxel-touch-capture.sh --seconds 90
#   nuxel-touch-capture.sh --seconds 120 --out /var/lib/nuxel/touch-capture/tap-swipe
#   nuxel-touch-capture.sh --dry-run            # collect state, arm nothing
#   nuxel-touch-capture.sh --commands           # print the manual diagnostic set only
set -uo pipefail

SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
# The deploy manifest installs the canonical tracer here.  Prefer it over any
# legacy sibling left by an older diagnostic bundle; otherwise a repaired tracer
# could be shadowed by stale /usr/local/bin code during the owner proof.
TRACER="/usr/libexec/nuxel/nuxel-touch-trace.py"
[ -x "$TRACER" ] || TRACER="$SELF_DIR/nuxel-touch-trace.py"
BOOTMODE_GUARD="$SELF_DIR/nuxel-bootmode-guard.py"
LOCK="/run/nuxel-touch-capture.lock"

SECONDS_BUDGET=90
MAX_EVENTS=4000
MAX_BYTES=1048576
DRY_RUN=0
OUT=""
OUT_FROM_ARG=0
EXPECT_FINGER=1
PRINT_COMMANDS=0

while [ $# -gt 0 ]; do
  case "$1" in
    --seconds)      SECONDS_BUDGET="${2:?}"; shift 2 ;;
    --max-events)   MAX_EVENTS="${2:?}"; shift 2 ;;
    --max-bytes)    MAX_BYTES="${2:?}"; shift 2 ;;
    --out)          OUT="${2:?}"; OUT_FROM_ARG=1; shift 2 ;;
    --dry-run)      DRY_RUN=1; shift ;;
    --no-expect-finger) EXPECT_FINGER=0; shift ;;
    --commands)     PRINT_COMMANDS=1; shift ;;
    -h|--help)
      sed -n '2,40p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 64 ;;
  esac
done

# ---------------------------------------------------------------------------
# the exact manual diagnostic set (the verify-touch / final-verify basis).
# Kept in the script so the owner instructions and the automation can never drift.
# ---------------------------------------------------------------------------
print_commands() {
  cat <<'CMDS'
=== touch / boot-mode diagnostics (run these and keep the output) ===
# 1. boot mode first: a charger-mode boot has NO touchscreen at all
tr ' ' '\n' < /proc/cmdline | grep -E 'androidboot.mode|lpcharge|charging_mode'
# 2. did the driver bind, and did the input device appear?
dmesg | grep -i -E 'sec_ts|sec_touchscreen|tsp_|is_lpm' | tail -40
grep -A5 sec_touchscreen /proc/bus/input/devices
# 3. the IRQ line (must exist once the driver is bound)
grep -i -E 'sec_ts|4-0048' /proc/interrupts
# 4. which node is the panel? by capability, never by number:
#    (on the device the tracer is installed at /usr/libexec/nuxel/; from a
#     checkout use tools/s10plus/a33/nuxel-touch-trace.py)
python3 /usr/libexec/nuxel/nuxel-touch-trace.py --live --dry-run --seconds 5 \
        --out /var/lib/nuxel/touch-capture/node-scan
grep -A3 'PROP=' /var/lib/nuxel/touch-capture/node-scan/evdev.txt
# 5. did libinput accept it through the shim?
grep -a 'accepted=1' /run/nuxel-libinput-path.state | tail -3
# 6. does the compositor hold the input fd?
p=$(systemctl show -p MainPID --value nuxel-wayland); find /proc/"$p"/fd -maxdepth 1 | grep -c input
# 7. is the launcher's own DOM probe seeing events?
grep -a NUXEL_INPUT /run/nuxel-home.state | tail -10
# 8. the full bounded capture (this script):
nuxel-touch-capture.sh --seconds 90
CMDS
}

if [ "$PRINT_COMMANDS" = 1 ]; then
  print_commands
  exit 0
fi

if [ ! -f "$TRACER" ]; then
  echo "CAPTURE_GATE=BLOCKED reason=tracer-not-found path=$TRACER" >&2
  exit 70
fi

TS="$(date -u +%Y%m%dT%H%M%SZ)"
if [ -z "$OUT" ]; then
  OUT="/var/lib/nuxel/touch-capture/$TS"
fi
# The evidence bundle must NEVER be created inside the repository.  On the
# phone the default /var/lib/nuxel path always works; on a development host
# (unprivileged, or a read-only /var) the fallback is ${TMPDIR:-/tmp}, never
# "./" - Nuxel must not litter its own source tree with capture bundles.
if ! mkdir -p "$OUT" 2>/dev/null; then
  # An operator-supplied --out that cannot be created is a hard error: silently
  # writing somewhere else would break the BUNDLE= contract this script prints.
  if [ "$OUT_FROM_ARG" = 1 ]; then
    echo "CAPTURE_GATE=BLOCKED reason=out-dir-unwritable path=$OUT" >&2
    exit 71
  fi
  OUT="${TMPDIR:-/tmp}/nuxel-touch-capture-$TS"
  if ! mkdir -p "$OUT" 2>/dev/null; then
    echo "CAPTURE_GATE=BLOCKED reason=out-dir-unwritable path=$OUT (pass --out with a writable directory)" >&2
    exit 71
  fi
  echo "note: the default bundle path is not writable here; bundle goes to $OUT (outside the repository)" >&2
fi

echo "== nuxel-touch-capture =="
echo "BUNDLE=$OUT"
echo "BUDGET_SECONDS=$SECONDS_BUDGET MAX_EVENTS=$MAX_EVENTS MAX_BYTES=$MAX_BYTES DRY_RUN=$DRY_RUN"

# 1. owner-test lock: while this exists the boot-mode guard suppresses any reboot
#    ("never a blind reboot"). Released by the trap whatever happens.
if [ "$DRY_RUN" = 0 ]; then
  printf '%s %s\n' "$$" "$TS" > "$LOCK" 2>/dev/null || true
fi
release_lock() { [ "$DRY_RUN" = 0 ] && rm -f "$LOCK" 2>/dev/null; }
trap release_lock EXIT INT TERM

# 2. boot-mode classification into the bundle (cheap, and it explains an empty capture)
if [ -f "$BOOTMODE_GUARD" ]; then
  python3 "$BOOTMODE_GUARD" --status --no-write --json > "$OUT/bootmode.txt" 2>&1 || true
  if grep -q 'BOOTMODE=CHARGER_LPM' "$OUT/bootmode.txt" 2>/dev/null; then
    echo "!! charger-mode boot detected: the touchscreen does not exist on this boot."
    echo "   Unplug the charger and reboot normally, then re-run this capture."
    echo "CAPTURE_GATE=BLOCKED reason=charger-mode-boot evidence=$OUT/bootmode.txt"
    exit 10
  fi
fi

# 3. The sequence to perform while the window is open.  Printed BEFORE the capture
#    starts so the operator has it in front of them (and so the same text is in the
#    bundle's commands.txt).  One tap sequence = down/up, one swipe, one multi-contact.
cat <<'SEQ'
---- TOUCH SEQUENCE (perform these while the capture is armed) ----------------
  1. TAP DOWN/UP      one deliberate tap in the centre of the screen (slow, ~0.3 s)
  2. THREE TAPS       top-left, centre, bottom-right (catches a swapped/inverted axis)
  3. SWIPE            bottom third -> top third, slowly (>= 1 s), for scroll/gesture
  4. MULTI-CONTACT    two fingers down together for ~1 s, then lift both
  5. SELECT AN APP    tap a launcher tile (Terminal or Settings) and let it open
  6. KEYBOARD         if a text field is reachable, type three keys on the on-screen
                      keyboard (proves the keyboard's own hit testing)
  Then, and only then, answer the human half: did the UI actually respond?
------------------------------------------------------------------------------
SEQ
echo "SEQUENCE recorded in \$OUT/commands.txt (and above)"

# 3b. bounded capture through the one implementation of the logic.  --capture is used
#     (not --live) because it guarantees the per-event JSONL stream with kernel
#     timestamps AND coordinate-map.json, which is exactly what the owner taps are
#     graded against.
TRACER_ARGS=(--capture "$SECONDS_BUDGET" --out "$OUT"
             --max-events "$MAX_EVENTS" --max-bytes "$MAX_BYTES")
[ "$EXPECT_FINGER" = 1 ] && TRACER_ARGS+=(--expect-finger)
[ "$DRY_RUN" = 1 ] && TRACER_ARGS+=(--dry-run)

RUNNER=()
if command -v timeout >/dev/null 2>&1; then
  RUNNER=(timeout -k 5 "$((SECONDS_BUDGET + 25))")
fi
"${RUNNER[@]}" python3 "$TRACER" "${TRACER_ARGS[@]}" 2>&1 | tee "$OUT/trace.txt"
TRACE_RC="${PIPESTATUS[0]:-$?}"

# 4. the operator-facing diagnostics, into the same bundle
print_commands > "$OUT/commands.txt"
{
  echo "=== uptime / boot mode ==="; uptime 2>/dev/null
  tr ' ' '\n' < /proc/cmdline 2>/dev/null | grep -E 'androidboot.mode|lpcharge|charging_mode' \
    || echo "androidboot.mode: ABSENT (normal boot)"
  echo "=== driver / input devices ==="
  (dmesg 2>/dev/null | grep -i -E 'sec_ts|sec_touchscreen|tsp_|is_lpm' | tail -40) \
    || cat /proc/last_kmsg 2>/dev/null | grep -i -E 'sec_ts|sec_touchscreen|is_lpm' | tail -40
  grep -A5 sec_touchscreen /proc/bus/input/devices 2>/dev/null
  echo "=== irq ==="; grep -i -E 'sec_ts|4-0048' /proc/interrupts 2>/dev/null
  echo "=== libinput shim ==="; tail -6 /run/nuxel-libinput-path.state 2>/dev/null
  echo "=== services ==="; systemctl is-active nuxel-wayland nuxel-wl-fb nuxel-button-manager seatd 2>/dev/null
  echo "=== compositor input fds ==="
  p=$(systemctl show -p MainPID --value nuxel-wayland 2>/dev/null)
  # find, not `ls | grep` (SC2010): the count must not depend on filename quirks.
  echo "phoc input fds: $(find /proc/"$p"/fd -maxdepth 1 2>/dev/null | grep -c input)"
  echo "=== launcher DOM probe ==="; grep -a NUXEL_INPUT /run/nuxel-home.state 2>/dev/null | tail -10
  echo "=== bridge ==="; cat /run/nuxel-wl-fb.state 2>/dev/null
} > "$OUT/diagnostics.txt" 2>&1

# 5. one machine gate, stated once
GATE="BLOCKED"
VERDICT="NEEDS_OWNER_TEST"
if [ -f "$OUT/gate.json" ]; then
  read -r GATE VERDICT <<EOF
$(python3 - "$OUT/gate.json" <<'PY'
import json, sys
try:
    g = json.load(open(sys.argv[1]))
except Exception as e:
    print("BLOCKED UNKNOWN_%s" % e); raise SystemExit
if g.get("pass"):
    print("PASS NEEDS_OWNER_CONFIRMATION")
else:
    dom = g.get("dom_layer_state", "?")
    print("FAIL NEEDS_OWNER_TEST(dom=%s btn=%s down=%s up=%s points=%s)" %
          (dom, g.get("btn_touch_events"), g.get("down"), g.get("up"), g.get("points")))
PY
)
EOF
fi

echo "----------------------------------------------------------------"
echo "CAPTURE_GATE=$GATE"
echo "VERDICT=$VERDICT"
echo "BUNDLE=$OUT"
echo "EVIDENCE: $OUT/gate.json  $OUT/trace.txt  $OUT/events.jsonl  $OUT/coordinate-map.json"
echo "          $OUT/diagnostics.txt  $OUT/raw-touch.bin  $OUT/touch-events.log"
echo "ARCHIVE (from the host, so the evidence lands in the repository):"
echo "  tools/s10plus/a33/nuxel-touch-trace.py --archive $OUT --archive-dir docs/beta-finalization/live/evidence"
echo "log paths: /run/nuxel-touch-dom.log (DOM), /run/nuxel-libinput-path.state (libinput),"
echo "           /run/nuxel-home.state (launcher NUXEL_INPUT), $OUT/touch-events.log (raw decode)"
if [ "$GATE" = "PASS" ]; then
  echo
  echo "The pipeline delivered a real touch end to end. A human must now confirm the"
  echo "on-screen result (the UI actually responded) before this becomes VERIFIED:"
  echo "the gate proves events, not a usable UI."
else
  echo
  echo "No end-to-end touch was proven. Read the per-layer verdicts in trace.txt:"
  echo "  grep '^LAYER=' $OUT/trace.txt"
  echo "  grep '^FIRST_FAIL_LAYER=' $OUT/trace.txt"
  echo "The FIRST failing layer is where the pipeline stops; that is the thing to fix."
  echo "This item stays NEEDS_OWNER_TEST; it must NOT be reported as VERIFIED_ON_S10PLUS."
fi

if [ "$TRACE_RC" != 0 ] && [ "$GATE" != "PASS" ]; then
  exit 1
fi
exit 0
