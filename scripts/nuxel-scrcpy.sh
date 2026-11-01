#!/usr/bin/env bash
# nuxel-scrcpy.sh — run OFFICIAL scrcpy against a real Android ADB target.
#
# scrcpy mirrors ANDROID devices over ADB. It is NOT a Nuxel/Wayland screen
# share. The Nuxel S10+ runs native Fedora/Phoc and is not an Android target;
# use VNC Screen Sharing (scripts/nuxel-gui-tunnel.sh + Jump Desktop nux-vnc)
# to mirror the phone itself.
#
# Usage:
#   nuxel-scrcpy.sh --list
#   nuxel-scrcpy.sh --usb [SERIAL]
#   nuxel-scrcpy.sh --tcpip HOST[:PORT]        # adb connect then scrcpy
#   nuxel-scrcpy.sh --pair HOST:PORT           # prompts for the pairing code
#   nuxel-scrcpy.sh --gui ...                  # guiscrcpy if installed
#
# Security: the pairing code is never written to disk or logs. It is read from
# a prompt (or ADB_PAIR_CODE for automation). No ADB private key is touched.
# Only the official scrcpy/adb binaries from PATH are used. No binary download.
set -euo pipefail

ADB="${ADB:-adb}"
SCRCPY="${SCRCPY:-scrcpy}"
MODE=""; SERIAL=""; TARGET=""; PAIR=""; GUI=0
EXTRA=()

say() { printf '%s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 2; }

while [ $# -gt 0 ]; do
  case "$1" in
    --list) MODE=list; shift ;;
    --usb) MODE=usb; shift; if [ $# -gt 0 ] && [ "${1#-}" = "$1" ]; then SERIAL="$1"; shift; fi ;;
    --tcpip) MODE=tcpip; TARGET="${2:-}"; [ -n "$TARGET" ] || die "--tcpip needs HOST[:PORT]"; shift 2 ;;
    --pair) MODE=pair; PAIR="${2:-}"; [ -n "$PAIR" ] || die "--pair needs HOST:PORT"; shift 2 ;;
    --gui) GUI=1; shift ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    --) shift; EXTRA=("$@"); break ;;
    *) EXTRA+=("$1"); shift ;;
  esac
done

command -v "$ADB" >/dev/null 2>&1 || die "adb not found in PATH"
[ "$MODE" = list ] || command -v "$SCRCPY" >/dev/null 2>&1 || die "scrcpy not found in PATH"
if [ "$GUI" = 1 ]; then
  command -v guiscrcpy >/dev/null 2>&1 || say "guiscrcpy not installed; using official scrcpy CLI"
  GUI=0
fi

list_targets() {
  "$ADB" devices -l 2>/dev/null | sed '/^List of devices/d;/^$/d'
}

target_ready() {
  "$ADB" devices 2>/dev/null | awk -v s="$1" '$1==s && $2=="device" {ok=1} END{exit ok?0:1}'
}

# Native Nuxel detection: only used to give the truthful message, never to fake
# an Android endpoint.
if grep -qs '^ID=nuxel' /etc/os-release 2>/dev/null || [ -e /etc/nuxel/phone-runtime-status ]; then
  say "NOT_APPLICABLE_NATIVE_NUXEL"
  say "scrcpy supports Android ADB targets only; native Nuxel is Fedora/Wayland."
  say "Use VNC Screen Sharing for the Nuxel screen."
  exit 3
fi

case "$MODE" in
  list|"")
    if [ -z "$(list_targets)" ]; then
      say "NO_ANDROID_TARGET"
      say "Connect an Android device with USB debugging enabled, then re-run --usb."
      exit 1
    fi
    say "ANDROID_TARGETS"
    list_targets
    exit 0
    ;;
  pair)
    [ -z "${ADB_PAIR_CODE:-}" ] && { printf 'Pairing code: ' >&2; read -r ADB_PAIR_CODE; }
    [ -n "$ADB_PAIR_CODE" ] || die "empty pairing code"
    "$ADB" pair "$PAIR" "$ADB_PAIR_CODE"
    unset ADB_PAIR_CODE
    say "PAIRED $PAIR (wireless debugging; stop it on the Android device when done)"
    exit 0
    ;;
  usb)
    if [ -z "$SERIAL" ]; then
      mapfile -t devices < <("$ADB" devices 2>/dev/null | awk '$2=="device"{print $1}')
      [ "${#devices[@]}" -gt 0 ] || { say "NO_ANDROID_TARGET"; exit 1; }
      SERIAL="${devices[0]}"
    fi
    target_ready "$SERIAL" || die "target $SERIAL is not authorized/ready (check the Android USB-debugging prompt)"
    say "SCRCPY_USB target=$SERIAL"
    exec "$SCRCPY" -s "$SERIAL" --max-size=1280 --max-fps=30 "${EXTRA[@]}"
    ;;
  tcpip)
    case "$TARGET" in *:*) : ;; *) TARGET="$TARGET:5555" ;; esac
    "$ADB" connect "$TARGET"
    "$ADB" -s "$TARGET" wait-for-device
    say "SCRCPY_TCPIP target=$TARGET (adb Wi-Fi debugging; disconnect on exit)"
    set +e
    "$SCRCPY" -s "$TARGET" --max-size=1280 --max-fps=30 "${EXTRA[@]}"
    rc=$?
    set -e
    "$ADB" disconnect "$TARGET" >/dev/null 2>&1 || true
    exit "$rc"
    ;;
  *) die "unknown mode" ;;
esac
