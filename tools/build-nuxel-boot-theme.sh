#!/usr/bin/env bash
# =============================================================================
# tools/build-nuxel-boot-theme.sh
#
# Single source of truth for converting the Nuxel boot animation MP4 into a
# Plymouth "script" theme (PNG frame sequence + theme descriptors). This is
# shared by the image build (images/mkrootfs.sh) and the UTM VM deploy path:
# the VM bootstrap (vm/nuxel-vm-bootstrap.sh) can call this inside the guest,
# and the host-side deploy scripts (vm/deploy-vm.sh, vm/build-vm-image.sh)
# call it before shipping the pre-built theme into the guest so the VM does
# NOT need ffmpeg/H.264 decode support.
#
# Output layout (in the chosen --out dir):
#   frame-0001.png ... frame-NNNN.png   # 720x1280 RGBA frames, navy padded
#   nuxel.plymouth                       # Plymouth theme descriptor
#   nuxel.script                         # loops the animation until Plymouth
#                                        # quits (set NUXEL_BOOT_THEME_LOOP=0
#                                        # to play once and hold the last frame)
#
# Usage:
#   tools/build-nuxel-boot-theme.sh --mp4 <file> --out <dir>
#   tools/build-nuxel-boot-theme.sh --mp4 <file> --tarball <file.tar.gz>
#
# Env overrides (match images/mkrootfs.sh):
#   NUXEL_BOOT_WIDTH  (default 720)
#   NUXEL_BOOT_HEIGHT (default 1280)
#   NUXEL_BOOT_FPS    (default 12)
#   NUXEL_BOOT_THEME_LOOP  (default 1; set to 0 to play the animation once
#                        and hold the final frame instead of looping until
#                        Plymouth quits)
# =============================================================================

set -euo pipefail

MP4=""
OUT_DIR=""
TARBALL=""
WIDTH="${NUXEL_BOOT_WIDTH:-720}"
HEIGHT="${NUXEL_BOOT_HEIGHT:-1280}"
FPS="${NUXEL_BOOT_FPS:-12}"
NAVY="0x0a1628"

usage() {
    cat <<'EOF'
Usage:
  tools/build-nuxel-boot-theme.sh --mp4 <file> --out <dir>
  tools/build-nuxel-boot-theme.sh --mp4 <file> --tarball <file.tar.gz>

Options:
  --mp4 <file>       source boot animation MP4 (required)
  --out <dir>        write theme files into <dir>
  --tarball <tgz>    write a tar.gz of the theme instead
  --width N          frame width  (default 720)
  --height N         frame height (default 1280)
  --fps N            frame rate   (default 12)
EOF
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --mp4) MP4="$2"; shift 2 ;;
        --out) OUT_DIR="$2"; shift 2 ;;
        --tarball) TARBALL="$2"; shift 2 ;;
        --width) WIDTH="$2"; shift 2 ;;
        --height) HEIGHT="$2"; shift 2 ;;
        --fps) FPS="$2"; shift 2 ;;
        -h|--help) usage; exit 0 ;;
        *) echo "unknown option: $1" >&2; usage >&2; exit 2 ;;
    esac
done

if [ -z "${MP4}" ]; then
    echo "error: --mp4 <file> is required" >&2
    usage >&2
    exit 2
fi

if [ -z "${OUT_DIR}" ] && [ -z "${TARBALL}" ]; then
    echo "error: one of --out <dir> or --tarball <file.tar.gz> is required" >&2
    usage >&2
    exit 2
fi

if [ ! -f "${MP4}" ]; then
    echo "error: MP4 not found: ${MP4}" >&2
    exit 1
fi

if ! command -v ffmpeg >/dev/null 2>&1; then
    echo "error: ffmpeg is required to extract boot animation frames" >&2
    exit 1
fi

WORK_DIR="${OUT_DIR:-}"
CLEANUP_DIR=""
if [ -z "${WORK_DIR}" ]; then
    WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/nuxel-boot-theme.XXXXXX")"
    CLEANUP_DIR="${WORK_DIR}"
fi
mkdir -p "${WORK_DIR}"

# If the requested MP4 already lives inside the theme dir (in-guest rebuild),
# guard against ffmpeg overwriting its own input.
if [ "${MP4}" = "${WORK_DIR}/nuxel-boot-animation.mp4" ]; then
    echo "error: --mp4 must not be inside the --out directory" >&2
    [ -n "${CLEANUP_DIR}" ] && rm -rf "${CLEANUP_DIR}"
    exit 2
fi

echo "Extracting frames: ${WIDTH}x${HEIGHT} @ ${FPS} fps (navy #0a1628 pad)"
ffmpeg -y -v error -i "${MP4}" \
    -vf "fps=${FPS},scale=${WIDTH}:${HEIGHT}:force_original_aspect_ratio=decrease,pad=${WIDTH}:${HEIGHT}:(ow-iw)/2:(oh-ih)/2:color=${NAVY},format=rgba" \
    "${WORK_DIR}/frame-%04d.png"

FRAME_COUNT=0
for f in "${WORK_DIR}"/frame-*.png; do
    [ -f "$f" ] && FRAME_COUNT=$((FRAME_COUNT + 1))
done

