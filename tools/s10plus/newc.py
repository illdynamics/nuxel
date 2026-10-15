#!/usr/bin/env python3
"""newc.py — dependency-free newc (SVR4 "070701") cpio reader/replacer.

Used by the Nuxel S10+ boot chain because macOS ships no `cpio`.  The kernel's
initramfs parser (`init/initramfs.c`) accepts exactly this format and *requires*
the archive to end with a `TRAILER!!!` record, so every tool here validates the
trailer rather than trusting the file length.

Subcommands
  list    <archive>                    print one line per record
  extract <archive> <name> <outfile>   write one member's bytes to outfile
  replace <archive> <name> <newfile> <out>
                                       rebuild the archive with <name> replaced
                                       by <newfile> (mode forced executable for
                                       regular files named by --mode)
  trailer <archive>                    print the byte offset just past the
                                       TRAILER!!! record (the logical end)
  delete <archive> <out> --name NAME [--name NAME ...]
                                       drop members (and their payloads)
  insert <archive> <out> --after NAME --name NAME --mode OCT
         [--type file|dir|char|block|fifo] [--major N --minor N] [--file PATH]
                                       insert a record immediately after an
                                       existing member (before TRAILER!!!)

Exit codes: 0 ok, 1 malformed archive, 2 usage/IO error.
"""

import os
import sys

MAGIC = b"070701"
MAGIC_CRC = b"070702"
HDR = 110
TRAILER = "TRAILER!!!"

S_IFMT = 0o170000
S_IFREG = 0o100000
S_IFDIR = 0o040000
S_IFLNK = 0o120000


class CpioError(Exception):
    pass


def _align4(n):
    return (n + 3) & ~3


def _fields(hdr):
    if hdr[:6] not in (MAGIC, MAGIC_CRC):
        raise CpioError("bad magic %r" % (hdr[:6],))
    try:
        return [int(hdr[6 + i * 8:6 + (i + 1) * 8], 16) for i in range(13)]
    except ValueError as exc:
        raise CpioError("non-hex header field: %s" % exc)


def parse_header(hdr):
    """Return the 13 numeric header fields of a 110-byte newc header."""
    return _fields(hdr)


def iter_records(data):
    """Yield (offset, name, mode, filesize, data_start, data_len_padded)."""
    off = 0
    seen_trailer = False
    while off + HDR <= len(data):
        hdr = data[off:off + HDR]
        f = _fields(hdr)
        mode, filesize, namesize = f[1], f[6], f[11]
        name_start = off + HDR
        name_end = name_start + namesize
        name = data[name_start:name_end - 1].decode("latin1", "replace")
        data_start = _align4(name_end)
        data_len = _align4(filesize)
        if data_start + data_len > len(data):
            raise CpioError("record %r overruns archive" % name)
        yield off, name, mode, filesize, data_start, data_len
        off = data_start + data_len
        if name == TRAILER:
            seen_trailer = True
            break
    if not seen_trailer:
        raise CpioError("no TRAILER!!! record — archive is truncated")


def logical_end(path):
    data = open(path, "rb").read()
    end = None
    for off, name, mode, filesize, dstart, dlen in iter_records(data):
        end = dstart + dlen
    return end, len(data)


def cmd_list(argv):
    if len(argv) != 1:
        raise SystemExit("usage: newc.py list <archive>")
    data = open(argv[0], "rb").read()
    n = 0
    for off, name, mode, filesize, dstart, dlen in iter_records(data):
        kind = {S_IFREG: "file", S_IFDIR: "dir", S_IFLNK: "link"}.get(mode & S_IFMT, "?")
        print("%08d  %-7s %06o %9d  %s" % (off, kind, mode & 0o7777, filesize, name))
        n += 1
    print("# %d records, logical end %d, file size %d" % (n, logical_end(argv[0])[0], len(data)))
    return 0


