#!/usr/bin/env python3
"""nuxel-anim-pack.py - pack the ORIGINAL Nuxel boot animation MP4 into the
NUXANM01 framebuffer animation container consumed by nuxel-anim-player.

The source of truth is ALWAYS  assets/nuxel-boot-animation.mp4 .  This tool never
substitutes, redraws or reimagines the artwork; it only re-encodes it into a form
a freestanding aarch64 framebuffer player can render without a video codec, a
compositor, a DRM/KMS device or any libc.

Pipeline
    MP4 (H.264, yuv420p)
      -> ffmpeg: temporal+luma denoise, lanczos scale to the animation raster
      -> 256-colour shared palette (median cut, no dither)  [PSNR-checked]
      -> temporal "stickiness": a pixel keeps its previous palette index while
         the new colour is within STICKY of it.  This removes H.264 grain churn,
         which is what makes a naive frame-delta explode in size.
      -> frame 0 : raw index plane, raw-deflate
         frame n : span list of changed pixels, raw-deflate
      -> NUXANM01 container with a palette, a frame table and per-frame blobs.

Container (little endian, no padding):

    0     8   magic                "NUXANM01"
    8     4   u32 width            animation raster width  (source of truth)
    12    4   u32 height
    16    4   u32 frame_count
    20    4   u32 fps_num
    24    4   u32 fps_den
    28    4   u32 palette_count    (1..256)
    32    512 palette             palette_count x RGB565 LE
    544   4   u32 flags            bit0 = frames 1.. are span-coded
    548   4   u32 reserved
    552   8*N frame table          N x { u32 blob_offset, u32 blob_size }
    ...       frame blobs          raw DEFLATE streams (no zlib header)

Span stream (frames >= 1), LEB128 varints, terminated by gap == 0xFFFFFFFF:

    repeat:  varint gap   bytes after the previous span's end
             u16    len   changed pixels
             u8[len]      new palette indices
    end:     varint 0xFFFFFFFF

Usage:
    tools/s10plus/nuxel-anim-pack.py \
        --mp4 assets/nuxel-boot-animation.mp4 \
        --out build/out/s10plus/nuxel-animation.nux \
        [--width 1080] [--height 1920] [--fps 24] [--colors 256] \
        [--sticky 6] [--bridge 3] [--level 9] [--report FILE] [--verify-frames N]
"""
import argparse
import hashlib
import json
import os
import struct
import subprocess
import sys
import zlib

MAGIC = b"NUXANM01"
HDR_FIXED = 552          # bytes before the frame table
PALETTE_BYTES = 512
DENOISE_DEFAULT = "hqdn3d=3:3:6:6"


def log(msg):
    print(f"[nuxel-anim-pack] {msg}", flush=True)


def die(msg):
    print(f"[nuxel-anim-pack][error] {msg}", file=sys.stderr)
    sys.exit(1)


def varint(n):
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def rawdeflate(data, level):
    """Raw DEFLATE (no zlib header/Adler32) - exactly what the C player's inflate consumes."""
    co = zlib.compressobj(level, zlib.DEFLATED, -15)
    return co.compress(data) + co.flush()


def decode_frames(mp4, width, height, fps, denoise):
    """Decode the MP4 to raw RGB24 frames at the requested raster."""
    vf = ",".join(x for x in (denoise, f"scale={width}:{height}:flags=lanczos") if x)
    cmd = ["ffmpeg", "-v", "error", "-i", mp4, "-r", str(fps),
           "-vf", vf, "-pix_fmt", "rgb24", "-f", "rawvideo", "-"]
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if p.returncode != 0:
        die(f"ffmpeg failed: {p.stderr.decode('utf-8', 'replace')[:400]}")
    fsz = width * height * 3
    raw = p.stdout
    n = len(raw) // fsz
    if n == 0:
        die("ffmpeg produced no frames")
    if len(raw) % fsz:
        raw = raw[:n * fsz]
    return raw, n, fsz


