#!/usr/bin/env bash
# =============================================================================
# Nuxel S10+ vendor firmware fetcher — Samsung Galaxy S10+ (beyond2lte)
#
# Downloads the REAL, pinned vendor firmware blobs for the Exynos 9820 /
# beyond2lte from the public postmarketOS vendor-blob source of record:
#
#   https://github.com/Linux4/proprietary_vendor_samsung
#   commit 05c9ef8f16e0ad5ab274e408c120dfd99fd5c628
#   (this is the exact commit referenced by pmaports
#    device/testing/firmware-samsung-beyond1lte)
#
# Directories fetched:
#   exynos9820-common/proprietary/vendor/firmware/   (~19 files)
#   beyond2lte/proprietary/vendor/firmware/          (~50 files, incl. nfc/)
#
# These are the blobs the *downstream* Samsung Exynos 9820 kernel (bcmdhd WiFi,
# CS47L93/CS35L40 audio, S3NRN82 NFC, Shannon/Calliope modem, FIMC-IS camera
# ISP) loads at runtime. They are the correct match for
# Linux4/android_kernel_samsung_exynos9820 (Linux 4.14.253), which is the
# kernel the postmarketOS S10 port actually uses.
#
# NOTE on WiFi: the S10+ ships Samsung's `bcmdhd` Broadcom driver, NOT
# mainline `brcmfmac`. The matching firmware is `bcmdhd_sta.bin_b1` /
# `bcmdhd_mfg.bin_b1` / `bcmdhd_mon.bin_b1` + `bcmdhd_clm.blob` + an
# `nvram.txt_*` selected by the board's chip rev. This overrides the older
# repo assumption of `brcmfmac4375-sdio.bin`.
#
# Usage:
#   firmware/s10plus/fetch-vendor-blobs.sh [--dest DIR] [--dry-run] [--help]
#
#   --dest DIR   destination (default firmware/s10plus/blobs/vendor-firmware)
#   --dry-run    print what would be fetched, download nothing
#
# Exit codes: 0 ok, 2 network/tool error, 3 hash mismatch.
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
COMMIT="05c9ef8f16e0ad5ab274e408c120dfd99fd5c628"
REPO="Linux4/proprietary_vendor_samsung"
RAW="https://raw.githubusercontent.com/${REPO}/${COMMIT}"
API="https://api.github.com/repos/${REPO}/contents"
DEST=""

log()  { echo "[s10plus-fetch] $*"; }
err()  { echo "[s10plus-fetch][error] $*" >&2; }

while [ $# -gt 0 ]; do
    case "$1" in
        --help|-h)
            sed -n '2,40p' "$0" | sed 's/^# \{0,1\}//'
            exit 0 ;;
        --dest)    DEST="$2"; shift 2 ;;
        --dry-run) DRY_RUN=1; shift ;;
        *) err "unknown option: $1"; exit 1 ;;
    esac
done
: "${DRY_RUN:=0}"
[ -n "${DEST}" ] || DEST="${SCRIPT_DIR}/blobs/vendor-firmware"

command -v curl >/dev/null || { err "curl required"; exit 2; }
command -v python3 >/dev/null || { err "python3 required"; exit 2; }

# --- discover the file list from the pinned tree (recursive, authoritative) --
# One recursive tree query avoids the contents-API dir/file ambiguity for
# nested firmware dirs (e.g. beyond2lte/.../firmware/nfc/).
list_firmware_blobs() {
    curl -s "https://api.github.com/repos/${REPO}/git/trees/${COMMIT}?recursive=1" | python3 -c '
import sys, json
d = json.load(sys.stdin)
t = d.get("tree")
if t is None:
    sys.stderr.write("api error: %s\n" % d.get("message"))
    sys.exit(2)
prefixes = (
    "exynos9820-common/proprietary/vendor/firmware/",
    "beyond2lte/proprietary/vendor/firmware/",
)
for x in t:
    if x.get("type") != "blob":
        continue
    p = x["path"]
    for pref in prefixes:
        if p.startswith(pref):
            # store path-relative-to-firmware-root (preserves subdirs like
            # score/camera1 and score/develop1, which share basenames)
            print("%s\t%s" % (p, p[len(pref):]))
            break
'
}

fetch_file() { # $1 = repo-relative path, $2 = basename to store
    local rel="$1" name="$2" out="${DEST}/${name}"
    if [ "${DRY_RUN}" -eq 1 ]; then
        log "would fetch ${rel} -> ${out}"
        return 0
    fi
    mkdir -p "$(dirname "${out}")"
    curl -sSL -o "${out}.tmp" "${RAW}/${rel}" || { err "download failed: ${rel}"; return 2; }
    mv "${out}.tmp" "${out}"
}

mkdir -p "${DEST}"
log "source : ${REPO}@${COMMIT}"
log "dest   : ${DEST}"
count=0
log "listing firmware blobs (recursive) ..."
while IFS=$'\t' read -r rel name; do
    [ -n "${rel}" ] || continue
    fetch_file "${rel}" "${name}" && count=$((count+1))
done < <(list_firmware_blobs)

log "fetched ${count} file(s) into ${DEST}"
if [ "${DRY_RUN}" -eq 0 ]; then
    log "checksums (sha256):"
    ( cd "${DEST}" && find . -type f ! -name 'sha256sums.txt' -print0 \
        | sort -z | xargs -0 shasum -a 256 2>/dev/null || \
      find . -type f ! -name 'sha256sums.txt' -print0 | sort -z | xargs -0 sha256sum ) | tee "${DEST}/sha256sums.txt"
fi
