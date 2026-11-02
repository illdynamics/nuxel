#!/usr/bin/env bash
# Nuxel USB connection-mode state machine (Charging <-> File Transfer).
#
# This helper owns the real configfs gadget transition.  It never exports a
# mounted filesystem as raw USB mass storage: File Transfer uses the vendor
# f_mtp function and the Nuxel MTP responder, which serves /home/nuxel through
# MTP object operations.  The existing CDC-ACM recovery console stays present
# in every mode.
set -uo pipefail
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

GADGET=${NUXEL_USB_GADGET:-/sys/kernel/config/usb_gadget/nuxel}
UDC_NAME=${NUXEL_UDC_NAME:-10c00000.dwc3}
CONFIG=${NUXEL_USB_CONFIG:-c.1}
FUNC=mtp.gs0
STATE_DIR=${NUXEL_USB_RUN_DIR:-/run/nuxel}
SELECTION="$STATE_DIR/connection-mode.json"
ACTIVATION="$STATE_DIR/usb-mode.state"
MTP_STATE="$STATE_DIR/mtp.state"
MTP_UNIT=nuxel-mtp.service
LOG_TAG=nuxel-usb-mode
# Only an explicit shared root is exported.  Never /home/nuxel, the rootfs,
# SSH keys, browser profiles or authenticator storage.
MTP_ROOT=${NUXEL_MTP_ROOT:-/home/nuxel/Shared}
# One controlled combined tree: an explicitly mounted removable card appears as
# "SD Card/" inside the shared MTP root.  This is a bind mount of the mounted
# filesystem, never a block-device export and never the live root/home.
SD_BIND="$MTP_ROOT/SD Card"
SD_STATE="$STATE_DIR/mtp-sd.mount"
MEDIA_STATE="$STATE_DIR/mtp-media.mounts"
MEDIA_DIRS="${NUXEL_MTP_MEDIA_DIRS:-Gallery Pictures Videos DCIM Downloads}"

log() { printf '%s %s: %s\n' "$(date -u +%FT%TZ)" "$LOG_TAG" "$*" >&2; }
say_state() { log "$*"; }

