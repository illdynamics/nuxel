#!/usr/bin/env bash
# =============================================================================
# build-a25-initramfs.sh — assemble the A25 S10+ initramfs FROM REPO SOURCES
#
# This is the CI-capable, from-source replacement for the local candidate
# chain (tools/s10plus/a2x/build-a2x-initramfs.sh), which edited a *prebuilt*
# base archive that only exists on the bring-up workstation
# (build/out/s10plus/debug-candidates/A24/initramfs.cpio).  Nothing here needs
# that base: every member is produced or copied from a file committed to the
# repository, so a clean GitHub checkout can rebuild the exact archive that
# boots on the handset.
#
# WHAT THE A25 INITRAMFS IS (all hardware-proven on SM-G975F):
#   * /init                       boot/initramfs/init.sh (A20..A25 logic: userdata
#                                 discovery, Fedora ext4 root mount, switch_root,
#                                 embedded-anim handoff, live console, UI install)
#   * /bin/toybox + applet links  images/initramfs/bin/toybox
#   * /opt/nuxel/nuxel-ui         tools/s10plus/nuxel-ui.c            (freestanding aarch64;
#                                 A28 = the Nuxel Home launcher, registry from
#                                 pwa/nuxel-home/js/apps.js + css/style.css)
#   * /opt/nuxel/nuxel-console    tools/s10plus/a24-nuxel-console.c   (HUP-proof live shell)
#   * /opt/nuxel/nuxel-anim-player tools/s10plus/nuxel-anim-player.c  (MP4 -> DECON fbdev)
#   * /opt/nuxel/nuxel-fb-phone   tools/s10plus/nuxel-fb-phone.c
#   * /opt/nuxel/nuxel-postboot.sh tools/s10plus/a24/nuxel-postboot.sh
#   * /opt/nuxel/nuxel-ui.service  tools/s10plus/a28/nuxel-ui.service (A28: launcher)
#   * /opt/nuxel/nuxel-ui-fallback.service tools/s10plus/a23/nuxel-ui-fallback.service
#   * /opt/nuxel/nuxel-ui.rev     tools/s10plus/a28/nuxel-ui.rev     (A28 rev: the
#   * /opt/nuxel/libsystemd-shared-258.11-1.fc43.so
#                                 boot/s10plus/payload/ (kernel-4.14 pidfd patch,
#                                 SHA-256 pinned; see that directory's README)
#   * /opt/nuxel/nuxel-verify     tools/s10plus/a17/nuxel-verify.c    (init.sh uses it)
#
# Usage:
#   bash tools/s10plus/build-a25-initramfs.sh
#   CAND=A25 NUXEL_S10PLUS_A25_DIR=build/out/s10plus bash tools/s10plus/build-a25-initramfs.sh
#
# Env:
#   CAND                     candidate name (default A25)
#   NUXEL_S10PLUS_A25_DIR    output dir (default build/out/s10plus/debug-candidates/<CAND>)
#   NUXEL_AARCH64_CC         cross compiler (default aarch64-linux-gnu-gcc)
#
# Output (all under $NUXEL_S10PLUS_A25_DIR):
#   bin/<name>            cross-built aarch64 binaries
#   tree/                 staged initramfs root
#   initramfs.cpio        deterministic newc archive (uncompressed; the kernel
#                         embeds THIS file, the BOOT container carries lzma)
#   initramfs.manifest.json  per-member sha256 + the source each came from
#
# Exit: 0 ok, 1 build/verification failure, 2 missing toolchain/input.
# Fail-closed: a member whose bytes do not match its source fails the build.
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
export NUXEL_ROOT="${ROOT}"
CAND="${CAND:-A25}"
OUT="${NUXEL_S10PLUS_A25_DIR:-${ROOT}/build/out/s10plus/debug-candidates/${CAND}}"
CC="${NUXEL_AARCH64_CC:-aarch64-linux-gnu-gcc}"
NEWC="${ROOT}/tools/s10plus/newc.py"
CPIOBUILD="${ROOT}/tools/s10plus/mkinitramfs-cpio.py"
TOYBOX="${ROOT}/images/initramfs/bin/toybox"
PAYLOAD="${ROOT}/boot/s10plus/payload"
SD_LIB="${PAYLOAD}/libsystemd-shared-258.11-1.fc43.so"
SD_LIB_SHA="848149cf4b506aef00c0f777840c8e0b5306b65dcf1ae0a1b8c1a63057b4d981"

