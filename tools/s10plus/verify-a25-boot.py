#!/usr/bin/env python3
"""verify-a25-boot.py — FAIL-CLOSED gate for the A25 S10+ BOOT image.

The release workflow must never publish an S10+ boot image that differs from the
one that runs on the handset.  Two properties are what make the hardware image
work at all (docs/s10plus-autonomous-boot-repair/INITRAMFS-DELIVERY-ROOT-CAUSE.md):

  1. the BOOT container's kernel payload is a RAW arm64 Image
     (S-Boot executes a gzip payload as code -> seven silent loads), and
  2. that Image has the initramfs EMBEDDED (CONFIG_INITRAMFS_SOURCE), because the
     bootloader advertises /chosen/linux,initrd-start|end without populating that
     memory, so the container's ramdisk is never executed.

Structure of the checks
  * container structure/limits  -> delegated to the vetted tools/s10plus/verify-boot-image.py
                                   (ANDROID! v1 header, page 2048, sha256, partition slack)
  * raw kernel, no gzip payload -> this script
  * embedded initramfs present and is the SAME archive we built -> this script
  * the loaded ramdisk copy is that same archive -> this script
  * ARM64 / ELF identity of the pinned payloads -> this script

Usage:
  python3 tools/s10plus/verify-a25-boot.py \
      --boot-image build/out/s10plus/nuxel-beyond2lte-boot.img \
      --kernel     build/out/s10plus/Image-A25 \
      --initramfs  build/out/s10plus/debug-candidates/A25/initramfs.cpio \
      --partition-bytes 57671680 \
      --report     build/out/s10plus/a25-boot.report.txt

Exit: 0 = every check passed, 1 = at least one check failed (nothing is reported
      as flashable), 2 = usage error.
"""

import argparse
import hashlib
import io
import lzma
import os
import struct
import subprocess
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
NEWC = os.path.join(HERE, "newc.py")

ARM64_MAGIC = b"ARM\x64"            # at offset 56 of a raw Linux arm64 Image
REQUIRED_MEMBERS = [
    "init",
    "opt/nuxel/nuxel-ui",
    "opt/nuxel/nuxel-console",
    "opt/nuxel/nuxel-anim-player",
    "opt/nuxel/nuxel-postboot.sh",
    "opt/nuxel/libsystemd-shared-258.11-1.fc43.so",
]

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))
    print("  [%s] %s%s" % ("ok" if ok else "FAIL", name, (" — " + detail) if detail else ""))
    return bool(ok)


def sha256(data):
    return hashlib.sha256(data).hexdigest()


# --------------------------------------------------------------------------- #
# initramfs archive helpers
# --------------------------------------------------------------------------- #
sys.path.insert(0, HERE)
import newc  # noqa: E402


def parse_cpio(data):
    """Return {name: (mode, sha256)} for a newc archive, or None if malformed."""
    if not data.startswith(b"070701"):
        return None
    members = {}
    try:
        for off, name, mode, size, dstart, dlen in newc.iter_records(data):
            if name == "TRAILER!!!":
                members["__trailer__"] = True
                break
            members[name] = (mode, sha256(data[dstart:dstart + size]), size)
    except Exception:
        return None
    return members if members.get("__trailer__") else None


def find_embedded_cpio(image):
    """Locate the initramfs the kernel embedded. Returns (offset, members, raw)."""
    attempts = [
        (b"\x1f\x8b\x08", "gzip", lambda d: zlib.decompressobj(16 + zlib.MAX_WBITS).decompress(d)),
        (b"\xfd7zXZ\x00", "xz", lambda d: lzma.LZMADecompressor().decompress(d)),
        (b"(\xb5/\xfd", "zstd", lambda d: __import__("zstandard").ZstdDecompressor().decompress(d, max_output_size=1 << 30)),
    ]
    for magic, label, fn in attempts:
        start = 0
        while True:
            i = image.find(magic, start)
            if i < 0:
                break
            start = i + 1
            try:
                blob = fn(image[i:i + (96 << 20)])
            except Exception:
                continue
            members = parse_cpio(blob)
            if members:
                return i, members, blob, label
    # uncompressed initramfs image (CONFIG_INITRAMFS_COMPRESSION_NONE)
    for i in find_all(image, b"070701"):
        members = parse_cpio(image[i:])
        if members:
            return i, members, image[i:], "none"
    return None, None, None, None


def find_all(hay, needle, limit=8):
    out, start = [], 0
    while len(out) < limit:
        i = hay.find(needle, start)
        if i < 0:
            return out
        out.append(i)
        start = i + 4
    return out


def decompress_ramdisk(blob):
    return lzma.LZMADecompressor().decompress(blob)


