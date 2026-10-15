#!/usr/bin/env python3
"""A26 — build the early-boot splash asset from the ORIGINAL animation.

Mission P0: the initramfs currently paints an obsolete diagnostic splash
("nuxel_first_light" -> /opt/nuxel/nuxel-fb-phone) about two seconds before the
real MP4-derived animation starts, which the operator sees as a flash of the old
screen.

The correct way to remove that flash is NOT to draw a *second* piece of art that
merely looks similar: it is to light the panel with **frame 0 of the very
animation container the player is about to run**, using the same palette, the
same raster and the same pixel packing.  Then the handoff is not a transition at
all -- the first frame the player commits is identical to what is already on the
glass, so there is nothing to flash.

So this tool reads `nuxel-animation.nux` (NUXANM01, built by nuxel-anim-pack.py
from assets/nuxel-boot-animation.mp4) and emits a standalone `NUXSPL01` asset:

    0   8   magic           "NUXSPL01"
    8   4   u32 width
    12  4   u32 height
    16  4   u32 palette_count
    20  4   u32 flags         (bit0 = index plane is raw DEFLATE)
    24  4   u32 blob_size
    28  512 palette          palette_count x RGB565 LE  (copied verbatim)
    540 ... index plane      raw DEFLATE of the width*height palette indices

Verification (all offline, no phone needed):
  * the index plane decodes byte-identically to NUXANM01 frame 0;
  * the palette is byte-identical to NUXANM01's;
  * the raster equals the source MP4's frame size, so the aspect ratio and the
    on-screen position of the early frame are the animation's own;
  * ffmpeg independently decodes MP4 frame 0 and the mean absolute error against
    the asset is reported as a cross-check of the pack pipeline (not the truth --
    the container's frame 0 is the truth, because that is what the player shows).
"""
import argparse, hashlib, json, os, struct, subprocess, sys, zlib

MAGIC = b"NUXANM01"
OUT_MAGIC = b"NUXSPL01"


def le32(b, o):
    return struct.unpack_from("<I", b, o)[0]


def read_anim(path):
    d = open(path, "rb").read()
    if d[:8] != MAGIC:
        sys.exit("not a NUXANM01 container: %s" % path)
    w, h, n, fps_num, fps_den, paln = struct.unpack_from("<IIIIII", d, 8)
    pal = d[32:32 + paln * 2]
    flags = le32(d, 544)
    table = 552
    off, size = struct.unpack_from("<II", d, table)
    blob = d[off:off + size]
    idx = zlib.decompress(blob, -15)          # raw DEFLATE
    if len(idx) != w * h:
        sys.exit("frame 0 index plane is %d bytes, expected %d" % (len(idx), w * h))
    return dict(w=w, h=h, frames=n, fps_num=fps_num, fps_den=fps_den,
                palette=pal, paln=paln, index=idx, blob=blob,
                sha=hashlib.sha256(d).hexdigest())


def ffmpeg_frame0(mp4, w, h):
    """Independent cross-check only: decode MP4 frame 0 to rgb24 at w x h."""
    try:
        out = subprocess.run(
            ["ffmpeg", "-v", "error", "-i", mp4, "-vf",
             "select=eq(n\\,0),scale=%d:%d:flags=lanczos" % (w, h),
             "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
            capture_output=True, check=True).stdout
    except Exception as e:
        return None, str(e)
    if len(out) != w * h * 3:
        return None, "ffmpeg returned %d bytes" % len(out)
    return out, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--anim", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--mp4", default=None, help="optional MP4 for the cross-check")
    ap.add_argument("--report", default=None)
    ap.add_argument("--raw-out", default=None,
                    help="also write an UNCOMPRESSED plane (flags=0) for the "
                         "freestanding painter, which has no inflate")
    a = ap.parse_args()

    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    A = read_anim(a.anim)
    blob = zlib.compress(A["index"], 9)
    blob = blob[2:-4] if False else blob          # keep raw-deflate only below

    # emit a raw-DEFLATE stream (no zlib header/trailer), like the container does
    co = zlib.compressobj(9, zlib.DEFLATED, -15)
    raw = co.compress(A["index"]) + co.flush()

    payload = OUT_MAGIC + struct.pack("<IIIIII", A["w"], A["h"], A["paln"], 1,
                                      len(raw), 0)[:24] + A["palette"] + raw
    with open(a.out, "wb") as f:
        f.write(payload)

    # --- verification -------------------------------------------------------
    v = open(a.out, "rb").read()
    assert v[:8] == OUT_MAGIC
    vw, vh, vpaln, vflags, vblob, _r = struct.unpack_from("<IIIIII", v, 8)
    vpal = v[32:32 + vpaln * 2]
    vidx = zlib.decompress(v[32 + vpaln * 2:], -15)
    ok_pal = vpal == A["palette"]
    ok_idx = vidx == A["index"]
    ok_dim = (vw, vh) == (A["w"], A["h"])

    mae = None
    if a.mp4 and os.path.exists(a.mp4):
        rgb, err = ffmpeg_frame0(a.mp4, A["w"], A["h"])
        if rgb:
            pal = [struct.unpack_from("<H", A["palette"], i * 2)[0] for i in range(A["paln"])]
            tot = n = 0
            for i in range(0, len(A["index"]), 997):      # stride-sample
                p = pal[A["index"][i]]
                r5, g6, b5 = (p >> 11) & 31, (p >> 5) & 63, p & 31
                R = r5 * 255 // 31; G = g6 * 255 // 63; B = b5 * 255 // 31
                tot += abs(R - rgb[i * 3]) + abs(G - rgb[i * 3 + 1]) + abs(B - rgb[i * 3 + 2])
                n += 3
            mae = tot / n
        else:
            mae = "unavailable: %s" % err

    if a.raw_out:
        os.makedirs(os.path.dirname(a.raw_out) or ".", exist_ok=True)
        rhdr = OUT_MAGIC + struct.pack("<IIIIII", A["w"], A["h"], A["paln"], 0,
                                       len(A["index"]), 0)
        with open(a.raw_out, "wb") as f:
            f.write(rhdr + A["palette"] + A["index"])
        rv = open(a.raw_out, "rb").read()
        rw, rh, rp, rf, rb, _ = struct.unpack_from("<IIIIII", rv, 8)
        assert (rw, rh, rp, rf) == (A["w"], A["h"], A["paln"], 0)
        assert rv[32 + rp * 2:32 + rp * 2 + rb] == A["index"]
        assert rv[32:32 + rp * 2] == A["palette"]
        print("UNCOMPRESSED_ASSET_OK %s %d bytes" % (a.raw_out, len(rv)))

    rep = dict(source_anim=a.anim, source_anim_sha256=A["sha"], out=a.out,
               out_bytes=len(payload),
               out_sha256=hashlib.sha256(payload).hexdigest(),
               width=vw, height=vh, palette_colors=vpaln,
               frames_in_source=A["frames"], fps="%d/%d" % (A["fps_num"], A["fps_den"]),
               verify_index_identical=ok_idx, verify_palette_identical=ok_pal,
               verify_raster_matches_animation=ok_dim,
               mae_vs_mp4_frame0_rgb=mae)
    print(json.dumps(rep, indent=2))
    if a.report:
        open(a.report, "w").write(json.dumps(rep, indent=2) + "\n")
    if not (ok_idx and ok_pal and ok_dim):
        sys.exit("VERIFY FAILED")
    print("FIRSTLIGHT_ASSET_OK")


if __name__ == "__main__":
    main()