# Portable SHA-256 (GNU coreutils in CI, BSD/macOS locally).
sha256() {
    if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | cut -d' ' -f1
    elif command -v shasum >/dev/null 2>&1; then shasum -a 256 "$1" | cut -d' ' -f1
    else python3 -c 'import hashlib,sys;print(hashlib.sha256(open(sys.argv[1],"rb").read()).hexdigest())' "$1"
    fi
}

log()  { printf '[a25-initramfs] %s\n' "$*"; }
err()  { printf '[a25-initramfs][error] %s\n' "$*" >&2; }
die()  { err "$*"; exit 1; }

command -v "${CC}" >/dev/null 2>&1 || die "cross compiler not found: ${CC} (set NUXEL_AARCH64_CC)"
command -v python3 >/dev/null 2>&1 || die "python3 required"
[ -s "${TOYBOX}" ] || die "missing committed toybox: ${TOYBOX}"
[ -f "${NEWC}" ] || die "missing ${NEWC}"
[ -f "${CPIOBUILD}" ] || die "missing ${CPIOBUILD}"
[ -f "${ROOT}/boot/initramfs/init.sh" ] || die "missing boot/initramfs/init.sh"

# The patched systemd library is a *pinned* input: /init installs it over the
# Fedora rootfs copy after re-verifying exactly these constants.
[ -s "${SD_LIB}" ] || die "missing patched systemd library: ${SD_LIB}"
got="$(sha256 "${SD_LIB}")"
[ "${got}" = "${SD_LIB_SHA}" ] || die "systemd library sha256 mismatch: ${got} != ${SD_LIB_SHA}"
initsha="$(grep -m1 'NUXEL_SD_SHA256=' "${ROOT}/boot/initramfs/init.sh" | cut -d'"' -f2)"
[ "${initsha}" = "${SD_LIB_SHA}" ] || die "init.sh pins ${initsha} but this payload is ${SD_LIB_SHA} — refusing to ship a mismatch"
log "systemd payload pinned: ${SD_LIB_SHA:0:16}… (matches boot/initramfs/init.sh)"

# Never silently overwrite a candidate directory that already holds a PACKED
# image (a hardware-proven candidate: Image-A25 + boot.img + this archive). The
# A25 chain is incremental and evidence-carrying, so clobbering an archive that a
# flashed Image embeds destroys the only copy of that pairing. Use
# NUXEL_S10PLUS_A25_FORCE=1 (or a different NUXEL_S10PLUS_A25_DIR) deliberately.
if [ -s "${OUT}/initramfs.cpio" ] && [ -s "${OUT}/boot.img" ] && [ "${NUXEL_S10PLUS_A25_FORCE:-0}" != "1" ]; then
    err "refusing to overwrite ${OUT}/initramfs.cpio: ${OUT} holds a packed candidate (boot.img present)."
    err "Set NUXEL_S10PLUS_A25_FORCE=1 to overwrite, or use another NUXEL_S10PLUS_A25_DIR."
    exit 2
fi

BIN="${OUT}/bin"
STAGE="${OUT}/tree"
CPIO="${OUT}/initramfs.cpio"
mkdir -p "${BIN}"

# --- static aarch64 link probe (fail fast, with the actual fix) -------------
# nuxel-console / nuxel-verify / nuxel-hwprobe are statically linked against the
# TARGET libc. A cross toolchain installed without the target libc headers/libs
# still finds the HOST /usr/include and fails deep inside the build with
#   "/usr/include/features-time64.h: bits/wordsize.h: No such file or directory"
# (measured on the first v0.5.1-alpha CI run). Catch it here instead.
if ! printf '#include <stdio.h>\nint main(void){return 0;}\n' \
        | "${CC}" -static -o "${BIN}/.cc-probe" -x c - 2>"${BIN}/.cc-probe.log"; then
    err "cannot link a static aarch64 binary with ${CC}:"
    sed 's/^/    /' "${BIN}/.cc-probe.log" >&2
    err "the TARGET libc headers/libs are missing. On Debian/Ubuntu install:"
    err "    sudo apt-get install -y libc6-dev-arm64-cross"
    exit 2
fi
rm -f "${BIN}/.cc-probe" "${BIN}/.cc-probe.log"
log "static aarch64 link probe OK (${CC})"

