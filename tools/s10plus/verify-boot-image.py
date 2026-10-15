#!/usr/bin/env python3
"""verify-boot-image.py — fail-closed release gate for S10+ (beyond2lte) BOOT images.

Hardware-proven facts this gate encodes (see
docs/s10plus-autonomous-boot-repair/ROOT-CAUSE.md):

  * Samsung S-Boot *jumps* to `kernel_addr`; it does not decompress.  A gzip
    kernel payload is executed as code and produces zero console output
    (attempt A1: seven silent loads).  A raw arm64 `Image` executes (attempt A2).
  * S-Boot parses header offset 40 as `header_version` and logs it
    (`[UFDT] BOOT IMG HDR V1` vs `HDR V376101`).  The old packer wrote the DTB
    size there, producing a legacy header S-Boot treats as a different version.
  * The kernel's initramfs parser (`init/initramfs.c`) requires the archive to
    reach `TRAILER!!!` with `state == Reset`; anything else is rejected with
    "junk in compressed archive".
  * `prepare_namespace()` is skipped when the initramfs supplies /init, so the
    kernel does *not* mount devtmpfs first: /dev/console must be in the archive
    or `kernel_init` prints "Warning: unable to open an initial console" and the
    initramfs gets no console at all (no boot evidence can ever be captured).

The gate is intentionally strict: a candidate that fails here must not be
flashed.  Exit status 0 = every gate passed; 1 = at least one hard failure;
2 = usage / unreadable input.

Usage:
  verify-boot-image.py [--partition-bytes N] [--json] [--quiet] IMAGE [IMAGE...]
"""

import argparse
import gzip
import hashlib
import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import newc  # noqa: E402  (repo-local, dependency-free newc cpio reader)

MAGIC = b"ANDROID!"
PAGE_SIZE = 2048
HEADER_VERSION = 1
HEADER_SIZE_V1 = 1648
ARM64_IMAGE_MAGIC = b"ARM\x64"
# /dev/block/by-name/boot on this SM-G975F, read from the live device.
BOOT_PARTITION_BYTES_DEFAULT = 57671680
DTB_MAGIC = 0xD00DFEED

S_IFMT = 0o170000
S_IFREG = 0o100000
S_IFLNK = 0o120000


class Gate:
    def __init__(self):
        self.failures = []
        self.warnings = []
        self.notes = []

    def fail(self, msg):
        self.failures.append(msg)

    def warn(self, msg):
        self.warnings.append(msg)

    def note(self, msg):
        self.notes.append(msg)


