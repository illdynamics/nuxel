#!/usr/bin/env python3
"""Compatibility shim for bubblewrap 0.12's --*-fd options on Nuxel 4.14.

bwrap 0.12's --ro-bind-fd/--bind-fd path resolution fails on the Samsung 4.14
kernel ("Can't find source path /proc/self/fd/N": it closes the source fd
before resolving it).  Translate those options to --ro-bind/--bind with the
procfs fd path, which bwrap opens itself and which remains valid here.
The shim only rewrites its own --args payload and execs the real bwrap.
"""
import os, sys

REAL = os.environ.get("NUXEL_BWRAP_REAL", "/usr/libexec/bwrap.real")
argv = sys.argv[1:]
if argv[:1] != ["--args"] or len(argv) < 3:
    os.execv(REAL, [REAL] + argv)

try:
    src_fd = int(argv[1])
except ValueError:
    os.execv(REAL, [REAL] + argv)

data = b""
while True:
    chunk = os.read(src_fd, 65536)
    if not chunk:
        break
    data += chunk
tokens = data.split(b"\x00")
# args files are NUL-separated; a trailing NUL yields an empty final token
if tokens and tokens[-1] == b"":
    tokens = tokens[:-1]
out = []
i = 0
rewrote = 0
keep = []
while i < len(tokens):
    t = tokens[i]
    if t in (b"--ro-bind-fd", b"--bind-fd") and i + 1 < len(tokens):
        fd = tokens[i + 1].decode("ascii", "replace")
        try:
            target = os.readlink("/proc/self/fd/" + fd)
        except OSError:
            target = "/proc/self/fd/" + fd
        out.append(b"--ro-bind" if t == b"--ro-bind-fd" else b"--bind")
        out.append(target.encode())
        i += 2
        rewrote += 1
        continue
    out.append(t)
    i += 1

newfd = os.memfd_create("bwrap-args-compat", 0)
os.write(newfd, b"\x00".join(out) + b"\x00")
os.lseek(newfd, 0, os.SEEK_SET)
os.set_inheritable(newfd, True)
if rewrote:
    sys.stderr.write("nuxel-bwrap-compat: rewrote %d fd-bind options\n" % rewrote)
os.execv(REAL, [REAL, "--args", str(newfd)] + argv[2:])