# ---------------------------------------------------------------------------
# 1. userspace binaries
# ---------------------------------------------------------------------------
# Two build disciplines, both hardware-proven:
#   freestanding — no libc, no crt, raw syscalls (-nostdlib -ffreestanding).
#     nuxel-ui / nuxel-anim-player / nuxel-fb-phone are syscall-only renderers.
#   glibc static — -static, needed by the console (termios/pty) and the verifier.
FREESTANDING=(nuxel-ui nuxel-anim-player nuxel-fb-phone)
GLIBC_STATIC=(nuxel-console nuxel-hwprobe nuxel-verify)

src_of() {
    case "$1" in
        nuxel-ui)           echo "${ROOT}/tools/s10plus/nuxel-ui.c" ;;
        nuxel-anim-player)  echo "${ROOT}/tools/s10plus/nuxel-anim-player.c" ;;
        nuxel-fb-phone)     echo "${ROOT}/tools/s10plus/nuxel-fb-phone.c" ;;
        nuxel-console)      echo "${ROOT}/tools/s10plus/a24-nuxel-console.c" ;;
        nuxel-hwprobe)      echo "${ROOT}/tools/s10plus/nuxel-hwprobe.c" ;;
        nuxel-verify)       echo "${ROOT}/tools/s10plus/a17/nuxel-verify.c" ;;
        nuxel-syscall-probe) echo "${ROOT}/tools/s10plus/nuxel-syscall-probe.c" ;;
        nuxel-spawn-probe)  echo "${ROOT}/tools/s10plus/nuxel-spawn-probe.c" ;;
        nuxel-spawn-probe-static) echo "${ROOT}/tools/s10plus/nuxel-spawn-probe.c" ;;
        *) echo "" ;;
    esac
}

build_required() {
    local name="$1" src="$2"; shift 2
    [ -s "${src}" ] || die "missing source for ${name}: ${src}"
    log "cc ${name}  <- ${src#"${ROOT}/"}"
    if ! "${CC}" -Os -w -static -s -Wl,--build-id=none -o "${BIN}/${name}" "${src}" "$@" 2>"${BIN}/${name}.log"; then
        err "compiling ${name} failed:"; sed 's/^/    /' "${BIN}/${name}.log" >&2; exit 1
    fi
    [ -s "${BIN}/${name}" ] || die "${name} produced no binary"
    if command -v file >/dev/null 2>&1; then
        case "$(file -b "${BIN}/${name}" 2>/dev/null || echo unknown)" in
            *aarch64*) : ;;
            *) die "${name} is not an aarch64 binary" ;;
        esac
    fi
}

build_freestanding() {
    local name="$1" src="$2"
    [ -s "${src}" ] || die "missing source for ${name}: ${src}"
    log "cc ${name}  (freestanding)  <- ${src#"${ROOT}/"}"
    if ! "${CC}" -Os -w -ffreestanding -fno-builtin -nostdlib -static -s \
            -Wl,--build-id=none -o "${BIN}/${name}" "${src}" 2>"${BIN}/${name}.log"; then
        err "compiling ${name} failed:"; sed 's/^/    /' "${BIN}/${name}.log" >&2; exit 1
    fi
    [ -s "${BIN}/${name}" ] || die "${name} produced no binary"
}

for n in "${FREESTANDING[@]}"; do build_freestanding "$n" "$(src_of "$n")"; done
for n in "${GLIBC_STATIC[@]}";  do build_required   "$n" "$(src_of "$n")"; done

# Optional on-device diagnostic probes. /init runs each of them only if it is
# executable, so a toolchain that cannot build one (the spawn probe needs a
# libc that declares pidfd_spawn(): glibc >= 2.39) degrades the evidence but
# never the boot.
# Optional on-device diagnostic probes.  /init runs each of them only if it is
# executable, so a toolchain that cannot build one degrades the evidence but
# never the boot:
#   * nuxel-syscall-probe      freestanding, builds anywhere (runs in the initramfs)
#   * nuxel-spawn-probe        DYNAMIC aarch64: compiled on the Fedora glibc the
#                              phone rootfs ships and executed inside it after
#                              chroot (init.sh), so it must NOT be static
#   * nuxel-spawn-probe-static static build of the same probe, for the initramfs
# Both spawn probes call pidfd_spawn(), declared only by glibc >= 2.39
# (CI: ubuntu-24.04 = 2.39).  A host with an older sysroot skips them.
OPTIONAL_SKIPPED=""
optional_build() {  # name method
    local name="$1" method="$2" src
    src="$(src_of "${name}")"
    case "${method}" in
        freestanding) set -- -Os -w -ffreestanding -fno-builtin -nostdlib -static -s -Wl,--build-id=none ;;
        static)       set -- -Os -w -static -s -Wl,--build-id=none ;;
        dynamic)      set -- -Os -w ;;
    esac
    if "${CC}" "$@" -o "${BIN}/${name}" "${src}" 2>"${BIN}/${name}.log"; then
        log "cc ${name}  (optional diagnostic, ${method})  <- ${src#"${ROOT}/"}"
    else
        OPTIONAL_SKIPPED="${OPTIONAL_SKIPPED} ${name}"
        err "NOTE: optional diagnostic ${name} did not compile on this toolchain (${CC});"
        err "      it stays out of the archive (builds on glibc >= 2.39, CI: ubuntu-24.04)."
        rm -f "${BIN}/${name}"
    fi
}
optional_build nuxel-syscall-probe     freestanding
optional_build nuxel-spawn-probe       dynamic
optional_build nuxel-spawn-probe-static static
if [ -n "${OPTIONAL_SKIPPED}" ]; then log "optional probes skipped:${OPTIONAL_SKIPPED}"; fi

