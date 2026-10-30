#!/usr/bin/env python3
"""Seed the Nuxel Gallery with real, clearly-labelled sample media.

Two ingestion paths are populated so the Gallery shows media from both of its
authoritative sources:

  1. Camera media store  (``camera.list-captures``) — 3 content-hashed photos.
  2. User media folders  (``storage.media-list``)  — 2 image assets in
     ``<files-root>/Gallery`` and 1 video asset in ``<files-root>/Videos``.

All writes are idempotent and never overwrite a user's own media: camera-store
items dedupe by SHA-256, and folder copies keep their canonical asset names but
skip an existing file with identical content (a user file with different content
is never replaced; a distinct Nuxel sample name is used instead).  Every write is
confined to NUXEL_MEDIA_DIR / NUXEL_APP_DATA_DIR / NUXEL_FILES_ROOT.
"""
import os
import sys
import hashlib
import io
import shutil
import argparse
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
APPS = os.path.abspath(os.path.join(HERE, '..'))
REPO = os.path.abspath(os.path.join(APPS, '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'services', 'nuxel-bridge', 'src'))
# Deployed webroot layout keeps the bridge modules under /usr/lib/nuxel.
if not os.path.isdir(os.path.join(REPO, 'services', 'nuxel-bridge', 'src')):
    sys.path.insert(0, '/usr/lib/nuxel/nuxel-bridge')

import media_store  # noqa: E402
import pwa_store  # noqa: E402

CAMERA_ASSET_CANDIDATES = [
    os.path.join(REPO, 'assets', 'nuxel-applications-icon-pack', '06-11_linux-tux.png'),
    os.path.join(REPO, 'assets', 'nuxel-applications-icon-pack', '06-12_linux-tux-alternative.png'),
    os.path.join(REPO, 'assets', 'nuxel-applications-icon-pack', '03-02_gallery.png'),
]

# Two images + one video copied into the user-facing Gallery folders.
GALLERY_IMAGES = [
    (os.path.join(REPO, 'assets', 'nuxel-background.png'), 'nuxel-wallpaper.png'),
    (os.path.join(REPO, 'assets', 'nuxel-charging.png'), 'nuxel-charging.png'),
]
GALLERY_VIDEOS = [
    (os.path.join(REPO, 'assets', 'nuxel-boot-animation.mp4'), 'nuxel-boot-animation.mp4'),
]
# Deployed images ship the boot animation under /usr/share/nuxel/boot.
GALLERY_VIDEO_FALLBACKS = [
    '/usr/share/nuxel/boot/nuxel-boot-animation.mp4',
]


def generate_png(label, size=(640, 420), bg=(20, 45, 33), fg=(59, 234, 161)):
    from PIL import Image, ImageDraw
    img = Image.new('RGB', size, bg)
    d = ImageDraw.Draw(img)
    d.rectangle([24, 24, size[0] - 24, size[1] - 24], outline=fg, width=6)
    d.text((40, 36), 'Nuxel Gallery sample', fill=fg)
    d.text((40, 60), label, fill=fg)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    return buf.getvalue()


def _sha256(data):
    return hashlib.sha256(data).hexdigest()


def seed_camera_store() -> int:
    store = media_store.MediaStore()
    added = 0
    for i, label in enumerate(['sample-penguin-01', 'sample-penguin-02', 'sample-penguin-03']):
        data = None
        candidate = CAMERA_ASSET_CANDIDATES[i % len(CAMERA_ASSET_CANDIDATES)]
        if os.path.isfile(candidate):
            with open(candidate, 'rb') as fh:
                data = fh.read()
            if not data.startswith(b'\x89PNG\r\n\x1a\n'):
                data = None
        if data is None:
            data = generate_png(label)
        rec = store.save('photo', data, mime='image/png')
        print('camera-store seeded %s -> %s (%d bytes)' % (label, rec['path'], rec['size']))
        added += 1
    return added


def _copy_if_absent(src, dst_dir, name, content_hash):
    """Idempotent, collision-safe asset copy. Never overwrites user media."""
    os.makedirs(dst_dir, mode=0o750, exist_ok=True)
    dst = os.path.join(dst_dir, name)
    if os.path.exists(dst):
        with open(dst, 'rb') as fh:
            existing_hash = _sha256(fh.read())
        if existing_hash == content_hash:
            print('gallery already present: %s' % dst)
            return dst
        # Same canonical name but different bytes -> keep the user file, use a
        # clearly-labelled Nuxel sample name instead.
        stem, ext = os.path.splitext(name)
        dst = os.path.join(dst_dir, '%s-nuxel-sample%s' % (stem, ext))
    shutil.copyfile(src, dst)
    os.chmod(dst, 0o640)
    print('gallery copied %s -> %s' % (os.path.basename(src), dst))
    return dst


def seed_gallery_folders() -> int:
    store = pwa_store.PwaStore()
    files_root = store.files_root
    gallery_dir = os.path.join(files_root, 'Gallery')
    videos_dir = os.path.join(files_root, 'Videos')
    count = 0
    for src, name in GALLERY_IMAGES:
        if not os.path.isfile(src):
            print('gallery image missing: %s' % src)
            continue
        data = open(src, 'rb').read()
        _copy_if_absent(src, gallery_dir, name, _sha256(data))
        count += 1
    for src, name in GALLERY_VIDEOS:
        if not os.path.isfile(src):
            for fallback in GALLERY_VIDEO_FALLBACKS:
                if os.path.isfile(fallback):
                    src = fallback
                    break
        if not os.path.isfile(src):
            print('gallery video missing: %s' % src)
            continue
        data = open(src, 'rb').read()
        _copy_if_absent(src, videos_dir, name, _sha256(data))
        count += 1
    # The bridge runs as root on the phone and must hand these files to the
    # session user.  Best-effort only; a non-root dev run is a no-op.
    try:
        store._chown_tree(Path(gallery_dir))
        store._chown_tree(Path(videos_dir))
    except Exception:
        pass
    return count


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--media-dir', default=os.environ.get('NUXEL_MEDIA_DIR'))
    ap.add_argument('--app-data-dir', default=os.environ.get('NUXEL_APP_DATA_DIR'))
    ap.add_argument('--files-root', default=os.environ.get('NUXEL_FILES_ROOT'))
    args = ap.parse_args()
    if args.media_dir:
        os.environ['NUXEL_MEDIA_DIR'] = args.media_dir
    if args.app_data_dir:
        os.environ['NUXEL_APP_DATA_DIR'] = args.app_data_dir
    if args.files_root:
        os.environ['NUXEL_FILES_ROOT'] = args.files_root

    cam = seed_camera_store()
    gal = seed_gallery_folders()
    print('gallery samples: %d camera-store + %d folder media (idempotent)' % (cam, gal))
    return 0


if __name__ == '__main__':
    sys.exit(main())
