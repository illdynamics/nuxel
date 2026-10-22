#!/usr/bin/env python3
"""nuxel-v4l2-probe.py — read-only V4L2 enumeration + bounded single-frame capture.

A minimal, dependency-free V4L2 diagnostic for the Samsung S10+ (beyond2lte)
Exynos FIMC-IS camera stack, run directly on the phone (no v4l-utils needed).

Safety: this program performs ONLY standard V4L2 ioctls on the nodes it is told
to inspect.  It never writes device registers, never touches /dev/fb0, never
flashes anything, and (unless --capture is given) never starts a stream.

Modes:
  probe                        (default) QUERYCAP + ENUM_FMT for every /dev/video*
  probe --capture DEV OUT      bounded single-frame capture (MMAP, 1 buffer)

Exit codes:
  0 = probe completed (see per-node state)
  1 = usage error
  2 = capture failed (stream/format) — details on stderr
"""
from __future__ import annotations
import argparse, fcntl, mmap, os, struct, sys, time

# --- linux/ioctl.h (asm-generic) -------------------------------------------
_IOC_NRBITS = 8; _IOC_TYPEBITS = 8; _IOC_SIZEBITS = 14
_IOC_NRSHIFT = 0
_IOC_TYPESHIFT = _IOC_NRSHIFT + _IOC_NRBITS
_IOC_SIZESHIFT = _IOC_TYPESHIFT + _IOC_TYPEBITS
_IOC_DIRSHIFT = _IOC_SIZESHIFT + _IOC_SIZEBITS
_IOC_NONE, _IOC_WRITE, _IOC_READ = 0, 1, 2
def _ioc(d, t, nr, size):
    return (d << _IOC_DIRSHIFT) | (ord(t) << _IOC_TYPESHIFT) | (nr << _IOC_NRSHIFT) | (size << _IOC_SIZESHIFT)
def _ior(t, nr, size): return _ioc(_IOC_READ, t, nr, size)
def _iow(t, nr, size): return _ioc(_IOC_WRITE, t, nr, size)
def _iowr(t, nr, size): return _ioc(_IOC_READ | _IOC_WRITE, t, nr, size)

# --- linux/videodev2.h (kernel 4.14) ----------------------------------------
V = 'V'
# v4l2_capability
CAP_FMT = '16s32s32sIII3I'
VIDIOC_QUERYCAP = _ior(V, 0, struct.calcsize(CAP_FMT))
# v4l2_fmtdesc
FMT_FMT = 'III32sI4I'
VIDIOC_ENUM_FMT = _iowr(V, 2, struct.calcsize(FMT_FMT))
# v4l2_format + v4l2_pix_format
PIX_FMT = 'IIIIIIIIIIII'   # width,height,pixfmt,field,bpl,sizeimage,colorspace,priv,flags,ycbcr_enc,quantization,xfer
FORMAT_FMT = 'I' + PIX_FMT
VIDIOC_S_FMT = _iowr(V, 5, struct.calcsize(FORMAT_FMT))
VIDIOC_G_FMT = _iowr(V, 4, struct.calcsize(FORMAT_FMT))
# v4l2_requestbuffers
REQBUFS_FMT = 'IIII'       # count,type,memory,reserved
VIDIOC_REQBUFS = _iowr(V, 8, struct.calcsize(REQBUFS_FMT))
# v4l2_buffer (non-mplane)
BUF_FMT = 'IIIIIIIIII' + 'I' + 'I' + 'III'  # placeholder — see build below
def _buf_fmt():
    # index,type,bytesused,flags,field,timestamp(2xlong),timecode(2xI),sequence,memory,offset,length,reserved2,input,reserved
    return 'IIIIII4sIIIIIIIII'
BUF_FMT = _buf_fmt()
VIDIOC_QUERYBUF = _iowr(V, 9, struct.calcsize(BUF_FMT))
VIDIOC_QBUF = _iowr(V, 15, struct.calcsize(BUF_FMT))
VIDIOC_DQBUF = _iowr(V, 17, struct.calcsize(BUF_FMT))
STREAMON_FMT = 'I'
VIDIOC_STREAMON = _iow(V, 18, struct.calcsize(STREAMON_FMT))
VIDIOC_STREAMOFF = _iow(V, 19, struct.calcsize(STREAMON_FMT))

