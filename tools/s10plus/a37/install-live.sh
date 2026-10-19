#!/bin/sh
# Apply an A37 userspace payload on the running S10+.
#
# The archive must contain files/<absolute-target-without-leading-slash> and a
# manifest.tsv of: target<TAB>mode<TAB>sha256.  Every old file is copied under
# /var/lib/nuxel/a37/rollback-* before its atomic replacement.  This script
# never accepts block devices, partitions, firmware, or boot artefacts.
set -eu

[ "$#" -eq 1 ] || { echo "usage: $0 PAYLOAD.tar.gz" >&2; exit 2; }
PAYLOAD=$1
case "$PAYLOAD" in /var/tmp/*) ;; *) echo 'payload must be in /var/tmp' >&2; exit 2;; esac
[ -f "$PAYLOAD" ] || { echo "payload missing: $PAYLOAD" >&2; exit 2; }

stamp=$(date -u +%Y%m%dT%H%M%SZ)
work=/var/tmp/nuxel-a37-install-$$
backup=/var/lib/nuxel/a37/rollback-$stamp
state=$backup/state.tsv
mkdir -p "$work" "$backup/files"
cleanup() { rm -rf "$work"; }
rollback() {
  [ -f "$state" ] || return 0
  while IFS='	' read -r target existed; do
    [ -n "$target" ] || continue
    if [ "$existed" = yes ]; then
      cp -a "$backup/files$target" "$target.a37-restore"
      mv -f "$target.a37-restore" "$target"
    else
      rm -f "$target"
    fi
  done < "$state"
  systemctl daemon-reload || true
  systemctl try-restart nuxel-button-manager.service nuxel-haptics.service || true
}
failed() {
  code=$?
  # Do not invoke this EXIT handler again while returning the rollback result.
  trap - EXIT HUP INT TERM
  echo "A37 install failed; restoring userspace backup $backup" >&2
  rollback
  cleanup
  exit "$code"
}
trap failed HUP INT TERM

# The handset's deliberately small rootfs has Python but no tar binary.
# Use the stdlib reader and reject links/path traversal before extracting.
/usr/bin/python3 - "$PAYLOAD" "$work" <<'PY'
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
[ -s "$manifest" ] || { echo 'manifest missing' >&2; exit 2; }

# Validate every target and every payload digest before replacing one byte.
while IFS='	' read -r target mode want; do
  case "$target" in
    /usr/share/nuxel/*|/usr/lib/nuxel/*|/usr/libexec/nuxel/*|/usr/local/bin/*|/etc/systemd/system/*|/etc/nuxel/*|/var/lib/nuxel/a37/*) ;;
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
done < "$manifest"

trap 'failed' EXIT
while IFS='	' read -r target mode want; do
  src=$work/files$target
  mkdir -p "$(dirname "$target")" "$(dirname "$backup/files$target")"
  if [ -e "$target" ]; then
    cp -a "$target" "$backup/files$target"
    printf '%s\tyes\n' "$target" >> "$state"
  else
    printf '%s\tno\n' "$target" >> "$state"
  fi
  staged="$target.a37-stage-$$"
  install -m "$mode" "$src" "$staged"
  test "$(sha256sum "$staged" | awk '{print $1}')" = "$want"
  mv -f "$staged" "$target"
  test "$(sha256sum "$target" | awk '{print $1}')" = "$want"
done < "$manifest"

systemctl daemon-reload
systemctl restart nuxel-button-manager.service
systemctl try-restart nuxel-haptics.service
systemctl enable nuxel-boot-sound.service
systemctl is-active --quiet nuxel-button-manager.service
systemctl is-active --quiet nuxel-haptics.service
test -p /run/nuxel-pwa-host.cmd
printf 'action reload-launcher\n' > /run/nuxel-pwa-host.cmd

printf '%s\n' "$backup" > /var/lib/nuxel/a37/latest-rollback
trap - EXIT
cleanup
echo "A37 install complete; rollback=$backup"
