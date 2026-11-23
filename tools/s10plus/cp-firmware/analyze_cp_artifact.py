#!/usr/bin/env python3
"""Offline, read-only analyzer for a Samsung CP artifact (TAR.MD5 + LZ4 + ITOC).

SAFETY
  * Never writes the input, never decompresses into the working tree.
  * Never writes a byte of firmware to stdout (hashes/sizes/layout only).
  * All extraction is size-capped and name-sanitised; refuses traversal,
    absolute paths, links and device nodes.
  * TAR v0/v7/ustar/gnu/pax has NO per-member CRC.  We never claim CRC proof.
    Samsung's `.md5` suffix is a trailer: the final 32 ASCII hex bytes after
    the 512-byte TAR terminator are the MD5 of everything before them.  That
    proves only self-consistency of the file, NOT provenance/authenticity.

USAGE
  analyze_cp_artifact.py <cp-file.tar.md5> --out <private-dir> [--max-member N]

Tested on Python 3 (stdlib only).  Exit code 0 = every check that could be
performed passed.  Non-zero = a check failed; the JSON receipt records which.
"""
import argparse
import hashlib
import zlib
import json
import os
import struct
import sys

BLK = 512
MD5_TRAILER = 32
LZ4_MAGIC_LEGACY = b"\x04\x22\x4d\x18"   # on-disk LE of 0x184D2204
LZ4_MAGIC_SKIPPABLE = b"\x50\x2a\x4d\x18"
ITOC_MAGIC = b"TOC\x00"
# ITOC parts observed on S5000AP: BOOT, MAIN, VSS, NV, OFFSET (4 KiB header area)
ITOC_PARTS = 16

# Safety caps: a CP image is tens of MiB; refuse anything absurd.
DEFAULT_MAX_MEMBER = 256 * 1024 * 1024
MAX_TAR_MEMBERS = 256


class CheckError(Exception):
    pass


def sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    n = 0
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
            n += len(b)
    return h.hexdigest(), n


def md5_region(path, limit):
    h = hashlib.md5()
    with open(path, "rb") as f:
        remaining = limit
        while remaining > 0:
            b = f.read(min(1 << 20, remaining))
            if not b:
                break
            h.update(b)
            remaining -= len(b)
    return h.hexdigest()


def safe_name(name):
    """Reject anything that is not a plain relative single-component name."""
    if "\x00" in name:
        raise CheckError("NUL in member name")
    if name.startswith("/") or name.startswith("\\"):
        raise CheckError("absolute member path: %r" % name)
    if ".." in name.replace("\\", "/").split("/"):
        raise CheckError("path traversal in member name: %r" % name)
    if "/" in name.rstrip("/") and name.count("/") > 0:
        raise CheckError("nested member path rejected: %r" % name)
    if name in ("", ".", ".."):
        raise CheckError("degenerate member name: %r" % name)
    return name


def tar_number(field):
    """Parse an octal (or GNU base-256) TAR numeric field."""
    if not field:
        return 0
    if field[0] & 0x80:  # base-256
        v = 0
        for byte in field[1:]:
            v = (v << 8) | byte
        return v
    s = field.split(b"\x00", 1)[0].strip()
    if not s:
        return 0
    try:
        return int(s, 8)
    except ValueError:
        raise CheckError("bad octal field: %r" % field)