# --------------------------------------------------------------------------- #
def main(argv=None):
    ap = argparse.ArgumentParser(prog="verify-a25-boot.py")
    ap.add_argument("--boot-image", required=True)
    ap.add_argument("--kernel", required=True, help="the raw arm64 Image that was packed")
    ap.add_argument("--initramfs", help="the archive that was embedded (identity check)")
    ap.add_argument("--partition-bytes", type=int, default=57671680)
    ap.add_argument("--report", help="write the full report here")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args(argv)

    for f in (a.boot_image, a.kernel):
        if not os.path.isfile(f):
            print("missing file: %s" % f, file=sys.stderr)
            return 2
    if a.initramfs and not os.path.isfile(a.initramfs):
        print("missing file: %s" % a.initramfs, file=sys.stderr)
        return 2

    print("== verify-a25-boot: %s ==" % a.boot_image)
    boot = open(a.boot_image, "rb").read()
    image = open(a.kernel, "rb").read()
    cpio = open(a.initramfs, "rb").read() if a.initramfs else None

    # --- container structure (vetted tool) ---------------------------------
    gate = os.path.join(HERE, "verify-boot-image.py")
    if os.path.isfile(gate):
        proc = subprocess.run([sys.executable, gate, a.boot_image,
                               "--partition-bytes", str(a.partition_bytes), "--quiet"],
                              capture_output=True, text=True)
        check("container: verify-boot-image.py PASS", proc.returncode == 0,
              (proc.stdout + proc.stderr).strip().splitlines()[-1] if (proc.stdout or proc.stderr) else "")
    else:
        check("container: verify-boot-image.py present", False, gate)

    # --- header vs the raw Image we packed ---------------------------------
    magic = boot[:8]
    check("container: ANDROID! magic", magic == b"ANDROID!", repr(magic))
    kernel_size, kernel_addr = struct.unpack_from("<II", boot, 8)
    page_size, field40 = struct.unpack_from("<II", boot, 36)
    check("container: page_size 2048", page_size == 2048, str(page_size))
    check("container: kernel_size == raw Image size", kernel_size == len(image),
          "%d vs %d" % (kernel_size, len(image)))
    check("container: kernel_addr is a real load address", kernel_addr != 0, hex(kernel_addr))

    # --- the kernel payload must be a RAW arm64 Image ----------------------
    payload = boot[2048:2048 + kernel_size]
    check("kernel payload: not gzip (S-Boot executes gzip as code)",
          not payload.startswith(b"\x1f\x8b"), payload[:4].hex())
    check("kernel payload: raw arm64 Image magic at 56",
          payload[56:60] == ARM64_MAGIC, repr(payload[56:60]))
    img_magic = image[56:60]
    check("kernel file: raw arm64 Image magic at 56", img_magic == ARM64_MAGIC, repr(img_magic))

    # --- the initramfs must be INSIDE the kernel ---------------------------
    off, members, blob, how = find_embedded_cpio(payload)
    check("kernel: initramfs embedded (CONFIG_INITRAMFS_SOURCE)", members is not None,
          ("%s at offset %d, %d bytes" % (how, off, len(blob))) if members else
          "no valid newc cpio found inside the kernel Image")
    if members:
        for m in REQUIRED_MEMBERS:
            check("kernel: embedded /%s" % m, m in members,
                  members.get(m, ("",))[1][:16] if m in members else "absent")
        if cpio is not None:
            built = parse_cpio(cpio)
            same = built is not None and all(
                members.get(k, (None, None))[1] == v[1] for k, v in built.items()
                if k != "__trailer__")
            check("kernel: embedded archive == built initramfs (member-by-member)",
                  bool(same), "sha256 %s" % sha256(blob)[:16])
            check("kernel: embedded archive size == built archive size",
                  len(blob) == len(cpio), "%d vs %d" % (len(blob), len(cpio)))

        # the pinned systemd payload must be byte-identical where it matters
        sdl = "opt/nuxel/libsystemd-shared-258.11-1.fc43.so"
        if sdl in members:
            check("kernel: pinned systemd payload sha256",
                  members[sdl][1] == "848149cf4b506aef00c0f777840c8e0b5306b65dcf1ae0a1b8c1a63057b4d981",
                  members[sdl][1][:16])

    # --- the container ramdisk must be that same archive -------------------
    ramdisk_size = struct.unpack_from("<I", boot, 16)[0]
    ramdisk = boot[2048 + ((kernel_size + 2047) // 2048) * 2048:][:ramdisk_size]
    try:
        plain = decompress_ramdisk(ramdisk)
        check("container: ramdisk decompresses (lzma-alone)", True, "%d bytes" % len(plain))
        rmem = parse_cpio(plain)
        check("container: ramdisk is a newc cpio", rmem is not None)
        if rmem and cpio is not None:
            padded = plain[:len(cpio)] == cpio
            tail_zero = set(plain[len(cpio):]) <= {0}
            check("container: ramdisk == built initramfs (+ zero padding)",
                  padded and tail_zero,
                  "payload %d, padding %d" % (len(cpio), len(plain) - len(cpio)))
    except Exception as exc:  # noqa: BLE001
        check("container: ramdisk decompresses (lzma-alone)", False, str(exc))

    # --- partition budget --------------------------------------------------
    check("container: fits the BOOT partition", len(boot) <= a.partition_bytes,
          "%d <= %d (slack %d)" % (len(boot), a.partition_bytes, a.partition_bytes - len(boot)))

    failed = [n for n, ok, _ in results if not ok]
    verdict = "PASS" if not failed else "FAIL"
    lines = [
        "== verify-a25-boot: %s ==" % verdict,
        "boot.img        : %s (%d bytes, sha256 %s)" % (a.boot_image, len(boot), sha256(boot)),
        "kernel Image    : %s (%d bytes, sha256 %s)" % (a.kernel, len(image), sha256(image)),
    ]
    if cpio is not None:
        lines.append("initramfs cpio  : %s (%d bytes, sha256 %s)" % (a.initramfs, len(cpio), sha256(cpio)))
    lines += ["", "checks:"]
    lines += ["  %-6s %s%s" % ("ok" if ok else "FAIL", n, (" — " + d) if d else "") for n, ok, d in results]
    if failed:
        lines += ["", "FAILED: " + ", ".join(failed)]
    report = "\n".join(lines) + "\n"
    if a.report:
        with open(a.report, "w") as fh:
            fh.write(report)
    if not a.quiet:
        print(report, end="")
    if failed:
        print("::error::verify-a25-boot: %d check(s) failed" % len(failed), file=sys.stderr)
        return 1
    print("verify-a25-boot: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
