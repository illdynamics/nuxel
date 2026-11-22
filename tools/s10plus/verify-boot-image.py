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
import fdt_binary
import dt_graph
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
        gate.fail("%s: %d non-zero bytes after TRAILER!!! (ambiguous ramdisk trailing content)"
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
        gate.fail("%s: /dev/console is missing — prepare_namespace() is skipped "
                  "for a built-in initramfs, so kernel_init cannot open an initial "
                  "console and NO initramfs output can ever be captured" % label)
    return info


def _read_dt_string(blob, off):
    end = blob.find(b"\x00", off)
    if end < 0:
        return None
    return blob[off:end].decode("ascii", "replace")


def check_dtb(dtb, gate, label="appended DTB"):
    """Validate the real beyond2lte hardware statements in the boot DTB.

    The combined NFC image must not rely on a stale DTB that lacks the actual
    controller node.  Parse the flat DT structure conservatively (strings and
    the properties in this device's encoder are little-endian / big-endian
    mixed: names are length-prefixed BE, values are BE cells).
    """
    if len(dtb) < 40 or struct.unpack_from(">I", dtb, 0)[0] != DTB_MAGIC:
        gate.fail("%s: bad FDT magic/short header" % label)
        return {}
    total, off_struct, off_strings = struct.unpack_from(">III", dtb, 4)
    if total > len(dtb) or off_struct >= total or off_strings >= total:
        gate.fail("%s: invalid FDT offsets" % label)
        return {}
    pos = off_struct
    depth = 0
    cur = ""
    path = ""
    props = {}
    while pos + 4 <= total:
        tok = struct.unpack_from(">I", dtb, pos)[0]
        pos += 4
        if tok == 1:  # FDT_BEGIN_NODE, NUL-terminated and 4-byte aligned
            nul = dtb.find(b"\x00", pos, total)
            if nul < 0:
                gate.fail("%s: unterminated FDT node name" % label)
                break
            name = dtb[pos:nul].decode("ascii", "replace")
            pos = _align4(nul + 1)
            path = name if depth == 0 else (path + "/" + name if path else name)
            depth += 1
            cur = path
        elif tok == 2:
            depth -= 1
            if depth <= 0:
                break
            path = path.rsplit("/", 1)[0] if "/" in path else ""
        elif tok == 3:  # FDT_PROP: u32 len, u32 nameoff, value
            nlen = struct.unpack_from(">I", dtb, pos)[0]
            nameoff = struct.unpack_from(">I", dtb, pos + 4)[0]
            pos += 8
            name = _read_dt_string(dtb, off_strings + nameoff) or ""
            value = dtb[pos:pos + nlen]
            if len(value) != nlen:
                gate.fail("%s: truncated FDT property %s" % (label, name))
                break
            pos += _align4(nlen)
            props[(cur, name)] = value
        elif tok == 4:
            continue
        elif tok == 9:
            break
        else:
            gate.fail("%s: unknown FDT token 0x%x" % (label, tok))
            break

    nfc = [(node, v) for (node, name), v in props.items()
           if node.endswith("sec-nfc@27") and name == "compatible"]
    if not nfc:
        gate.fail("%s: no sec-nfc@27 node (NFC controller missing)" % label)
        return props
    node = nfc[0][0]
    if props.get((node, "reg")) != b"\x00\x00\x00\x27":
        gate.fail("%s: sec-nfc@27 reg is not 0x27" % label)
    ven = props.get((node, "sec-nfc,ven-gpio"))
    firm = props.get((node, "sec-nfc,firm-gpio"))
    irq = props.get((node, "sec-nfc,irq-gpio"))
    if not all(isinstance(x, bytes) and len(x) == 12 for x in (ven, firm, irq)):
        gate.fail("%s: NFC GPIO properties are absent or malformed" % label)
        return props
    # The pin-controller pin numbers come from the real board overlays:
    # ven=gpp6-2, firm=gpp6-3, irq=gpa1-2 (all beyond2lte revisions).
    if ven[4:8] != b"\x00\x00\x00\x02" or firm[4:8] != b"\x00\x00\x00\x03":
        gate.fail("%s: NFC ven/firm pins are not gpp6-2/gpp6-3" % label)
    if irq[4:8] != b"\x00\x00\x00\x02":
        gate.fail("%s: NFC IRQ pin is not gpa1-2" % label)
    gate.note("%s: sec-nfc@27 present at I2C 0x27 with ven/firm/irq GPIOs" % label)
    return props


def _align4(n):
    return (n + 3) & ~3


def inspect(path, partition_bytes, gate, expected=None, selected_appended_idx=None):
    expected = expected or {}
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
            gate.fail("recovery_dtbo_offset/size (%d/%d) point past the image"
                      % (rdtbo_off, rdtbo_size))
    if os_version == 0:
        gate.warn("os_version is 0; S-Boot logs it and the device's own images "
                  "use 0x18000171 (12.0.0)")
    if ssize != 0:
        gate.fail("second_size is %d (expected 0 on this device)" % ssize)

    if (rdtbo_size == 0) != (rdtbo_off == 0):
        gate.fail('recovery_dtbo header fields inconsistent (this is NOT the dtbo partition)')
    if expected.get('boot') and rep['sha256'] != expected['boot']:
        gate.fail('BOOT full-image SHA-256 differs from approved candidate source')
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
    if expected.get('kernel') and rep['kernel_sha256'] != expected['kernel']:
        gate.fail('kernel member SHA-256 mismatch against approved input')
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
    if expected.get('ramdisk') and rep['ramdisk_sha256'] != expected['ramdisk']:
        gate.fail('ramdisk member SHA-256 mismatch against approved input')

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

    # ---- gate 5: appended DTBs; exact count and bootloader selection --------
    doff = roff + round_up(rsize, page)
    if doff >= size:
        gate.fail('BOOT has no appended DTB; bootloader DT selection unproven')
    else:
        pos = doff
        found = []
        while pos < size:
            tail = data[pos:]
            if not any(tail):
                break  # partition padding is permitted only after an FDT
            if len(tail) < 40 or tail[:4] != struct.pack('>I', DTB_MAGIC):
                gate.fail('unexpected non-FDT payload at BOOT offset %d (magic/size)' % pos)
                break
            try:
                h = fdt_binary.inspect(tail)
                segment = tail[:h['totalsize']]
                dt_graph.parse_fdt(segment)
                found.append((pos, segment))
            except (ValueError, UnicodeError, struct.error) as e:
                gate.fail('appended DTB at offset %d is malformed: %s' % (pos, e))
                break
            nextp = round_up(pos + h['totalsize'], 4)
            # Concatenated FDTs must be unambiguously packed; no magic scans.
            if any(data[pos + h['totalsize']:nextp]):
                gate.fail('nonzero bytes in appended FDT alignment padding')
                break
            pos = nextp
            # Boot images frequently pad DT to 2048 and then continue with
            # another FDT: accept ONLY zero-padding to exact page boundary.
            if pos < size and data[pos:pos+4] != struct.pack('>I', DTB_MAGIC):
                boundary = round_up(pos, page)
                if boundary < size and data[boundary:boundary+4] == struct.pack('>I', DTB_MAGIC):
                    if any(data[pos:boundary]):
                        gate.fail('nonzero bytes between appended FDTs')
                        break
                    pos = boundary
        rep['appended_dtb_count'] = len(found)
        rep['appended_dtb_entries'] = [{'offset': p, 'size': len(b),
              'sha256': hashlib.sha256(b).hexdigest()} for p, b in found]
        if not found:
            gate.fail('no valid appended BOOT FDT')
        elif len(found) > 1 and selected_appended_idx is None:
            gate.fail('%d appended DTBs, but bootloader-selected index is unproven' % len(found))
        elif selected_appended_idx is not None and not (0 <= selected_appended_idx < len(found)):
            gate.fail('selected appended DTB index %d absent' % selected_appended_idx)
        else:
            idx = selected_appended_idx if selected_appended_idx is not None else 0
            rep['selected_appended_dtb_index'] = idx
            rep['dtb_offset'], chosen = found[idx]
            rep['dtb_size'] = len(chosen)
            rep['dtb_sha256'] = hashlib.sha256(chosen).hexdigest()
            if expected.get('dtb') and rep['dtb_sha256'] != expected['dtb']:
                gate.fail('selected appended DTB member SHA-256 mismatch')
            for prop in (b'linux,initrd-start', b'linux,initrd-end'):
                if prop in chosen:
                    gate.warn('appended FDT has bootloader-initialized %s; validate merged tree'
                              % prop.decode())
            try:
                check_dtb(chosen, gate)
            except (ValueError, struct.error, IndexError) as e:
                gate.fail('existing NFC protection could not parse appended DTB: %s' % e)
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
    ap.add_argument('--expect-boot-sha256')
    ap.add_argument('--expect-kernel-sha256')
    ap.add_argument('--expect-ramdisk-sha256')
    ap.add_argument('--expect-dtb-sha256')
    ap.add_argument('--selected-appended-dtb-index', type=int)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    overall = 0
    reports = []
    for path in args.images:
        gate = Gate()
        try:
            rep = inspect(path, args.partition_bytes, gate, expected={
                'boot': args.expect_boot_sha256,
                'kernel': args.expect_kernel_sha256,
                'ramdisk': args.expect_ramdisk_sha256,
                'dtb': args.expect_dtb_sha256,
            }, selected_appended_idx=args.selected_appended_dtb_index)
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
