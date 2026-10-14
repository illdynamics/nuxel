#!/usr/bin/env python3
"""Fail-closed real runtime check: staging dir or an ext4 image, macOS compatible.
Checks executables and per-device metadata; does NOT prove GPU/display boot.
"""
import argparse, pathlib, stat, struct, sys
from ext4lite import Ext4

REQUIRED = ('/usr/bin/python3', '/sbin/openrc', '/usr/bin/phosh',
            '/usr/bin/phoc', '/sbin/init',
            '/etc/udev/rules.d/90-nuxel-beyond2lte.rules',
            '/etc/nuxel/nuxel-beyond2lte.conf',
            '/usr/share/nuxel/nuxel-home/index.html')

def check_staging(path):
    for item in REQUIRED:
        p=path/item.lstrip('/')
        if not (p.exists() or p.is_symlink()): raise RuntimeError('missing: '+item)
        if item.startswith(('/usr/bin/', '/sbin/')) and not (p.is_file() or p.is_symlink()):
            raise RuntimeError('not a real runtime binary: '+item)
    if (path/'etc/nuxel/device/g7power').exists(): raise RuntimeError('Motorola overlay present')
    print('PASS: ARM64 phone-runtime staging paths present (architecture/package integrity requires container checks)')

def check_ext4(path):
    fs=Ext4(str(path))
    for item in REQUIRED:
        try: ino=fs.resolve(item)
        except (KeyError,AssertionError) as e: raise RuntimeError('missing: '+item) from e
        inode,_=fs.inode(ino)
        mode=fs.u16(inode,0)
        if stat.S_ISLNK(mode) and not (fs.u32(inode,32)&0x80000):
            # ext4 fast symlink is inline in i_block, not extents.
            length=fs.u32(inode,4)
            data=inode[40:40+length]
        else:
            data=fs.get(ino)
        if not data: raise RuntimeError('empty: '+item)
        if item in ('/usr/bin/phosh','/usr/bin/phoc'):
            if data[:4]!=b'\x7fELF' or struct.unpack_from('<H',data,18)[0]!=183:
                raise RuntimeError('not a real ARM64 ELF: '+item)
    try: fs.resolve('/etc/nuxel/device/g7power')
    except KeyError: pass
    else: raise RuntimeError('Motorola overlay still present')
    print('PASS: actual ARM64 Phosh/Phoc and Python/OpenRC paths in ext4 (not a hardware boot test)')

if __name__=='__main__':
    parser=argparse.ArgumentParser(); group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--staging',type=pathlib.Path)
    group.add_argument('--ext4',type=pathlib.Path)
    args=parser.parse_args()
    try:
        if args.staging:check_staging(args.staging)
        else:check_ext4(args.ext4)
    except Exception as exc:
        print('PHONE RUNTIME NOT COMPLETE:',exc,file=sys.stderr)
        sys.exit(1)