def cmd_extract(argv):
    if len(argv) != 3:
        raise SystemExit("usage: newc.py extract <archive> <name> <outfile>")
    data = open(argv[0], "rb").read()
    for off, name, mode, filesize, dstart, dlen in iter_records(data):
        if name == argv[1]:
            if (mode & S_IFMT) != S_IFREG:
                raise SystemExit("member %r is not a regular file" % name)
            open(argv[2], "wb").write(data[dstart:dstart + filesize])
            return 0
    raise SystemExit("member %r not found" % argv[1])


def cmd_trailer(argv):
    if len(argv) != 1:
        raise SystemExit("usage: newc.py trailer <archive>")
    end, size = logical_end(argv[0])
    print(end)
    return 0


def _pack_header(name, ino, mode, nlink, mtime, filesize, devmajor, devminor,
                 rdevmajor, rdevminor, uid=0, gid=0):
    """Serialise a newc header.  Lower-case hex, exactly like GNU cpio, so that
    replacing a member with identical bytes reproduces the archive byte-for-byte."""
    nm = name.encode("latin1") + b"\0"
    fields = [ino, mode, uid, gid, nlink, mtime, filesize, devmajor, devminor,
              rdevmajor, rdevminor, len(nm), 0]
    return MAGIC + b"".join(b"%08x" % (v & 0xFFFFFFFF) for v in fields) + nm


def cmd_replace(argv):
    if len(argv) not in (4, 5):
        raise SystemExit("usage: newc.py replace <archive> <name> <newfile> <out> "
                         "[--mode OCTAL]")
    src, member, newfile, out = argv[:4]
    mode = None
    if len(argv) == 5:
        if not argv[4].startswith("--mode="):
            raise SystemExit("unknown option %r" % argv[4])
        mode = int(argv[4].split("=", 1)[1], 8)
    payload = open(newfile, "rb").read()
    data = open(src, "rb").read()
    chunks = []
    found = False
    for off, name, rmode, filesize, dstart, dlen in iter_records(data):
        if name == TRAILER:
            break
        if name == member:
            found = True
            # Preserve the original metadata (inode, nlink, mtime, dev/rdev) so a
            # replacement with identical bytes reproduces the archive exactly.
            f = parse_header(data[off:off + HDR])
            ino, uid, gid, nlink, mtime = f[0], f[2], f[3], f[4], f[5]
            devmaj, devmin, rdevmaj, rdevmin = f[7], f[8], f[9], f[10]
            newmode = mode if mode is not None else rmode
            newmode = (newmode & ~S_IFMT) | S_IFREG
            if mode is None:
                newmode |= (rmode & 0o111)  # keep the executable bits
            hdr = _pack_header(name, ino, newmode, nlink, mtime, len(payload),
                               devmaj, devmin, rdevmaj, rdevmin, uid, gid)
            chunks.append(hdr.ljust(_align4(len(hdr)), b"\0"))
            chunks.append(payload.ljust(_align4(len(payload)), b"\0"))
        else:
            chunks.append(data[off:dstart + dlen])
    if not found:
        raise SystemExit("member %r not found" % member)
    # Reproduce the source archive's trailer record verbatim when present.
    for off, name, rmode, filesize, dstart, dlen in iter_records(data):
        if name == TRAILER:
            chunks.append(data[off:dstart + dlen])
            break
    else:
        chunks.append(_pack_header(TRAILER, 0, 0, 1, 0, 0, 0, 0, 0, 0))
    blob = b"".join(chunks)
    blob = blob.ljust(_align4(len(blob)), b"\0")
    with open(out, "wb") as fh:
        fh.write(blob)
    end = logical_end(out)[0]
    tmpl = "newc: wrote %s (%d bytes, logical end %d)\n"
    sys.stderr.write(tmpl % (out, len(blob), end))
    return 0


