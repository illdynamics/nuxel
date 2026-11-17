#!/usr/bin/env python3
"""Collect matching SSP runtime from owner-local raw ext4 images, without mounts.

Requires debugfs (read-only mode). Resolve Android links inside the images;
never resolve them against the host. Supports Samsung Android 10 flattened
runtime APEX. Compressed APEX and other layouts are deliberately unsupported.
"""
import argparse
import functools
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess

from ssp_stock_collect import collect, load_repo_elf, valid_relative, MAX_SINGLE_FILE


def image_path(relative):
    if not valid_relative(relative):
        raise ValueError('unsafe Android path: ' + relative)
    if relative.startswith('vendor/'):
        return 'vendor', '/' + relative[7:]
    if relative.startswith('apex/com.android.runtime/'):
        return 'system', '/system/apex/com.android.runtime.release/' + relative[25:]
    if relative.startswith('system/'):
        return 'system', '/' + relative
    return None


class ImageReader:
    def __init__(self, system, vendor, debugfs):
        self.images = {'system': system.resolve(strict=True), 'vendor': vendor.resolve(strict=True)}
        if any(not p.is_file() for p in self.images.values()):
            raise ValueError('images must be regular host files')
        self.debugfs = debugfs

    def command(self, image, command):
        return subprocess.run([self.debugfs, '-R', command, str(self.images[image])],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              timeout=15, check=True).stdout

    @functools.lru_cache(maxsize=8192)
    def fetch(self, relative):
        return self._fetch(relative, ())

    def _fetch(self, relative, chain):
        if relative in chain or len(chain) >= 8:
            raise ValueError('Android symlink cycle: ' + relative)
        mapped = image_path(relative)
        if mapped is None:
            return None, None
        image, path = mapped
        info = self.command(image, 'stat ' + path).decode('utf8', 'replace')
        if 'Type: symlink' in info:
            link = re.search(r'Fast link dest: "([^"\n]+)"', info)
            if not link:
                raise ValueError('unsupported long symlink: ' + relative)
            target = link[1]
            if not target.startswith('/'):
                target = str(PurePosixPath(relative).parent / target)
            target = target.lstrip('/')
            # Reject traversal rather than guessing normalization.
            if not valid_relative(target):
                raise ValueError('unsafe image link: ' + target)
            return self._fetch(target, chain + (relative,))
        if 'Type: regular' not in info:
            return None, None
        size = re.search(r'\bSize:\s+(\d+)', info)
        if not size or not 0 < int(size[1]) <= MAX_SINGLE_FILE:
            return None, None
        data = self.command(image, 'cat ' + path)
        if len(data) != int(size[1]):
            raise ValueError('short image read: ' + relative)
        return data, image + '.img:' + path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--system-image', type=Path, required=True)
    ap.add_argument('--vendor-image', type=Path, required=True)
    ap.add_argument('--repo-root', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--debugfs', default='debugfs')
    args = ap.parse_args()
    repo = args.repo_root.resolve(strict=True)
    out = args.output.resolve()
    if out == repo or out.is_relative_to(repo):
        ap.error('proprietary runtime output must be outside the repository')
    reader = ImageReader(args.system_image, args.vendor_image, args.debugfs)
    result = collect(repo, out, reader, load_repo_elf(repo))
    # Preserve canonical APEX paths as regular files too, for namespace links.
    extra = ['apex/com.android.runtime/bin/linker64',
             'apex/com.android.runtime/lib64/bionic/libc.so',
             'apex/com.android.runtime/lib64/bionic/libm.so',
             'apex/com.android.runtime/lib64/bionic/libdl.so',
             'apex/com.android.runtime/etc/ld.config.txt']
    for rel in extra:
        data, source = reader.fetch(rel)
        if data is None:
            continue
        p = out / rel
        if not p.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
        result['origin_paths'][rel] = source
        result['files'][rel] = {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
    # Retain VNDK variants, not just the broad static resolver's first match.
    # The real linker config decides which namespace uses each variant.
    elf_meta = load_repo_elf(repo)
    names = {Path(rel).name for rel in result['files'] if rel.endswith('.so')}
    seen = set()
    while names - seen:
        name = sorted(names - seen)[0]
        seen.add(name)
        if len(seen) > 192:
            raise ValueError('VNDK dependency limit exceeded')
        for directory in ('system/lib64/vndk-29', 'system/lib64/vndk-sp-29'):
            rel = directory + '/' + name
            data, source = reader.fetch(rel)
            if data is None:
                continue
            meta = elf_meta(data)
            if not meta or meta.get('class') != 64 or meta.get('machine') != 183:
                raise ValueError('invalid VNDK ELF: ' + rel)
            for needed in meta['needed']:
                if not re.fullmatch(r'[a-zA-Z0-9_+@.-]+\.so(?:\.[0-9]+)*', needed):
                    raise ValueError('unsafe dependency: ' + needed)
                names.add(needed)
            p = out / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
            result['origin_paths'][rel] = source
            result['files'][rel] = {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
    result['source'] = 'owner-local raw ext4 images; debugfs read-only; no mounts'
    result['images'] = {}
    for name, p in reader.images.items():
        h = hashlib.sha256()
        with p.open('rb') as f:
            for block in iter(lambda: f.read(1024*1024), b''):
                h.update(block)
        result['images'][name] = {'sha256': h.hexdigest(), 'bytes': p.stat().st_size}
    (out/'ssp-stock-collection.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k: result[k] for k in ('status', 'missing', 'properties', 'images')}, indent=2))
    return 0 if not result['missing'] else 3


if __name__ == '__main__':
    raise SystemExit(main())