V4L2_BUF_TYPE_VIDEO_CAPTURE = 1
V4L2_MEMORY_MMAP = 1
V4L2_FIELD_ANY = 0
V4L2_CAP_VIDEO_CAPTURE = 0x00000001
V4L2_CAP_VIDEO_CAPTURE_MPLANE = 0x00001000
V4L2_CAP_STREAMING = 0x04000000

def fourcc(v):
    return struct.unpack('<I', v)[0]

def fourcc_str(v):
    b = struct.pack('<I', v)
    return ''.join(chr(x) if 32 <= x < 127 else '.' for x in b)

def pstr(b):
    return b.split(b'\0', 1)[0].decode('utf-8', 'replace')

def probe_node(path):
    fd = os.open(path, os.O_RDWR | os.O_NONBLOCK)
    try:
        cap = bytearray(struct.calcsize(CAP_FMT))
        fcntl.ioctl(fd, VIDIOC_QUERYCAP, cap, True)
        driver, card, bus, version, capabilities, device_caps, *_ = struct.unpack(CAP_FMT, cap)
        info = {
            'path': path, 'driver': pstr(driver), 'card': pstr(card), 'bus': pstr(bus),
            'version': version, 'caps': capabilities, 'device_caps': device_caps,
            'is_capture': bool(device_caps & V4L2_CAP_VIDEO_CAPTURE),
            'is_mplane': bool(device_caps & V4L2_CAP_VIDEO_CAPTURE_MPLANE),
            'streaming': bool(device_caps & V4L2_CAP_STREAMING),
            'formats': [],
        }
        is_cap = info['is_capture'] or info['is_mplane']
        if is_cap:
            idx = 0
            while idx < 64:
                f = bytearray(struct.calcsize(FMT_FMT))
                struct.pack_into(FMT_FMT, f, 0, idx, V4L2_BUF_TYPE_VIDEO_CAPTURE, 0, b'', 0, 0, 0, 0, 0)
                try:
                    fcntl.ioctl(fd, VIDIOC_ENUM_FMT, f, True)
                except OSError:
                    break
                _i, _t, _fl, desc, pix, *_ = struct.unpack(FMT_FMT, f)
                info['formats'].append((fourcc_str(pix), pstr(desc)))
                idx += 1
        return info
    finally:
        os.close(fd)

