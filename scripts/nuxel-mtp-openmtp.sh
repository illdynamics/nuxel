#!/usr/bin/env bash
# nuxel-mtp-openmtp.sh — macOS host helper for the Nuxel MTP gadget.
#
# Why this exists
# ---------------
# The Nuxel (Samsung-derived) composite gadget advertises TWO configurations:
#
#   config #1 : MTP only
#   config #2 : CDC-ACM console + MTP
#
# macOS's AppleUSBCDCCompositeDevice driver prefers config #2, because the ACM
# interface matches a kernel driver. On config #2 libusb cannot claim the MTP
# interface and every libusb-based client (OpenMTP/kalam, MTPLX) fails with:
#
#   USBInterfaceOpen: error 0xe00002c5   (kIOReturnExclusiveAccess)
#
# libmtp works because it explicitly SET_CONFIGURATION to config #1 first.
# This script does that switch for OpenMTP, using OpenMTP's own bundled engine,
# with libmtp as a fallback. After the switch, macOS keeps config #1 and
# OpenMTP connects normally.
#
# Side effect: config #1 has no CDC-ACM, so /dev/cu.usbmodem* goes away for the
# duration. Detect this and do not surprise the user.
#
# Usage:
#   nuxel-mtp-openmtp.sh            # status + repair if needed
#   nuxel-mtp-openmtp.sh --status   # report only, never touch USB
#   nuxel-mtp-openmtp.sh --claim    # force the config switch, report result
#   nuxel-mtp-openmtp.sh --app      # claim, then launch the OpenMTP GUI
set -u

VID=0x18d1
PID=0x4ee7
OPENMTP_APP=${OPENMTP_APP:-/Applications/OpenMTP.app}
KALAM_CLI="$OPENMTP_APP/Contents/Resources/bin/mtp-cli"

die() { printf 'error: %s\n' "$*" >&2; exit 1; }
say() { printf '%s\n' "$*"; }

[ "$(uname -s)" = "Darwin" ] || die "this helper is macOS-only"

# Print the device record (empty when absent).
device_record() {
  ioreg -r -c IOUSBHostDevice -w0 -l 2>/dev/null |
    awk -v vid="6353" -v pid="20199" '
      BEGIN { RS = "" ; ORS = "\n\n" }
      $0 ~ ("\"idVendor\" = " vid) && $0 ~ ("\"idProduct\" = " pid) { print }
    '
}

current_config() {
  device_record | sed -n 's/.*"kUSBCurrentConfiguration" = \([0-9][0-9]*\).*/\1/p' | head -1
}

acm_port() { ls /dev/cu.usbmodem* 2>/dev/null | head -1; }

# A running GUI holds the USB interface, which makes the CLI probes fail for a
# legitimate reason. Never treat that as a broken device.
openmtp_running() { pgrep -f "$OPENMTP_APP/Contents/MacOS/OpenMTP" >/dev/null 2>&1; }

probe_kalam() {
  [ -x "$KALAM_CLI" ] || return 2
  local out
  out=$("$KALAM_CLI" 2>&1) || true
  printf '%s' "$out" | grep -qi 'no mtp device found' && return 1
  printf '%s' "$out" | grep -q 'selected storage' && return 0
  return 1
}

probe_libmtp() {
  command -v mtp-detect >/dev/null 2>&1 || return 2
  mtp-detect 2>&1 | grep -qi "Device recognized as MTP"
}

status() {
  local rec cfg port
  rec=$(device_record)
  if [ -z "$rec" ]; then
    say "device   : not present (VID $VID / PID $PID not on the USB bus)"
    say "action   : check cable; on the phone pick 'File transfer' on the lockscreen banner"
    return 1
  fi
  cfg=$(current_config)
  port=$(acm_port)
  say "device   : Nuxel S10+ Live Console present (VID $VID / PID $PID)"
  say "config   : ${cfg:-unknown}  (1 = MTP only, 2 = CDC-ACM + MTP)"
  say "serial   : $(printf '%s' "$rec" | sed -n 's/.*"kUSBSerialNumberString" = "\(.*\)".*/\1/p' | head -1)"
  say "acm port : ${port:-none}"
  if openmtp_running; then
    say "openmtp  : running and holding the device (expected)"
    return 0
  fi
  if probe_kalam; then
    say "openmtp  : OK — engine can claim the device"
    return 0
  fi
  say "openmtp  : cannot claim the device (this is the macOS config #2 problem)"
  return 2
}

claim() {
  local before after
  before=$(current_config)
  [ -n "$before" ] || die "device not present"

  if openmtp_running; then
    if [ "$(uname -s)" = "Darwin" ] && ioreg -r -c IOUSBHostDevice -w0 -l 2>/dev/null |
         grep -q "kUSBCurrentConfiguration\" = 1"; then
      say "OpenMTP is already running with config 1; nothing to do"
      return 0
    fi
    say "OpenMTP is running but the device is on the wrong config; quit it first:" >&2
    say "  osascript -e 'quit app \"OpenMTP\"'" >&2
    return 1
  fi

  if probe_kalam; then
    say "already claimable (config ${before:-?}); nothing to do"
    return 0
  fi

  say "switching USB configuration (was config ${before:-unknown}) ..."
  if probe_kalam; then :; else
    if command -v mtp-detect >/dev/null 2>&1; then
      mtp-detect >/dev/null 2>&1 || true
    fi
  fi
  sleep 1
  after=$(current_config)

  if probe_kalam; then
    say "openmtp attached (config ${after:-?})"
    return 0
  fi
  say "still not claimable (config ${after:-?})" >&2
  say "if the device vanished, replug it and retry" >&2
  return 1
}

case "${1:---status-and-repair}" in
  --status) status ;;
  --claim)  claim ;;
  --app)
    claim || exit 1
    open -a "$OPENMTP_APP" || die "could not launch $OPENMTP_APP"
    say "OpenMTP launched"
    ;;
  -h|--help) sed -n '2,30p' "$0" ;;
  --status-and-repair)
    status
    rc=$?
    if [ "$rc" = 2 ]; then
      say ""
      claim || exit 1
    fi
    ;;
  *) die "unknown option: $1 (try --help)" ;;
esac
