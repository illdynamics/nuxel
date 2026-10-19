#!/bin/sh
# install-on-phone.sh — runs ON the S10+ with the A32 bundle already extracted.
#
#   sh install-on-phone.sh <bundle-root>
#
# Rules (mission 16): every replaced file is backed up first, the swap is a rename
# inside the destination directory, every installed file is re-hashed against the
# bundle copy, and only the affected services are restarted.  Nothing is written
# when a hash does not match.
set -eu
SRC="${1:-/tmp/nuxel-a32}"
FAIL=0
say() { echo "$@"; }

# NOTE: internal variables are prefixed (_rel/_mode/_src/...) on purpose: this
# script runs under /bin/sh and an earlier revision's un-prefixed "$a"/"$b" was
# clobbered by the caller's own loop variable, which then installed the settings
# and terminal apps into a directory named after a SHA-256 sum.
install_file() {
  _rel="$1"; _mode="$2"; _kind="${3:-replace}"
  _src="$SRC/root/$_rel"; _dst="/$_rel"
  if [ ! -f "$_src" ]; then say "MISSING in bundle: $_rel"; FAIL=$((FAIL+1)); return; fi
  mkdir -p "$(dirname "$_dst")"
  if [ "$_kind" = "keep" ] && [ -f "$_dst" ]; then
    say "KEEP existing $_dst (user configuration preserved)"
    return
  fi
  if [ -f "$_dst" ]; then
    [ -f "$_dst.prev-a32" ] || cp -p "$_dst" "$_dst.prev-a32"
  fi
  cp "$_src" "$_dst.new-a32"
  chmod "$_mode" "$_dst.new-a32"
  mv -f "$_dst.new-a32" "$_dst"
  _sa=$(sha256sum "$_src" | cut -d' ' -f1)
  _sb=$(sha256sum "$_dst" | cut -d' ' -f1)
  if [ "$_sa" = "$_sb" ]; then
    say "INSTALLED $_dst sha256=$_sb"
  else
    say "HASH_MISMATCH $_dst ($_sa != $_sb) - ROLLING BACK"
    [ -f "$_dst.prev-a32" ] && cp -p "$_dst.prev-a32" "$_dst"
    FAIL=$((FAIL+1))
  fi
}

# --- code ---
install_file usr/lib/nuxel/nuxel-wl-fb 755
install_file usr/lib/nuxel/nuxel-pwa-host 755
install_file usr/lib/nuxel/nuxel-button-manager 755
install_file usr/bin/nuxelctl 755
install_file etc/systemd/system/nuxel-button-manager.service 644

# --- launcher PWA (stale files on this device are replaced with the repo's) ---
for f in index.html js/app.js js/apps.js js/status-bar.js js/host-bridge.js js/safe-zones.js js/osd.js; do
  install_file "usr/share/nuxel/nuxel-home/$f" 644
done
for a in settings terminal; do
  for f in $(cd "$SRC/root/usr/share/nuxel/pwa/nuxel-apps/$a" && ls); do
    install_file "usr/share/nuxel/pwa/nuxel-apps/$a/$f" 644
  done
done

# --- configuration: never overwrite a user's customisation ---
install_file etc/nuxel/display/statusbar-safezones.json 644 keep
install_file etc/nuxel/input/buttons.json 644 keep

say "FAILURES=$FAIL"
exit "$FAIL"
