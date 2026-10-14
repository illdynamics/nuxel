"""newc ("070701") cpio archive builder (pure stdlib, deterministic).

Used to assemble the Nuxel initramfs without depending on a host ``cpio``
binary.  Records regular files, directories, symlinks, char/block devices and
FIFOs exactly, and pads to the cpio 512-byte block convention.  Deterministic
for a given staging tree (sorted walk, fixed mtime when requested).
"""

import io
import os
import stat

MAGIC = b"070701"
TRAILER = b"TRAILER!!!"
BLOCK = 512
ALIGN = 4
HDR = 110  # magic(6) + 13 * 8-char fields


def _align(b: io.BytesIO, n: int = ALIGN) -> None:
    while b.tell() % n:
        b.write(b"\x00")


def _f(v) -> bytes:
    return b"%08x" % (v & 0xFFFFFFFF)


class _Node:
    __slots__ = ("name", "mode", "uid", "gid", "nlink", "mtime", "size",
                 "dev_major", "dev_minor", "rdev_major", "rdev_minor",
                 "body", "ftype")

    def __init__(self, path, rel, _ino):
        st = os.lstat(path)
        self.name = rel
        self.mode = st.st_mode
        self.uid = st.st_uid
        self.gid = st.st_gid
        self.nlink = st.st_nlink or 1
        self.mtime = int(st.st_mtime)
        self.dev_major = os.major(st.st_dev)
        self.dev_minor = os.minor(st.st_dev)
        self.rdev_major = 0
        self.rdev_minor = 0
        self.body = b""
        m = self.mode
        if stat.S_ISREG(m):
            self.ftype = b"0"
            with open(path, "rb") as fh:
                self.body = fh.read()
        elif stat.S_ISDIR(m):
            self.ftype = b"4"
        elif stat.S_ISLNK(m):
            self.ftype = b"2"
            self.body = os.readlink(path).encode("utf-8")
        elif stat.S_ISCHR(m):
            self.ftype = b"2"
            self.rdev_major = os.major(st.st_rdev)
            self.rdev_minor = os.minor(st.st_rdev)
        elif stat.S_ISBLK(m):
            self.ftype = b"6"
            self.rdev_major = os.major(st.st_rdev)
            self.rdev_minor = os.minor(st.st_rdev)
        elif stat.S_ISFIFO(m):
            self.ftype = b"1"
        elif stat.S_ISSOCK(m):
            self.ftype = b"s"
        else:
            raise ValueError(f"unsupported file type in initramfs: {rel}")
        self.size = len(self.body) if (stat.S_ISREG(m) or stat.S_ISLNK(m)) else 0


def build_cpio(stage: str, out: io.BytesIO, fixed_mtime: int = None) -> int:
    """Write a newc cpio of *stage* into *out*; returns entry count."""
    import posixpath

    nodes = []

    def _walk(root, rel):
        entries = sorted(os.scandir(root), key=lambda e: (e.name, e.is_dir()))
        dirs = []
        for e in entries:
            child_rel = posixpath.join(rel, e.name)
            st = e.stat(follow_symlinks=False)
            if stat.S_ISDIR(st.st_mode):
                node = _Node(e.path, child_rel, 0)
                nodes.append(node)
                dirs.append((e.path, child_rel))
            else:
                nodes.append(_Node(e.path, child_rel, 0))
        for dp, dr in dirs:
            _walk(dp, dr)

    _walk(stage, "")
    # NOTE: no explicit '.' root entry is emitted.  The Linux kernel's
    # initramfs unpacker and most cpio tools (including macOS/BSD cpio)
    # unpack the root-relative newc entries without needing a '.' record.
    nodes.sort(key=lambda n: n.name)

    checksum = 0
    for i, node in enumerate(nodes, start=1):
        name = node.name.encode("utf-8") + b"\x00"
        namesize = len(name)

        mtime = fixed_mtime if fixed_mtime is not None else node.mtime
        header = (
            MAGIC
            + _f(i)                       # ino
            + _f(node.mode & 0o7777777)  # full mode including S_IFMT type bits
            + _f(node.uid)
            + _f(node.gid)
            + _f(node.nlink)
            + _f(mtime)
            + _f(node.size)
            + _f(node.dev_major)
            + _f(node.dev_minor)
            + _f(node.rdev_major)
            + _f(node.rdev_minor)
            + _f(namesize)
            + _f(0)                       # check field (0 by convention)
        )
        assert len(header) == HDR, f"header length {len(header)}"
        out.write(header)
        out.write(name)
        _align(out)
        if node.body:
            out.write(node.body)
        _align(out)
        for byte in node.body:
            checksum += byte
        checksum += namesize

    # trailer
    trailer_name = TRAILER + b"\x00"
    header = (
        MAGIC
        + _f(len(nodes) + 1) + _f(0) + _f(0) + _f(0) + _f(1) + _f(0)
        + _f(0) + _f(0) + _f(0) + _f(0) + _f(0)
        + _f(len(trailer_name)) + _f(0)
    )
    out.write(header)
    out.write(trailer_name)
    _align(out)

    # pad whole archive to 512
    while (out.tell()) % BLOCK:
        out.write(b"\x00")
    return len(nodes)


def gzip_bytes(data: bytes, level: int = 9) -> bytes:
    import gzip
    return gzip.compress(data, mtime=0, compresslevel=level)
