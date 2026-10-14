"""Stage the Nuxel initramfs tree and produce boot/initramfs + initramfs.cpio.gz.

The staging directory is assembled from:
  * boot/initramfs/init.sh     -> initramfs /init  (capable of generating bins)
  * images/initramfs/          -> base tree (bin/toybox, base dirs, luks hook)
  * assets/nuxel-boot-animation.mp4 -> /boot/nuxel-boot-animation.mp4
  * a generated RGB565 splash         -> /boot/nuxel-boot-splash.raw
  * kernel modules (optional)        -> /lib/modules/... (from kernel build)

Then the tree is serialised to a deterministic newc cpio archive and gzip'd.

Usage:  python3 images/bootpack/assembler.py --stage <dir> --out <boot.img>
        [--width 720 --height 1280] [--animation <mp4>] [--splash <png>]
        [--modules-dir <dir>] [--no-splash]
"""

import argparse
import io
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cpio_builder import build_cpio, gzip_bytes   # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BASE_TREE = os.path.join(ROOT, "images", "initramfs")
INIT_SHD = os.path.join(ROOT, "boot", "initramfs", "init.sh")
ASSET_ANIM = os.path.join(ROOT, "assets", "nuxel-boot-animation.mp4")
ASSET_WALL = os.path.join(ROOT, "assets", "nuxel-background.png")


def _copy(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)


def make_splash(src_mp4, wall, width, height, out_dir):
    """Generate an RGB565 raw framebuffer splash from the animation's first
    frame (preferred) or the wallpaper fallback.  Returns path or None."""
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "nuxel-boot-splash.raw")
    vf = (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=0x0a1628"
    )
    cmds = []
    if src_mp4 and os.path.isfile(src_mp4):
        cmds.append(["ffmpeg", "-y", "-loglevel", "error", "-i", src_mp4,
                     "-frames:v", "1", "-vf", vf, "-pix_fmt", "rgb565le",
                     "-f", "rawvideo", out])
    if (not os.path.isfile(out)) and wall and os.path.isfile(wall):
        cmds.append(["ffmpeg", "-y", "-loglevel", "error", "-i", wall,
                     "-vf", vf, "-pix_fmt", "rgb565le", "-f", "rawvideo", out])
    if (not os.path.isfile(out)) and wall and os.path.isfile(wall):
        cmds.append(["magick", wall, "-resize", f"{width}x{height}",
                     "-background", "#0a1628", "-gravity", "center",
                     "-extent", f"{width}x{height}", "-depth", "8",
                     "rgb565:" + out])
    # ffmpeg/magick can hang indefinitely in constrained environments (no
    # usable codec/GPU).  Bound every conversion so the initramfs assembles
    # without a generated splash instead of blocking the whole build: on
    # timeout we fall through to the next candidate (wallpaper, then magick),
    # and the caller writes a solid-colour fallback raw splash if all fail.
    splash_timeout = 30  # seconds per conversion (enforced via `timeout -k`)
    kill_after = 5       # SIGKILL grace for `timeout -k`
    # Python-side hard cap: covers D-state children that ignore even SIGKILL.
    # subprocess.run() on timeout kills the direct child and wait()s; if that
    # child were unkillable (e.g. stuck ffmpeg), wait() would block forever.
    # Wrapping in coreutils `timeout` keeps the direct child killable, so the
    # TimeoutExpired path below always returns and the build proceeds.
    backstop = splash_timeout + 15
    timeout_bin = shutil.which("timeout")
    for c in cmds:
        wrapped = c
        if timeout_bin:
            wrapped = [timeout_bin, "-k", str(kill_after),
                       str(splash_timeout)] + c
        try:
            r = subprocess.run(wrapped, capture_output=True, timeout=backstop)
        except FileNotFoundError:
            continue
        except subprocess.TimeoutExpired:
            print(
                f"[assembler] splash command unresponsive after {backstop}s, "
                f"abandoning: {' '.join(c)}",
                file=sys.stderr,
            )
            continue
        if r.returncode == 0 and os.path.isfile(out) and os.path.getsize(out) > 0:
            return out
    return None


