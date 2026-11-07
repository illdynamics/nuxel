#!/usr/bin/env python3
"""nuxel-v4l2-probe.py — corrected V4L2 enumeration + bounded capture (PWNAGE-83000).

The previous revision advertised multi-planar capture capability
(V4L2_CAP_VIDEO_CAPTURE_MPLANE) but then used the SINGLE-planar buffer type
(V4L2_BUF_TYPE_VIDEO_CAPTURE = 1) and single-planar structs on those nodes,
which is an ABI mismatch on FIMC-IS.  This revision selects the buffer type
from the node's device_caps:

    single-planar node -> V4L2_BUF_TYPE_VIDEO_CAPTURE + v4l2_pix_format
                          + v4l2_buffer (offset)
    multi-planar node  -> V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE (9)
                          + v4l2_pix_format_mplane + v4l2_buffer with
                          m.planes / v4l2_plane array

Struct layouts are defined with ctypes so AArch64 alignment is correct, and
ioctl numbers are computed from the real struct sizes with the asm-generic
_IOC macros.  The program remains read-only unless --capture is given.
"""
from __future__ import annotations

import argparse
import ctypes
import ctypes.util
import fcntl
import mmap
import os
import struct
import sys
import time

VIDEO_MAX_PLANES = 8
V4L2_BUF_TYPE_VIDEO_CAPTURE = 1
V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE = 9
V4L2_MEMORY_MMAP = 1
V4L2_FIELD_ANY = 0
V4L2_CAP_VIDEO_CAPTURE = 0x00000001
V4L2_CAP_VIDEO_CAPTURE_MPLANE = 0x00001000
V4L2_CAP_STREAMING = 0x04000000

# --- asm-generic ioctl number construction ---------------------------------
_IOC_NRBITS = 8
_IOC_TYPEBITS = 8
_IOC_SIZEBITS = 14
_IOC_NRSHIFT = 0
_IOC_TYPESHIFT = _IOC_NRSHIFT + _IOC_NRBITS
_IOC_SIZESHIFT = _IOC_TYPESHIFT + _IOC_TYPEBITS
_IOC_DIRSHIFT = _IOC_SIZESHIFT + _IOC_SIZEBITS
_IOC_NONE, _IOC_WRITE, _IOC_READ = 0, 1, 2


def _ioc(direction, typechar, nr, size):
    return ((direction << _IOC_DIRSHIFT) | (ord(typechar) << _IOC_TYPESHIFT)
            | (nr << _IOC_NRSHIFT) | (size << _IOC_SIZESHIFT))


def _ior(t, nr, size): return _ioc(_IOC_READ, t, nr, size)
def _iow(t, nr, size): return _ioc(_IOC_WRITE, t, nr, size)
def _iowr(t, nr, size): return _ioc(_IOC_READ | _IOC_WRITE, t, nr, size)


# --- ctypes struct definitions (kernel 4.14 UAPI, aarch64) -----------------
class v4l2_capability(ctypes.Structure):
    _fields_ = [
        ("driver", ctypes.c_uint8 * 16),
        ("card", ctypes.c_uint8 * 32),
        ("bus_info", ctypes.c_uint8 * 32),
        ("version", ctypes.c_uint32),
        ("capabilities", ctypes.c_uint32),
        ("device_caps", ctypes.c_uint32),
        ("reserved", ctypes.c_uint32 * 3),
    ]


class v4l2_fmtdesc(ctypes.Structure):
    _fields_ = [
        ("index", ctypes.c_uint32),
        ("type", ctypes.c_uint32),
        ("flags", ctypes.c_uint32),
        ("description", ctypes.c_uint8 * 32),
        ("pixelformat", ctypes.c_uint32),
        ("reserved", ctypes.c_uint32 * 4),
    ]


class v4l2_pix_format(ctypes.Structure):
    _fields_ = [
        ("width", ctypes.c_uint32),
        ("height", ctypes.c_uint32),
        ("pixelformat", ctypes.c_uint32),
        ("field", ctypes.c_uint32),
        ("bytesperline", ctypes.c_uint32),
        ("sizeimage", ctypes.c_uint32),
        ("colorspace", ctypes.c_uint32),
        ("priv", ctypes.c_uint32),
        ("flags", ctypes.c_uint32),
        ("ycbcr_enc", ctypes.c_uint32),
        ("quantization", ctypes.c_uint32),
        ("xfer_func", ctypes.c_uint32),
    ]


