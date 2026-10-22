#!/usr/bin/env python3
"""nuxel-v4l2-capture-test.py — bounded standard V4L2 capture attempt (single node).

Documents the exact failure stage of a STANDARD V4L2 capture protocol against a
Samsung FIMC-IS vendor node.  Read-only w.r.t. hardware: only standard ioctls,
no register writes.  Prints each stage and the first failing errno.
"""
import fcntl, mmap, os, struct, sys

# ioctl helpers
def _ioc(d,t,nr,size): return (d<<30)|(ord(t)<<8)|(nr)|(size<<16)
def _ior(t,nr,size): return _ioc(2,t,nr,size)
def _iow(t,nr,size): return _ioc(1,t,nr,size)
def _iowr(t,nr,size): return _ioc(3,t,nr,size)
V='V'
VIDIOC_S_FMT=_iowr(V,5,204)     # v4l2_format = 4 + 200
VIDIOC_G_FMT=_iowr(V,4,204)
VIDIOC_REQBUFS=_iowr(V,8,20)    # 4+4+4+4+4
VIDIOC_QUERYBUF=_iowr(V,9,88)   # v4l2_buffer aarch64
VIDIOC_QBUF=_iowr(V,15,88)
VIDIOC_DQBUF=_iowr(V,17,88)
VIDIOC_STREAMON=_iow(V,18,4)
VIDIOC_STREAMOFF=_iow(V,19,4)
CAPTURE=1
MMAP=1
FIELD_ANY=0
NV12=struct.unpack('<I', b'NV12')[0]

def fourcc(v):
    b=struct.pack('<I', v); return ''.join(chr(x) if 32<=x<127 else '.' for x in b)

def try_sfmt(fd):
    fmt=bytearray(204)
    struct.pack_into('I', fmt, 0, CAPTURE)
    # v4l2_pix_format at offset 4: width,height,pixfmt,field,bpl,sizeimage,colorspace,priv,flags,ycbcr,quant,xfer
    struct.pack_into('IIIIIIIIIIII', fmt, 4, 640,480,NV12,FIELD_ANY,0,0,0,0,0,0,0,0)
    try:
        fcntl.ioctl(fd, VIDIOC_S_FMT, fmt, True)
    except OSError as e:
        return 'S_FMT FAILED errno=%d (%s)' % (e.errno, e.strerror)
    w,h,pix,bpl,size = struct.unpack_from('IIIII', fmt, 4)
    return 'S_FMT OK %s %dx%d bpl=%d sizeimage=%d' % (fourcc(pix), w, h, bpl, size)

def try_reqbufs(fd):
    rb=bytearray(20)
    struct.pack_into('IIIII', rb, 0, 1, CAPTURE, MMAP, 0, 0)
    try:
        fcntl.ioctl(fd, VIDIOC_REQBUFS, rb, True)
    except OSError as e:
        return 'REQBUFS FAILED errno=%d (%s)' % (e.errno, e.strerror)
    n=struct.unpack_from('I', rb, 0)[0]
    return 'REQBUFS OK count=%d' % n

def try_querybuf(fd):
    qb=bytearray(88)
    struct.pack_into('I', qb, 0, 0)  # index
    try:
        fcntl.ioctl(fd, VIDIOC_QUERYBUF, qb, True)
    except OSError as e:
        return 'QUERYBUF FAILED errno=%d (%s)' % (e.errno, e.strerror)
    off=struct.unpack_from('I', qb, 64)[0]
    length=struct.unpack_from('I', qb, 72)[0]
    return 'QUERYBUF OK offset=%d length=%d' % (off, length)

def main():
    node=sys.argv[1] if len(sys.argv)>1 else '/dev/video111'
    print('node:', node)
    fd=os.open(node, os.O_RDWR|os.O_NONBLOCK)
    try:
        print('1.', try_sfmt(fd))
        print('2.', try_reqbufs(fd))
        print('3.', try_querybuf(fd))
    finally:
        os.close(fd)
main()