def capture_one(path, out, fourcc_value, w, h, timeout=15.0):
    """Bounded single-frame MMAP capture.  Returns (ok, detail)."""
    fd = os.open(path, os.O_RDWR | os.O_NONBLOCK)
    try:
        # set format
        fmt = bytearray(struct.calcsize(FORMAT_FMT))
        pix = (w, h, fourcc_value, V4L2_FIELD_ANY, 0, 0, 0, 0, 0, 0, 0, 0)
        struct.pack_into(FORMAT_FMT, fmt, 0, V4L2_BUF_TYPE_VIDEO_CAPTURE, *pix)
        fcntl.ioctl(fd, VIDIOC_S_FMT, fmt, True)
        got = struct.unpack(FORMAT_FMT, fmt)
        gw, gh, gpix, gfield, gbpl, gsize = got[1], got[2], got[3], got[4], got[5], got[6]
        # request 1 buffer
        rb = bytearray(struct.calcsize(REQBUFS_FMT))
        struct.pack_into(REQBUFS_FMT, rb, 0, 1, V4L2_BUF_TYPE_VIDEO_CAPTURE, V4L2_MEMORY_MMAP, 0)
        fcntl.ioctl(fd, VIDIOC_REQBUFS, rb, True)
        nbuf = struct.unpack(REQBUFS_FMT, rb)[0]
        if nbuf < 1:
            return False, "REQBUFS returned %d buffers" % nbuf
        # query buffer -> mmap
        qb = bytearray(struct.calcsize(BUF_FMT))
        fcntl.ioctl(fd, VIDIOC_QUERYBUF, qb, True)
        # our BUF_FMT layout: index(0) type(1) bytesused(2) flags(3) field(4) ts(5=8bytes? we used 4s at index5..6)
        idx_v, _type, _used, _flags, _field = struct.unpack_from(BUF_FMT, qb, 0)[:5]
        # offset is field index 9 in our layout (after ts/timecode/sequence/memory)
        _off = struct.unpack_from(BUF_FMT, qb, 9 * 4)[0]
        _len = struct.unpack_from(BUF_FMT, qb, 10 * 4)[0]
        if _len <= 0:
            _len = gsize
        buf = mmap.mmap(fd, _len, mmap.MAP_SHARED, mmap.PROT_READ | mmap.PROT_WRITE, offset=_off)
        # qbuf
        struct.pack_into(BUF_FMT, qb, 0, 0, V4L2_BUF_TYPE_VIDEO_CAPTURE, 0, 0, V4L2_FIELD_ANY, b'\0'*4, 0, 0, 0, V4L2_MEMORY_MMAP, _off, _len, 0, 0, 0)
        fcntl.ioctl(fd, VIDIOC_QBUF, qb, True)
        # streamon
        fcntl.ioctl(fd, VIDIOC_STREAMON, struct.pack(STREAMON_FMT, V4L2_BUF_TYPE_VIDEO_CAPTURE), True)
        # dqbuf with deadline
        deadline = time.time() + timeout
        dq = bytearray(struct.calcsize(BUF_FMT))
        struct.pack_into(BUF_FMT, dq, 0, 0, V4L2_BUF_TYPE_VIDEO_CAPTURE, 0, 0, V4L2_FIELD_ANY, b'\0'*4, 0, 0, 0, V4L2_MEMORY_MMAP, _off, _len, 0, 0, 0)
        got_frame = False
        while time.time() < deadline:
            try:
                fcntl.ioctl(fd, VIDIOC_DQBUF, dq, True)
                got_frame = True
                break
            except OSError as e:
                if e.errno in (11,):  # EAGAIN
                    time.sleep(0.05); continue
                raise
        # streamoff regardless
        try:
            fcntl.ioctl(fd, VIDIOC_STREAMOFF, struct.pack(STREAMON_FMT, V4L2_BUF_TYPE_VIDEO_CAPTURE), True)
        except OSError:
            pass
        if not got_frame:
            return False, "DQBUF timed out after %.1fs (no frame produced)" % timeout
        bytesused = struct.unpack_from(BUF_FMT, dq, 2)[0] or _len
        data = bytes(buf[:bytesused])
        with open(out, 'wb') as fh:
            fh.write(data)
        return True, "captured %d bytes (%s %dx%d bpl=%d sizeimage=%d) -> %s" % (bytesused, fourcc_str(gpix), gw, gh, gbpl, gsize, out)
    finally:
        os.close(fd)

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--capture', nargs=2, metavar=('DEV', 'OUT'), help='bounded single-frame capture')
    ap.add_argument('--fourcc', default='NV12', help='capture fourcc (default NV12)')
    ap.add_argument('--width', type=int, default=640)
    ap.add_argument('--height', type=int, default=480)
    ap.add_argument('--timeout', type=float, default=15.0)
    ap.add_argument('nodes', nargs='*', help='specific /dev/video* nodes to probe (default: all)')
    args = ap.parse_args(argv)

    if args.capture:
        dev, out = args.capture
        ok, detail = capture_one(dev, out, fourcc(args.fourcc.encode()), args.width, args.height, args.timeout)
        print('%s %s' % ('CAPTURED' if ok else 'CAPTURE_FAILED', detail))
        return 0 if ok else 2

    nodes = args.nodes or sorted(
        ('/dev/' + f for f in os.listdir('/dev') if f.startswith('video')),
        key=lambda p: int(''.join(ch for ch in p if ch.isdigit()) or '0'))
    for p in nodes:
        try:
            info = probe_node(p)
        except OSError as e:
            print('%-16s OPEN_FAILED %s' % (p, e)); continue
        fmtstr = ' '.join('%s(%s)' % (fc, dsc) for fc, dsc in info['formats']) or '(none/not-a-capture-node)'
        print('%-16s driver=%-28s card=%-28s caps=0x%08x dcaps=0x%08x stream=%s fmt=[%s]' % (
            info['path'], info['driver'], info['card'], info['caps'], info['device_caps'],
            info['streaming'], fmtstr))
    return 0

if __name__ == '__main__':
    sys.exit(main())
