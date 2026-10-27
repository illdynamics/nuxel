#!/usr/bin/env python3
"""Seed the Nuxel Gallery media store with clearly-labelled sample images.

The samples are REAL PNGs (either copied from repository assets or generated
with Pillow when the asset is absent), written through media_store.save() so
they are content-hashed, indexed and never overwrite a user's own media.  The
script is idempotent and refuses to touch anything outside NUXEL_MEDIA_DIR.
"""
import os
import sys
import hashlib
import io
import argparse

HERE = os.path.dirname(os.path.abspath(__file__))
APPS = os.path.abspath(os.path.join(HERE, '..'))
REPO = os.path.abspath(os.path.join(APPS, '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'services', 'nuxel-bridge', 'src'))

import media_store  # noqa: E402

ASSET_CANDIDATES = [
    os.path.join(REPO, 'assets', 'nuxel-applications-icon-pack', '06-11_linux-tux.png'),
    os.path.join(REPO, 'assets', 'nuxel-applications-icon-pack', '06-12_linux-tux-alternative.png'),
    os.path.join(REPO, 'assets', 'nuxel-applications-icon-pack', '03-02_gallery.png'),
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--media-dir', default=os.environ.get('NUXEL_MEDIA_DIR'))
    args = ap.parse_args()
    if args.media_dir:
        os.environ['NUXEL_MEDIA_DIR'] = args.media_dir
    store = media_store.MediaStore()
    added = 0
    for i, label in enumerate(['sample-penguin-01', 'sample-penguin-02', 'sample-penguin-03']):
        data = None
        candidate = ASSET_CANDIDATES[i % len(ASSET_CANDIDATES)]
        if os.path.isfile(candidate):
            with open(candidate, 'rb') as fh:
                data = fh.read()
            # Validate: the asset must really be a PNG (no fake "text renamed .png").
            if not data.startswith(b'\x89PNG\r\n\x1a\n'):
                data = None
        if data is None:
            data = generate_png(label)
        rec = store.save('photo', data, mime='image/png')
        print('seeded %s -> %s (%d bytes)' % (label, rec['path'], rec['size']))
        added += 1
    print('gallery samples: %d present (dedupe by content hash; existing media untouched)' % added)
    return 0


if __name__ == '__main__':
    sys.exit(main())