# ---------------------------------------------------------------------------
# 2. stage the initramfs tree
# ---------------------------------------------------------------------------
rm -rf "${STAGE}"
mkdir -p "${STAGE}"/{bin,boot,dev,etc,lib/modules,luks,newroot,proc,run,sys,tmp,opt/nuxel}

install -m 0755 "${BIN}/nuxel-ui"            "${STAGE}/opt/nuxel/nuxel-ui"
install -m 0755 "${BIN}/nuxel-console"       "${STAGE}/opt/nuxel/nuxel-console"
install -m 0755 "${BIN}/nuxel-anim-player"   "${STAGE}/opt/nuxel/nuxel-anim-player"
install -m 0755 "${BIN}/nuxel-fb-phone"      "${STAGE}/opt/nuxel/nuxel-fb-phone"
install -m 0755 "${BIN}/nuxel-hwprobe"       "${STAGE}/opt/nuxel/nuxel-hwprobe"
install -m 0755 "${BIN}/nuxel-verify"        "${STAGE}/opt/nuxel/nuxel-verify"
for n in nuxel-syscall-probe nuxel-spawn-probe nuxel-spawn-probe-static; do
    [ -s "${BIN}/${n}" ] && install -m 0755 "${BIN}/${n}" "${STAGE}/opt/nuxel/${n}"
done
install -m 0755 "${ROOT}/tools/s10plus/a24/nuxel-postboot.sh"        "${STAGE}/opt/nuxel/nuxel-postboot.sh"
install -m 0755 "${ROOT}/tools/s10plus/a28/nuxel-ui.service"         "${STAGE}/opt/nuxel/nuxel-ui.service"
install -m 0755 "${ROOT}/tools/s10plus/a23/nuxel-ui-fallback.service" "${STAGE}/opt/nuxel/nuxel-ui-fallback.service"
install -m 0644 "${ROOT}/tools/s10plus/a28/nuxel-ui.rev"             "${STAGE}/opt/nuxel/nuxel-ui.rev"
install -m 0755 "${SD_LIB}"                                          "${STAGE}/opt/nuxel/libsystemd-shared-258.11-1.fc43.so"

install -m 0755 "${ROOT}/boot/initramfs/init.sh" "${STAGE}/init"
install -m 0755 "${TOYBOX}"                      "${STAGE}/bin/toybox"
install -m 0644 "${ROOT}/images/initramfs/README.toybox.md" "${STAGE}/README.toybox.md"
install -m 0644 "${ROOT}/images/initramfs/luks/userdata.crypttab.in" "${STAGE}/luks/userdata.crypttab.in"

# toybox applet links (the proven set: /init depends on sh, mount, dd, grep,
# switch_root, e2fsck, modprobe, ...)
for applet in awk blkid cat chmod chown cp cut date dd df dmesg du e2fsck echo \
              false find grep gunzip gzip head ln losetup ls mdev mkdir mkfs.ext4 \
              mknod mkswap modprobe mount mountpoint mv poweroff printf ps reboot \
              rm sed sh sleep switch_root sync tail tar tr true umount; do
    ln -sfn toybox "${STAGE}/bin/${applet}"
done

# ---------------------------------------------------------------------------
# 3. deterministic newc archive + device records
# ---------------------------------------------------------------------------
log "packing newc archive (deterministic, fixed mtime)"
python3 "${CPIOBUILD}" --tree "${STAGE}" --out "${OUT}/initramfs.tree.cpio" --mtime 0

