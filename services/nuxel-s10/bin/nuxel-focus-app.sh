#!/bin/sh
# Wait for a just-launched native toplevel, then raise it above the fullscreen
# Home surface and keep the layer-shell top bar / nav dock visible.  The bridge
# starts this after a successful native launch; it never kills anything.
#
# Flatpak/reverse-DNS ids often differ from the Wayland app_id the client
# publishes (com.sindresorhus.Caprine -> Caprine, org.ferdium.Ferdium ->
# ferdium, com.github.*.teams_for_linux -> teams-for-linux).  Match both the
# full id and its short/desktop StartupWMClass form so newly installed apps do
# not need a per-app table.
#
# Usage: nuxel-focus-app.sh <app-or-surface-id> [--probe]
#   --probe   one inventory pass only; 0 if an existing window was focused.
set -u
APP="${1:-}"
MODE="${2:-wait}"
[ -n "$APP" ] || exit 2
export XDG_RUNTIME_DIR=/run/nuxel-wayland
export WAYLAND_DISPLAY=wayland-0
FT=/usr/lib/nuxel/nuxel-foreign-toplevel

norm() {
  printf '%s' "$1" | tr 'A-Z' 'a-z' | tr -cd 'a-z0-9'
}

WANT=$(norm "$APP")
LAST=$(printf '%s' "$APP" | sed 's/.*\.//')
WANT_LAST=$(norm "$LAST")
WM_KEY=""
for d in /var/lib/flatpak/exports/share/applications \
         /home/nuxel/.local/share/flatpak/exports/share/applications \
         /usr/share/applications \
         /home/nuxel/.local/share/applications; do
  f="$d/$APP.desktop"
  [ -f "$f" ] || continue
  wm=$(sed -n '/^\[Desktop Entry\]/,/^\[/s/^StartupWMClass=//p' "$f" 2>/dev/null | head -n 1)
  [ -n "$wm" ] && WM_KEY=$(norm "$wm") && break
done

matches() {
  id="$1"
  nid=$(norm "$id")
  [ -n "$nid" ] || return 1
  [ "$nid" = "$WANT" ] && return 0
  [ -n "$WANT_LAST" ] && [ "$nid" = "$WANT_LAST" ] && return 0
  [ -n "$WM_KEY" ] && [ "$nid" = "$WM_KEY" ] && return 0
  # Short product id is a suffix of the reverse-DNS launcher id (Caprine).
  if [ "${#nid}" -ge 5 ]; then
    case "$WANT" in *"$nid") return 0 ;; esac
  fi
  # Launcher id is a suffix of the published id (rare, but harmless).
  if [ "${#WANT}" -ge 5 ]; then
    case "$nid" in *"$WANT") return 0 ;; esac
  fi
  return 1
}

pick() {
  listing="$1"
  ids=$(printf '%s\n' "$listing" | sed -n 's/.*app_id=\([^ ]*\).*/\1/p')
  # Exact/candidate-key matches win over suffix heuristics.
  for id in $ids; do
    nid=$(norm "$id")
    if [ "$nid" = "$WANT" ] || { [ -n "$WANT_LAST" ] && [ "$nid" = "$WANT_LAST" ]; } || \
       { [ -n "$WM_KEY" ] && [ "$nid" = "$WM_KEY" ]; }; then
      printf '%s' "$id"; return 0
    fi
  done
  for id in $ids; do
    if matches "$id"; then printf '%s' "$id"; return 0; fi
  done
  return 1
}

i=0
LIMIT=180
while [ "$i" -lt "$LIMIT" ]; do
  listing=$("$FT" list 2>/dev/null) || listing=""
  found=$(pick "$listing") || found=""
  if [ -n "$found" ]; then
    "$FT" focus "$found" >/dev/null 2>&1
    printf 'FOCUSED app_id=%s want=%s\n' "$found" "$APP"
    exit 0
  fi
  [ "$MODE" = "--probe" ] && exit 1
  i=$((i + 1))
  sleep 0.25
done
exit 1
