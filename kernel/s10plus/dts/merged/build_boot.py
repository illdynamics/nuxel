#!/usr/bin/env python3
import struct

kernel = open("new-kernel-Image","rb").read()
ramdisk = open("ramdisk.img","rb").read()

pagesize = 2048
kernel_addr = 0x10008000
ramdisk_addr = 0x11000000
second_addr = 0
tags_addr = 0x10000100
header_version = 1
os_version = 0x00000000  # we don't need OS version
name = b"nuxel-s10plus"
cmdline = b"buildvariant=userdebug nuxel.device=s10plus root=/dev/block/platform/13d60000.ufs/by-name/userdata rootfstype=ext4 rootwait rw"

ksize = len(kernel)
rsize = len(ramdisk)
second_size = 0

# Round up to page
def pround(x): return (x + pagesize - 1)//pagesize * pagesize

# layout
hdr = bytearray(pagesize)
struct.pack_into("<8s", hdr, 0, b"ANDROID!")
struct.pack_into("<I", hdr, 8, ksize)
struct.pack_into("<I", hdr, 12, kernel_addr)
struct.pack_into("<I", hdr, 16, rsize)
struct.pack_into("<I", hdr, 20, ramdisk_addr)
struct.pack_into("<I", hdr, 24, second_size)
struct.pack_into("<I", hdr, 28, second_addr)
struct.pack_into("<I", hdr, 32, tags_addr)
struct.pack_into("<I", hdr, 36, pagesize)
struct.pack_into("<I", hdr, 40, header_version)
struct.pack_into("<I", hdr, 44, os_version)
hdr[48:48+len(name)] = name
hdr[64:64+len(cmdline)] = cmdline
# id (sha256) left zero

# Build image: header page + kernel (page aligned) + ramdisk (page aligned)
out = bytearray()
out += hdr
out += kernel + b"\x00"*(pround(ksize)-ksize)
out += ramdisk + b"\x00"*(pround(rsize)-rsize)

open("nuxel-boot-camera-v2.img","wb").write(out)
print("BOOT IMAGE:")
print("  kernel_size", ksize, "(old was 45645832)")
print("  ramdisk_size", rsize)
print("  total image", len(out), "bytes")
print("  kernel_addr 0x%08x ramdisk_addr 0x%08x tags 0x%08x page %d ver %d"%(kernel_addr,ramdisk_addr,tags_addr,pagesize,header_version))
