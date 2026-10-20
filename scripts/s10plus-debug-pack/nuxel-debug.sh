#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
cat_usage() {
  cat <<'USAGE'
Nuxel S10+ read-only bootloop debugging launcher

Usage:
  bash nuxel-debug.sh doctor
  bash nuxel-debug.sh install-tools             # preview
  bash nuxel-debug.sh install-tools --apply     # install tools on Mac
  bash nuxel-debug.sh collect                   # full previous-boot + TWRP capture
  bash nuxel-debug.sh watch                     # passive ADB state monitor
  bash nuxel-debug.sh inspect-boot /path/boot.img
  bash nuxel-debug.sh inspect-rootfs /path/rootfs.img
  bash nuxel-debug.sh triage /path/captures/session
  bash nuxel-debug.sh share /path/captures/session
  bash nuxel-debug.sh help

Read-only phone operations only. This kit cannot repair a kernel panic or display driver.
USAGE
}
case "${1:-help}" in
 doctor) shift; exec bash "$HERE/tools/doctor.sh" "$@";;
 install-tools) shift; exec bash "$HERE/tools/install-mac-deps.sh" "$@";;
 collect) shift; exec bash "$HERE/scripts/12-full-diagnostics.sh" "$@";;
 watch) shift; exec bash "$HERE/scripts/08-adb-usb-watch.sh" "$@";;
 inspect-boot) shift; exec bash "$HERE/scripts/09-inspect-boot-image.sh" "$@";;
 inspect-rootfs) shift; exec bash "$HERE/scripts/10-inspect-fedora-rootfs.sh" "$@";;
 triage) shift; exec bash "$HERE/scripts/11-triage-collected-logs.sh" "$@";;
 share) shift; exec bash "$HERE/scripts/14-create-share-bundle.sh" "$@";;
 help|-h|--help) cat_usage;;
 *) cat_usage; exit 2;;
esac
