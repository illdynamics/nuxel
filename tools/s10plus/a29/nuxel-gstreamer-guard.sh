#!/bin/sh
# Keep GStreamer away from the broken vendor video devices.
#
# The S10+ downstream MFC exposes /dev/video* nodes whose open() blocks in
# request_firmware()/mfc_open.  GStreamer's plugin scanner and WebKit's media
# path can enter uninterruptible D state while probing them, freezing the UI
# (measured during PWNAGE-33000: gst-plugin-scanner in _request_firmware and a
# WebKitWebProcess in abox_wait_restored).  Camera capture is explicitly out of
# scope, so disable only the plugins that probe those devices.  Audio,
# demuxers and software video decoders are untouched.
set -eu
for f in libgstvideo4linux2.so libgstv4l2codecs.so libgstkms.so libgstopengl.so; do
    p="/usr/lib64/gstreamer-1.0/$f"
    if [ -e "$p" ] && [ ! -e "$p.nuxel-disabled" ]; then
        mv "$p" "$p.nuxel-disabled"
        echo "nuxel-gstreamer-guard: disabled $f"
    fi
done
# Drop a scanner registry that may have been built while a probe was wedged.
for d in /root/.cache/gstreamer-1.0 /home/nuxel/.cache/gstreamer-1.0; do
    [ -d "$d" ] || continue
    find "$d" -maxdepth 1 -name 'registry.*' -type f -exec rm -f {} + 2>/dev/null || true
done
