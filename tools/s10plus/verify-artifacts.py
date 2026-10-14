#!/usr/bin/env python3
"""Read-only preflight of S10+ phase-1 images (not a hardware-boot test).
No ext4 mount or third-party Python modules required, so runs on macOS.
"""
import argparse, gzip, hashlib, pathlib, struct, sys, stat, subprocess, tempfile
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
from ext4lite import Ext4

def check(cond, reason):
    if not cond: raise RuntimeError(reason)

def sha(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        while b:=f.read(1<<20):h.update(b)
    return h.hexdigest()

def parse_cpio(data):
    entries={};offset=0
    while offset<len(data):
        check(data[offset:offset+6] in (b'070701',b'070702'),'invalid newc magic')
        values=[int(data[offset+6+i*8:offset+14+i*8],16) for i in range(13)]
        mode, size,nlen=values[1],values[6],values[11]
        check(0<nlen<4096,'invalid newc filename length')
        name=data[offset+110:offset+110+nlen-1].decode()
        pos=(offset+110+nlen+3)&~3
        body=data[pos:pos+size]
        check(len(body)==size,'truncated cpio entry')
        offset=(pos+size+3)&~3
        if name=='TRAILER!!!':return entries
        check(name not in entries,'duplicate cpio entry')
        entries[name]=(mode,body)
    raise RuntimeError('missing cpio trailer')

def verify(boot, rootfs):
    print('BOOT:',boot,'sha256',sha(boot))
    print('ROOT:',rootfs,'sha256',sha(rootfs))
    b=boot.read_bytes()
    h=struct.unpack_from('<8s10I',b)
    magic,klen,kaddr,rlen,raddr,slen,saddr,tags,page,dlen,ver=h
    check(magic==b'ANDROID!' and page==2048 and slen==0,'not expected Android v1 Samsung boot format')
    check(b'nuxel.device=s10plus' in b[:2048], 'not S10+ cmdline')
    up=lambda n:(n+page-1)//page*page
    kernel=b[page:page+klen]; start=page+up(klen)
    ram=b[start:start+rlen]; dt=b[start+up(rlen):start+up(rlen)+dlen]
    check(len(kernel)==klen and len(ram)==rlen and len(dt)==dlen,'truncated boot fields')
    check(dt[:4]==b'\xd0\x0d\xfe\xed' and struct.unpack_from('>I',dt,4)[0]==len(dt),'bad flattened DTB')
    check(kernel[:2]==b'\x1f\x8b','kernel gzip signature missing')
    rawkernel=gzip.decompress(kernel)
    check(rawkernel[56:60]==b'ARM\x64','decompressed ARM64 kernel image signature missing')
    entries=parse_cpio(gzip.decompress(ram))
    check('init' in entries and stat.S_ISREG(entries['init'][0]),'no initramfs /init')
    check(entries['init'][1].startswith(b'#!/bin/sh\n'),'wrong init interpreter')
    check('bin/sh' in entries and stat.S_ISLNK(entries['bin/sh'][0]) and entries['bin/sh'][1]==b'toybox','no /bin/sh -> toybox')
    toybox=entries['bin/toybox'][1]
    check(toybox[:4]==b'\x7fELF' and struct.unpack_from('<H',toybox,18)[0]==183,'initramfs toybox not aarch64 ELF')
    for token in (b'PARTNAME=userdata',b'/sys/class/block/',b'refusing SYSTEM fallback',b's10plus_userdata_device'):
        check(token in entries['init'][1], 'patched S10+ root logic absent: '+repr(token))
    print('  BOOT PASS: v1 header, ARM64 kernel, DTB, gzip newc, interpreter and root resolver')
    fs=Ext4(str(rootfs))
    check(fs.get(fs.resolve('/bin/toybox'))[:4]==b'\x7fELF','rootfs no Toybox ELF')
    check(struct.unpack_from('<H',fs.get(fs.resolve('/bin/toybox')),18)[0]==183,'rootfs Toybox not aarch64')
    check(fs.get(fs.resolve('/bin/sh'))==b'toybox','rootfs /bin/sh target wrong')
    init=fs.get(fs.resolve('/sbin/init'))
    check(init.startswith(b'#!/bin/sh\n'),'rootfs init invalid interpreter')
    for path in ('/etc/nuxel/nuxel-beyond2lte.conf',
                 '/etc/nuxel/s10plus-bringup-facts.txt',
                 '/etc/udev/rules.d/90-nuxel-beyond2lte.rules',
                 '/etc/nuxel/device/s10plus/libinput/99-nuxel-beyond2lte-touch.conf'):
        check(len(fs.get(fs.resolve(path)))>0,'missing S10+ file '+path)
    check(b'MODE=phase1-hardware-bringup-only' in fs.get(fs.resolve('/etc/nuxel/s10plus-bringup-facts.txt')),'rootfs scope marker missing')
    check(b'nuxel.debug=1' in init and b'USB root shell disabled' in init,'expected USB debug opt-in missing')
    with tempfile.NamedTemporaryFile(mode='wb',suffix='.sh') as f:
        f.write(init);f.flush()
        res=subprocess.run(['sh','-n',f.name],capture_output=True,text=True)
        check(res.returncode==0,'/sbin/init sh -n failed: '+res.stderr)
    print('  ROOT PASS: ext4 paths, ARM64 Toybox, PID1 syntax, S10+ rules/config')
    print('  NOTE: all checks offline; bootloader, PIT/board revision and hardware boot unverified')

if __name__=='__main__':
    a=argparse.ArgumentParser()
    a.add_argument('--boot',type=pathlib.Path,required=True)
    a.add_argument('--rootfs',type=pathlib.Path,required=True)
    args=a.parse_args()
    try: verify(args.boot,args.rootfs)
    except Exception as exc: print('FAIL:',exc,file=sys.stderr);sys.exit(1)
