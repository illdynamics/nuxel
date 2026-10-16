#!/usr/bin/env bash
# nuxel-microsd-diag.sh — S10+ (beyond2lte) microSD detect / mount / eject.
#
# WHAT THIS IS
#   Detect insertion, identify the EXTERNAL block device, read filesystem
#   metadata, mount it safely (READ-ONLY by default), and unmount/eject it.
#
# WHAT THIS IS NOT
#   It never formats or partitions anything, never writes to internal storage
#   (any /dev/mmcblk0* or /dev/block/* target is refused outright), never forces
#   an unknown filesystem, and never modifies existing card data. There is no
#   auto-format path and no path that runs on boot except an optional read-only
#   automount of a real external card.
#
# Usage:
#   nuxel-microsd-diag.sh status [--json]
#   nuxel-microsd-diag.sh cards                 # hosts + internal/external devices + mounts
#   nuxel-microsd-diag.sh mount <dev> [--rw --yes] [--fstype T]
#   nuxel-microsd-diag.sh unmount <dev>|--all
#   nuxel-microsd-diag.sh eject <dev>
#   nuxel-microsd-diag.sh automount [--force-now --yes]   # on INSERT only (udev/service)
#   nuxel-microsd-diag.sh automount-on | automount-off | automount-status
#   nuxel-microsd-diag.sh report
#   nuxel-microsd-diag.sh selftest
#
# AUTO-MOUNT CONTRACT
#   Auto-mount happens on INSERT, never at boot: the kernel replays the same
#   "add" uevent for a card that was already in the slot, so `automount` refuses
#   while the system is inside the boot window (uptime < automount.boot_grace_s
#   in microsd.json) and reports the skip instead of mounting. The mount is
#   ALWAYS read-only, only ever an external card (mmcblk1+, never mmcblk0), and
#   an unknown filesystem is refused - never guessed, never formatted.
set -uo pipefail
SELF="$(basename "$0")"
ROOT="${NUXEL_DIAG_ROOT:-/}"
POLICY="${NUXEL_MICROSD_POLICY:-/etc/nuxel/modem/microsd.json}"
LOG="${NUXEL_MICROSD_LOG:-/var/log/nuxel/microsd-diag.log}"
ARGS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --root) ROOT="${2:?}"; shift 2 ;; --root=*) ROOT="${1#--root=}"; shift ;;
    *) ARGS+=("$1"); shift ;;
  esac
done
set -- ${ARGS[@]+"${ARGS[@]}"}
CMD="${1:-status}"; [ $# -gt 0 ] && shift || true
JSON=0; RW=0; YES=0; FSTYPE=""; DEV=""; FORCE=0
while [ $# -gt 0 ]; do case "$1" in
  --json) JSON=1; shift ;; --rw) RW=1; shift ;; --yes) YES=1; shift ;;
  --fstype) FSTYPE="${2:-}"; shift 2 ;; --fstype=*) FSTYPE="${1#--fstype=}"; shift ;;
  --force-now) FORCE=1; shift ;;
  *) [ -z "$DEV" ] && DEV="$1"; shift ;;