def assemble(stage, width=720, height=1280, with_splash=True,
             modules_dir=None, animation=None, wall=None, no_copy=False):
    """Assemble a complete, bootable initramfs tree into *stage*."""
    os.makedirs(stage, exist_ok=True)

    # 1. base tree (toybox, dirs)
    if os.path.isdir(BASE_TREE):
        # copy contents (preserve bin/toybox)
        for root, _dirs, files in os.walk(BASE_TREE):
            rel = os.path.relpath(root, BASE_TREE)
            target = stage if rel == "." else os.path.join(stage, rel)
            os.makedirs(target, exist_ok=True)
            for f in files:
                src = os.path.join(root, f)
                if not os.path.isfile(src):
                    continue
                dst = os.path.join(target, f)
                _copy(src, dst)

    # 2. /init from boot/initramfs/init.sh
    if os.path.isfile(INIT_SHD):
        shutil.copy2(INIT_SHD, os.path.join(stage, "init"))
        os.chmod(os.path.join(stage, "init"), 0o0755)

    # fallback: if we only wind up with a plain shell-less tree, keep it usable
    # (init.sh detects toybox at runtime and wires /bin/sh automatically)
    for sub in ("proc", "sys", "dev", "run", "tmp", "newroot", "etc", "boot", "lib/modules"):
        os.makedirs(os.path.join(stage, sub), exist_ok=True)

    # 3. boot animation into /boot (single-source, build-time copy)
    anim = animation or (ASSET_ANIM if os.path.isfile(ASSET_ANIM) else None)
    if anim and os.path.isfile(anim):
        _copy(anim, os.path.join(stage, "boot", "nuxel-boot-animation.mp4"))

    # 4. RGB565 splash into /boot
    if with_splash:
        wall_src = wall or (ASSET_WALL if os.path.isfile(ASSET_WALL) else None)
        splash = make_splash(anim, wall_src, width, height,
                             os.path.join(stage, "boot"))
        # if generation failed, generate a minimal solid-navy raw splash
        # (RGB565 0x08A5 repeated) so init.sh always has something to draw.
        if not (splash and os.path.isfile(splash)):
            raw = os.path.join(stage, "boot", "nuxel-boot-splash.raw")
            try:
                px = (0x08A5).to_bytes(2, "little")
                with open(raw, "wb") as fh:
                    fh.write(px * (width * height))
            except OSError:
                pass

    # 5. optional kernel modules
    if modules_dir and os.path.isdir(modules_dir):
        dst = os.path.join(stage, "lib", "modules")
        os.makedirs(dst, exist_ok=True)
        for entry in os.listdir(modules_dir):
            src = os.path.join(modules_dir, entry)
            if os.path.isdir(src):
                shutil.copytree(src, os.path.join(dst, entry), dirs_exist_ok=True)
            elif os.path.isfile(src):
                _copy(src, os.path.join(dst, entry))
    return stage


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--width", type=int, default=720)
    ap.add_argument("--height", type=int, default=1280)
    ap.add_argument("--animation")
    ap.add_argument("--splash")
    ap.add_argument("--modules-dir")
    ap.add_argument("--no-splash", action="store_true")
    ap.add_argument("--level", type=int, default=9)
    args = ap.parse_args()

    stage = args.stage
    assemble(stage, width=args.width, height=args.height,
             with_splash=not args.no_splash,
             modules_dir=args.modules_dir,
             animation=args.animation, wall=args.splash)

    buf = io.BytesIO()
    n = build_cpio(stage, buf, fixed_mtime=0)
    raw = buf.getvalue()
    gz = gzip_bytes(raw, args.level)
    with open(args.out, "wb") as fh:
        fh.write(gz)
    print(
        f"initramfs entries={n} raw={len(raw)} gzip={len(gz)} -> {args.out}"
    )


if __name__ == "__main__":
    main()
