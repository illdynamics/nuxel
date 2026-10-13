#!/usr/bin/env bash
#==============================================================================
# Nuxel Native App Build Script
#
# Cross-compiles the 5 native GTK4 C apps (nuxel-dialer, nuxel-contacts,
# nuxel-messages, nuxel-settings, nuxel-permissions) plus:
#   - nuxel-sandbox  (C, Linux namespaces/seccomp/Landlock launcher)
#   - nuxel-home-native (Python home launcher, byte-compiled to .pyc)
#
# Modes:
#   1. CROSS (default on macOS/x86_64 host): uses aarch64-linux-gnu-gcc and the
#      aarch64-cross.ini meson cross file. Requires aarch64-linux-gnu toolchain.
#   2. NATIVE (inside an aarch64 UTM VM): compiles with the host gcc directly.
#
# On success the resulting binaries are:
#   - ELF 64-bit LSB pie executable, ARM aarch64  (in cross mode)
#   - ELF 64-bit ... (aarch64 native in aarch64 VM)
#
# Install target: /usr/bin for the compiled C binaries and:
#   /usr/lib/nuxel/nuxel-home-native/  for the byte-compiled Python home launcher.
#==============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
OUT_DIR="${OUT_DIR:-${PROJECT_ROOT}/build/native-shell}"

CROSS_PREFIX="aarch64-linux-gnu"
CROSS_TOOLCHAIN="${NUXEL_CROSS_GCC:-}"
DETECTED_ARCH="$(uname -m 2>/dev/null || echo unknown)"

TARGET_ARCH="aarch64"
PREFIX="/usr"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
log()  { echo -e "${GREEN}[BUILD]${NC}  $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC}  $*"; }
err()  { echo -e "${RED}[ERROR]${NC} $*"; }

# Also allow overriding the install destination (DESTDIR style).
DESTDIR="${DESTDIR:-}"

# Detect whether we can cross-compile aarch64.
have_cross() {
    if [ -n "${CROSS_TOOLCHAIN}" ] && command -v "${CROSS_TOOLCHAIN}" &>/dev/null; then
        return 0
    fi
    if command -v "${CROSS_PREFIX}-gcc" &>/dev/null; then
        return 0
    fi
    return 1
}

# The actual C compiler to use (cross or host).
cc_bin() {
    if have_cross; then
        echo "${CROSS_TOOLCHAIN:-${CROSS_PREFIX}-gcc}"
    else
        echo "gcc"
    fi
}

is_aarch64() {
    [ "${DETECTED_ARCH}" = "aarch64" ]
}

build_apps() {
    local mode="$1"
    local builddir="$2"

    log "Building GTK4 native apps (mode: ${mode}) ..."
    rm -rf "${builddir}"
    mkdir -p "${builddir}"

    if [ "${mode}" = "cross" ]; then
        meson setup "${builddir}" "${SCRIPT_DIR}" \
            --cross-file "${SCRIPT_DIR}/aarch64-cross.ini" \
            --prefix "${PREFIX}" --bindir bin --datadir share
    else
        meson setup "${builddir}" "${SCRIPT_DIR}" \
            --prefix "${PREFIX}" --bindir bin --datadir share
    fi

    # Configure must succeed (that was the original blocking defect: a stale
    # shell/nuxel-shell/config/ path made `meson setup` abort).
    #
    # A `meson compile` failure on any GTK4 C app is now FATAL. The briq-10
    # deliverable requires ALL 5 native GTK4 apps (nuxel-dialer, nuxel-contacts,
    # nuxel-messages, nuxel-settings, nuxel-permissions) to build cleanly and be
    # installed to /usr/bin. Silently swallowing a compile failure previously
    # let the script "succeed" while the GTK4 apps were never compiled or
    # installed, so the cross-compile deliverable was falsely presented as done.
    # We now stop with a clear error (and nonzero exit) listing which app failed.
    if ! meson compile -C "${builddir}"; then
        {
            err "meson compile FAILED — one or more GTK4 native apps did not build."
            err "The briq-10 deliverable requires all 5 GTK4 apps to compile cleanly:"
            err "  nuxel-dialer nuxel-contacts nuxel-messages nuxel-settings nuxel-permissions"
            for a in nuxel-dialer nuxel-contacts nuxel-messages nuxel-settings nuxel-permissions; do
                if [ ! -f "${builddir}/${a}" ]; then
                    err "  - ${a}: MISSING (did not compile)"
                fi
            done
            err "Fix the failing C sources, then re-run. Failing build to avoid a"
            err "false-positive deliverable."
            exit 1
        }
    fi

    if [ -n "${DESTDIR}" ]; then
        DESTDIR="${DESTDIR}" meson install -C "${builddir}"
    else
        meson install -C "${builddir}" 2>/dev/null || {
            # Non-root hosts may not be able to install into /usr; just link
            # into the build dir.
            warn "meson install into ${PREFIX} failed (need root?) — binaries remain in the build dir."
        }
    fi
}