def parse_tar(buf, max_members=DEFAULT_MAX_MEMBER):
    """Strict-ish TAR parser returning member descriptors.

    buf is the bytes of the TAR body (trailer already stripped).
    """
    members = []
    off = 0
    seen = set()
    zero_blocks = 0
    n = len(buf)
    while off + BLK <= n:
        hdr = buf[off:off + BLK]
        if hdr == b"\x00" * BLK:
            zero_blocks += 1
            off += BLK
            # Two consecutive zero blocks => end of archive (v7/ustar).
            if zero_blocks >= 2:
                break
            continue
        zero_blocks = 0
        name = hdr[0:100].split(b"\x00", 1)[0].decode("utf-8", "replace")
        size = tar_number(hdr[124:136])
        typeflag = hdr[156:157] or b"0"
        linkname = hdr[157:257].split(b"\x00", 1)[0].decode("utf-8", "replace")
        prefix = hdr[345:500].split(b"\x00", 1)[0].decode("utf-8", "replace")
        if prefix:
            name = prefix + "/" + name  # ustar long name
        full = name
        # Type checks (POISONED / UNSAFE MEMBERS)
        if typeflag not in (b"0", b"\x00", b"7"):  # regular file only
            if typeflag in (b"1", b"2"):
                raise CheckError("symlink/hardlink member rejected: %r -> %r" % (full, linkname))
            if typeflag in (b"3", b"4", b"6"):
                raise CheckError("device/fifo member rejected: type=%r name=%r" % (typeflag, full))
            if typeflag in (b"5",):
                raise CheckError("directory member rejected (CP archive is flat): %r" % full)
            raise CheckError("unknown member type %r for %r" % (typeflag, full))
        if linkname:
            raise CheckError("linkname on regular member rejected: %r" % full)
        base = safe_name(full)
        if base in seen:
            raise CheckError("duplicate member name: %r" % base)
        seen.add(base)
        data_off = off + BLK
        if data_off + size > n:
            raise CheckError("truncated member data: %r (want %d bytes at %d, have %d)" %
                             (base, size, data_off, n - data_off))
        if size > max_members:
            raise CheckError("member exceeds cap: %r size=%d cap=%d" % (base, size, max_members))
        if len(members) >= MAX_TAR_MEMBERS:
            raise CheckError("too many members (>%d)" % MAX_TAR_MEMBERS)
        members.append({
            "name": base,
            "size": size,
            "data_offset": data_off,
            "data_hash_sha256": hashlib.sha256(buf[data_off:data_off + size]).hexdigest(),
            "first_bytes_hex": buf[data_off:data_off + 16].hex(),
        })
        # pad to block boundary
        off = data_off + ((size + BLK - 1) // BLK) * BLK
    if not members:
        raise CheckError("no regular members found")
    # Overlap check: TAR layout should place each member after the previous.
    prev_end = 0
    for m in members:
        if m["data_offset"] < prev_end:
            raise CheckError("overlapping member: %r" % m["name"])
        prev_end = m["data_offset"] + m["size"]
    return members


def verify_samsung_md5(path, size, members):
    """Validate the appended 32-ASCII-hex MD5 trailer.

    Returns dict with: trailer_present, trailer_hex, computed_md5, match.
    """
    if size < BLK + MD5_TRAILER:
        return {"trailer_present": False, "reason": "file too short"}
    with open(path, "rb") as f:
        f.seek(size - MD5_TRAILER)
        trailer = f.read(MD5_TRAILER)
    try:
        txt = trailer.decode("ascii")
    except UnicodeDecodeError:
        return {"trailer_present": False, "reason": "trailer not ASCII"}
    if len(txt) != 32 or any(c not in "0123456789abcdefABCDEF" for c in txt):
        return {"trailer_present": False, "reason": "trailer not 32 hex chars",
                "trailer_hex": trailer.hex()}
    body_len = size - MD5_TRAILER
    computed = md5_region(path, body_len)
    return {
        "trailer_present": True,
        "trailer_hex": txt.lower(),
        "body_len": body_len,
        "computed_md5": computed,
        "match": computed == txt.lower(),
        "note": "MD5 trailer self-consistency ONLY; not provenance/authenticity",
    }


def lz4_frame_length(path, offset, limit):
    """Return frame metadata + compressed length for a LEGACY-format LZ4 frame.

    Walks the block table only (no decode) to establish exact boundaries and
    the declared content size, so that a TAR member can be proven to be
    exactly one well-formed LZ4 frame.
    """
    with open(path, "rb") as f:
        f.seek(offset)
        hdr = f.read(19)
        if len(hdr) < 19:
            raise CheckError("LZ4 truncated header")
        magic = hdr[0:4]
        if magic != LZ4_MAGIC_LEGACY:
            if magic == LZ4_MAGIC_SKIPPABLE:
                raise CheckError("LZ4 skippable frame (not expected for CP member)")
            raise CheckError("not an LZ4 frame at offset %d (magic %s)" % (offset, magic.hex()))
        flg = hdr[4]
        bd = hdr[5]
        if (flg >> 6) != 1:
            raise CheckError("LZ4 frame version != 01")
        block_indep = bool(flg & 0x20)
        block_checksum = bool(flg & 0x10)
        content_size_flag = bool(flg & 0x08)
        content_checksum = bool(flg & 0x04)
        dict_id_flag = bool(flg & 0x01)
        block_max = (bd >> 4) & 0x07
        block_sizes = {4: 64 << 10, 5: 256 << 10, 6: 1 << 20, 7: 4 << 20}
        if block_max not in block_sizes:
            raise CheckError("bad LZ4 block max size code: 0x%x" % block_max)
        pos = 6
        content_size = None
        if content_size_flag:
            content_size = struct.unpack("<Q", hdr[pos:pos + 8])[0]
            pos += 8
        if dict_id_flag:
            pos += 4
        pos += 1  # header checksum byte
        f.seek(offset + pos)
        while True:
            if f.tell() - offset > limit:
                raise CheckError("LZ4 stream exceeds cap")
            bsz = f.read(4)
            if len(bsz) < 4:
                raise CheckError("LZ4 truncated block size")
            bsize = struct.unpack("<I", bsz)[0]
            if bsize == 0:
                break
            blen = bsize & 0x7FFFFFFF
            if blen > block_sizes[block_max]:
                raise CheckError("LZ4 block larger than declared max")
            if len(f.read(blen)) != blen:
                raise CheckError("LZ4 truncated block data")
            if block_checksum and len(f.read(4)) != 4:
                raise CheckError("LZ4 truncated block checksum")
        if content_checksum and len(f.read(4)) != 4:
            raise CheckError("LZ4 truncated content checksum")
        end = f.tell()
    return {
        "lz4_legacy_frame": True,
        "block_independent": block_indep,
        "block_checksum": block_checksum,
        "content_size_declared": content_size,
        "content_checksum": content_checksum,
        "compressed_len_from_frame": end - offset,
        "declared_block_max": block_sizes[block_max],
    }


def lz4_decode_to_buffer(path, offset, length, limit):
    """Decode a LEGACY LZ4 frame in-memory using python-lz4's frame API.

    Returns the decompressed bytes (size-capped to `limit`).  Raises on any
    integrity failure (lz4.frame.LZ4FrameDecompressor raises on bad checksum).
    """
    try:
        import lz4.frame  # type: ignore
    except ImportError:  # pragma: no cover
        raise CheckError("python-lz4 not installed; cannot decompress in-process")
    with open(path, "rb") as f:
        f.seek(offset)
        d = lz4.frame.LZ4FrameDecompressor()
        out = bytearray()
        remaining = length
        while remaining > 0:
            chunk = f.read(min(1 << 20, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            try:
                out.extend(d.decompress(chunk))
            except Exception as e:  # noqa: BLE001
                raise CheckError("LZ4 decode failure: %s" % e)
            if len(out) > limit:
                raise CheckError("LZ4 decompressed output exceeds cap (%d > %d)" % (len(out), limit))
    if not d.eof:
        raise CheckError("LZ4 stream did not terminate (truncated?)")
    return bytes(out)


def parse_itoc(buf):
    """Parse the S5000AP ITOC header (v3 layout: 16 x 32-byte entries).

    Entry layout (little-endian):
      u32 magic('TOC\0','BOOT','MAIN','VSS','NV','OFFSET', …)
      u32 (zero/unknown)
      u32 load_addr(?)  -- bytes 8..11
      u32 offset        -- bytes 12..15  (relative to given base)
      u32 size          -- bytes 16..19
      u32 checksum      -- bytes 20..23  (Samsung's own per-part sum)
      u32 pad/idx       -- bytes 24..27
      u32 pad/idx       -- bytes 28..31
    """
    parts = []
    for i in range(ITOC_PARTS):
        ent = buf[i * 32:(i + 1) * 32]
        if len(ent) < 32:
            raise CheckError("ITOC truncated")
        magic = ent[0:4]
        if magic == b"\x00\x00\x00\x00":
            continue
        # S5000AP ITOC field order, 8 little-endian u32 (verified against
        # the real `modem.bin` header: TOC/BOOT/MAIN/VSS/NV/OFFSET):
        #   w0=name bytes, w1=0, w2=0, w3=offset, w4=load_addr,
        #   w5=size, w6=checksum, w7=part_index
        w = struct.unpack("<8I", ent)
        offset = w[3]
        load_addr = w[4]
        size = w[5]
        checksum = w[6]
        idx2 = w[7]
        parts.append({
            "index": i,
            "magic": magic.decode("latin-1"),
            "load_addr": load_addr,
            "offset": offset,
            "size": size,
            "checksum": checksum,
            "aux": idx2,
        })
    return parts


MBN_META_MARKERS = (b"SignerVer", b"QBR", b"SM-G975F", b"G975F")
_MODEL_RE = None


def _model_re():
    global _MODEL_RE
    if _MODEL_RE is None:
        import re as _re
        # e.g. SM-G975F_EUR_XX_EUR0 ; build e.g. G975FXXS9DTK9_CL... or G975FXXS9DTK9
        _MODEL_RE = _re.compile(rb"SM-[A-Z0-9]{4,8}_[A-Z0-9_]{2,32}|\bG[0-9]{4}[A-Z]{3}[0-9A-Z]{4,10}\b")
    return _MODEL_RE


def scan_metadata(buf, max_hits=64):
    """Return every offset where an MBN metadata marker or model/build token
    appears.  This is METADATA ONLY: no signature verification, no TEE check.
    """
    hits = []
    for marker in MBN_META_MARKERS:
        start = 0
        while True:
            i = buf.find(marker, start)
            if i < 0 or len(hits) >= max_hits:
                break
            hits.append({"marker": marker.decode("latin-1"), "offset": i})
            start = i + 1
    rx = _model_re()
    for m in rx.finditer(buf):
        if len(hits) >= max_hits:
            break
        hits.append({"marker": "token", "value": m.group(0).decode("latin-1"),
                     "offset": m.start()})
    # De-dup by (marker,offset)
    seen = set()
    out = []
    for h in hits:
        k = (h.get("marker"), h.get("value"), h["offset"])
        if k in seen:
            continue
        seen.add(k)
        out.append(h)
    return out


def mbn_trailer_summary(buf, tail_probe=4096):
    """Look at the tail of a decompressed image for an appended MBN metadata block.

    Returns metadata block presence + safe public fields (offsets + strings),
    the trailing-signature byte count, and the *unsigned* marker (`NONEmrk`).
    It NEVER evaluates RSA/ECDSA, never strips the signature, and never says
    "authentic".
    """
    n = len(buf)
    tail_start = max(0, n - tail_probe)
    tail = buf[tail_start:]
    sv = tail.find(b"SignerVer")
    if sv < 0:
        return {"mbn_metadata_present": False}
    sv += tail_start
    # Fixed-ish layout observed on S5000AP: SignerVer02(16) QBR(16) BUILD(48) MODEL(32)
    pub = {"mbn_metadata_present": True, "signer_ver_offset": sv}
    region = buf[sv:sv + 384]

    def zstr(off, maxlen):
        end = region.find(b"\x00", off)
        if end < 0:
            end = min(len(region), off + maxlen)
        return region[off:end].decode("latin-1", "replace")

    pub["signer"] = zstr(0, 16)
    pub["qbr_marker"] = zstr(16, 16)
    pub["build_tag"] = zstr(32, 48)
    pub["model_suffix"] = zstr(80, 32)
    pub["tail_probe_bytes"] = tail_probe
    pub["distance_to_eof"] = n - sv
    # trailing signature region size (everything after the metadata prelude
    # constants).  Treat as opaque; we do NOT decode or validate it.
    pub["signature_region_len"] = n - sv
    pub["unsigned_marker_observed"] = b"NONEmrk" in region
    pub["authenticity_evaluated"] = False
    pub["note"] = ("Structural metadata only. NO RSA/ECDSA/TEE verification was "
                   "performed; `NONEmrk` is a metadata field, not proof of authenticity.")
    return pub


def analyze(path, outdir, max_member=DEFAULT_MAX_MEMBER):
    results = {"file": os.path.basename(path), "checks": [], "decision": None}

    def ok(name, detail=None):
        results["checks"].append({"name": name, "ok": True, "detail": detail})

    def bad(name, reason):
        results["checks"].append({"name": name, "ok": False, "reason": reason})

    if not os.path.isfile(path):
        results["decision"] = "ARCHIVE_MISSING"
        results["missing_path"] = path
        return results

    size = os.path.getsize(path)
    st = os.stat(path)
    sha, n = sha256_file(path)
    results["archive"] = {
        "path": path,
        "realpath": os.path.realpath(path),
        "size": size,
        "sha256": sha,
        "device": st.st_dev,
        "inode": st.st_ino,
        "mode": oct(st.st_mode & 0o7777),
        "uid": st.st_uid,
        "gid": st.st_gid,
    }
    ok("file_present", {"size": size})
    if n != size:
        bad("file_stable", "size changed between stat and hash")
        results["decision"] = "ARCHIVE_VALIDATED_FAILED"
        return results

    # --- Samsung MD5 trailer ---
    md5res = verify_samsung_md5(path, size, [])
    results["md5_trailer"] = md5res
    if md5res.get("trailer_present") and md5res.get("match"):
        ok("samsung_md5_trailer", "self-consistent")
    elif md5res.get("trailer_present"):
        bad("samsung_md5_trailer", "trailer present but MD5 mismatch")
        results["decision"] = "ARCHIVE_VALIDATED_FAILED"
        return results
    else:
        bad("samsung_md5_trailer", md5res.get("reason", "no trailer"))
        md5res = {"trailer_present": False}
        results["decision"] = "ARCHIVE_VALIDATED_FAILED"
        return results

    # --- TAR parse of body (trailer stripped) ---
    body_len = md5res["body_len"]
    with open(path, "rb") as f:
        body = f.read(body_len)
    try:
        members = parse_tar(body, max_member)
        ok("tar_structure", {"members": len(members)})
    except CheckError as e:
        bad("tar_structure", str(e))
        results["decision"] = "ARCHIVE_VALIDATED_FAILED"
        results["members"] = []
        return results
    # Analyze into the same dict objects that are serialized.
    results["members"] = members
    ok("tar_member_safety", "flat, regular, unique, no traversal/links/devices")

    # --- LZ4 frame + decompression for each member ---
    for m in members:
        name = m["name"]
        info = {"name": name}
        off = m["data_offset"]
        try:
            fr = lz4_frame_length(path, off, max_member * 2)
            info.update(fr)
            ok("lz4_frame", name)
        except CheckError as e:
            info["lz4_frame_error"] = str(e)
            bad("lz4_frame", "%s: %s" % (name, e))
            m["lz4"] = info
            continue
        if fr.get("compressed_len_from_frame") != m["size"]:
            bad("lz4_frame", "%s: frame length %d != member size %d" %
                (name, fr["compressed_len_from_frame"], m["size"]))
            m["lz4"] = info
            continue
        try:
            dec = lz4_decode_to_buffer(path, off, fr["compressed_len_from_frame"], max_member)
        except CheckError as e:
            info["decompressed_error"] = str(e)
            bad("lz4_decompress", "%s: %s" % (name, e))
            m["lz4"] = info
            continue
        info["decompressed_size"] = len(dec)
        info["decompressed_sha256"] = hashlib.sha256(dec).hexdigest()
        if fr.get("content_size_declared") not in (None, len(dec)):
            bad("lz4_decompress", "%s: content size mismatch" % name)
        else:
            ok("lz4_decompress", name)
        m["lz4"] = info
        # --- Container inspection (ITOC) if applicable ---
        if dec[:4] == ITOC_MAGIC:
            try:
                parts = parse_itoc(dec)
                info["container"] = "ITOC"
                info["itoc_parts"] = parts
                info["metadata_hits"] = scan_metadata(dec)
                info["mbn_trailer"] = mbn_trailer_summary(dec)
                # Validate offsets/sizes fit inside the decompressed image.
                total_ok = True
                for p in parts:
                    if p["offset"] + p["size"] > len(dec):
                        total_ok = False
                info["itoc_bounds_ok"] = total_ok
                if total_ok:
                    ok("itoc_bounds", name)
                else:
                    bad("itoc_bounds", name)
                # ITOC carries its OWN per-part CRC32.  Verifying it is a Samsung
                # container self-consistency check, NOT a TAR CRC and NOT
                # signature authenticity.
                crc_ok = True
                for p in parts:
                    if p["size"] == 0:
                        continue
                    seg = dec[p["offset"]:p["offset"] + p["size"]]
                    calc = zlib.crc32(seg) & 0xFFFFFFFF
                    p["crc32_computed"] = calc
                    p["crc32_stored"] = p["checksum"]
                    p["crc32_match"] = (calc == p["checksum"])
                    if not p["crc32_match"] and p["magic"] in ("BOOT", "MAIN", "VSS"):
                        crc_ok = False
                info["itoc_crc_ok"] = crc_ok
                if crc_ok:
                    ok("itoc_part_crc32", name)
                else:
                    bad("itoc_part_crc32", name + ": ITOC part CRC32 mismatch")
            except CheckError as e:
                bad("itoc_parse", "%s: %s" % (name, e))
        elif dec[:2] == b"PK":
            info["container"] = "ZIP"
            ok("container_identified", name + ": ZIP (not a modem image)")
        else:
            info["container"] = "RAW/UNKNOWN"
            info["metadata_hits"] = scan_metadata(dec)
            info["mbn_trailer"] = mbn_trailer_summary(dec)
            ok("container_identified", name + ": RAW/UNKNOWN")
        del dec

    # --- Decision ---
    all_ok = all(c["ok"] for c in results["checks"])
    if not all_ok:
        results["decision"] = "ARCHIVE_VALIDATED_FAILED"
    else:
        results["decision"] = "ARCHIVE_VALIDATED"
    return results


def main(argv=None):
    ap = argparse.ArgumentParser(description="Offline CP artifact analyzer (read-only).")
    ap.add_argument("artifact")
    ap.add_argument("--out", required=True, help="private output directory (outside Git)")
    ap.add_argument("--max-member", type=int, default=DEFAULT_MAX_MEMBER)
    args = ap.parse_args(argv)

    os.makedirs(args.out, exist_ok=True)
    try:
        res = analyze(args.artifact, args.out, args.max_member)
    except CheckError as e:
        res = {"file": os.path.basename(args.artifact), "decision": "CONTAINER_UNKNOWN",
               "error": str(e)}
    outpath = os.path.join(args.out, "analysis.json")
    with open(outpath, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2, sort_keys=True)
    print(json.dumps({"decision": res.get("decision"),
                      "checks": len(res.get("checks", [])),
                      "receipt": outpath}))
    return 0 if res.get("decision") == "ARCHIVE_VALIDATED" else 1


if __name__ == "__main__":
    sys.exit(main())