class v4l2_plane_pix_format(ctypes.Structure):
    _fields_ = [
        ("sizeimage", ctypes.c_uint32),
        ("bytesperline", ctypes.c_uint32),
        ("reserved", ctypes.c_uint16 * 6),
    ]


class v4l2_pix_format_mplane(ctypes.Structure):
    _fields_ = [
        ("width", ctypes.c_uint32),
        ("height", ctypes.c_uint32),
        ("pixelformat", ctypes.c_uint32),
        ("field", ctypes.c_uint32),
        ("colorspace", ctypes.c_uint32),
        ("plane_fmt", v4l2_plane_pix_format * VIDEO_MAX_PLANES),
        ("num_planes", ctypes.c_uint8),
        ("flags", ctypes.c_uint8),
        ("ycbcr_enc", ctypes.c_uint8),
        ("quantization", ctypes.c_uint8),
        ("xfer_func", ctypes.c_uint8),
        ("reserved", ctypes.c_uint8 * 7),
    ]


class _v4l2_format_union(ctypes.Union):
    _fields_ = [
        ("pix", v4l2_pix_format),
        ("pix_mp", v4l2_pix_format_mplane),
        ("raw", ctypes.c_uint8 * 208),
    ]


class v4l2_format(ctypes.Structure):
    _anonymous_ = ("fmt",)
    _fields_ = [
        ("type", ctypes.c_uint32),
        ("fmt", _v4l2_format_union),
    ]


class v4l2_requestbuffers(ctypes.Structure):
    _fields_ = [
        ("count", ctypes.c_uint32),
        ("type", ctypes.c_uint32),
        ("memory", ctypes.c_uint32),
        ("reserved", ctypes.c_uint32 * 2),
    ]


class v4l2_timecode(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_uint32),
        ("flags", ctypes.c_uint32),
        ("frames", ctypes.c_uint8),
        ("seconds", ctypes.c_uint8),
        ("minutes", ctypes.c_uint8),
        ("hours", ctypes.c_uint8),
        ("userbits", ctypes.c_uint8 * 4),
    ]


class v4l2_plane(ctypes.Structure):
    class _m(ctypes.Union):
        _fields_ = [
            ("mem_offset", ctypes.c_uint32),
            ("userptr", ctypes.c_ulong),
            ("fd", ctypes.c_int32),
        ]
    _fields_ = [
        ("bytesused", ctypes.c_uint32),
        ("length", ctypes.c_uint32),
        ("m", _m),
        ("data_offset", ctypes.c_uint32),
        ("reserved", ctypes.c_uint32 * 11),
    ]


class v4l2_buffer(ctypes.Structure):
    class _m(ctypes.Union):
        _fields_ = [
            ("offset", ctypes.c_uint32),
            ("userptr", ctypes.c_ulong),
            ("planes", ctypes.POINTER(v4l2_plane)),
            ("fd", ctypes.c_int32),
        ]
    _fields_ = [
        ("index", ctypes.c_uint32),
        ("type", ctypes.c_uint32),
        ("bytesused", ctypes.c_uint32),
        ("flags", ctypes.c_uint32),
        ("field", ctypes.c_uint32),
        ("timestamp", ctypes.c_long * 2),
        ("timecode", v4l2_timecode),
        ("sequence", ctypes.c_uint32),
        ("memory", ctypes.c_uint32),
        ("m", _m),
        ("length", ctypes.c_uint32),
        ("reserved2", ctypes.c_uint32),
        ("request_fd", ctypes.c_int32),
    ]


# --- ioctl numbers ---------------------------------------------------------
V = "V"
VIDIOC_QUERYCAP = _ior(V, 0, ctypes.sizeof(v4l2_capability))
VIDIOC_ENUM_FMT = _iowr(V, 2, ctypes.sizeof(v4l2_fmtdesc))
VIDIOC_S_FMT = _iowr(V, 5, ctypes.sizeof(v4l2_format))
VIDIOC_G_FMT = _iowr(V, 4, ctypes.sizeof(v4l2_format))
VIDIOC_REQBUFS = _iowr(V, 8, ctypes.sizeof(v4l2_requestbuffers))
VIDIOC_QUERYBUF = _iowr(V, 9, ctypes.sizeof(v4l2_buffer))
VIDIOC_QBUF = _iowr(V, 15, ctypes.sizeof(v4l2_buffer))
VIDIOC_DQBUF = _iowr(V, 17, ctypes.sizeof(v4l2_buffer))
VIDIOC_STREAMON = _iow(V, 18, ctypes.sizeof(ctypes.c_uint32))
VIDIOC_STREAMOFF = _iow(V, 19, ctypes.sizeof(ctypes.c_uint32))