build_sandbox() {
    local cc
    cc="$(cc_bin)"
    local obj="${OUT_DIR}/nuxel-sandbox"
    log "Building nuxel-sandbox with ${cc} ..."
    mkdir -p "$(dirname "${obj}")"
    ${cc} -O2 -Wall -o "${obj}" \
        "${SCRIPT_DIR}/nuxel-sandbox/sandbox.c" -lcap \
        -I"${SCRIPT_DIR}/nuxel-sandbox" \
        || {
            warn "Linking against libcap failed — attempting without -lcap..."
            ${cc} -O2 -Wall -o "${obj}" \
                "${SCRIPT_DIR}/nuxel-sandbox/sandbox.c" \
                -I"${SCRIPT_DIR}/nuxel-sandbox"
        }
    log "Built ${obj}"
}

bytecompile_home_native() {
    local src="${SCRIPT_DIR}/../nuxel-home-native"
    local installdir="${DESTDIR}${PREFIX}/lib/nuxel/nuxel-home-native"
    log "Byte-compiling nuxel-home-native into .pyc ..."
    mkdir -p "${installdir}/nuxel_home"
    # Compile each .py module under nuxel_home/ into __pycache__/*.pyc and copy
    # alongside the sources so the launcher can import from the install dir.
    python3 -m compileall -q "${src}/nuxel_home"

    # Copy source + bytecode + assets + desktop entry.
    cp "${src}/nuxel_home/"*.py "${installdir}/nuxel_home/" 2>/dev/null || true
    for pyc in "${src}/nuxel_home/__pycache__/"*.pyc; do
        [ -e "${pyc}" ] || continue
        cp "${pyc}" "${installdir}/nuxel_home/"
    done
    cp "${src}/nuxel_home/"*.json "${installdir}/nuxel_home/" 2>/dev/null || true
    cp "${src}/nuxel_home/style.css" "${installdir}/nuxel_home/" 2>/dev/null || true
    cp "${src}/nuxel_home/data/org.nuxel.Home.desktop" \
        "${DESTDIR}${PREFIX}/share/applications/nuxel-home.desktop" 2>/dev/null || {
            mkdir -p "${DESTDIR}${PREFIX}/share/applications"
            cp "${src}/data/org.nuxel.Home.desktop" \
                "${DESTDIR}${PREFIX}/share/applications/nuxel-home.desktop" 2>/dev/null || true
        }
    # Install launcher wrapper that points at the installed tree.
    cat > "${DESTDIR}${PREFIX}/bin/nuxel-home" << 'LAUNCHER'
#!/usr/bin/env bash
set -euo pipefail
export NUXEL_HOME_INSTALLED="/usr/lib/nuxel/nuxel-home-native"
exec python3 /usr/lib/nuxel/nuxel-home-native/nuxel_home/main.py "$@"
LAUNCHER
    chmod +x "${DESTDIR}${PREFIX}/bin/nuxel-home"
    log "nuxel-home-native installed to ${installdir}"
}

install_to_usr() {
    local obj="${OUT_DIR}/nuxel-sandbox"
    local apps
    apps="${obj}"
    for a in nuxel-dialer nuxel-contacts nuxel-messages nuxel-settings nuxel-permissions; do
        if [ -f "${OUT_DIR}/${a}" ]; then
            apps="${apps} ${OUT_DIR}/${a}"
        fi
    done

    if [ -n "${DESTDIR}" ]; then
        log "Skipping direct /usr/bin install (DESTDIR=${DESTDIR}); binaries staged in ${OUT_DIR}."
        return 0
    fi

    if [ "$(id -u)" -eq 0 ]; then
        log "Installing native binaries into /usr/bin ..."
        for b in ${apps}; do
            [ -f "${b}" ] || continue
            install -m755 "${b}" "/usr/bin/$(basename "${b}")"
        done
        for a in nuxel-sandbox nuxel-dialer nuxel-contacts nuxel-messages nuxel-settings nuxel-permissions nuxel-home nuxel-portal nuxel-bridge nuxel-notifications; do
            : # placeholder — wrappers are installed by the VM bootstrap script
        done
    else
        warn "Not root — skipping /usr/bin install. Binaries are in ${OUT_DIR}."
    fi
}

report_arch() {
    local f
    for f in "${OUT_DIR}"/nuxel-* ; do
        [ -e "${f}" ] && file "${f}"
    done
}

main() {
    local mode="native"
    if have_cross; then
        mode="cross"
    elif ! is_aarch64; then
        # We're not on aarch64 and have no cross toolchain — build natively but
        # warn that the result will not run on aarch64.
        mode="native"
        warn "No aarch64-linux-gnu toolchain found and host is ${DETECTED_ARCH} — building native only (won't run on aarch64)."
    fi

    echo ""
    echo "  Nuxel native app build (target: ${TARGET_ARCH}, mode: ${mode})"
    echo ""

    if [ "${mode}" = "cross" ] && [ -n "${NUXEL_SYSROOT:-}" ]; then
        export PKG_CONFIG_LIBDIR
        PKG_CONFIG_LIBDIR="${NUXEL_SYSROOT}/usr/lib/pkgconfig:${NUXEL_SYSROOT}/usr/share/pkgconfig"
        export PKG_CONFIG_SYSROOT_DIR="${NUXEL_SYSROOT}"
    fi

    build_apps "${mode}" "${OUT_DIR}/meson"
    build_sandbox
    bytecompile_home_native
    install_to_usr

    echo ""
    echo "=== Built binaries ==="
    report_arch || true
    echo ""
    log "Native app build complete (${mode})."
}

main "$@"