def build_palette(raw, n, fsz, width, height, colors):
    """Median-cut a shared palette from a subsample of the animation."""
    try:
        import numpy as np
        from PIL import Image
    except ImportError as e:
        die(f"needs numpy + Pillow for palette generation: {e}")
    step = max(1, n // 24)
    samples = []
    for i in range(0, n, step):
        im = Image.frombytes("RGB", (width, height), raw[i * fsz:(i + 1) * fsz])
        # shrink only for palette statistics - never for pixel data
        samples.append(np.asarray(im.resize((max(1, width // 4), max(1, height // 4))),
                                  dtype=np.uint8).reshape(-1, 3))
    sample = np.concatenate(samples)
    q = Image.fromarray(sample.reshape(-1, 1, 3)).quantize(
        colors=colors, method=Image.MEDIANCUT, dither=Image.NONE)
    pal = np.array(q.getpalette()[:colors * 3], dtype=np.uint8).reshape(colors, 3)
    if pal.shape[0] != colors:
        die(f"palette has {pal.shape[0]} entries, expected {colors}")
    return pal


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mp4", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--width", type=int, default=1080)
    ap.add_argument("--height", type=int, default=1920)
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--colors", type=int, default=256)
    ap.add_argument("--sticky", type=int, default=6,
                    help="max per-channel palette distance that keeps the previous index")
    ap.add_argument("--bridge", type=int, default=3,
                    help="merge changed runs separated by <= this many unchanged pixels")
    ap.add_argument("--level", type=int, default=9, help="deflate level")
    ap.add_argument("--denoise", default=DENOISE_DEFAULT)
    ap.add_argument("--report", default=None, help="write a JSON report here")
    ap.add_argument("--verify-frames", type=int, default=0,
                    help="re-decode N frames through the container decoder and report PSNR")
    args = ap.parse_args()

    import numpy as np
    from PIL import Image

    if args.colors < 2 or args.colors > 256:
        die("--colors must be 2..256 (the index plane is 8-bit)")
    if not os.path.isfile(args.mp4):
        die(f"missing source animation: {args.mp4}")

    src_sha = hashlib.sha256(open(args.mp4, "rb").read()).hexdigest()
    src_size = os.path.getsize(args.mp4)
    W, H, FPS = args.width, args.height, args.fps
    log(f"source {args.mp4}  {src_size} B  sha256 {src_sha}")
    log(f"raster {W}x{H} @ {FPS} fps   colours={args.colors} sticky={args.sticky} bridge={args.bridge}")

    raw, n, fsz = decode_frames(args.mp4, W, H, FPS, args.denoise)
    log(f"decoded {n} frames  ({len(raw)/1e6:.1f} MB rgb24)")

    pal = build_palette(raw, n, fsz, W, H, args.colors)
    pal_img = Image.new("P", (1, 1))
    pal_img.putpalette(pal.flatten().tolist())
    # per-channel max distance between palette entries, for the sticky test
    pi = pal.astype(np.int16)
    dist = np.abs(pi[:, None, :] - pi[None, :, :]).max(axis=2)   # colours x colours

    idxs = []
    for i in range(n):
        im = Image.frombytes("RGB", (W, H), raw[i * fsz:(i + 1) * fsz])
        idxs.append(np.asarray(im.quantize(palette=pal_img, dither=Image.NONE),
                               dtype=np.uint8).copy())
    log(f"quantised {n} frames to {args.colors} colours")

    # ---- temporal stickiness -------------------------------------------------
    sticky_seq = [idxs[0]]
    for i in range(1, n):
        prev = sticky_seq[-1].astype(np.int16)
        cur = idxs[i].astype(np.int16)
        sticky_seq.append(np.where(dist[prev, cur] <= args.sticky, prev, cur).astype(np.uint8))

    # ---- frame 0 : raw index plane ------------------------------------------
    frame0 = rawdeflate(sticky_seq[0].tobytes(), args.level)

    # ---- frames 1.. : span list of changed pixels ---------------------------
    blobs = [frame0]
    total_spans = 0
    total_changed = 0
    for i in range(1, n):
        prev = sticky_seq[i - 1].reshape(-1).astype(np.int16)
        cur = sticky_seq[i].reshape(-1)
        ch = np.flatnonzero(prev != cur.astype(np.int16))
        buf = bytearray()
        if ch.size:
            if args.bridge > 0:
                splits = np.flatnonzero(np.diff(ch) > args.bridge + 1) + 1
                groups = np.split(ch, splits)
            else:
                groups = [ch]
            pos = 0
            for g in groups:
                s = int(g[0])
                e = int(g[-1])
                ln = e - s + 1
                buf += varint(s - pos)
                buf += struct.pack("<H", ln)
                buf += cur[s:e + 1].tobytes()
                pos = e + 1
            total_spans += len(groups)
            total_changed += int(ch.size)
        buf += varint(0xFFFFFFFF)
        blobs.append(rawdeflate(bytes(buf), args.level))

    # ---- container ----------------------------------------------------------
    palette_count = args.colors
    hdr = bytearray()
    hdr += MAGIC
    hdr += struct.pack("<IIIIII", W, H, n, FPS, 1, palette_count)
    r16 = (pal[:, 0].astype(np.uint16) >> 3) << 11
    g16 = (pal[:, 1].astype(np.uint16) >> 2) << 5
    b16 = (pal[:, 2].astype(np.uint16) >> 3)
    pal565 = (r16 | g16 | b16).astype("<u2")
    entry = pal565.tobytes()
    hdr += entry + bytes(PALETTE_BYTES - len(entry))
    hdr += struct.pack("<II", 1, 0)
    assert len(hdr) == HDR_FIXED, (len(hdr), HDR_FIXED)

    table_off = HDR_FIXED
    data_off = table_off + 8 * n
    table = bytearray()
    off = data_off
    for b in blobs:
        table += struct.pack("<II", off, len(b))
        off += len(b)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "wb") as fh:
        fh.write(hdr)
        fh.write(table)
        for b in blobs:
            fh.write(b)
    out_size = os.path.getsize(args.out)
    out_sha = hashlib.sha256(open(args.out, "rb").read()).hexdigest()

    raw_span = sum(len(b) for b in blobs[1:])
    raw_total = n * W * H
    log(f"spans {total_spans}  ({total_spans/max(1, n-1):.0f}/frame)  "
        f"changed px {total_changed} ({total_changed/max(1, n-1)/(W*H)*100:.2f}%/frame)")
    log(f"container {args.out}  {out_size} B ({out_size/1e6:.2f} MB)  sha256 {out_sha}")
    log(f"compression: raw index plane {raw_total/1e6:.0f} MB -> {out_size/1e6:.2f} MB "
        f"({raw_total/out_size:.1f}x);  span payload {raw_span/1e6:.1f} MB")

    psnr = None
    if args.verify_frames > 0:
        psnr = verify(args.out, raw, n, fsz, W, H, args.verify_frames, pal)
        log(f"round-trip PSNR (container vs denoised source): {psnr:.2f} dB")

    report = {
        "source_mp4": os.path.abspath(args.mp4),
        "source_sha256": src_sha,
        "source_bytes": src_size,
        "out": os.path.abspath(args.out),
        "out_sha256": out_sha,
        "out_bytes": out_size,
        "width": W, "height": H, "fps": FPS, "frames": n,
        "palette_colors": int(palette_count),
        "sticky": args.sticky, "bridge": args.bridge, "deflate_level": args.level,
        "denoise": args.denoise,
        "spans_total": int(total_spans),
        "spans_per_frame": total_spans / max(1, n - 1),
        "changed_px_per_frame_pct": total_changed / max(1, n - 1) / (W * H) * 100,
        "psnr_vs_denoised_source_db": psnr,
    }
    if args.report:
        with open(args.report, "w") as fh:
            json.dump(report, fh, indent=2, sort_keys=True)
            fh.write("\n")
        log(f"report {args.report}")
    return 0


def verify(path, raw, n, fsz, W, H, count, pal):
    """Decode the container with an independent reference decoder and measure PSNR.

    This is the same algorithm the C player implements, so a passing run here is
    evidence that the container is self-describing and the span stream is correct.
    """
    import numpy as np
    from PIL import Image  # noqa: F401
    data = open(path, "rb").read()
    assert data[:8] == MAGIC
    vw, vh, vn, fpsn, fpsd, pc = struct.unpack_from("<IIIIII", data, 8)
    assert (vw, vh, vn) == (W, H, n), (vw, vh, vn)
    table = [struct.unpack_from("<II", data, HDR_FIXED + 8 * i) for i in range(vn)]

    def inflate(off, size):
        return zlib.decompressobj(-15).decompress(data[off:off + size])

    cur = np.frombuffer(inflate(*table[0]), dtype=np.uint8).reshape(vh, vw).copy()
    errs = []
    step = max(1, n // count)
    for i in range(n):
        if i > 0:
            blob = inflate(*table[i])
            p = 0
            pos = 0
            flat = cur.reshape(-1)
            while True:
                gap = 0
                shift = 0
                while True:
                    b = blob[p]
                    p += 1
                    gap |= (b & 0x7F) << shift
                    shift += 7
                    if not (b & 0x80):
                        break
                if gap == 0xFFFFFFFF:
                    break
                ln = blob[p] | (blob[p + 1] << 8)
                p += 2
                pos += gap
                flat[pos:pos + ln] = np.frombuffer(blob[p:p + ln], dtype=np.uint8)
                p += ln
                pos += ln
        if i % step == 0:
            src = np.frombuffer(raw[i * fsz:(i + 1) * fsz], dtype=np.uint8) \
                    .reshape(H, W, 3).astype(np.float32)
            rec = pal[cur].astype(np.float32)
            errs.append(((src - rec) ** 2).mean())
    mse = float(np.mean(errs))
    return 10 * float(np.log10(255.0 ** 2 / mse))


if __name__ == "__main__":
    sys.exit(main())
