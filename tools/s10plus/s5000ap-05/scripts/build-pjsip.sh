#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-2.0-only
# SIP only; no audio/video runtime. Immutable upstream source revision.
set -euo pipefail
revision=6cab30cec44af36ba7c8a45ff7af2f74a8ed288c # pjproject 2.16 (GPL-2.0-or-later)
prefix=${1:?installation prefix required}
source_dir=${2:?build source directory required}
if [[ ! -d "$source_dir/.git" ]]; then
    git clone --depth 1 --branch 2.16 https://github.com/pjsip/pjproject.git "$source_dir"
fi
[[ $(git -C "$source_dir" rev-parse HEAD) == "$revision" ]]
cd "$source_dir"
cat > pjlib/include/pj/config_site.h <<'EOF'
#define PJSIP_HAS_DIGEST_AKA_AUTH 1
#define PJ_LOG_MAX_LEVEL 0
#define PJMEDIA_HAS_VIDEO 0
#define PJ_HAS_IPV6 1
EOF
./configure --prefix="$prefix" --disable-shared --disable-sound --disable-video \
    --disable-opencore-amr --disable-silk --disable-libyuv --disable-libwebrtc \
    --disable-ffmpeg --disable-v4l2 --disable-sdl --disable-openh264 --disable-libavdevice
make dep
make -j2 lib
make install
