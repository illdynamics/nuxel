#!/usr/bin/env bash
# =============================================================================
# tools/dedupe-assets.sh
#
# Single-source asset copy step for Nuxel PWA applications (briq-23 / briq-as1).
#
# The background wallpaper (nuxel-background.png) is checked in ONLY once,
# in assets/ (the canonical copy). Its per-app copies are NOT committed —
# they are regenerated here at build time, just before VM/PWA packaging.
# The boot animation (nuxel-boot-animation.mp4) IS the Nuxel boot animation:
# the canonical copy AND the per-app copies are checked in (never ignored),
# and --verify still guarantees every copy stays byte-identical to the
# canonical source. This keeps the repo footprint small while every app's
# ./assets/ reference still resolves.
#
# Canonical sources:
#   assets/nuxel-background.png
#   assets/nuxel-boot-animation.mp4
#
# Destinations (each app's assets/ dir):
#   pwa/nuxel-home/assets/
#   pwa/nuxel-apps/{calendar,camera-gallery,files,mail,notes}/assets/
#
# Usage:
#   tools/dedupe-assets.sh            # populate per-app copies (default)
#   tools/dedupe-assets.sh --verify   # CI check: fail if any copy diverges
#                                     # from canonical or a stray copy exists
# =============================================================================

set -euo pipefail

# Repo root: this script lives at <repo>/tools/dedupe-assets.sh
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

BACKGROUND_SRC="${REPO_ROOT}/assets/nuxel-background.png"
ANIMATION_SRC="${REPO_ROOT}/assets/nuxel-boot-animation.mp4"

# All PWA application asset dirs that need a copy of the shared media.
PWA_ASSET_DIRS=(
    "${REPO_ROOT}/pwa/nuxel-home/assets"
    "${REPO_ROOT}/pwa/nuxel-apps/calendar/assets"
    "${REPO_ROOT}/pwa/nuxel-apps/camera-gallery/assets"
    "${REPO_ROOT}/pwa/nuxel-apps/files/assets"
    "${REPO_ROOT}/pwa/nuxel-apps/mail/assets"
    "${REPO_ROOT}/pwa/nuxel-apps/notes/assets"
)

copy_asset() {
    local src="$1"
    local dest="$2"
    if [ ! -f "$src" ]; then
        echo "[WARN] canonical asset missing: ${src}" >&2
        return 1
    fi
    mkdir -p "$(dirname "$dest")"
    cp -f "$src" "$dest"
    echo "[OK] ${src} -> ${dest}"
}

# verify_asset: byte-compare a destination copy against the canonical source.
# Fails the run when the file is missing or differs from canonical.
verify_asset() {
    local src="$1"
    local dest="$2"
    local label="$(basename "$src")"
    if [ ! -f "$dest" ]; then
        echo "[VERIFY-FAIL] ${dest} is missing (run dedupe-assets.sh to regenerate)" >&2
        return 1
    fi
    if cmp -s "$src" "$dest"; then
        echo "[VERIFY-OK] ${dest} matches canonical ${label}"
        return 0
    fi
    echo "[VERIFY-FAIL] ${dest} DIVERGES from canonical ${label}" >&2
    return 1
}

# find_stray_duplicates: locate any copy of the canonical assets that lives
# outside assets/ and outside the expected PWA asset dirs (i.e. a newly
# committed duplicate that git-ignoring + build-time copy should prevent).
find_stray_duplicates() {
    local stray=0
    # Walk the whole repo tree (excluding .git, .qq, kernel build trees and
    # the canonical assets/ dir) looking for files named after the media.
    while IFS= read -r -d '' f; do
        case "$f" in
            "$REPO_ROOT"/assets/*) continue ;;
            "$REPO_ROOT"/.git/*)   continue ;;
            "$REPO_ROOT"/.qq/*)    continue ;;
            "$REPO_ROOT"/kernel/*) continue ;;
        esac
        # Skip expected destination copies (they exist as build-time artifacts).
        local skip=0
        for dir in "${PWA_ASSET_DIRS[@]}"; do
            if [ "${f%/}" = "${dir%/}/nuxel-background.png" ] || \
               [ "${f%/}" = "${dir%/}/nuxel-boot-animation.mp4" ]; then
                skip=1
                break
            fi
        done
        if [ "$skip" -eq 1 ]; then
            continue
        fi
        echo "[VERIFY-FAIL] stray duplicate detected: ${f}" >&2
        stray=1
    done < <(find "$REPO_ROOT" \
        \( -type d -name .git -o -type d -name .qq -o -type d -name .codeseeq \) -prune -o \
        -type d -path "$REPO_ROOT/kernel" -prune -o \
        -type d -path "$REPO_ROOT/build" -prune -o \
        -type f \( -name "nuxel-background.png" -o -name "nuxel-boot-animation.mp4" \) \
        -print0 2>/dev/null)
    return "$stray"
}

MODE="populate"
if [ "${1:-}" = "--verify" ] || [ "${1:-}" = "--check" ]; then
    MODE="verify"
fi

if [ ! -f "$BACKGROUND_SRC" ]; then
    echo "[ERROR] canonical wallpaper missing: ${BACKGROUND_SRC}" >&2
    exit 1
fi

if [ "$MODE" = "verify" ]; then
    # CI assertion mode: fail if the single-source invariant is broken.
    echo "[VERIFY] Checking single-source PWA asset invariant..."
    errors=0

    for dir in "${PWA_ASSET_DIRS[@]}"; do
        verify_asset "$BACKGROUND_SRC" "${dir}/nuxel-background.png" || errors=$((errors + 1))
    done
    if [ -f "$ANIMATION_SRC" ]; then
        for dir in "${PWA_ASSET_DIRS[@]}"; do
            verify_asset "$ANIMATION_SRC" "${dir}/nuxel-boot-animation.mp4" || errors=$((errors + 1))
        done
    fi

    # Fail on any stray duplicate that a build-time copy should have removed.
    find_stray_duplicates || errors=$((errors + 1))

    if [ "$errors" -gt 0 ]; then
        echo "[VERIFY-FAIL] ${errors} single-source check(s) failed." >&2
        exit 1
    fi
    echo "[VERIFY-OK] All ${#PWA_ASSET_DIRS[@]} PWA asset dirs are byte-identical to the canonical assets/ tree."
    exit 0
fi

# Default populate mode.
for dir in "${PWA_ASSET_DIRS[@]}"; do
    copy_asset "$BACKGROUND_SRC" "${dir}/nuxel-background.png"
done

# Copy the boot animation into each app too so the full media set is
# available to every PWA.
if [ -f "$ANIMATION_SRC" ]; then
    for dir in "${PWA_ASSET_DIRS[@]}"; do
        copy_asset "$ANIMATION_SRC" "${dir}/nuxel-boot-animation.mp4"
    done
fi

echo "[DONE] PWA assets populated from single-source assets/ tree."
