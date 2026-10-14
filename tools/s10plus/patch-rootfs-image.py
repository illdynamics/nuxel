#!/usr/bin/env python3
"""Patch a specific S10+ phase-1 ext4 rootfs image (Linux build host).

Uses the libext2fs-based ext4_import helper to insert S10+ files. The
original rootfs /sbin/init is overwritten IN PLACE only when the replacement
is smaller than its existing allocation (no metadata modifications). This is
for the supplied minimal diagnostic image, not general-purpose ext4 editing.

Build helper on Debian/Fedora with ext2fs headers:
  cc -O2 -o /tmp/ext4_import tools/s10plus/ext4_import.c -lext2fs -lcom_err
Run:
  python3 tools/s10plus/patch-rootfs-image.py --input OLD.img \\
      --output NEW.img --importer /tmp/ext4_import
"""
import argparse, pathlib, shutil, subprocess, sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
from ext4lite import Ext4
ROOT=pathlib.Path(__file__).resolve().parents[2]

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--input',type=pathlib.Path,required=True)
    parser.add_argument('--output',type=pathlib.Path,required=True)
    parser.add_argument('--importer',type=pathlib.Path,required=True)
    args=parser.parse_args()
    if args.output.resolve()==args.input.resolve():raise SystemExit('must not overwrite input')
    shutil.copyfile(args.input,args.output)
    fs=Ext4(str(args.output),'r+b')
    old=fs.get(fs.resolve('/sbin/init'))
    new=(ROOT/'boot/s10plus/bringup-init.sh').read_bytes().rstrip(b'\n')+b'\n'
    if len(new)+1>len(old):raise SystemExit('PID1 does not fit existing inode, rebuild ext4 from staging instead')
    content=new+b'#'*(len(old)-len(new))
    fs.write_same_size(fs.resolve('/sbin/init'),content)
    fs.f.close()
    files={
        '/etc/nuxel/nuxel-beyond2lte.conf':ROOT/'device/s10plus/nuxel-beyond2lte.conf',
        '/etc/udev/rules.d/90-nuxel-beyond2lte.rules':ROOT/'device/s10plus/90-nuxel-beyond2lte.rules',
    }
    for file in (ROOT/'configs/s10plus').rglob('*'):
        if file.is_file():
            files['/etc/nuxel/device/s10plus/'+str(file.relative_to(ROOT/'configs/s10plus'))]=file
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        status=pathlib.Path(tmp)/'s10plus-bringup-facts.txt'
        status.write_text('NUXEL_DEVICE=s10plus\nNUXEL_CODENAME=beyond2lte\nMODE=phase1-hardware-bringup-only\nOS_PRODUCTION_READY=false\n')
        files['/etc/nuxel/s10plus-bringup-facts.txt']=status
        for target,source in files.items():
            subprocess.run([str(args.importer),str(args.output),str(source),target,
                            '0755' if source.suffix=='.sh' else '0644'],check=True)
    verify=Ext4(str(args.output))
    assert verify.get(verify.resolve('/sbin/init')).startswith(b'#!/bin/sh')
    for path,source in files.items():
        if path.endswith('s10plus-bringup-facts.txt'):continue
        assert verify.get(verify.resolve(path))==source.read_bytes(),path
    print(f'Wrote {args.output}: S10+ files and minimal PID1 verified offline')
if __name__=='__main__': main()