if [ "${FRAME_COUNT}" -eq 0 ]; then
    echo "error: no frames generated from ${MP4}" >&2
    [ -n "${CLEANUP_DIR}" ] && rm -rf "${CLEANUP_DIR}"
    exit 1
fi

echo "Generated ${FRAME_COUNT} frames"

# Also emit a GRUB-friendly background image (plain RGB, no alpha). GRUB's PNG
# reader can load the RGBA Plymouth frames, but an explicit RGB background is
# safer across GRUB builds and avoids alpha-blending surprises. This gives the
# graphical GRUB stage a Nuxel splash the instant GRUB renders, closing the
# "Display output is not active" gap that otherwise lasts until Plymouth takes
# over the display.
GRUB_BG="${WORK_DIR}/nuxel-grub-background.png"
if [ -f "${WORK_DIR}/frame-0001.png" ]; then
    ffmpeg -y -v error -i "${WORK_DIR}/frame-0001.png" \
        -vf "format=rgb24" -frames:v 1 "${GRUB_BG}" 2>/dev/null || true
    [ -f "${GRUB_BG}" ] || cp -f "${WORK_DIR}/frame-0001.png" "${GRUB_BG}"
fi


cat > "${WORK_DIR}/nuxel.plymouth" <<'PLYEOF'
[Plymouth Theme]
Name=Nuxel
Description=Nuxel OS Animated Boot Splash
ModuleName=script

[script]
ImageDir=/usr/share/plymouth/themes/nuxel
ScriptFile=/usr/share/plymouth/themes/nuxel/nuxel.script
PLYEOF

{
    cat <<SCRIPTEOF
WallpaperFile = nil;

bg_image = Image("frame-0001.png");
bg_sprite = Sprite(bg_image);
bg_sprite.SetZ(-100);

# Pace the refresh callback at the frame-extraction rate. The script plugin
# defaults to 50 refresh callbacks/second; without this the animation plays
# ~4x too fast (96 frames in ~2s instead of the intended ${FPS} fps).
Plymouth.SetRefreshRate(${FPS});

nframes = ${FRAME_COUNT};
filenames = [
SCRIPTEOF
    # Emit one filename per frame as literal strings so the Plymouth script
    # language does not need string concatenation or formatting (it supports
    # neither). Frame files are loaded one at a time in refresh_callback to
    # keep the initramfs footprint small.
    i=1
    while [ "${i}" -le "${FRAME_COUNT}" ]; do
        if [ "${i}" -lt "${FRAME_COUNT}" ]; then
            printf '    "frame-%04d.png",\n' "${i}"
        else
            printf '    "frame-%04d.png"\n' "${i}"
        fi
        i=$((i + 1))
    done
    if [ "${NUXEL_BOOT_THEME_LOOP:-1}" = "1" ]; then
        # Default: keep looping the animation until Plymouth quits. A boot
        # splash that plays once and then holds a still frame reads as a hang
        # while the desktop is still coming up (boot can outlast the 8s clip),
        # so loop the clip at the extraction rate until plymouthd hands the
        # display to the desktop.
        cat <<'SCRIPTEOF'
];
current_frame = 0;

fun refresh_callback ()
{
    img = Image(filenames[current_frame]);
    bg_sprite.SetImage(img);
    current_frame = current_frame + 1;
    if (current_frame >= nframes)
    {
        current_frame = 0;
    }
}

# The script plugin keeps calling the registered refresh function on every
# tick until Plymouth quits, so register it exactly once. Re-arming it from
# inside the callback is unnecessary and on some Plymouth versions leaves the
# splash frozen after the first pass (which reads as the animation hanging).
Plymouth.SetRefreshFunction(refresh_callback);
SCRIPTEOF
    else
        # Opt-out (NUXEL_BOOT_THEME_LOOP=0): play the animation exactly once,
        # then hold the final frame. Only useful when the boot is guaranteed
        # to finish within the clip length; otherwise the still frame reads
        # as a hang before the UI loads.
        cat <<'SCRIPTEOF'
];
current_frame = 0;

fun refresh_callback ()
{
    img = Image(filenames[current_frame]);
    bg_sprite.SetImage(img);
    current_frame = current_frame + 1;
    if (current_frame < nframes)
    {
        Plymouth.SetRefreshFunction(refresh_callback);
    }
}

Plymouth.SetRefreshFunction(refresh_callback);
SCRIPTEOF
    fi
} > "${WORK_DIR}/nuxel.script"

if [ -n "${TARBALL}" ]; then
    TARBALL_DIR="$(cd "$(dirname "${TARBALL}")" && pwd)"
    mkdir -p "${TARBALL_DIR}"
    # Normalize ownership: the tarball is extracted as root in the guest, and
    # without explicit owner/group the host uid (e.g. 501 on macOS) leaks into
    # /usr/share/plymouth/themes/nuxel, breaking plymouth-set-default-theme and
    # (with SELinux) plymouthd reads.
    tar --owner=0 --group=0 -czf "${TARBALL}" -C "${WORK_DIR}" .
    echo "Wrote ${FRAME_COUNT}-frame Plymouth theme tarball: ${TARBALL}"
fi

[ -n "${CLEANUP_DIR}" ] && rm -rf "${CLEANUP_DIR}"

echo "OK: ${FRAME_COUNT} frames (${WIDTH}x${HEIGHT} @ ${FPS} fps)"