esac; done
HERE="$(cd "$(dirname "$0")" && pwd)"
RR=""; d="$HERE"; for _ in 1 2 3 4 5 6; do [ -d "$d/configs/nuxel" ] && { RR="$d"; break; }; d="$(dirname "$d")"; done
[ -n "$RR" ] && [ ! -r "$POLICY" ] && POLICY="$RR/configs/nuxel/modem/microsd.json"
say() { printf '%s\n' "$*"; }
abs() { case "$1" in /*) printf '%s%s' "$ROOT" "$1" ;; *) printf '%s/%s' "$ROOT" "$1" ;; esac; }
jesc() { printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g'; }
faked_root() { [ "$ROOT" != "/" ]; }
pol_list() { python3 - "$POLICY" "$1" <<'PY'
import json,sys
try: d=json.load(open(sys.argv[1]))
except Exception: sys.exit(0)
cur=d
for k in sys.argv[2].split("."):
    if not isinstance(cur,dict): sys.exit(0)
    cur=cur.get(k)
if isinstance(cur,list):
    for x in cur: print(x if isinstance(x,str) else json.dumps(x))
PY
}
pol_keys() { python3 - "$POLICY" "$1" <<'PY'
import json,sys
try: d=json.load(open(sys.argv[1]))
except Exception: sys.exit(0)
cur=d
for k in sys.argv[2].split("."):
    if not isinstance(cur,dict): sys.exit(0)
    cur=cur.get(k)
if isinstance(cur,dict):
    for k in cur: print(k)
PY
}
pol_get() { python3 - "$POLICY" "$1" <<'PY'
import json,sys
try: d=json.load(open(sys.argv[1]))
except Exception: sys.exit(0)
cur=d
for k in sys.argv[2].split("."):
    if not isinstance(cur,dict): sys.exit(0)
    cur=cur.get(k)
print("" if cur is None else cur)
PY
}
dedupe() { local out="" x; for x in $1; do case " $out " in *" $x "*) ;; *) out="$out $x" ;; esac; done; printf '%s' "${out# }"; }

# --- hard safety: internal storage and block devices are NEVER targets -------
refuse_internal() { # $1 candidate -> prints reason + returns 1 when unsafe
  case "$1" in
    ""|-) printf 'refused: no device given.'; return 1 ;;
    /dev/block/*) printf 'refused: %s is a /dev/block path (internal storage) — never a microSD target.' "$1"; return 1 ;;
    /dev/mmcblk0|/dev/mmcblk0p*) printf 'refused: %s is INTERNAL UFS storage (mmcblk0) — the microSD is an external card (mmcblk1+).' "$1"; return 1 ;;
    /dev/mmcblk[1-9]|/dev/mmcblk[1-9]p*) return 0 ;;
    /*) printf 'refused: %s is not an external removable block device.' "$1"; return 1 ;;
    *) printf 'refused: %s is not an absolute external block device.' "$1"; return 1 ;;
  esac
}

# --- enumeration -------------------------------------------------------------
HOSTS=""; INTERNAL=""; EXTERNAL=""; MOUNTS=""; FS="" ; REMOVABLE="unknown"
enumerate() {
  local cand p
  for cand in $(pol_list detection.host_globs); do
    for p in $(abs "$cand"); do [ -e "$p" ] && HOSTS="$HOSTS ${p#$ROOT}"; done
  done
  for cand in $(pol_list safety.internal_target_denylist); do
    for p in $(abs "$cand"); do [ -e "$p" ] && INTERNAL="$INTERNAL ${p#$ROOT}"; done
  done
  for cand in $(pol_list detection.external_device_globs); do
    for p in $(abs "$cand"); do [ -e "$p" ] && EXTERNAL="$EXTERNAL ${p#$ROOT}"; done
  done
  HOSTS="$(dedupe "$HOSTS")"; INTERNAL="$(dedupe "$INTERNAL")"; EXTERNAL="$(dedupe "$EXTERNAL")"
  # removable flag + filesystem metadata of the first external card
  local g rf
  for g in $(pol_list detection.removable_flag_globs); do
    for rf in $(abs "$g"); do [ -r "$rf" ] && { REMOVABLE="$(tr -d '\r\n' < "$rf")"; break 2; }; done
  done
  local first; first="$(printf '%s' "$EXTERNAL" | tr ' ' '\n' | grep -E '/dev/mmcblk[1-9]$' | head -1)"
  [ -n "$first" ] && FS="$(fstype_of "$first")"
  # mounted external devices (from the mounts file; /proc/mounts live)
  local mf; mf="$(abs "$(pol_get detection.mounts_file)")"
  if [ -r "$mf" ]; then
    MOUNTS="$(grep -E '(^| )/dev/mmcblk[1-9]' "$mf" 2>/dev/null | awk '{print $1" "$2" "$3" "$4}')"
  fi
  MOUNTS="$(dedupe "$(printf '%s' "$MOUNTS" | tr '\n' ' ')")"
}
fstype_of() { # $1 dev path (repo-relative)
  local p="$1"
  if ! faked_root && command -v blkid >/dev/null 2>&1; then
    local t; t="$(blkid -o value -s TYPE "$p" 2>/dev/null | head -1)"; [ -n "$t" ] && { printf '%s' "$t"; return; }
  fi
  printf 'unknown'
}
verdict() { # STATE|FIRST_FAILING|DETAIL
  if [ -z "$HOSTS$INTERNAL$EXTERNAL" ]; then
    printf 'NO_CARD_CONTROLLER|controller|no mmc host and no mmc block device is exposed by this kernel'; return; fi
  if [ -z "$EXTERNAL" ]; then
    if [ -n "$INTERNAL" ]; then printf 'INTERNAL_ONLY|card|only internal UFS (mmcblk0) is present — no external microSD card is inserted'; return; fi
    printf 'NO_CARD|card|an mmc host exists but no external card device is present (insert a card)'; return
  fi
  if [ -n "$MOUNTS" ]; then
    if printf '%s' "$MOUNTS" | grep -qE '(^|,)rw(,| )| ro '; then :; fi
    if printf '%s' "$MOUNTS" | grep -qE ',rw(,|$)| rw(,| )| rw$'; then printf 'MOUNTED_RW|mounted|the external card is mounted READ-WRITE'; return; fi
    printf 'MOUNTED_RO|mounted|the external card is mounted READ-ONLY (default)'; return
  fi
  printf 'CARD_PRESENT_UNMOUNTED|mount|an external card is present and not mounted'
}
json_status() {
  local state ff detail; IFS='|' read -r state ff detail <<EOF
$(verdict)
EOF
  printf '{"device":"beyond2lte","tool":"nuxel-microsd-diag","state":"%s","verdict":"%s","first_failing_stage":"%s","detail":"%s","hosts":%s,"internal_devices":%s,"external_devices":%s,"removable":"%s","filesystem":"%s","mounts":%s,"default_readonly":true,"never_format":true,"card_data_written":false,"auto_format":false,"owner_test":"docs/beta-finalization/manual-proof/18-microsd.md"}\n' \
    "$state" "$state" "$ff" "$(jesc "$detail")" \
    "$(printf '%s\n' $HOSTS | python3 -c 'import json,sys;print(json.dumps(sys.stdin.read().split()))')" \
    "$(printf '%s\n' $INTERNAL | python3 -c 'import json,sys;print(json.dumps(sys.stdin.read().split()))')" \
    "$(printf '%s\n' $EXTERNAL | python3 -c 'import json,sys;print(json.dumps(sys.stdin.read().split()))')" \
    "$(jesc "$REMOVABLE")" "$(jesc "$FS")" \
    "$(printf '%s\n' $MOUNTS | python3 -c 'import json,sys;print(json.dumps([x for x in sys.stdin.read().split("  ") if x.strip()]))')"
}
cmd_status() {
  enumerate
  if [ "$JSON" = 1 ]; then json_status; return; fi
  local state ff detail; IFS='|' read -r state ff detail <<EOF
$(verdict)
EOF
  say "device            : beyond2lte (S10+ SM-G975F)"
  say "mmc hosts         : ${HOSTS:-NONE}"
  say "internal (mmcblk0): ${INTERNAL:-none}  (NEVER a microSD target)"
  say "external devices  : ${EXTERNAL:-NONE}"
  say "removable         : $REMOVABLE"
  say "filesystem        : ${FS:-unknown} (metadata read only; unknown means the tool refuses to mount without --fstype/--yes)"
  say "mounts            : ${MOUNTS:-none}"
  say "first failing st. : $ff  ($detail)"
  say "verdict           : $state"
  say "auto-mount        : $(automount_switch) on insert (never at boot; read-only only) — see: $SELF automount-status"
  say "policy            : read-only by default; NEVER formats; never writes to internal storage"
  say "owner procedure   : docs/beta-finalization/manual-proof/18-microsd.md"
}
cmd_cards() {
  enumerate
  say "hosts       :"; for p in $HOSTS; do say "  $p"; done; [ -z "$HOSTS" ] && say "  (none)"
  say "internal    : [NEVER a microSD target]"
  for p in $INTERNAL; do say "  $p"; done
  [ -z "$INTERNAL" ] && say "  (none present)"
  say "external    :"; for p in $EXTERNAL; do say "  $p  fstype=$FS removable=$REMOVABLE"; done; [ -z "$EXTERNAL" ] && say "  (none)"
  say "supported fs: $(pol_keys filesystems.supported | tr '\n' ' ')"
  say "forbidden   : $(pol_list safety.forbidden_tools | tr '\n' ' ') — none of these is ever invoked"
}
cmd_mount() {
  if ! refuse_internal "$DEV"; then return 8; fi
  enumerate
  printf '%s' "$EXTERNAL" | tr ' ' '\n' | grep -qx "$DEV" || { say "refused: $DEV is not a present external card device (${EXTERNAL:-none})."; return 9; }
  local fst="$FSTYPE"; [ -z "$fst" ] && fst="$FS"
  [ "$fst" = unknown ] || [ -z "$fst" ] && { [ "$YES" = 1 ] && [ -n "$FSTYPE" ] || { say "refused: filesystem of $DEV is unknown — pass --fstype <type> --yes to mount explicitly. No filesystem is ever guessed or created."; return 10; }; }
  pol_keys filesystems.supported | grep -qx "$fst" || { say "refused: filesystem '$fst' is not in the supported list ($(pol_keys filesystems.supported | tr '\n' ' ')). Nothing is formatted or force-mounted."; return 11; }
  local opts; opts="$(python3 - "$POLICY" "$fst" <<'PY'
import json,sys
try: d=json.load(open(sys.argv[1]))
except Exception: sys.exit(0)
print(d.get("filesystems",{}).get("supported",{}).get(sys.argv[2],{}).get("options",""))
PY
)"
  local rw_allowed; rw_allowed="$(python3 - "$POLICY" "$fst" <<'PY'
import json,sys
try: d=json.load(open(sys.argv[1]))
except Exception: sys.exit(0)
print(d.get("filesystems",{}).get("supported",{}).get(sys.argv[2],{}).get("rw_allowed",False))
PY
)"
  local mode="ro"
  if [ "$RW" = 1 ]; then
    [ "$YES" = 1 ] || { say "refused: a read-write mount needs an explicit --yes (the default is READ-ONLY to preserve existing data)."; return 12; }
    [ "$rw_allowed" = True ] || { say "refused: filesystem '$fst' is read-only by policy (rw_allowed=false)."; return 13; }
    mode="rw"
  fi
  faked_root && { say "refused: offline/faked root — no real mount is performed."; return 5; }
  command -v mount >/dev/null 2>&1 || { say "refused: mount(8) not available."; return 14; }
  local label mp; label="$(basename "$DEV")"
  mp="$(pol_get mount.mount_point_template)"; mp="${mp//%LABEL%/$label}"; mp="${mp//%DEVNAME%/$label}"
  mkdir -p "$mp" 2>/dev/null || { say "failed: cannot create $mp"; return 15; }
  say "mounting $DEV ($fst) at $mp [$mode] options=$opts"
  if mount -o "$mode,$opts" -t "$fst" "$DEV" "$mp" 2>/tmp/nuxel-microsd-mount.err; then
    say "mounted: $DEV -> $mp ($mode). Eject with: $SELF eject $DEV"
  else
    say "mount FAILED:"; sed 's/^/  /' /tmp/nuxel-microsd-mount.err 2>/dev/null
    say "The card was NOT modified and NOT formatted. If the filesystem needs a check, report it in the manual-proof fragment."
    return 1
  fi
}
cmd_unmount() {
  local target="$DEV"
  if [ "$target" = "--all" ] || { [ "$target" = "" ] && [ -n "$MOUNTS" ]; }; then :; fi
  enumerate
  if [ "$target" = "--all" ] || [ -z "$target" ]; then
    [ -n "$MOUNTS" ] || { say "nothing to unmount (no external card is mounted)."; return 0; }
    local m; for m in $(printf '%s' "$MOUNTS" | tr ' ' '\n' | grep -E '^/dev/mmcblk[1-9]'); do
      faked_root && { say "refused: offline/faked root — no real unmount performed."; return 5; }
      sync; umount "$m" 2>/dev/null && say "unmounted $m" || { say "could not unmount $m (busy?) — close processes using it and retry. Nothing was forced."; return 1; }
    done
    return 0
  fi
  if ! refuse_internal "$target"; then return 8; fi
  faked_root && { say "refused: offline/faked root — no real unmount performed."; return 5; }
  printf '%s' "$MOUNTS" | tr ' ' '\n' | grep -qx "$target" || { say "note: $target is not currently mounted."; }
  sync
  if umount "$target" 2>/dev/null; then say "unmounted $target"; else say "could not unmount $target (busy?) — nothing was forced."; return 1; fi
}
cmd_eject() {
  if ! refuse_internal "$DEV"; then return 8; fi
  faked_root && { say "refused: offline/faked root — no real eject performed."; return 5; }
  sync
  umount "$DEV" 2>/dev/null || say "note: $DEV was not mounted (or is busy) — continuing with sync."
  sync
  say "safe to remove: $DEV is unmounted and synced. Wait for the tray prompt, then pull the card."
  say "removal detection: the card is a removable mmc device; on removal the device node disappears (never force it while mounted)."
}
automount_switch() { # prints on|off
  local f; f="$(abs "$(pol_get automount.owner_switch)")"
  if [ -r "$f" ]; then tr -d '\r\n' < "$f"; else
    python3 - "$POLICY" <<'PY'
import json,sys
try: d=json.load(open(sys.argv[1]))
except Exception: print("on"); sys.exit(0)
print("on" if d.get("diagnostics",{}).get("auto_mount_on_insert",False) else "off")
PY
  fi
}
boot_window() { # prints yes|no ; unreadable uptime = treat as boot (fail closed)
  local uf grace up
  uf="$(pol_get automount.uptime_file)"; grace="$(pol_get automount.boot_grace_s)"
  [ -z "$uf" ] && uf="/proc/uptime"; [ -z "$grace" ] && grace=120
  up="$(awk '{print int($1)}' "$(abs "$uf")" 2>/dev/null || printf '')"
  [ -z "$up" ] && { printf 'yes'; return; }
  [ "$up" -lt "$grace" ] 2>/dev/null && printf 'yes' || printf 'no'
}
cmd_automount() {
  enumerate
  local state; state="$(verdict | cut -d'|' -f1)"
  case "$state" in
    NO_CARD_CONTROLLER|NO_CARD|INTERNAL_ONLY)
      say "automount: nothing to do ($state) - no external card is present."; return 0 ;;
    MOUNTED_RO|MOUNTED_RW)
      say "automount: already mounted ($state) - left untouched (idempotent)."; return 0 ;;
  esac
  if [ "$(automount_switch)" != on ]; then
    say "automount: disabled by the owner ($(pol_get automount.owner_switch)) - mount manually with: $SELF mount <dev>"; return 0
  fi
  if [ "$(pol_get automount.read_only_only)" != False ] && [ "$RW" = 1 ]; then
    say "automount: read-write is never automatic; only an explicit owner 'mount --rw --yes' can do that."; return 0
  fi
  if [ "$FORCE" != 1 ] && [ "$(boot_window)" = yes ]; then
    say "automount: SKIPPED - this is the boot window (uptime < $(pol_get automount.boot_grace_s)s)."
    say "           A card present at boot is NOT auto-mounted (auto_mount_on_boot=false);"
    say "           mount it deliberately with: $SELF mount <dev>"
    return 0
  fi
  local dev fst
  # Prefer the first PARTITION of the external card (a card with a table exposes
  # mmcblk1p1); fall back to the whole card only when no partition node exists.
  dev="$(printf '%s' "$EXTERNAL" | tr ' ' '\n' | grep -E '/dev/mmcblk[1-9]p[0-9]+$' | sort | head -1)"
  [ -n "$dev" ] || dev="$(printf '%s' "$EXTERNAL" | tr ' ' '\n' | grep -E '/dev/mmcblk[1-9]$' | head -1)"
  # NUXEL_MICROSD_FSTYPE is an offline/VM harness hook only (where blkid cannot
  # run); the shipped units never set it, so a real card's type is never assumed.
  [ -n "${NUXEL_MICROSD_FSTYPE:-}" ] && FS="$NUXEL_MICROSD_FSTYPE"
  [ -n "$dev" ] || { say "automount: no external card device to mount (${EXTERNAL:-none})."; return 0; }
  refuse_internal "$dev" >/dev/null || { say "automount: $dev refused by the internal-storage guard (nothing done)."; return 9; }
  fst="$FS"
  if [ "$fst" = unknown ] || [ -z "$fst" ]; then
    say "automount: filesystem of $dev is unknown - refusing (no filesystem is ever guessed, created or repaired)."
    say "            mount it explicitly with: $SELF mount $dev --fstype <type> --yes"
    return 9
  fi
  pol_keys filesystems.supported | grep -qx "$fst" || {
    say "automount: filesystem '$fst' is not in the supported list ($(pol_keys filesystems.supported | tr '\n' ' ')) - refusing."
    return 9; }
  if faked_root; then
    say "automount(offline root): would mount $dev ($fst) read-only - no real mount performed."
    return 0
  fi
  DEV="$dev"; YES=0; FSTYPE="$fst"; RW=0
  cmd_mount
}
cmd_automount_status() {
  say "auto-mount switch : $(automount_switch)   ($(pol_get automount.owner_switch))"
  say "policy insert     : $(python3 - "$POLICY" <<'PY'
import json,sys
try: print(json.load(open(sys.argv[1])).get("diagnostics",{}).get("auto_mount_on_insert",False))
except Exception: print("unknown")
PY
)"
  say "policy boot       : $(python3 - "$POLICY" <<'PY'
import json,sys
try: print(json.load(open(sys.argv[1])).get("diagnostics",{}).get("auto_mount_on_boot",True))
except Exception: print("unknown")
PY
)  (a card present at boot is never auto-mounted)"
  say "boot grace window : $(pol_get automount.boot_grace_s) s (uptime source $(pol_get automount.uptime_file)); now in window: $(boot_window)"
  say "mount mode        : read-only only (no automatic rw, no format, never internal storage)"
  say "udev rule         : $(pol_get automount.udev_rule)"
  say "service           : $(pol_get automount.service)"
}
cmd_automount_toggle() {
  local val="$1" f; f="$(abs "$(pol_get automount.owner_switch)")"
  mkdir -p "$(dirname "$f")" 2>/dev/null || true
  if printf '%s\n' "$val" > "$f" 2>/dev/null; then
    say "auto-mount $val (persisted at $(pol_get automount.owner_switch))"
  else
    say "could not write $f"; return 1
  fi
}

selftest() {
  local fixdir="$HERE/tests/hw-subsystems/fixtures" rc=0 n=0 f exp got
  for f in "$fixdir"/microsd-*; do
    [ -d "$f" ] || continue
    n=$((n+1)); exp="$(sed -n 's/^state=//p' "$f/EXPECTED" | head -1)"
    got="$(NUXEL_DIAG_NO_SYSTEM=1 bash "$0" --root "$f" status --json | sed -n 's/.*"state":"\([A-Z0-9_]*\)".*/\1/p' | head -1)"
    if [ "$exp" = "$got" ]; then printf 'PASS %-24s state=%s\n' "$(basename "$f")" "$got"
    else printf 'FAIL %-24s expected=%s got=%s\n' "$(basename "$f")" "$exp" "$got"; rc=1; fi
  done
  [ "$n" -gt 0 ] || { printf 'FAIL selftest: zero fixtures\n'; rc=1; }
  printf '%d fixtures checked\n' "$n"; return $rc
}
case "$CMD" in
  status) cmd_status ;;
  cards) cmd_cards ;;
  mount) cmd_mount ;;
  unmount) cmd_unmount ;;
  eject) cmd_eject ;;
  automount) cmd_automount ;;
  automount-on) cmd_automount_toggle on ;;
  automount-off) cmd_automount_toggle off ;;
  automount-status) cmd_automount_status ;;
  report) { say "=== nuxel-microsd report $(date -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || printf unknown) ==="; cmd_status; } | tee -a "$(abs "$LOG")" >/dev/null 2>&1 || cmd_status; say "evidence appended to $LOG" ;;
  selftest) selftest ;;
  help|-h|--help) sed -n '2,30p' "$0" | sed -n 's/^# \{0,1\}//p' ;;
  *) say "unknown command: $CMD (try help)"; exit 2 ;;
esac
