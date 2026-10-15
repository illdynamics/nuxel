#!/bin/sh
# A17: rebuild systemd 258.11-1.fc43 (aarch64) with BOTH Nuxel kernel-4.14 edits.
set -eu
B=/b
TOP=$B/rpmbuild
SPEC=$TOP/SPECS/systemd.spec
LOG=$B/nx17/build4.log
OUT=$B/nx17/out4
exec >"$LOG" 2>&1
say() { printf '[%s] %s\n' "$(date -u +%H:%M:%S)" "$*"; }

say "host: $(uname -m), $(nproc) cpus, $(free -m | awk '/Mem:/{print $2}') MiB"
mkdir -p "$OUT"
cp -f "$B/nx17/nuxel-systemd-edit.py" "$B/nuxel-systemd-edit.py" 2>/dev/null || true

say "spec hook (idempotent)"
if ! grep -q 'NUXEL/S10+ pidfd_spawn fallback' "$SPEC"; then
  sed -i 's|^%autosetup -C -p1$|%autosetup -C -p1\n\n# NUXEL/S10+ pidfd_spawn fallback (see /b/nuxel-systemd-edit.py)\n/usr/bin/python3 /b/nuxel-systemd-edit.py|' "$SPEC"
fi
grep -n 'NUXEL/S10+\|^%autosetup\|nuxel-systemd-edit' "$SPEC"

say "rpmbuild -bp"
rpmbuild -bp --define "_topdir $TOP" "$SPEC" >/dev/null

SRC=$(find "$TOP/BUILD" -name process-util.c -path "*/src/basic/*" 2>/dev/null | head -1 | sed "s|/src/basic/process-util.c$||")
say "source tree: $SRC"
grep -q "pidfd_spawn() is unavailable" "$SRC/src/basic/process-util.c" \
  || { say "FATAL: edit1 (posix_spawn fallback) missing"; exit 1; }
grep -q "or has no pidfd support" "$SRC/src/basic/pidref.c" \
  || { say "FATAL: edit2 (pidref_set_pid degrade) missing"; exit 1; }
say "BOTH EDITS VERIFIED PRESENT:"
grep -n "pidfd_spawn() is unavailable" "$SRC/src/basic/process-util.c"
grep -n "or has no pidfd support" "$SRC/src/basic/pidref.c"
say "--- pidref.c hunk ---"
grep -n -A8 "fd = pidfd_open(pid, 0);" "$SRC/src/basic/pidref.c" | head -14

say "rpmbuild -bb --nocheck (full build)"
rpmbuild -bb --nocheck --define "_topdir $TOP" "$SPEC" >/dev/null
say "BUILD OK"

cd "$OUT"
rpm2cpio "$TOP/RPMS/aarch64/systemd-258.11-1.fc43.aarch64.rpm" | cpio -idm --quiet
SO=usr/lib64/systemd/libsystemd-shared-258.11-1.fc43.so
ls -la "$SO"
sha256sum "$SO"
cp "$SO" "$B/nx17/libsystemd-shared-258.11-1.fc43.so"
# also grab the executor + main binary so we can diff them against the rootfs
rpm2cpio "$TOP/RPMS/aarch64/systemd-258.11-1.fc43.aarch64.rpm" | cpio -idm --quiet ./usr/lib/systemd/systemd ./usr/lib/systemd/systemd-executor 2>/dev/null || true
sha256sum usr/lib/systemd/systemd usr/lib/systemd/systemd-executor 2>/dev/null || true
say "deliverable: $B/nx17/libsystemd-shared-258.11-1.fc43.so"
say done
