#!/bin/sh
# Apply the A39 Home-only payload on a running S10+.
# Uses only atomic file replacement below /usr/share/nuxel and restores the
# per-file backup on any error.  It never writes partitions, firmware, or boot
# artifacts, and deliberately does not reload any service.
set -eu

[ "$#" -eq 2 ] || { echo "usage: $0 PAYLOAD.tar.gz ROLLBACK_DIR" >&2; exit 2; }
payload=$1
backup=$2
case "$payload" in /var/tmp/nuxel-a39-home.tar.gz) ;; *) echo "unexpected payload path" >&2; exit 2;; esac
case "$backup" in /var/lib/nuxel/a39/rollback-*) ;; *) echo "unexpected rollback path" >&2; exit 2;; esac
[ -f "$payload" ] && [ -d "$backup" ] || { echo "payload or rollback directory missing" >&2; exit 2; }

work=/var/tmp/nuxel-a39-install-$$
state=$backup/targets-before.tsv
mkdir -p "$work" "$backup/files"
cleanup() { rm -rf "$work"; }
rollback() {
  [ -f "$state" ] || return 0
  tab=$(printf '\t')
  while IFS="$tab" read -r target existed; do
    [ -n "$target" ] || continue
    if [ "$existed" = yes ]; then
      cp -a "$backup/files$target" "$target.a39-restore"
      mv -f "$target.a39-restore" "$target"
    else
      rm -f "$target"
    fi
  done < "$state"
}
failed() {
  rc=$?
  trap - EXIT HUP INT TERM
  echo "A39 install failed; restoring $backup" >&2
  rollback
  cleanup
  exit "$rc"
}
trap failed EXIT HUP INT TERM

/usr/bin/python3 - "$payload" "$work" <<'PY'
import pathlib, sys, tarfile
archive, destination = sys.argv[1:]
root = pathlib.Path(destination).resolve()
with tarfile.open(archive, 'r:gz') as tf:
    for member in tf.getmembers():
        path = pathlib.PurePosixPath(member.name)
        if (path.is_absolute() or '..' in path.parts or member.issym() or
                member.islnk() or member.isdev()):
            raise SystemExit(f'unsafe payload member: {member.name}')
    tf.extractall(root, filter='data')
PY

manifest=$work/manifest.tsv
[ -s "$manifest" ] || { echo "manifest missing" >&2; exit 2; }
: > "$state"
tab=$(printf '\t')
while IFS="$tab" read -r target mode want; do
  case "$target" in
    /usr/share/nuxel/pwa/nuxel-home/*|/usr/share/nuxel/assets/nuxel-bottom-bar.jpg|/usr/share/nuxel/assets/nuxel-bottom-bar2.png) ;;
    *) echo "unsafe target: $target" >&2; exit 2;;
  esac
  case "$target" in
    /dev/*|/boot|/boot/*|*.img|*/firmware/*|*/partition/*|*.dtb|*.dtbo|*/modem/*|*/efs/*)
      echo "forbidden target: $target" >&2; exit 2;;
  esac
  src=$work/files$target
  [ -f "$src" ] || { echo "payload missing $target" >&2; exit 2; }
  got=$(sha256sum "$src" | awk '{print $1}')
  [ "$got" = "$want" ] || { echo "payload hash mismatch $target" >&2; exit 2; }
  mkdir -p "$(dirname "$backup/files$target")"
  if [ -e "$target" ]; then
    cp -a "$target" "$backup/files$target"
    printf '%s\tyes\n' "$target" >> "$state"
  else
    printf '%s\tno\n' "$target" >> "$state"
  fi
done < "$manifest"

while IFS="$tab" read -r target mode want; do
  src=$work/files$target
  mkdir -p "$(dirname "$target")"
  staged="$target.a39-stage-$$"
  install -m "$mode" "$src" "$staged"
  test "$(sha256sum "$staged" | awk '{print $1}')" = "$want"
  mv -f "$staged" "$target"
  test "$(sha256sum "$target" | awk '{print $1}')" = "$want"
done < "$manifest"

while IFS="$tab" read -r target mode want; do
  test "$(sha256sum "$target" | awk '{print $1}')" = "$want"
done < "$manifest"
printf '%s\n' "A39 deploy complete: rollback=$backup" > "$backup/DEPLOYED.txt"
trap - EXIT HUP INT TERM
cleanup
echo "A39 install complete; rollback=$backup"
