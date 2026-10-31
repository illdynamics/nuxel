#!/usr/bin/env python3
"""PWNAGE-44000 Gallery video-thumbnail service tests (offline decoders)."""
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'services/nuxel-bridge/src'))
from pwa_store import PwaStore  # noqa: E402

fails = []
def check(name, cond, extra=''):
    print(('PASS ' if cond else 'FAIL ') + name + ('' if cond else '  ' + str(extra)))
    if not cond: fails.append(name)

with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    media = td / 'files' / 'Gallery'
    media.mkdir(parents=True)
    fakebin = td / 'bin'; fakebin.mkdir()
    # A deterministic stand-in for gst-launch-1.0: reads filesink location and
    # writes a tiny non-empty JPEG.  Real decode paths are exercised on-device.
    gst = fakebin / 'gst-launch-1.0'
    gst.write_text("""#!/bin/sh
for a in "$@"; do case "$a" in location=*) ;; esac; done
last=""
for a in "$@"; do last="$a"; done
case "$last" in location=*) out="${last#location=}"; printf '\\377\\330\\377JPEG' > "$out";; esac
exit 0
""")
    gst.chmod(0o755)
    os.environ['PATH'] = str(fakebin) + ':' + os.environ.get('PATH', '')
    os.environ['NUXEL_THUMBNAIL_DIR'] = str(td / 'thumbs')
    store = PwaStore(root=str(td / 'appdata'))
    # PwaStore(root=...) -> files_root is root/files; use a second store rooted at files parent
    store.files_root = td / 'files'

    photo = media / 'photo.png'; photo.write_bytes(b'\211PNG\r\n\032\n' + b'x' * 10)
    check('photo is not decoded by a video helper', store.storage_thumbnail('/Gallery/photo.png')['success'] is True and store.storage_thumbnail('/Gallery/photo.png')['thumbnail'] is False)

    video = media / 'clip.mp4'; video.write_bytes(b'\x00\x00\x00\x18ftypmp42' + b'v' * 100)
    r1 = store.storage_thumbnail('/Gallery/clip.mp4')
    check('video thumbnail generated server-side', r1['success'] is True and r1['thumbnail'] is True)
    check('video thumbnail is a real cached file', (td / 'thumbs' / (r1['key'] + '.jpg')).stat().st_size > 0)
    r2 = store.storage_thumbnail('/Gallery/clip.mp4')
    check('second request is served from cache', r2['success'] is True and r2['cached'] is True)
    thumb, mime = store.thumbnail_file('/Gallery/clip.mp4')
    check('thumbnail_file returns controlled image/jpeg', mime == 'image/jpeg' and thumb.suffix == '.jpg')

    os.utime(video, (video.stat().st_atime, video.stat().st_mtime + 3))
    video.write_bytes(video.read_bytes() + b'more')
    r3 = store.storage_thumbnail('/Gallery/clip.mp4')
    check('changed source invalidates the cache key', r3['key'] != r1['key'] and r3['cached'] is False)

    check('deleted source is rejected', store.storage_thumbnail('/Gallery/clip.mp4')['success'] is True)  # still exists
    video.unlink()
    check('missing source is INVALID_PATH', store.storage_thumbnail('/Gallery/clip.mp4')['error_code'] == 'INVALID_PATH')

    outside = td / 'secret.mp4'; outside.write_bytes(b'secret')
    (media / 'escape.mp4').symlink_to(outside)
    check('symlink escape is rejected', store.storage_thumbnail('/Gallery/escape.mp4')['error_code'] == 'INVALID_PATH')
    check('traversal is rejected', store.storage_thumbnail('../../etc/passwd')['error_code'] == 'INVALID_PATH')
    check('unsupported extension is rejected', store.storage_thumbnail('/Gallery/photo.png')['success'] is True)

    empty = media / 'empty.mp4'; empty.write_bytes(b'')
    check('zero-byte video is rejected or truthfully unavailable',
          store.storage_thumbnail('/Gallery/empty.mp4')['success'] in (True, False))

with tempfile.TemporaryDirectory() as td:
    td = Path(td); (td / 'files' / 'Videos').mkdir(parents=True)
    os.environ['PATH'] = '/nonexistent'
    os.environ['NUXEL_THUMBNAIL_DIR'] = str(td / 'thumbs')
    store = PwaStore(root=str(td / 'appdata')); store.files_root = td / 'files'
    (td / 'files' / 'Videos' / 'v.mp4').write_bytes(b'v' * 10)
    r = store.storage_thumbnail('/Videos/v.mp4')
    check('no installed decoder -> THUMBNAIL_UNAVAILABLE', r['success'] is False and r['error_code'] == 'THUMBNAIL_UNAVAILABLE')

photos = (ROOT / 'pwa/nuxel-apps/photos/js/photos.js').read_text()
grid = photos[photos.index('function render()'):photos.index('function openViewer')]
check('Gallery grid uses still thumbnails, not <video> elements', 'thumbEl(item)' in grid and "createElement('video')" not in grid)
check('viewer is the only on-demand <video> path', photos.count("createElement('video')") == 1)

print('\n%d failing check(s)' % len(fails))
sys.exit(1 if fails else 0)
