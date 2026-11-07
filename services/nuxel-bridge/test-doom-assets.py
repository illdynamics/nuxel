#!/usr/bin/env python3
"""Offline tests for the Nuxel Doom WAD catalogue and stream endpoint."""
import importlib
import os
import struct
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "src"))
import doom_assets  # noqa: E402


def make_wad(path: Path, magic=b"IWAD", marker=b"E1M1"):
    # 12-byte header + one 16-byte directory entry.
    name = marker.ljust(8, b"\0")[:8]
    directory = struct.pack("<ii", 0, 0) + name
    header = magic + struct.pack("<ii", 1, 12)
    path.write_bytes(header + directory + b"payload")


def main():
    passed = failed = 0

    def check(name, cond, detail=""):
        nonlocal passed, failed
        if cond:
            passed += 1
            print("  PASS " + name + ((" — " + detail) if detail else ""))
        else:
            failed += 1
            print("  FAIL " + name + ((" — " + detail) if detail else ""))

    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "doom"
        outside = Path(td) / "outside"
        root.mkdir()
        outside.mkdir()
        make_wad(root / "freedoom1.wad", b"IWAD", b"E1M1")
        make_wad(root / "extra.wad", b"PWAD", b"MAP01")
        make_wad(outside / "escape.wad", b"IWAD", b"E1M1")
        # A symlink inside the allowlist must not expose an outside file.
        try:
            (root / "linked.wad").symlink_to(outside / "escape.wad")
        except OSError:
            pass
        old = doom_assets.ALLOWED_ROOTS
        doom_assets.ALLOWED_ROOTS = (str(root),)
        doom_assets._CACHE.update({"at": 0.0, "items": [], "by_id": {}})
        try:
            cat = doom_assets.public_catalogue()
            ids = {w["file"]: w for w in cat["wads"]}
            check("catalogue finds IWAD and PWAD", "freedoom1.wad" in ids and "extra.wad" in ids)
            check("catalogue omits absolute paths", all("path" not in w for w in cat["wads"]))
            check("IWAD is tagged", "IWAD" in ids["freedoom1.wad"]["tags"])
            check("PWAD is tagged", "PWAD" in ids["extra.wad"]["tags"])
            check("Map01 is recognised", "Doom 2 / Hexen" in ids["extra.wad"]["tags"])
            wid = ids["freedoom1.wad"]["id"]
            data = doom_assets.read_bytes(wid)
            check("stream returns exact WAD bytes", data == (root / "freedoom1.wad").read_bytes())
            check("unknown digest is rejected", doom_assets.read_bytes("0" * 64) is None)
            check("path-like id is rejected", doom_assets.read_bytes(str(root / "freedoom1.wad")) is None)
            check("symlink escape is not catalogued", "linked.wad" not in ids)
        finally:
            doom_assets.ALLOWED_ROOTS = old
            doom_assets._CACHE.update({"at": 0.0, "items": [], "by_id": {}})

    src = (HERE / "src" / "api.py").read_text()
    check("bridge exposes the read-only WAD catalogue", "/api/v1/doom/wads" in src)
    check("bridge streams by digest, not path", "/api/v1/doom/wad" in src and "parse_qs(parsed.query).get('id'" in src)
    check("bridge exposes only the Chocolate Doom native engine",
          "org.nuxel.Doom.Chocolate" in src and
          "org.nuxel.Doom.UZDoom" not in src and
          "org.nuxel.Doom.Crispy" not in src)
    wrapper = (HERE.parent.parent / "tools" / "s10plus" / "a33" / "doom-engines" / "nuxel-doom-engine")
    check("engine wrapper exists", wrapper.is_file())
    if wrapper.is_file():
        text = wrapper.read_text()
        check("wrapper sets the Nuxel Wayland session",
              "WAYLAND_DISPLAY" in text and "XDG_RUNTIME_DIR" in text)
        check("wrapper prefers Freedoom IWADs", "freedoom1.wad" in text and "freedoom2.wad" in text)
        check("wrapper supports nuxel/chocolate/uzdoom/crispy",
              all(k in text for k in ("chocolate", "uzdoom", "crispy")))

    print("\n%d passed, %d failed" % (passed, failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