# Device nodes cannot be created by a non-root CI build, and the kernel needs
# /dev/console before /init runs (devtmpfs is mounted over /dev afterwards).
# Recreate the exact nodes of the hardware-proven A25 archive by record.
install -m 0644 "${OUT}/initramfs.tree.cpio" "${CPIO}"
insert_node() {  # name type major minor mode
    python3 "${NEWC}" insert "${CPIO}" "${CPIO}.t" --after dev \
        --name "$1" --type "$2" --major "$3" --minor "$4" --mode "$5" >/dev/null
    mv -f "${CPIO}.t" "${CPIO}"
}
insert_node dev/console  char  5   1   0600
insert_node dev/null     char  1   3   0666
insert_node dev/kmsg     char  1   11  0600
insert_node dev/watchdog char  10  130 0600
insert_node dev/sda14    block 8   14  0660
insert_node dev/sda31    block 259 15  0660
rm -f "${OUT}/initramfs.tree.cpio"

# ---------------------------------------------------------------------------
# 4. fail-closed verification: every member must be the intended bytes
# ---------------------------------------------------------------------------
log "verifying members"
tmpv="${OUT}/.verify.tmp"
fail=0
check() {  # member expected_file
    python3 "${NEWC}" extract "${CPIO}" "$1" "${tmpv}" >/dev/null 2>&1 || { err "MISSING member $1"; fail=1; return; }
    a="$(sha256 "${tmpv}")"
    b="$(sha256 "$2")"
    if [ "${a}" = "${b}" ]; then log "  OK   $1  ${a:0:16}…"
    else err "  FAIL $1 (${a:0:16}… != ${b:0:16}…)"; fail=1; fi
}
check init                    "${ROOT}/boot/initramfs/init.sh"
check bin/toybox              "${TOYBOX}"
check opt/nuxel/nuxel-ui      "${BIN}/nuxel-ui"
check opt/nuxel/nuxel-console "${BIN}/nuxel-console"
check opt/nuxel/nuxel-anim-player "${BIN}/nuxel-anim-player"
check opt/nuxel/nuxel-fb-phone    "${BIN}/nuxel-fb-phone"
check opt/nuxel/nuxel-verify      "${BIN}/nuxel-verify"
check opt/nuxel/nuxel-postboot.sh "${ROOT}/tools/s10plus/a24/nuxel-postboot.sh"
check opt/nuxel/nuxel-ui.service  "${ROOT}/tools/s10plus/a28/nuxel-ui.service"
check opt/nuxel/nuxel-ui.rev      "${ROOT}/tools/s10plus/a28/nuxel-ui.rev"
check opt/nuxel/libsystemd-shared-258.11-1.fc43.so "${SD_LIB}"
for n in nuxel-syscall-probe nuxel-spawn-probe nuxel-spawn-probe-static; do
    [ -s "${BIN}/${n}" ] && check "opt/nuxel/${n}" "${BIN}/${n}"
done
rm -f "${tmpv}"
[ "${fail}" -eq 0 ] || die "member verification failed"

python3 "${NEWC}" list "${CPIO}" | tail -1
CPIO_SHA="$(sha256 "${CPIO}")"
log "initramfs.cpio  $(wc -c <"${CPIO}" | tr -d ' ') bytes  sha256 ${CPIO_SHA}"

python3 - "$CPIO" "$OUT/initramfs.manifest.json" "$CAND" "${OPTIONAL_SKIPPED}" <<'PY'
import json, sys, os
sys.path.insert(0, os.path.join(os.environ.get("NUXEL_ROOT", "."), "tools", "s10plus"))
import newc
cpio, outp, cand, skipped = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
import hashlib
data = open(cpio, "rb").read()
members = []
for off, name, mode, size, dstart, dlen in newc.iter_records(data):
    if name == "TRAILER!!!":
        break
    members.append({"name": name, "mode": oct(mode), "size": size,
                    "sha256": hashlib.sha256(data[dstart:dstart+size]).hexdigest()})
json.dump({"candidate": cand, "archive_sha256": hashlib.sha256(data).hexdigest(),
           "archive_bytes": len(data), "members": members,
           "optional_probes_skipped": skipped.split()}, open(outp, "w"), indent=2)
print("manifest:", outp, "(%d members)" % len(members))
PY

log "A25_INITRAMFS_BUILD_OK  ${CPIO}"