def _ioctl(fd, req, arg):
    fcntl.ioctl(fd, req, arg, True)


def fourcc_str(v):
    return struct.pack("<I", v).decode("latin1")


def pstr(b):
    return bytes(b).split(b"\0", 1)[0].decode("utf-8", "replace")


def _buf_type(is_mplane):
    return V4L2_BUF_TYPE_VIDEO_CAPTURE_MPLANE if is_mplane else V4L2_BUF_TYPE_VIDEO_CAPTURE


def probe_node(path):
    fd = os.open(path, os.O_RDWR | os.O_NONBLOCK)
    try:
        cap = v4l2_capability()
        _ioctl(fd, VIDIOC_QUERYCAP, cap)
        is_mplane = bool(cap.device_caps & V4L2_CAP_VIDEO_CAPTURE_MPLANE)
        is_cap = bool(cap.device_caps & V4L2_CAP_VIDEO_CAPTURE) or is_mplane
        formats = []
        if is_cap:
            bt = _buf_type(is_mplane)
            for idx in range(64):
                f = v4l2_fmtdesc()
                f.index = idx
                f.type = bt
                try:
                    _ioctl(fd, VIDIOC_ENUM_FMT, f)
                except OSError:
                    break
                formats.append((fourcc_str(f.pixelformat), pstr(f.description)))
        return {
            "path": path,
            "driver": pstr(cap.driver),
            "card": pstr(cap.card),
            "bus": pstr(cap.bus_info),
            "caps": cap.capabilities,
            "device_caps": cap.device_caps,
            "is_capture": is_cap,
            "is_mplane": is_mplane,
            "streaming": bool(cap.device_caps & V4L2_CAP_STREAMING),
            "formats": formats,
        }
    finally:
        os.close(fd)