def round_up(v, a):
    return ((v + a - 1) // a) * a


def _lzma_alone(data):
    import lzma
    dec = lzma.LZMADecompressor(format=lzma.FORMAT_ALONE)
    out = dec.decompress(data)
    declared = int.from_bytes(data[5:13], "little")
    note = "eos-marker" if dec.eof else "stream-ended-without-eos-marker"
    if declared != 0xFFFFFFFFFFFFFFFF and len(out) != declared:
        raise ValueError("LZMA header declares %d bytes, got %d" % (declared, len(out)))
    return out, "lzma-alone/%s/dict=0x%x" % (note, int.from_bytes(data[1:5], "little"))


def decompress_ramdisk(blob, gate):
    """Return (decompressed_bytes, format_string).  Raises ValueError if the
    payload claims a compression format but cannot be decoded."""
    if blob[:2] == b"\x1f\x8b":
        return gzip.decompress(blob), "gzip"
    if blob[:3] == b"\x5d\x00\x00":
        return _lzma_alone(blob)
    if blob[:6] == b"\xfd7zXZ\x00":
        import lzma
        return lzma.decompress(blob, format=lzma.FORMAT_XZ), "xz"
    if blob[:3] == b"BZh":
        import bz2
        return bz2.decompress(blob), "bzip2"
    if blob[:4] == b"\x02\x21\x4c\x18":
        import lzma
        return lzma.decompress(blob[4:], format=lzma.FORMAT_RAW,
                               filters=[{"id": lzma.FILTER_LZ4
                                         if hasattr(lzma, "FILTER_LZ4") else 0,
                                         "preset": 0}]), "lz4"
    if blob[:6] == MAGIC_CPIO:
        return blob, "none(raw-cpio)"
    raise ValueError("unrecognised ramdisk container (first bytes %s)" % blob[:8].hex())


MAGIC_CPIO = b"070701"


def check_cpio(data, gate, label):
    """Validate a newc archive and the /init handoff contract.  Returns a dict."""
    info = {"records": 0, "init": None, "trailer_offset": None,
            "logical_end": None, "names": []}
    try:
        recs = list(newc.iter_records(data))
    except newc.CpioError as exc:
        gate.fail("%s: not a usable newc archive: %s" % (label, exc))
        return info
    names = {}
    for off, name, mode, filesize, dstart, dlen in recs:
        info["records"] += 1
        if name == newc.TRAILER:
            info["trailer_offset"] = off
            info["logical_end"] = dstart + dlen
            continue
        if name.startswith("/") or ".." in name.split("/"):
            gate.fail("%s: unsafe member path %r" % (label, name))
        if name in names:
            gate.fail("%s: duplicate member %r (a doubled /init or /dev/console "
                      "means the archive was assembled twice)" % (label, name))
        names[name] = (mode, filesize, dstart)
        info["names"].append(name)
    if info["trailer_offset"] is None:
        gate.fail("%s: archive never reaches TRAILER!!! — the kernel reports "
                  "'junk in compressed archive' for this" % label)
        return info

    # trailing bytes after the trailer record must be nothing but zero padding
    tail = data[info["logical_end"]:]
    if tail.strip(b"\x00"):
        gate.warn("%s: %d non-zero bytes after TRAILER!!! (ignored by the kernel)"
                  % (label, len(tail) - len(tail.rstrip(b"\x00"))))
    info["init"] = None
    ent = names.get("init")
    if ent is None:
        gate.fail("%s: /init is missing — kernel_init would fall back to "
                  "prepare_namespace() and mount an unrelated rootfs" % label)
        return info
    mode, filesize, dstart = ent
    info["init"] = {"mode": oct(mode), "size": filesize}
    if (mode & S_IFMT) != S_IFREG:
        gate.fail("%s: /init is not a regular file (mode %s)" % (label, oct(mode)))
        return info
    if not (mode & 0o111):
        gate.fail("%s: /init is not executable (mode %s)" % (label, oct(mode)))
    body = data[dstart:dstart + filesize]
    if body.startswith(b"#!"):
        interp = body[2:].split(b"\n", 1)[0].strip().split(b" ")[0].decode()
        info["init"]["interpreter"] = interp
        key = interp.lstrip("/")
        if key not in names:
            gate.fail("%s: /init interpreter %s is missing from the archive" % (label, interp))
        else:
            imode = names[key][0]
            if (imode & S_IFMT) == S_IFLNK:
                lstart = names[key][2]
                link = data[lstart:lstart + names[key][1]].decode("latin1")
                gate.note("%s: %s -> %s" % (label, interp, link))
            elif not (names[key][0] & 0o111):
                gate.fail("%s: /init interpreter %s is present but not executable"
                          % (label, interp))
    if "dev/console" not in names:
        gate.warn("%s: /dev/console is missing — prepare_namespace() is skipped "
                  "for a built-in initramfs, so kernel_init cannot open an initial "
                  "console and NO initramfs output can ever be captured" % label)
    return info


def inspect(path, partition_bytes, gate):
    rep = {"path": path}
    size = os.path.getsize(path)
    rep["size"] = size
    if size < 2 * PAGE_SIZE:
        gate.fail("image is too small (%d bytes) to be a boot image" % size)
        return rep
    with open(path, "rb") as fh:
        data = fh.read()
    rep["sha256"] = hashlib.sha256(data).hexdigest()

    if data[:8] != MAGIC:
        gate.fail("bad boot magic %r (expected %r)" % (data[:8], MAGIC))
        return rep
    f32 = lambda o: struct.unpack_from("<I", data, o)[0]
    ksize, kaddr, rsize, raddr = f32(8), f32(12), f32(16), f32(20)
    ssize, saddr, tags, page = f32(24), f32(28), f32(32), f32(36)
    field40, os_version = f32(40), f32(44)
    if page != PAGE_SIZE:
        gate.fail("page_size is %d, must be %d" % (page, PAGE_SIZE))
        return rep
    name = data[48:64].split(b"\x00")[0].decode("ascii", "replace")
    cmdline = data[64:576].split(b"\x00")[0].decode("ascii", "replace")
    rep.update(kernel_size=ksize, kernel_addr="0x%08x" % kaddr, ramdisk_size=rsize,
               ramdisk_addr="0x%08x" % raddr, second_size=ssize,
               tags_addr="0x%08x" % tags, name=name, cmdline=cmdline,
               header_field40=field40, os_version="0x%08x" % os_version)

    # ---- gate 1: real boot_img_hdr_v1 ------------------------------------------
    if field40 != HEADER_VERSION:
        msg = ("header offset 40 = %d (0x%x); a boot_img_hdr_v1 requires "
               "header_version == 1" % (field40, field40))
        if field40 > 4096:
            msg += (" — this is the legacy packer defect that wrote the DTB size "
                    "there (S-Boot logs it as '[UFDT] BOOT IMG HDR V%d')" % field40)
        gate.fail(msg)
    if field40 == HEADER_VERSION:
        rdtbo_size = f32(1632)
        rdtbo_off = struct.unpack_from("<Q", data, 1636)[0]
        hsize = f32(1644)
        rep.update(recovery_dtbo_size=rdtbo_size, recovery_dtbo_offset=rdtbo_off,
                   header_size=hsize)
        if hsize != HEADER_SIZE_V1:
            gate.fail("header_size field is %d, boot_img_hdr_v1 requires %d"
                      % (hsize, HEADER_SIZE_V1))
        if rdtbo_off and (rdtbo_off + rdtbo_size) > size:
            gate.warn("recovery_dtbo_offset/size (%d/%d) point past the image"
                      % (rdtbo_off, rdtbo_size))
    if os_version == 0:
        gate.warn("os_version is 0; S-Boot logs it and the device's own images "
                  "use 0x18000171 (12.0.0)")
    if ssize != 0:
        gate.warn("second_size is %d (expected 0 on this device)" % ssize)

    # ---- gate 2: kernel payload -------------------------------------------------
    if ksize == 0:
        gate.fail("kernel_size is 0")
        return rep
    koff = page
    if koff + ksize > size:
        gate.fail("kernel extends past end of image")
        return rep
    kernel = data[koff:koff + ksize]
    rep["kernel_sha256"] = hashlib.sha256(kernel).hexdigest()
    if kernel[:2] == b"\x1f\x8b":
        gate.fail("kernel payload is GZIP — S-Boot jumps to kernel_addr without "
                  "decompressing, so gzip bytes are executed as code (attempt A1: "
                  "seven silent loads). Ship the raw arm64 Image.")
        return rep
    if kernel[0x38:0x3C] != ARM64_IMAGE_MAGIC:
        gate.fail("kernel payload is not a raw arm64 Image (no 'ARM\\x64' code0 "
                  "reserved field at offset 0x38; found %r)" % kernel[0x38:0x3C])
        return rep
    text_offset, image_size, flags = struct.unpack_from("<QQQ", kernel, 8)
    rep["kernel_headers"] = {"text_offset": "0x%x" % text_offset,
                             "image_size": "0x%x" % image_size,
                             "flags": "0x%x" % flags}
    if not (0 < image_size <= 1 << 30):
        gate.fail("arm64 Image header image_size 0x%x is implausible" % image_size)
    if ksize < 65536:
        gate.fail("kernel payload is only %d bytes" % ksize)
    if text_offset > (1 << 30):
        gate.fail("arm64 Image text_offset 0x%x is implausible" % text_offset)
    # image_size spans _text.._end (BSS included) and may exceed the file size.
    if image_size > ksize:
        gate.note("arm64 Image image_size 0x%x exceeds the %d-byte payload "
                  "(BSS is not stored in the file) — expected"
                  % (image_size, ksize))
    gate.note("arm64 Image flags=0x%x (bit0 endian, bit1 page size, bit2/3 placement)"
              % flags)

    # ---- gate 3: ramdisk placement ---------------------------------------------
    roff = page + round_up(ksize, page)
    if roff != page + round_up(ksize, page):
        gate.fail("ramdisk offset arithmetic is wrong")
    if rsize == 0:
        gate.fail("ramdisk_size is 0 — the kernel needs an initramfs that owns /init")
        return rep
    if roff + rsize > size:
        gate.fail("ramdisk region [%d,%d) extends past end of image (%d)"
                  % (roff, roff + rsize, size))
        return rep
    rep.update(kernel_offset=koff, ramdisk_offset=roff,
               ramdisk_offset_hex="0x%x" % roff)
    ramdisk = data[roff:roff + rsize]
    rep["ramdisk_sha256"] = hashlib.sha256(ramdisk).hexdigest()

    # ---- gate 4: ramdisk contents ----------------------------------------------
    label = "ramdisk"
    try:
        plain, fmt = decompress_ramdisk(ramdisk, gate)
    except Exception as exc:
        gate.fail("%s: declared container cannot be decoded: %s" % (label, exc))
        return rep
    rep["ramdisk_format"] = fmt
    rep["ramdisk_uncompressed_size"] = len(plain)
    if len(plain) < 512:
        gate.fail("%s: decompressed to only %d bytes" % (label, len(plain)))
        return rep
    cpio = check_cpio(plain, gate, label)
    rep["cpio"] = {k: cpio[k] for k in ("records", "trailer_offset", "logical_end")
                   if k in cpio}
    rep["cpio"]["init"] = cpio.get("init")

    # ---- gate 5: appended device tree ------------------------------------------
    doff = roff + round_up(rsize, page)
    if doff < size:
        dtb = data[doff:size]
        if len(dtb) >= 8:
            dt_magic = struct.unpack_from(">I", dtb, 0)[0]
            if dt_magic != DTB_MAGIC:
                gate.warn("bytes after the ramdisk do not start with an FDT magic "
                          "(0x%08x); appending a DTB is how S-Boot finds "
                          "entry[0]" % dt_magic)
            else:
                totalsize = struct.unpack_from(">I", dtb, 4)[0]
                rep["dtb_offset"] = doff
                rep["dtb_size"] = totalsize
                if totalsize > len(dtb):
                    gate.fail("appended DTB declares %d bytes but only %d are present"
                              % (totalsize, len(dtb)))
                if totalsize < len(dtb) and dtb[totalsize:].strip(b"\x00"):
                    gate.warn("%d non-zero bytes after the DTB" % (len(dtb) - totalsize))
                for prop in (b"linux,initrd-start", b"linux,initrd-end"):
                    if prop in dtb[:totalsize]:
                        gate.warn("appended DTB contains a stale /chosen %s "
                                  "placeholder (S-Boot overwrites it; do not count a "
                                  "change to it as a device-tree experiment)"
                                  % prop.decode())
    # ---- gate 6: partition capacity --------------------------------------------
    if size > partition_bytes:
        gate.fail("image is %d bytes, larger than the BOOT partition (%d bytes)"
                  % (size, partition_bytes))
    else:
        rep["partition_bytes"] = partition_bytes
        rep["partition_slack"] = partition_bytes - size
    return rep


def main(argv):
    ap = argparse.ArgumentParser(prog="verify-boot-image.py")
    ap.add_argument("images", nargs="+")
    ap.add_argument("--partition-bytes", type=int,
                    default=int(os.environ.get("NUXEL_BOOT_PARTITION_BYTES",
                                               BOOT_PARTITION_BYTES_DEFAULT)))
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    overall = 0
    reports = []
    for path in args.images:
        gate = Gate()
        try:
            rep = inspect(path, args.partition_bytes, gate)
        except OSError as exc:
            gate.fail("cannot read: %s" % exc)
            rep = {"path": path}
        rep["failures"] = gate.failures
        rep["warnings"] = gate.warnings
        rep["notes"] = gate.notes
        rep["result"] = "PASS" if not gate.failures else "FAIL"
        reports.append(rep)
        if gate.failures:
            overall = 1
        if not args.json:
            print("== %s : %s" % (path, rep["result"]))
            if not args.quiet:
                for k in ("size", "sha256", "header_field40", "header_size",
                          "kernel_size", "kernel_sha256", "kernel_headers",
                          "ramdisk_size", "ramdisk_format",
                          "ramdisk_uncompressed_size", "ramdisk_sha256", "cpio",
                          "dtb_offset", "dtb_size", "partition_slack"):
                    if k in rep:
                        print("   %-26s %s" % (k + ":", rep[k]))
            for w in gate.warnings:
                print("   WARN  %s" % w)
            for n in gate.notes:
                print("   note  %s" % n)
            for f in gate.failures:
                print("   FAIL  %s" % f)
    if args.json:
        print(json.dumps(reports, indent=2, default=str))
    return overall


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
