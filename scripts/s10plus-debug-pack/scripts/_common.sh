#!/usr/bin/env bash
# Shared macOS/Bash 3.2 helpers. All ADB operations in this pack are read-only.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACK_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
export PACK_DIR
say() { printf '[nuxel-debug] %s\n' "$*"; }
warn() { printf '[nuxel-debug][warn] %s\n' "$*" >&2; }
die() { warn "$*"; exit 1; }
require_cmd() { command -v "$1" >/dev/null 2>&1 || die "Missing $1. Run tools/install-mac-deps.sh"; }
adb_cmd() {
  if [ -n "${ANDROID_SERIAL:-}" ]; then command adb -s "$ANDROID_SERIAL" "$@";
  else command adb "$@"; fi
}
check_adb() {
  require_cmd adb
  local detected
  detected="$(adb devices | awk 'NR>1 && $2 ~ /^(recovery|device)$/ {n++} END {print n+0}')"
  if [ -z "${ANDROID_SERIAL:-}" ] && [ "$detected" -ne 1 ]; then
    adb devices -l >&2 || true
    die "Expected exactly one ADB device/recovery (found $detected). Set ANDROID_SERIAL for multiple devices."
  fi
  adb_cmd shell 'echo nuxel-adb-ok' >/dev/null || die 'ADB shell unavailable.'
}
require_recovery() {
  local serial state
  check_adb
  serial="$(adb_cmd get-serialno 2>/dev/null || true)"
  state="$(adb devices | awk -v s="$serial" '$1==s {print $2}')"
  [ "$state" = recovery ] || die "Device state is '$state', not recovery. Boot into TWRP before capturing previous-boot logs."
}
init_out() {
  local task="${1:-snapshot}"
  if [ -z "${NUXEL_OUT:-}" ]; then
    NUXEL_OUT="$PACK_DIR/captures/$(date -u +%Y%m%dT%H%M%SZ)-${task}-$$"
  fi
  mkdir -p "$NUXEL_OUT"
  export NUXEL_OUT
  if [ ! -e "$NUXEL_OUT/SESSION.txt" ]; then
    {
      printf 'Nuxel S10+ read-only debug collection\n'
      printf 'Captured UTC: %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
      printf 'Host OS: %s\n' "$(uname -a)"
      printf 'NOTE: Logs may contain serial numbers, IP addresses, credentials or private information.\n'
      printf 'No device partitions were written or mounted by this kit.\n'
    } > "$NUXEL_OUT/SESSION.txt"
  fi
  say "Output: $NUXEL_OUT"
}
record_status() { printf '%s\t%s\t%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1" "$2" >> "$NUXEL_OUT/CAPTURE-STATUS.tsv"; }
# Save remote command stdout and stderr separately, retaining nonfatal failures.
capture_shell() {
  local name="$1" remote="$2" destination="$NUXEL_OUT/$1" rc=0
  mkdir -p "$(dirname "$destination")"
  adb_cmd shell "$remote" > "$destination" 2> "${destination}.stderr" || rc=$?
  record_status "$name" "$rc"
  if [ "$rc" -ne 0 ]; then warn "$name: adb exit $rc (see .stderr)"; fi
  return 0
}
# ADB exec-out sends bytes without PTY line-ending transformation.
capture_file() {
  local name="$1" remote="$2" destination="$NUXEL_OUT/$1" rc=0
  mkdir -p "$(dirname "$destination")"
  adb_cmd exec-out "cat '$remote'" > "$destination" 2> "${destination}.stderr" || rc=$?
  if [ "$rc" -ne 0 ]; then rm -f "$destination"; fi
  record_status "$name" "$rc"
  if [ "$rc" -ne 0 ]; then warn "$name: missing or unreadable (adb exit $rc)"; fi
  return 0
}
find_e2fs_bin() {
  local tool="$1" prefix
  if command -v "$tool" >/dev/null 2>&1; then command -v "$tool"; return 0; fi
  if command -v brew >/dev/null 2>&1; then
    prefix="$(brew --prefix e2fsprogs 2>/dev/null || true)"
    if [ -x "$prefix/sbin/$tool" ]; then printf '%s\n' "$prefix/sbin/$tool"; return 0; fi
  fi
  return 1
}