def capture_one(path, out, fourcc_value, w, h, timeout=15.0):
    """Bounded single-frame capture.  Chooses the correct ABI per node."""
    fd = os.open(path, os.O_RDWR | os.O_NONBLOCK)
    try:
        cap = v4l2_capability()
        _ioctl(fd, VIDIOC_QUERYCAP, cap)
        is_mplane = bool(cap.device_caps & V4L2_CAP_VIDEO_CAPTURE_MPLANE)
        bt = _buf_type(is_mplane)

        fmt = v4l2_format()
        fmt.type = bt
        if is_mplane:
            fmt.fmt.pix_mp.width = w
            fmt.fmt.pix_mp.height = h
            fmt.fmt.pix_mp.pixelformat = fourcc_value
            fmt.fmt.pix_mp.field = V4L2_FIELD_ANY
            fmt.fmt.pix_mp.num_planes = 1
        else:
            fmt.fmt.pix.width = w
            fmt.fmt.pix.height = h
            fmt.fmt.pix.pixelformat = fourcc_value
            fmt.fmt.pix.field = V4L2_FIELD_ANY
        _ioctl(fd, VIDIOC_S_FMT, fmt)

        nplanes = int(fmt.fmt.pix_mp.num_planes) if is_mplane else 1
        if nplanes < 1:
            return False, "driver reported 0 planes"

        req = v4l2_requestbuffers()
        req.count = 1
        req.type = bt
        req.memory = V4L2_MEMORY_MMAP
        _ioctl(fd, VIDIOC_REQBUFS, req)
        if req.count < 1:
            return False, "REQBUFS returned %d buffers" % req.count

        # Query buffer; for mplane the kernel expects a populated planes array.
        planes = (v4l2_plane * nplanes)()
        qb = v4l2_buffer()
        qb.index = 0
        qb.type = bt
        qb.memory = V4L2_MEMORY_MMAP
        if is_mplane:
            qb.m.planes = ctypes.cast(planes, ctypes.POINTER(v4l2_plane))
            qb.length = nplanes
        _ioctl(fd, VIDIOC_QUERYBUF, qb)

        maps = []
        if is_mplane:
            for i in range(nplanes):
                plen = int(planes[i].length)
                off = int(planes[i].m.mem_offset)
                if plen <= 0:
                    plen = int(fmt.fmt.pix_mp.plane_fmt[i].sizeimage)
                maps.append(mmap.mmap(fd, plen, mmap.MAP_SHARED,
                                      mmap.PROT_READ | mmap.PROT_WRITE, offset=off))
            length_total = sum(int(planes[i].length) for i in range(nplanes))
        else:
            length = int(qb.length)
            off = int(qb.m.offset)
            maps.append(mmap.mmap(fd, length, mmap.MAP_SHARED,
                                  mmap.PROT_READ | mmap.PROT_WRITE, offset=off))
            length_total = length

        # Queue buffer.
        qb.bytesused = 0
        qb.flags = 0
        qb.field = V4L2_FIELD_ANY
        qb.index = 0
        qb.type = bt
        qb.memory = V4L2_MEMORY_MMAP
        if is_mplane:
            planes[0].bytesused = 0
            qb.m.planes = ctypes.cast(planes, ctypes.POINTER(v4l2_plane))
            qb.length = nplanes
        _ioctl(fd, VIDIOC_QBUF, qb)

        _ioctl(fd, VIDIOC_STREAMON, ctypes.c_uint32(bt))

        deadline = time.time() + timeout
        got = False
        while time.time() < deadline:
            dq = v4l2_buffer()
            dq.type = bt
            dq.memory = V4L2_MEMORY_MMAP
            if is_mplane:
                dq.m.planes = ctypes.cast(planes, ctypes.POINTER(v4l2_plane))
                dq.length = nplanes
            try:
                _ioctl(fd, VIDIOC_DQBUF, dq)
                got = True
                break
            except OSError as e:
                if e.errno == 11:
                    time.sleep(0.05)
                    continue
                raise

        try:
            _ioctl(fd, VIDIOC_STREAMOFF, ctypes.c_uint32(bt))
        except OSError:
            pass

        if not got:
            return False, "DQBUF timed out after %.1fs (no frame produced)" % timeout

        chunks = []
        for m in maps:
            chunks.append(m[:])
        data = b"".join(chunks)
        # Honour bytesused when it is sane.
        used = int(dq.bytesused) if not is_mplane else int(planes[0].bytesused)
        if used and 0 < used <= len(data):
            data = data[:used]
        with open(out, "wb") as fh:
            fh.write(data)
        return True, "captured %d bytes mplane=%s (%dx%d) -> %s" % (len(data), is_mplane, w, h, out)
    finally:
        os.close(fd)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--capture", nargs=2, metavar=("DEV", "OUT"))
    ap.add_argument("--fourcc", default="NV12")
    ap.add_argument("--width", type=int, default=640)
    ap.add_argument("--height", type=int, default=480)
    ap.add_argument("--timeout", type=float, default=15.0)
    ap.add_argument("nodes", nargs="*")
    args = ap.parse_args(argv)

    if args.capture:
        dev, out = args.capture
        ok, detail = capture_one(dev, out, struct.unpack("<I", args.fourcc.encode().ljust(4, b"\0"))[0],
                                 args.width, args.height, args.timeout)
        print("%s %s" % ("CAPTURED" if ok else "CAPTURE_FAILED", detail))
        return 0 if ok else 2

    nodes = args.nodes or sorted(
        ("/dev/" + f for f in os.listdir("/dev") if f.startswith("video")),
        key=lambda p: int("".join(ch for ch in p if ch.isdigit()) or "0"))
    for p in nodes:
        try:
            info = probe_node(p)
        except OSError as e:
            print("%-16s OPEN_FAILED %s" % (p, e))
            continue
        fmtstr = " ".join("%s(%s)" % (fc, dsc) for fc, dsc in info["formats"]) or "(none)"
        plane = "mplane" if info["is_mplane"] else ("single" if info["is_capture"] else "-")
        print("%-16s driver=%-24s card=%-24s caps=0x%08x dcaps=0x%08x stream=%s %s fmt=[%s]" % (
            info["path"], info["driver"], info["card"], info["caps"], info["device_caps"],
            info["streaming"], plane, fmtstr))
    return 0


if __name__ == "__main__":
    sys.exit(main())
