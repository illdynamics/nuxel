#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "$0")/_common.sh"
IMG="${1:-}"
[ -n "$IMG" ] && [ -f "$IMG" ] || die "Usage: $0 /path/to/nuxel-beyond2lte-rootfs-fedora-phone-fixed.img"
init_out rootfs-image
DBG="$(find_e2fs_bin debugfs)" || die 'debugfs not installed. Run tools/install-mac-deps.sh'
FSCK="$(find_e2fs_bin e2fsck)" || die 'e2fsck not installed. Run tools/install-mac-deps.sh'
mkdir -p "$NUXEL_OUT/rootfs-image"
file "$IMG" > "$NUXEL_OUT/rootfs-image/host-file.txt" 2>&1 || true
shasum -a 256 "$IMG" > "$NUXEL_OUT/rootfs-image/sha256.txt"
# -fn: readonly filesystem check, never modifies image. fsck return flags preserved.
rc=0
"$FSCK" -fn "$IMG" > "$NUXEL_OUT/rootfs-image/e2fsck-readonly.txt" 2>&1 || rc=$?
printf 'e2fsck_readonly_exit=%s\n' "$rc" > "$NUXEL_OUT/rootfs-image/check-status.txt"
for path in / /etc /etc/passwd /etc/fstab /home /home/nuxel /usr/bin/python3 /usr/libexec/phosh /usr/bin/phoc /usr/lib/systemd/systemd /sbin/init /etc/udev/rules.d/90-nuxel-beyond2lte.rules /etc/nuxel/nuxel-beyond2lte.conf /etc/nuxel/phone-runtime-status /etc/greetd /usr/share/nuxel/nuxel-home/index.html /etc/systemd/system /usr/lib/systemd/system; do
  safe="$(printf '%s' "$path" | sed 's#/#_#g')"
  "$DBG" -R "stat $path" "$IMG" > "$NUXEL_OUT/rootfs-image/stat${safe}.txt" 2>&1 || true
done
for path in /etc/fstab /etc/nuxel/phone-runtime-status /etc/greetd/config.toml /etc/passwd /etc/hostname /etc/systemd/system/default.target; do
  safe="$(printf '%s' "$path" | sed 's#/#_#g')"
  "$DBG" -R "cat $path" "$IMG" > "$NUXEL_OUT/rootfs-image/cat${safe}.txt" 2>&1 || true
done
for path in /etc/systemd/system /usr/lib/systemd/system /etc/udev/rules.d /home/nuxel; do
  safe="$(printf '%s' "$path" | sed 's#/#_#g')"
  "$DBG" -R "ls -l $path" "$IMG" > "$NUXEL_OUT/rootfs-image/list${safe}.txt" 2>&1 || true
done
say 'Read-only filesystem and service-file inspection completed. Note: file presence does not prove successful runtime launch.'
if [ "$rc" -ne 0 ]; then warn "e2fsck returned $rc. Inspect rootfs-image/e2fsck-readonly.txt before flashing."; fi