def cmd_insert(argv):
    import argparse
    ap = argparse.ArgumentParser(prog="newc.py insert")
    ap.add_argument("archive")
    ap.add_argument("out")
    ap.add_argument("--after", required=True, help="insert immediately after this member")
    ap.add_argument("--name", required=True)
    ap.add_argument("--mode", required=True, help="octal type+permission bits, e.g. 0100600")
    ap.add_argument("--type", default="file",
                    choices=["file", "dir", "char", "block", "fifo"])
    ap.add_argument("--major", type=int, default=0)
    ap.add_argument("--minor", type=int, default=0)
    ap.add_argument("--file", default=None, help="payload for --type file")
    a = ap.parse_args(argv)

    type_bits = {"file": S_IFREG, "dir": S_IFDIR, "char": 0o020000,
                 "block": 0o060000, "fifo": 0o010000}[a.type]
    mode = int(a.mode, 8)
    mode = (mode & 0o7777) | type_bits
    payload = b""
    if a.type == "file":
        if a.file is None:
            raise SystemExit("--type file needs --file")
        payload = open(a.file, "rb").read()
    rdevmaj, rdevmin = (a.major, a.minor) if a.type in ("char", "block") else (0, 0)

    data = open(a.archive, "rb").read()
    chunks = []
    inserted = False
    nlink = 1 if a.type != "dir" else 2
    for off, name, rmode, filesize, dstart, dlen in iter_records(data):
        if name == TRAILER:
            break
        chunks.append(data[off:dstart + dlen])
        if name == a.after:
            hdr = _pack_header(a.name, 0, mode, nlink, 0, len(payload),
                               0, 0, rdevmaj, rdevmin)
            chunks.append(hdr.ljust(_align4(len(hdr)), b"\0"))
            if payload:
                chunks.append(payload.ljust(_align4(len(payload)), b"\0"))
            inserted = True
    if not inserted:
        raise SystemExit("anchor member %r not found" % a.after)
    for off, name, rmode, filesize, dstart, dlen in iter_records(data):
        if name == TRAILER:
            chunks.append(data[off:dstart + dlen])
            break
    blob = b"".join(chunks)
    blob = blob.ljust(_align4(len(blob)), b"\0")
    with open(a.out, "wb") as fh:
        fh.write(blob)
    end = logical_end(a.out)[0]
    sys.stderr.write("newc: inserted %s after %s -> %s (%d bytes, logical end %d)\n"
                     % (a.name, a.after, a.out, len(blob), end))
    return 0


def cmd_delete(argv):
    import argparse
    ap = argparse.ArgumentParser(prog="newc.py delete")
    ap.add_argument("archive")
    ap.add_argument("out")
    ap.add_argument("--name", action="append", required=True)
    a = ap.parse_args(argv)
    drop = set(a.name)
    data = open(a.archive, "rb").read()
    chunks = []
    removed = []
    for off, name, rmode, filesize, dstart, dlen in iter_records(data):
        if name == TRAILER:
            break
        if name in drop:
            removed.append(name)
            continue
        chunks.append(data[off:dstart + dlen])
    for off, name, rmode, filesize, dstart, dlen in iter_records(data):
        if name == TRAILER:
            chunks.append(data[off:dstart + dlen])
            break
    blob = b"".join(chunks).ljust(4, b"\0")
    blob = blob.ljust(_align4(len(blob)), b"\0")
    open(a.out, "wb").write(blob)
    missing = sorted(drop - set(removed))
    sys.stderr.write("newc: deleted %s%s -> %s (%d bytes)\n"
                     % (removed, (" (absent: %s)" % missing) if missing else "",
                        a.out, len(blob)))
    return 0


COMMANDS = {"list": cmd_list, "extract": cmd_extract, "replace": cmd_replace,
            "trailer": cmd_trailer, "insert": cmd_insert, "delete": cmd_delete}


def main(argv):
    if not argv or argv[0] not in COMMANDS:
        sys.stderr.write(__doc__)
        return 2
    try:
        return COMMANDS[argv[0]](argv[1:])
    except CpioError as exc:
        sys.stderr.write("newc: %s\n" % exc)
        return 1
    except OSError as exc:
        sys.stderr.write("newc: %s\n" % exc)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
