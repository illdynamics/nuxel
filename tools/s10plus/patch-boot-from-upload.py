#!/usr/bin/env python3
"""Repack existing Samsung Android-v1 boot image using repo's corrected init.

Preserves the uploaded kernel and merged DTB without compiling a different
kernel, and uses load addresses from the INPUT header; the input MUST have
been taken from the intended Exynos S10+ build. Requires Python + gzip only.
Does not claim that Samsung hardware accepts/boots this image.
"""
import sys, argparse, gzip, io, os, pathlib, stat, struct, subprocess, shutil, tempfile
HERE=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(HERE/'images/bootpack'))
from cpio_builder import build_cpio,gzip_bytes

def parse_cpio(raw,stage):
    off=0; seen=set()
    while off<len(raw):
        if raw[off:off+6] not in (b'070701',b'070702'):
            raise ValueError('invalid cpio at offset %s'%off)
        vals=[int(raw[off+6+i*8:off+14+i*8],16) for i in range(13)]
        mode,size,namesize=vals[1],vals[6],vals[11]
        if namesize<1 or namesize>4096:raise ValueError('invalid name size')
        name=raw[off+110:off+110+namesize-1].decode()
        pos=(off+110+namesize+3)&~3
        body=raw[pos:pos+size]
        off=(pos+size+3)&~3
        if name=='TRAILER!!!':break
        path=pathlib.PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts or not name or name in seen:raise ValueError('unsafe cpio name '+name)
        seen.add(name)
        dst=stage/name
        dst.parent.mkdir(parents=True,exist_ok=True)
        if stat.S_ISDIR(mode):dst.mkdir(exist_ok=True)
        elif stat.S_ISLNK(mode):os.symlink(body.decode(),dst)
        elif stat.S_ISREG(mode):dst.write_bytes(body)
        else:raise ValueError('unexpected special file '+name)
        if not stat.S_ISLNK(mode):os.chmod(dst, stat.S_IMODE(mode))
    return seen

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('input',type=pathlib.Path)
    ap.add_argument('output',type=pathlib.Path)
    args=ap.parse_args()
    data=args.input.read_bytes()
    values=struct.unpack_from('<8s10I',data)
    magic,klen,kaddr,rlen,raddr,second,saddr,tags,page,dtlen,version=values
    if magic!=b'ANDROID!' or page!=2048 or second!=0:raise ValueError('unexpected Android boot format')
    def pad(x):return (x+page-1)//page*page
    header_cmdline=data[64:576].split(b'\0')[0].decode()  # starts after 8+10*4+16=64
    if 'nuxel.device=s10plus' not in header_cmdline:raise ValueError('not a Nuxel S10+ boot image')
    kern=data[page:page+klen]
    ram_start=page+pad(klen)
    ram=data[ram_start:ram_start+rlen]
    dtstart=ram_start+pad(rlen)
    dtb=data[dtstart:dtstart+dtlen]
    if len(dtb)!=dtlen or int.from_bytes(dtb[:4],'big')!=0xd00dfeed:raise ValueError('missing/invalid merged device tree')
    with tempfile.TemporaryDirectory(prefix='nuxel-boot-patch-') as tmp:
        t=pathlib.Path(tmp);stage=t/'initramfs';stage.mkdir()
        names=parse_cpio(gzip.decompress(ram),stage)
        if 'bin/toybox' not in names:raise ValueError('static ARM64 Toybox missing')
        shutil.copy2(HERE/'boot/initramfs/init.sh',stage/'init')
        os.chmod(stage/'init',0o755)
        sh=stage/'bin/sh'
        if sh.is_symlink():sh.unlink()
        elif sh.exists():raise ValueError('unexpected /bin/sh type')
        os.symlink('toybox',sh)
        # Ensure the early-boot applets required by the revised script exist.
        for cmd in ('sh','grep','mdev','sleep','cat','ls','mount','mountpoint','switch_root'):
            link=stage/'bin'/cmd
            if not link.exists() and not link.is_symlink():os.symlink('toybox',link)
        assert os.readlink(stage/'bin/sh')=='toybox'
        buf=io.BytesIO(); n=build_cpio(stage,buf,fixed_mtime=0)
        newram=gzip_bytes(buf.getvalue(),9)
        (t/'Image.gz').write_bytes(kern)
        (t/'initramfs.cpio.gz').write_bytes(newram)
        (t/'merged.dtb').write_bytes(dtb)
        packer=HERE/'boot/s10plus/pack-boot-v1.sh'
        args.output.parent.mkdir(parents=True,exist_ok=True)
        cmd=[sys.executable,str(packer),'--kernel',str(t/'Image.gz'), '--ramdisk',str(t/'initramfs.cpio.gz'), '--dtb',str(t/'merged.dtb'), '--cmdline',header_cmdline,'--kernel-addr',hex(kaddr),'--ramdisk-addr',hex(raddr),'--tags-addr',hex(tags),'--output',str(args.output)]
        subprocess.run(cmd,check=True)
        rebuilt=args.output.read_bytes(); check=struct.unpack_from('<8s10I',rebuilt)
        assert check[1]==klen and check[3]==len(newram) and check[9]==dtlen
        assert rebuilt[page:page+klen]==kern
        dtbegin=page+pad(klen)+pad(len(newram))
        assert rebuilt[dtbegin:dtbegin+dtlen]==dtb
        print('Verified unchanged kernel and merged DTB, /bin/sh link, rebuilt initramfs entries:',n)
        print('WARNING: hardware, board revision, bootloader compatibility NOT verified')
if __name__=='__main__':main()
