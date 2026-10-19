#!/usr/bin/env bash
# =============================================================================
# Nuxel release packager
#
# Collects the per-device build outputs under build/out/<device>/ and turns
# them into release-ready assets:
#
#   dist/nuxel-<version>-<device>.tar.gz   one archive per device
#   dist/nuxel-<version>-flashable.tar.gz  build/out/flashable/ (if present)
#   dist/SHA256SUMS.txt                    checksums for every asset
#   dist/RELEASE-NOTES.md                  CHANGELOG excerpt + manifest
#
# It is deliberately self-contained (pure bash + tar/sha256sum) so it runs both
# in GitHub Actions and locally against an existing build/out tree:
#
#   tools/package-release.sh --version v0.5.2-beta
#   tools/package-release.sh --version "$(cat VERSION)" --out build/dist
#
# Exit code is non-zero if no device output was found (nothing to release).
# =============================================================================
set -euo pipefail

NUXEL_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

IN_DIR="${NUXEL_ROOT}/build/out"
OUT_DIR="${NUXEL_ROOT}/dist"
VERSION=""
DEVICES=()
FROM_ASSETS=0

usage() {
    grep '^#' "$0" | sed 's/^# \{0,1\}//' | sed -n '1,30p'
    cat <<'USAGE'

Flags:
  --version V     version/tag used in asset names (default: contents of VERSION)
  --in DIR        source dir (default: build/out)
  --out DIR       destination dir (default: dist)
  --device KEY    only package this device (repeatable); default: all found
  --from-assets   don't read build/out; aggregate nuxel-<ver>-*.tar.gz already
                  present in --out (used by CI to build checksums + notes)
  -h, --help      show this help
USAGE
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --version) VERSION="$2"; shift 2 ;;
        --in)      IN_DIR="$2";  shift 2 ;;
        --out)     OUT_DIR="$2"; shift 2 ;;
        --device)  DEVICES+=("$2"); shift 2 ;;
        --from-assets) FROM_ASSETS=1; shift ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown argument: $1" >&2; usage >&2; exit 2 ;;
    esac
done

# Portable sha256 (coreutils sha256sum, else BSD shasum, else openssl).
sha256_of() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$@"
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$@"
    else
        for f in "$@"; do
            printf '%s  %s\n' "$(openssl dgst -sha256 -r "$f" | awk '{print $1}')" "$f"
        done
    fi
}

if [[ -z "${VERSION}" ]]; then
    VERSION="$(cat "${NUXEL_ROOT}/VERSION" 2>/dev/null || echo unknown)"
fi
# Sanitise: asset names must not contain spaces or path separators.
VERSION="${VERSION// /-}"
VERSION="${VERSION##*/}"
VER_TAG="${VERSION%-pre-alpha}"  # keep names short but recognisable

# Reproducible tarball flags when GNU tar is available (Linux CI); bsdtar
# (macOS) lacks --sort/--owner, so fall back to a plain archive there.
TAR_REPRO=()
if tar --version 2>/dev/null | grep -q 'GNU tar'; then
    TAR_REPRO=(--sort=name --owner=0 --group=0 --numeric-owner)
fi

mkdir -p "${OUT_DIR}"
OUT_DIR="$(cd "${OUT_DIR}" && pwd)"
if [[ "${FROM_ASSETS}" -eq 1 ]]; then
    IN_DIR=""
else
    [[ -d "${IN_DIR}" ]] || { echo "[package-release] no build output dir: ${IN_DIR}" >&2; exit 1; }
    IN_DIR="$(cd "${IN_DIR}" && pwd)"
fi

if [[ "${FROM_ASSETS}" -eq 1 ]]; then
    # Aggregate pre-built asset tarballs already in OUT_DIR.
    found=0
    : > "${OUT_DIR}/.manifest"
    for f in "${OUT_DIR}"/nuxel-"${VER_TAG}"-*.tar.gz; do
        [[ -e "$f" ]] || continue
        base="$(basename "$f")"
        dev="${base#nuxel-${VER_TAG}-}"; dev="${dev%.tar.gz}"
        printf '%s\t%s\n' "${dev}" "${base}" >> "${OUT_DIR}/.manifest"
        found=$((found + 1))
    done
    if [[ ${found} -eq 0 ]]; then
        echo "[package-release] --from-assets: no nuxel-${VER_TAG}-*.tar.gz in ${OUT_DIR}" >&2
        rm -f "${OUT_DIR}/.manifest"
        exit 1
    fi
    packed="${found}"
else
# Devices to package: explicit list, else every subdir of build/out that is not
# the shared rootfs staging dirs.
if [[ ${#DEVICES[@]} -eq 0 ]]; then
    for d in "${IN_DIR}"/*/; do
        [[ -d "$d" ]] || continue
        name="$(basename "$d")"
        case "$name" in rootfs|system.img) continue ;; esac
        DEVICES+=("$name")
    done
    if [[ ${#DEVICES[@]} -gt 1 ]]; then
        IFS=$'\n' DEVICES=($(printf '%s\n' "${DEVICES[@]}" | sort)); unset IFS
    fi
fi

packed=0
: > "${OUT_DIR}/.manifest"
for dev in "${DEVICES[@]}"; do
    src="${IN_DIR}/${dev}"
    if [[ ! -d "${src}" ]]; then
        echo "[package-release] skip '${dev}' (no ${src})"
        continue
    fi
    # Skip empty dirs (nothing to ship).
    if [[ -z "$(find "${src}" -type f -print -quit)" ]]; then
        echo "[package-release] skip '${dev}' (empty)"
        continue
    fi
    asset="nuxel-${VER_TAG}-${dev}.tar.gz"
    echo "[package-release] packaging ${dev} -> ${asset}"
    ( cd "${IN_DIR}" && COPYFILE_DISABLE=1 tar ${TAR_REPRO[@]+"${TAR_REPRO[@]}"} -czf "${OUT_DIR}/${asset}" "${dev}" )
    printf '%s\t%s\n' "${dev}" "${asset}" >> "${OUT_DIR}/.manifest"
    packed=$((packed + 1))
done

if [[ ${packed} -eq 0 ]]; then
    echo "[package-release] no device artifacts found under ${IN_DIR}" >&2
    rm -f "${OUT_DIR}/.manifest"
    exit 1
fi
fi

# Checksums over every asset produced.
( cd "${OUT_DIR}" && sha256_of ./*.tar.gz > SHA256SUMS.txt )

# Release notes: version + changelog excerpt (if present) + artifact manifest.
{
    echo "# Nuxel ${VERSION}"
    echo
    echo "Build artifacts for **Nuxel ${VERSION}** (Phase-1 bring-up images)."
    echo
    echo "## Artifacts"
    echo
    while IFS=$'\t' read -r dev asset; do
        echo "- \`${asset}\` (device: \`${dev}\`)"
    done < "${OUT_DIR}/.manifest"
    echo
    echo "## Checksums"
    echo
    echo '```'
    cat "${OUT_DIR}/SHA256SUMS.txt"
    echo '```'
    if [[ -f "${NUXEL_ROOT}/CHANGELOG.md" ]]; then
        echo
        echo "## Changelog"
        echo
        sed -n '1,60p' "${NUXEL_ROOT}/CHANGELOG.md"
    fi
} > "${OUT_DIR}/RELEASE-NOTES.md"

rm -f "${OUT_DIR}/.manifest"
echo "[package-release] wrote ${packed} device archive(s) + SHA256SUMS.txt + RELEASE-NOTES.md to ${OUT_DIR}"
ls -lh "${OUT_DIR}"
