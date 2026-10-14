#!/usr/bin/env python3
"""Strict ARM64 Fedora S10+ userspace verifier; operates on staging OR ext4.

No mount, chroot, Docker, or libext2fs required in --ext4 mode. This verifies
package binary payloads and S10+ assets; it cannot verify hardware support.
"""
import argparse
import pathlib
import posixpath
import stat
import struct
import sys
from ext4lite import Ext4

BINARIES=(
    '/usr/bin/python3', '/usr/libexec/phosh', '/usr/bin/phoc',
    '/usr/lib/systemd/systemd', '/sbin/init',
    '/usr/bin/nuxel-fb-phone',
)
FILES=(
    '/etc/udev/rules.d/90-nuxel-beyond2lte.rules',
    '/etc/nuxel/nuxel-beyond2lte.conf',
    '/usr/share/nuxel/nuxel-home/index.html',
    '/etc/nuxel/phone-runtime-status',
)


def read_staging(root, path):
    name=path
    for _ in range(25):
        p=root/name.lstrip('/')
        parts=pathlib.PurePosixPath(name).parts
        prefix=[]
        changed=False
        for j, part in enumerate(parts):
            if part=='/':continue
            prefix.append(part)
            cand=root.joinpath(*prefix)
            if cand.is_symlink():
                target=cand.readlink().as_posix()
                prior='/'+'/'.join(prefix[:-1])
                replacement=target if target.startswith('/') else posixpath.join(prior,target)
                rem=[v for v in parts[j+1:] if v!='/']
                name=posixpath.normpath(posixpath.join(replacement,*rem))
                changed=True
                break
        if not changed:
            if not p.is_file(): raise ValueError('not a file: '+path)
            return p.read_bytes()
    raise ValueError('excessive symlink depth: '+path)


def read_ext4(fs, path):
    name=path
    for _ in range(25):
        if not name.startswith('/'): raise ValueError('not absolute: '+name)
        parts=[p for p in name.strip('/').split('/') if p]
        parent=2
        changed=False
        for j,part in enumerate(parts):
            ino=fs.children(parent)[part][0]
            inode,_=fs.inode(ino)
            mode=fs.u16(inode,0)
            if stat.S_ISLNK(mode):
                link=fs.get(ino).decode('utf-8')
                prev='/'+'/'.join(parts[:j])
                replacement=link if link.startswith('/') else posixpath.join(prev,link)
                name=posixpath.normpath(posixpath.join(replacement,*parts[j+1:]))
                changed=True
                break
            parent=ino
        if not changed:
            inode,_=fs.inode(parent)
            if not stat.S_ISREG(fs.u16(inode,0)):raise ValueError('not a regular file: '+path)
            return fs.get(parent)
    raise ValueError('excessive symlink depth: '+path)


def validate(read):
    for p in BINARIES:
        b=read(p)
        if len(b)<64 or b[:4]!=b'\x7fELF' or b[4]!=2 or b[5]!=1 or struct.unpack_from('<H',b,18)[0]!=183:
            raise ValueError('expected actual aarch64 ELF, not a source/shim: '+p)
        print('PASS ELF aarch64:',p,len(b),'bytes')
    for p in FILES:
        b=read(p)
        if not b:raise ValueError('empty file '+p)
        print('PASS asset:',p,len(b),'bytes')
    status=read('/etc/nuxel/phone-runtime-status')
    for token in (b'BASE_OS=fedora-43-aarch64',b'INIT_SYSTEM=systemd',b'HARDWARE_BOOT_VERIFIED=false'):
        if token not in status:raise ValueError('incorrect runtime status '+repr(token))
    print('PASS: Fedora RPM installed ARM64 phone binaries, systemd, Nuxel S10+ overlays')
    print('NOT VERIFIED: kernel, GPU/DRM, DTBO/hw-revision, touch or actual phone boot')


def main():
    a=argparse.ArgumentParser()
    g=a.add_mutually_exclusive_group(required=True)
    g.add_argument('--staging',type=pathlib.Path)
    g.add_argument('--ext4',type=pathlib.Path)
    args=a.parse_args()
    try:
        if args.staging:
            root=args.staging
            if (root/'etc/nuxel/device/g7power').exists():raise ValueError('G7Power overlay found')
            validate(lambda p:read_staging(root,p))
        else:
            fs=Ext4(str(args.ext4))
            try:fs.resolve('/etc/nuxel/device/g7power')
            except KeyError:pass
            else:raise ValueError('G7Power overlay found')
            validate(lambda p:read_ext4(fs,p))
    except (ValueError,KeyError,AssertionError,IndexError,FileNotFoundError) as e:
        print('FAIL: FEDORA PHONE RUNTIME NOT COMPLETE: '+str(e),file=sys.stderr)
        return 1
    return 0
if __name__=='__main__':sys.exit(main())