json_escape() { printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'; }

write_selection() {
  local mode="$1" busy="${2:-false}" err="${3:-}"
  mkdir -p "$STATE_DIR"
  local tmp="$SELECTION.tmp.$$"
  {
    printf '{\n'
    printf '  "mode": "%s",\n' "$(json_escape "$mode")"
    printf '  "transition_in_progress": %s,\n' "$busy"
    if [ -n "$err" ]; then printf '  "last_error": "%s"\n' "$(json_escape "$err")"; else printf '  "last_error": null\n'; fi
    printf '}\n'
  } > "$tmp"
  mv -f "$tmp" "$SELECTION"
  # Persist the explicit user choice across reboot.  /run is tmpfs; without this
  # a File Transfer selection silently reverted to Charging on every boot.
  mkdir -p /var/lib/nuxel
  printf '%s\n' "$mode" > /var/lib/nuxel/usb-mode.tmp
  mv -f /var/lib/nuxel/usb-mode.tmp /var/lib/nuxel/usb-mode
}

write_activation() {
  local mode="$1" active="$2" endpoint="$3" source="$4" error="${5:-}"
  mkdir -p "$STATE_DIR"
  local tmp="$ACTIVATION.tmp.$$"
  {
    printf '{\n'
    printf '  "mode": "%s",\n' "$(json_escape "$mode")"
    printf '  "active": %s,\n' "$active"
    printf '  "endpoint_state": "%s",\n' "$(json_escape "$endpoint")"
    printf '  "source": "%s",\n' "$(json_escape "$source")"
    if [ -n "$error" ]; then printf '  "error": "%s",\n' "$(json_escape "$error")"; else printf '  "error": null,\n'; fi
    printf '  "updated_at": "%s"\n' "$(date -u +%FT%TZ)"
    printf '}\n'
  } > "$tmp"
  mv -f "$tmp" "$ACTIVATION"
}

udc_state() { cat "/sys/class/udc/$UDC_NAME/state" 2>/dev/null || true; }
udc_speed() { cat "/sys/class/udc/$UDC_NAME/current_speed" 2>/dev/null || true; }
typec_connected() {
  local f
  for f in /sys/class/typec/port*/data_role; do
    [ -r "$f" ] || continue
    grep -q '\[device\]' "$f" 2>/dev/null && return 0
  done
  return 1
}
vbus_online() {
  local d online=0
  for d in /sys/class/power_supply/*; do
    [ -r "$d/type" ] || continue
    case "$(cat "$d/type" 2>/dev/null)" in
      USB|USB_PD|USB_TYPEC|USB_TYPE_C|USB_C|Mains|AC|DC|Charger|Quick_Charge|HV_Charger)
        if [ -r "$d/online" ] && [ "$(cat "$d/online" 2>/dev/null)" = 1 ]; then online=1; fi ;;
    esac
  done
  [ "$online" = 1 ]
}

unbind_udc() {
  if [ -w "$GADGET/UDC" ] && [ -n "$(cat "$GADGET/UDC" 2>/dev/null)" ]; then
    printf '\n' > "$GADGET/UDC" 2>/dev/null || true
  fi
}

bind_udc() {
  if [ -w "$GADGET/UDC" ]; then
    printf '%s\n' "$UDC_NAME" > "$GADGET/UDC" 2>/dev/null || return 1
  fi
  return 0
}

wait_configured() {
  local n=0
  while [ "$n" -lt 80 ]; do
    [ "$(udc_state)" = configured ] && return 0
    n=$((n+1)); sleep 0.1
  done
  return 1
}

# Return a mounted removable block filesystem, never the root/boot partition.
sd_mountpoint() {
  local dev base rem mp
  for dev in /dev/mmcblk* /dev/sd*; do
    [ -b "$dev" ] || continue
    base=$(basename "$dev" | sed -E 's/p?[0-9]+$//')
    rem="/sys/block/$base/removable"
    [ -r "$rem" ] || continue
    [ "$(cat "$rem" 2>/dev/null)" = "1" ] || continue
    mp=$(findmnt -rn -o TARGET --source "$dev" 2>/dev/null | head -1)
    [ -n "$mp" ] || continue
    [ "$mp" = "/" ] && continue
    printf '%s\n' "$mp"
    return 0
  done
  return 1
}


# Expose the user's real media folders as subfolders of the explicit MTP root.
# This is a bind mount of existing user directories (never the live home/root)
# and is removed when the mode leaves File Transfer.
media_binds_start() {
  local name src dst
  : > "$MEDIA_STATE"
  for name in $MEDIA_DIRS; do
    src="/home/nuxel/$name"
    [ -d "$src" ] || continue
    dst="$MTP_ROOT/$name"
    install -d -m 0755 "$dst" || continue
    chown nuxel:nuxel "$dst" 2>/dev/null || true
    if mountpoint -q "$dst"; then
      printf '%s\n' "$dst" >> "$MEDIA_STATE"
      continue
    fi
    if mount --bind "$src" "$dst"; then
      printf '%s\n' "$dst" >> "$MEDIA_STATE"
      log "media folder exported as MTP subfolder: $name"
    else
      log "media bind failed: $src -> $dst"
    fi
  done
}

media_binds_stop() {
  local dst
  [ -r "$MEDIA_STATE" ] || return 0
  while IFS= read -r dst; do
    [ -n "$dst" ] || continue
    if mountpoint -q "$dst"; then
      umount "$dst" 2>/dev/null || umount -l "$dst" 2>/dev/null || true
    fi
  done < "$MEDIA_STATE"
  rm -f "$MEDIA_STATE" 2>/dev/null || true
}

sd_bind_start() {
  local mp
  mp=$(sd_mountpoint) || return 0
  [ -n "$mp" ] || return 0
  install -d -m 0755 "$SD_BIND" || return 1
  chown nuxel:nuxel "$SD_BIND" 2>/dev/null || true
  if mountpoint -q "$SD_BIND"; then
    printf '%s\n' "$SD_BIND" > "$SD_STATE"
    return 0
  fi
  if ! mount --bind "$mp" "$SD_BIND"; then
    log "SD bind mount failed: source=$mp target=$SD_BIND"
    return 1
  fi
  printf '%s\n' "$SD_BIND" > "$SD_STATE"
  log "SD card exported as MTP subfolder from $mp"
  return 0
}

sd_bind_stop() {
  local b
  [ -r "$SD_STATE" ] || return 0
  b=$(head -1 "$SD_STATE" 2>/dev/null)
  [ -n "$b" ] || { rm -f "$SD_STATE" 2>/dev/null || true; return 0; }
  if mountpoint -q "$b"; then
    umount "$b" 2>/dev/null || umount -l "$b" 2>/dev/null || true
  fi
  rm -f "$SD_STATE" 2>/dev/null || true
}

remove_mtp_function() {
  systemctl stop "$MTP_UNIT" >/dev/null 2>&1 || true
  sd_bind_stop
  media_binds_stop
  # Never pkill -f here: an SSH shell command line can contain the daemon
  # path and would be killed with it.  systemd owns the responder process.
  if pgrep -f '^python3 /usr/lib/nuxel/nuxel-mtp-server$' >/dev/null 2>&1; then
    pgrep -f '^python3 /usr/lib/nuxel/nuxel-mtp-server$' | xargs -r kill 2>/dev/null || true
  fi
  unbind_udc
  rm -f "$GADGET/configs/$CONFIG/$FUNC" 2>/dev/null || true
  if [ -d "$GADGET/functions/$FUNC" ]; then
    rmdir "$GADGET/functions/$FUNC" 2>/dev/null || true
  fi
  rm -f /run/nuxel/mtp.state 2>/dev/null || true
}

add_mtp_function() {
  mkdir -p "$GADGET/functions/$FUNC" || return 1
  ln -sfn "$GADGET/functions/$FUNC" "$GADGET/configs/$CONFIG/$FUNC" || return 1
  # Microsoft OS descriptors help Windows bind the MTP interface.  These are
  # optional on Linux/macOS and are only set when the configfs leaves exist.
  if [ -w "$GADGET/os_desc/use" ]; then printf '1\n' > "$GADGET/os_desc/use" 2>/dev/null || true; fi
  if [ -w "$GADGET/os_desc/b_vendor_code" ]; then printf '0xcd\n' > "$GADGET/os_desc/b_vendor_code" 2>/dev/null || true; fi
  if [ -w "$GADGET/configs/$CONFIG/os_desc" ]; then :; fi
  return 0
}

wait_mtp_ready() {
  local n=0
  while [ "$n" -lt 100 ]; do
    [ -c /dev/mtp_usb ] || { n=$((n+1)); sleep 0.1; continue; }
    if [ -r "$MTP_STATE" ] && grep -q '"running": true' "$MTP_STATE" 2>/dev/null; then
      return 0
    fi
    n=$((n+1)); sleep 0.1
  done
  return 1
}

to_charging() {
  local why="${1:-user}"
  say_state "switching to Charging Mode (reason=$why)"
  remove_mtp_function
  # Re-bind the ACM-only gadget.  The Nuxel serial recovery console is the
  # default composition and is never removed by this helper.
  if ! bind_udc; then
    write_activation charging false "acm" "error:udc-bind" "could not bind $UDC_NAME"
    return 1
  fi
  wait_configured || true
  write_activation charging false "acm" "gadget:acm-console"
  write_selection charging false
  say_state "Charging Mode active (ACM console preserved; no storage exposed)"
  return 0
}

to_file_transfer() {
  say_state "switching to File Transfer Mode"
  mkdir -p "$MTP_ROOT"
  chmod 0755 "$MTP_ROOT" 2>/dev/null || true
  chown nuxel:nuxel "$MTP_ROOT" 2>/dev/null || true
  remove_mtp_function
  # Re-create the explicit SD subfolder only when a real removable filesystem
  # is mounted; card absent leaves no fake volume behind.
  sd_bind_start || log "continuing without SD export (internal Shared only)"
  media_binds_start || log "continuing without media-folder export"
  if ! add_mtp_function; then
    write_activation file_transfer false "error" "error:configfs" "could not create $FUNC"
    return 1
  fi
  if ! bind_udc; then
    write_activation file_transfer false "error" "error:udc-bind" "could not bind $UDC_NAME"
    return 1
  fi
  if ! wait_configured; then
    write_activation file_transfer false "error" "error:not-configured" "UDC did not reach configured state"
    return 1
  fi
  systemctl reset-failed "$MTP_UNIT" >/dev/null 2>&1 || true
  if ! systemctl start "$MTP_UNIT" >/dev/null 2>&1; then
    write_activation file_transfer false "error" "error:mtp-service" "could not start $MTP_UNIT"
    return 1
  fi
  if ! wait_mtp_ready; then
    write_activation file_transfer false "error" "error:mtp-not-ready" "MTP responder did not open /dev/mtp_usb"
    return 1
  fi
  # Do not claim file transfer merely because configfs is populated.  The host
  # must actually have selected a configuration and the responder must be live.
  local speed
  speed="$(udc_speed)"
  case "$speed" in
    low-speed|full-speed|high-speed|super-speed|super-speed-plus) ;;
    *) write_activation file_transfer false "configured" "error:no-host-link" "UDC configured but no host link speed"; return 1 ;;
  esac
  write_activation file_transfer true "mtp" "gadget:mtp+acm" ""
  write_selection file_transfer false
  say_state "File Transfer Mode active (MTP root=$MTP_ROOT, ACM preserved, speed=$speed)"
  return 0
}

status() {
  local selected="charging" active="false" endpoint="inactive"
  if [ -r "$SELECTION" ]; then
    selected=$(sed -n 's/.*"mode"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$SELECTION" | head -1)
    [ -n "$selected" ] || selected=charging
  fi
  if [ -r "$ACTIVATION" ]; then
    grep -q '"active": true' "$ACTIVATION" 2>/dev/null && active=true
    endpoint=$(sed -n 's/.*"endpoint_state"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$ACTIVATION" | head -1)
    [ -n "$endpoint" ] || endpoint=inactive
    local amode
    amode=$(sed -n 's/.*"mode"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$ACTIVATION" | head -1)
    if [ ! -r "$SELECTION" ] && [ -n "$amode" ]; then selected="$amode"; fi
  fi
  local sd_export=false
  if [ -r "$SD_STATE" ] && mountpoint -q "$SD_BIND" 2>/dev/null; then sd_export=true; fi
  printf '{"selected":"%s","active":%s,"endpoint_state":"%s","udc_state":"%s","udc_speed":"%s","vbus":%s,"typec_device":%s,"mtp_device":%s,"sd_export":%s}\n' \
    "$selected" "$active" "$endpoint" "$(udc_state)" "$(udc_speed)" \
    "$(vbus_online && echo true || echo false)" \
    "$(typec_connected && echo true || echo false)" \
    "$([ -c /dev/mtp_usb ] && echo true || echo false)" "$sd_export"
}

monitor() {
  # Keep the persisted state truthful after a physical eject/disconnect.  This
  # is intentionally independent of the WebView.  A three-sample debounce keeps
  # a transient re-enumeration from flapping the mode.  Only an active File
  # Transfer session needs a 1 s cadence; while charging, a 5 s cadence halves
  # nothing important but removes 80% of the wakeups from an idle bash poller.
  local down=0
  while :; do
    local interval=5
    if [ -r "$ACTIVATION" ] && grep -q '"mode": "file_transfer"' "$ACTIVATION" 2>/dev/null && grep -q '"active": true' "$ACTIVATION" 2>/dev/null; then
      interval=1
      local typec_ok=1
      compgen -G '/sys/class/typec/port*' >/dev/null 2>&1 && ! typec_connected && typec_ok=0
      if [ "$(udc_state)" != configured ] || ! vbus_online || [ "$typec_ok" -eq 0 ]; then
        down=$((down+1))
        if [ "$down" -ge 3 ]; then
          say_state "host disconnect/eject detected; returning to Charging Mode"
          to_charging "host-disconnect"
          down=0
        fi
      else
        down=0
      fi
    else
      down=0
    fi
    sleep "$interval"
  done
}

case "${1:-}" in
  charging) to_charging "${2:-user}" ;;
  file_transfer) to_file_transfer ;;
  status) status ;;
  monitor) monitor ;;
  *) echo "usage: $0 {charging|file_transfer|status|monitor}" >&2; exit 2 ;;
esac
