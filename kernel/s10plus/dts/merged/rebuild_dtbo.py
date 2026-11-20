#!/usr/bin/env python3
import struct, os

MAGIC = 0xd7b7ab1e
PAGE = 2048

# Read existing partition
src = open("dtbo-sda13.img","rb").read()
total,hs,es,cnt,off,ps,ver = struct.unpack(">IIIIIII", src[4:32])

entries = []  # list of (size, blob, id, rev, c0,c1,c2,c3)
for i in range(cnt):
    e = src[32+i*32:32+(i+1)*32]
    size,doff,id,rev,c0,c1,c2,c3 = struct.unpack(">IIIIIIII", e)
    blob = src[doff:doff+size]
    entries.append([size, blob, id, rev, c0,c1,c2,c3])

print("Loaded", cnt, "entries from existing partition")

# Replace entry[9] with merged overlay
merged = open("merged-overlay.dtbo","rb").read()
print("merged-overlay.dtbo size:", len(merged))
entries[9][0] = len(merged)
entries[9][1] = merged

# Build new partition
header_size = 32
entry_table_size = cnt * 32
cur = header_size + entry_table_size
new_entries = []
for size, blob, id_, rev, c0,c1,c2,c3 in entries:
    # 4-byte align
    cur = (cur + 3) & ~3
    off = cur
    new_entries.append((size, off, id_, rev, c0,c1,c2,c3))
    cur += size
    cur = (cur + 3) & ~3  # align next

total_size = cur
total_size = (total_size + PAGE - 1) // PAGE * PAGE  # pad to page (2048)

out = bytearray(total_size)
# header
struct.pack_into(">I", out, 0, MAGIC)
struct.pack_into(">IIIIII", out, 4, total_size, header_size, 32, cnt, header_size, PAGE)
# version already 0
# entry table
for i,(size,off,id_,rev,c0,c1,c2,c3) in enumerate(new_entries):
    struct.pack_into(">IIIIIIII", out, 32+i*32, size, off, id_, rev, c0,c1,c2,c3)
# blobs
for i,(size,off,id_,rev,c0,c1,c2,c3) in enumerate(new_entries):
    out[off:off+size] = entries[i][1]

open("dtbo-new.img","wb").write(out)
print("Wrote dtbo-new.img:", total_size, "bytes")
print("Entry offsets:")
for i,(size,off,id_,rev,c0,c1,c2,c3) in enumerate(new_entries):
    print(f"  [{i}] size={size} off=0x{off:x} hwrev={c0:#x}-{c1:#x}")
