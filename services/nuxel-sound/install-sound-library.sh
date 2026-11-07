#!/bin/sh
# Install the supplied Nuxel sounds into the user-visible library and seed the
# central manager configuration.  Idempotent: existing files are left intact
# unless their bytes differ (originals are always preserved in assets/nuxel-sounds/).
set -eu
ROOT=${ROOT:-/usr/share/nuxel}
LIB=${LIB:-/home/nuxel/Sounds}
SHARED=${SHARED:-/usr/share/nuxel/sounds}
SRC=${SRC:-$ROOT/assets/nuxel-sounds}
install -d -m 0755 -o nuxel -g nuxel "$LIB" "$SHARED"
installed=0
preserved=0
for src in "$SRC"/*; do
  [ -f "$src" ] || continue
  f=$(basename "$src")
  case "$f" in
    *.[Mm][Pp]3|*.[Ww][Aa][Vv]|*.[Oo][Gg][Gg]|*.[Oo][Gg][Aa]|*.[Ff][Ll][Aa][Cc]|*.[Mm]4[Aa]|*.[Aa][Aa][Cc]|*.[Oo][Pp][Uu][Ss]) ;;
    *) continue ;;
  esac
  for dest in "$LIB" "$SHARED"; do
    if [ -e "$dest/$f" ] && ! cmp -s "$src" "$dest/$f"; then
      # Never replace an owner-edited/custom file.  The shipped original stays
      # in assets/nuxel-sounds and remains selectable by a different name only
      # if it was installed previously.
      echo "preserved existing $dest/$f (content differs)" >&2
      preserved=$((preserved + 1))
      continue
    fi
    if [ ! -e "$dest/$f" ]; then
      install -m 0644 -o nuxel -g nuxel "$src" "$dest/$f"
      installed=$((installed + 1))
    fi
  done
done
for f in nuxel-alarm.mp3 nuxel-boot-audio.mp3 nuxel-pow.mp3; do
  [ -f "$SRC/$f" ] || { echo "missing supplied sound: $SRC/$f" >&2; exit 1; }
done
install -d -m 0755 /var/lib/nuxel/sound
if [ ! -s /var/lib/nuxel/sound/assignments.json ]; then
  cat > /var/lib/nuxel/sound/assignments.json <<JSON
{
  "schema_version": 1,
  "actions": ["volume", "boot", "alarm", "timer", "message", "notification", "other"],
  "assignments": {
    "volume": {"path": "$LIB/nuxel-pow.mp3", "gain": 1.0},
    "boot": {"path": "$LIB/nuxel-boot-audio.mp3", "gain": 1.0},
    "alarm": {"path": "$LIB/nuxel-alarm.mp3", "gain": 1.0},
    "timer": {"path": "$LIB/nuxel-alarm.mp3", "gain": 1.0},
    "message": {"path": "$LIB/nuxel-pow.mp3", "gain": 1.0},
    "notification": {"path": "$LIB/nuxel-pow.mp3", "gain": 1.0},
    "other": {"path": "$LIB/nuxel-pow.mp3", "gain": 1.0}
  }
}
JSON
fi
chmod 0644 /var/lib/nuxel/sound/assignments.json
echo "installed $installed supplied sound file(s) in $LIB and $SHARED; preserved $preserved custom file(s)"
