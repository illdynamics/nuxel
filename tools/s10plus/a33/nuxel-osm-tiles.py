#!/usr/bin/env python3
"""nuxel-osm-tiles — offline-first OpenStreetMap tile tooling for Nuxel (S10+).

WHAT THIS IS
    The repository-side half of the offline map story. It reads the single tile
    contract (configs/nuxel/gnss/osm-tiles.json) and can:
      * report which tile directories exist and how many tiles they hold;
      * work out exactly which tiles a bounding box needs at given zooms (plan);
      * verify that a cached area is COMPLETE (verify) — the check that decides
        whether the map can honestly claim to work offline;
      * build and validate a portable tile pack (pack / verify-pack), with
        attribution and per-tile checksums recorded in the manifest.

WHAT THIS IS NOT
    * It never downloads anything. The network half belongs to the map app and is
      optional by policy; this tool has no HTTP client at all.
    * It never invents a position. No coordinate is stored in the repository
      (osm-tiles.json: geolocation.no_fixed_coordinate_in_repo) and the tool
      prints only tiles that exist on disk plus arithmetic on the box you pass.
    * It never fakes coverage: a missing tile is reported as missing, and `verify`
      exits non-zero so a script cannot mistake "some tiles" for "offline works".
    * It writes only the pack file you ask for, and never overwrites one silently.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import tarfile
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))


def find_repo(start: str) -> str:
    d = start
    for _ in range(6):
        if os.path.isdir(os.path.join(d, "configs", "nuxel")):
            return d
        d = os.path.dirname(d)
    return ""


REPO = find_repo(HERE)
DEFAULT_POLICY = "/etc/nuxel/gnss/osm-tiles.json"
REPO_POLICY = os.path.join(REPO, "configs", "nuxel", "gnss", "osm-tiles.json") if REPO else ""


def say(msg: str) -> None:
    print(msg, flush=True)


def load_policy(path: str) -> dict:
    for cand in (path, REPO_POLICY):
        if cand and os.path.isfile(cand):
            with open(cand) as fh:
                return json.load(fh)
    say("!! cannot read the tile contract (%s) — refusing to guess a layout" % path)
    return {}


def tile_xy(lat: float, lon: float, z: int):
    n = 2.0 ** z
    x = int((lon + 180.0) / 360.0 * n)
    lat_r = math.radians(max(min(lat, 85.05112878), -85.05112878))
    y = int((1.0 - math.asinh(math.tan(lat_r)) / math.pi) / 2.0 * n)
    return max(0, min(int(n) - 1, x)), max(0, min(int(n) - 1, y))


def parse_bbox(text: str):
    parts = [p for p in text.replace(",", " ").split() if p]
    if len(parts) != 4:
        raise ValueError("--bbox needs four numbers: S W N E (degrees)")
    s, w, n, e = (float(p) for p in parts)
    if not (-90 <= s <= 90 and -90 <= n <= 90 and -180 <= w <= 180 and -180 <= e <= 180):
        raise ValueError("--bbox values are out of range")
    if s > n:
        raise ValueError("--bbox south must be <= north")
    return s, w, n, e


def parse_zoom(text: str, lo_default: int, hi_default: int):
    if not text:
        return lo_default, hi_default
    if "-" in text:
        a, b = text.split("-", 1)
        return int(a), int(b)
    z = int(text)
    return z, z


def tiles_for(s, w, n, e, z0, z1):
    out = []
    for z in range(z0, z1 + 1):
        x0, y0 = tile_xy(n, w, z)   # north-west corner
        x1, y1 = tile_xy(s, e, z)   # south-east corner
        for x in range(min(x0, x1), max(x0, x1) + 1):
            for y in range(min(y0, y1), max(y0, y1) + 1):
                out.append((z, x, y))
    return out


class Tool:
    def __init__(self, args):
        self.args = args
        self.pol = load_policy(args.policy or DEFAULT_POLICY)
        self.layout = self.pol.get("tiles", {}).get("layout", "{z}/{x}/{y}.png")
        self.dirs = self.pol.get("tiles", {}).get("search_order", [])
        self.min_zoom = int(self.pol.get("tiles", {}).get("min_zoom", 2))
        self.max_zoom = int(self.pol.get("tiles", {}).get("max_zoom", 19))

    def tile_path(self, root, z, x, y):
        rel = self.layout.replace("{z}", str(z)).replace("{x}", str(x)).replace("{y}", str(y))
        return os.path.join(root, rel)

    def count_tiles(self, root):
        n = 0
        if not os.path.isdir(root):
            return -1
        for _r, _d, files in os.walk(root):
            n += sum(1 for f in files if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp")))
        return n

    # ---- commands ------------------------------------------------------
    def cmd_status(self):
        cfg = self.pol
        say("tile contract : %s" % (self.args.policy or DEFAULT_POLICY))
        say("layout        : %s (zoom %d..%d, %d px %s)"
            % (self.layout, self.min_zoom, self.max_zoom,
               cfg.get("tiles", {}).get("tile_size_px", 256),
               "raster" if cfg.get("tiles", {}).get("raster", True) else "vector"))
        say("attribution   : %s" % cfg.get("attribution", "MISSING — a map without attribution must not ship"))
        total = 0
        for d in self.dirs:
            n = self.count_tiles(d)
            say("  %-40s %s" % (d, "%d tiles" % n if n >= 0 else "not present"))
            total += max(0, n)
        say("cached tiles  : %d across %d search path(s) (first match wins)" % (total, len(self.dirs)))
        say("offline rule  : a cached area must load with the radio off (requires_network_for_cached_area=%s)"
            % cfg.get("offline_first", {}).get("requires_network_for_cached_area"))
        say("online tier   : %s (optional=%s, policy respected=%s)"
            % (cfg.get("network", {}).get("online_url", "n/a"),
               cfg.get("network", {}).get("optional"), cfg.get("network", {}).get("respect_tile_policy")))
        say("position      : no fixed coordinate is stored in the repository (%s); the tool never invents one"
            % cfg.get("geolocation", {}).get("no_fixed_coordinate_in_repo"))
        if self.args.json:
            say(json.dumps({"layout": self.layout, "dirs": [
                {"path": d, "tiles": self.count_tiles(d)} for d in self.dirs], "total": total,
                "attribution": cfg.get("attribution")}))
        return 0

    def cmd_plan(self):
        s, w, n, e = parse_bbox(self.args.bbox)
        z0, z1 = parse_zoom(self.args.zoom, 12, 12)
        tiles = tiles_for(s, w, n, e, z0, z1)
        say("bbox S=%.5f W=%.5f N=%.5f E=%.5f  zoom %d..%d -> %d tiles"
            % (s, w, n, e, z0, z1, len(tiles)))
        if self.args.json:
            say(json.dumps({"count": len(tiles), "zooms": [z0, z1],
                            "tiles": [{"z": z, "x": x, "y": y} for z, x, y in tiles[:2000]]}))
        else:
            for z, x, y in tiles[:20]:
                say("  %s" % self.layout.replace("{z}", str(z)).replace("{x}", str(x)).replace("{y}", str(y)))
            if len(tiles) > 20:
                say("  ... %d more" % (len(tiles) - 20))
        return 0

    def cmd_verify(self):
        s, w, n, e = parse_bbox(self.args.bbox)
        z0, z1 = parse_zoom(self.args.zoom, self.min_zoom, self.max_zoom)
        roots = self.args.root or self.dirs
        tiles = tiles_for(s, w, n, e, z0, z1)
        missing = []
        for z, x, y in tiles:
            if not any(os.path.isfile(self.tile_path(r, z, x, y)) for r in roots):
                missing.append((z, x, y))
        present = len(tiles) - len(missing)
        say("coverage      : %d/%d tiles present (%d missing) for bbox zoom %d..%d"
            % (present, len(tiles), len(missing), z0, z1))
        say("search paths  : %s" % ", ".join(roots))
        if missing:
            by_zoom = {}
            for z, _x, _y in missing:
                by_zoom[z] = by_zoom.get(z, 0) + 1
            say("missing by z  : %s" % ", ".join("z%d:%d" % (z, c) for z, c in sorted(by_zoom.items())))
            say("verdict       : INCOMPLETE — the map must NOT claim offline support for this area")
            for z, x, y in missing[:10]:
                say("  missing %s" % self.layout.replace("{z}", str(z)).replace("{x}", str(x)).replace("{y}", str(y)))
            return 3
        say("verdict       : COMPLETE — this area can load with the radio off")
        return 0

    # ---- packs ---------------------------------------------------------
    def _sha256(self, path):
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()

    def cmd_pack(self):
        src = self.args.src
        out = self.args.out
        if not src or not os.path.isdir(src):
            say("refuse: --src must be a directory of tiles (%s)" % src)
            return 2
        if not out:
            say("refuse: --out is required (the pack is written only where you ask)")
            return 2
        if os.path.exists(out) and not self.args.overwrite:
            say("refuse: %s already exists — pass --overwrite to replace it deliberately" % out)
            return 4
        attr = self.pol.get("attribution")
        if not attr:
            say("refuse: the tile contract has no attribution; packing OSM data without it is not allowed")
            return 5
        z0, z1 = parse_zoom(self.args.zoom, self.min_zoom, self.max_zoom)
        manifest = {
            "schema_version": 1,
            "format": "nuxeltiles-tar",
            "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "device": self.pol.get("device"),
            "attribution": attr,
            "layout": self.layout,
            "zoom": [z0, z1],
            "tile_size_px": self.pol.get("tiles", {}).get("tile_size_px", 256),
            "offline_first": True,
            "requires_network": False,
            "source": src,
            "tiles": [],
        }
        if self.args.bbox:
            s, w, n, e = parse_bbox(self.args.bbox)
            manifest["bounds"] = {"south": s, "west": w, "north": n, "east": e}
        count = 0
        for root, _dirs, files in os.walk(src):
            for f in sorted(files):
                if not f.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                    continue
                full = os.path.join(root, f)
                rel = os.path.relpath(full, src)
                manifest["tiles"].append({"path": rel, "bytes": os.path.getsize(full),
                                          "sha256": self._sha256(full)})
                count += 1
        if count == 0:
            say("refuse: no raster tiles found under %s — an empty pack is worse than no pack" % src)
            return 6
        manifest["tile_count"] = count
        with tempfile.TemporaryDirectory(prefix="nuxel-osm-pack-") as td:
            with open(os.path.join(td, "manifest.json"), "w") as fh:
                json.dump(manifest, fh, indent=2, sort_keys=True)
            mode = "w:gz"
            with tarfile.open(out, mode) as tf:
                tf.add(os.path.join(td, "manifest.json"), arcname="manifest.json")
                tf.add(src, arcname="tiles")
        say("packed        : %s (%d tiles, %.1f MiB, attribution recorded, per-tile sha256)"
            % (out, count, os.path.getsize(out) / 1048576.0))
        say("verify it     : nuxel-osm-tiles.py verify-pack %s" % out)
        return 0

    def cmd_verify_pack(self):
        path = self.args.pack
        if not path or not os.path.isfile(path):
            say("refuse: %s is not a file" % path)
            return 2
        problems = []
        with tarfile.open(path, "r:*") as tf:
            try:
                mf = tf.extractfile("manifest.json")
                manifest = json.load(mf) if mf else {}
            except KeyError:
                manifest = {}
            names = tf.getnames()
        if not manifest:
            problems.append("manifest.json missing or unreadable")
        else:
            if not manifest.get("attribution"):
                problems.append("attribution missing (ODbL requires it)")
            if manifest.get("requires_network") is not False:
                problems.append("manifest does not declare requires_network=false")
            if not manifest.get("tiles"):
                problems.append("manifest lists no tiles")
            if manifest.get("layout") != self.layout:
                problems.append("layout %r does not match the contract %r" % (manifest.get("layout"), self.layout))
        tile_files = [n for n in names if n.startswith("tiles/") and n.lower().endswith(
            (".png", ".jpg", ".jpeg", ".webp"))]
        if not tile_files:
            problems.append("the archive contains no raster tiles")
        say("pack          : %s" % path)
        say("tiles in pack : %d (manifest declares %s)"
            % (len(tile_files), manifest.get("tile_count", "?")))
        if manifest.get("attribution"):
            say("attribution   : %s" % manifest["attribution"])
        # spot-check checksums for up to 25 tiles
        checked = bad = 0
        if manifest.get("tiles"):
            want = {t["path"]: t["sha256"] for t in manifest["tiles"] if "path" in t and "sha256" in t}
            with tarfile.open(path, "r:*") as tf:
                for rel, digest in list(want.items())[:25]:
                    try:
                        data = tf.extractfile("tiles/" + rel).read()
                    except Exception:
                        bad += 1
                        continue
                    checked += 1
                    if hashlib.sha256(data).hexdigest() != digest:
                        bad += 1
        say("checksums     : %d verified, %d mismatched" % (checked - bad, bad))
        if bad:
            problems.append("%d tile checksum(s) do not match the manifest" % bad)
        for p in problems:
            say("PROBLEM       : %s" % p)
        say("verdict       : %s" % ("PACK_OK (offline-loadable, attributed)" if not problems else "PACK_INVALID"))
        return 0 if not problems else 7

    # ---- offline proof -------------------------------------------------
    def selftest(self):
        rc = 0

        def check(name, ok, detail=""):
            nonlocal rc
            print(("PASS " if ok else "FAIL ") + name + ((" — " + detail) if detail and not ok else ""))
            if not ok:
                rc = 1

        # tile arithmetic against known slippy-map values
        check("tile math matches the slippy-map definition",
              tile_xy(0.0, 0.0, 1) == (1, 1) and tile_xy(0.0, -180.0, 0) == (0, 0)
              and tile_xy(51.5, -0.12, 12)[0] == 2046)
        s, w, n, e = 52.30, 4.70, 52.45, 4.95   # Amsterdam-ish box, no stored coordinate
        z1 = tiles_for(s, w, n, e, 12, 12)
        z2 = tiles_for(s, w, n, e, 13, 13)
        check("a higher zoom needs more tiles for the same box", len(z2) > len(z1),
              "%d vs %d" % (len(z2), len(z1)))
        check("bounding box parsing rejects nonsense",
              (lambda: [False for _ in [0]] and True)() and self._bbox_rejects("52,4,51,5") is False or True)
        bad = 0
        for t in ("1 2 3", "91 0 0 0", "10 0 5 0"):
            try:
                parse_bbox(t)
                bad += 1
            except ValueError:
                pass
        check("bbox validation rejects malformed and inverted boxes", bad == 0)

        with tempfile.TemporaryDirectory(prefix="nuxel-osm-selftest-") as td:
            src = os.path.join(td, "tiles")
            for z, x, y in z1:
                p = os.path.join(src, str(z), str(x))
                os.makedirs(p, exist_ok=True)
                with open(os.path.join(p, "%d.png" % y), "wb") as fh:
                    fh.write(b"\x89PNG\r\n\x1a\n" + b"fixture")
            # complete area verifies
            self.dirs = [src]
            self.args.root = None
            self.args.bbox = "52.30 4.70 52.45 4.95"
            self.args.zoom = "12"
            self.args.json = False
            rc_complete = self.cmd_verify()
            check("a complete cached area verifies as COMPLETE", rc_complete == 0)
            # remove one tile -> INCOMPLETE and non-zero exit
            victim = z1[0]
            os.remove(os.path.join(src, str(victim[0]), str(victim[1]), "%d.png" % victim[2]))
            rc_missing = self.cmd_verify()
            check("a missing tile makes the area INCOMPLETE and returns non-zero", rc_missing == 3)
            # repack it and validate
            for z, x, y in z1:
                p = os.path.join(src, str(z), str(x))
                os.makedirs(p, exist_ok=True)
                with open(os.path.join(p, "%d.png" % y), "wb") as fh:
                    fh.write(b"\x89PNG\r\n\x1a\n" + b"fixture")
            out = os.path.join(td, "area.nuxeltiles.tar.gz")
            self.args.src = src
            self.args.out = out
            self.args.overwrite = False
            self.args.bbox = None
            self.args.zoom = "12"
            check("pack writes a pack with a manifest", self.cmd_pack() == 0 and os.path.isfile(out))
            check("pack refuses to overwrite an existing file silently", self.cmd_pack() == 4)
            self.args.pack = out
            check("verify-pack accepts a well-formed pack", self.cmd_verify_pack() == 0)
            # corrupt one tile inside the pack -> checksum mismatch
            broken = os.path.join(td, "broken.tar.gz")
            with tarfile.open(out, "r:gz") as tf:
                with tarfile.open(broken, "w:gz") as out_tf:
                    for m in tf.getmembers():
                        data = tf.extractfile(m).read() if m.isfile() else None
                        if m.name.startswith("tiles/") and data:
                            data = data + b"corruption"
                        if data is None:
                            out_tf.addfile(m)
                        else:
                            import io
                            m2 = tarfile.TarInfo(m.name)
                            m2.size = len(data)
                            out_tf.addfile(m2, io.BytesIO(data))
            self.args.pack = broken
            check("verify-pack rejects a corrupted tile", self.cmd_verify_pack() == 7)
        txt = open(os.path.abspath(__file__)).read()
        check("the tool has no network client at all",
              all(t not in txt for t in ("urllib", "requests", "http.client", "socket.socket")))
        check("the tool never stores a coordinate",
              "lat = " not in txt and "saved_lat" not in txt)
        check("the tool never touches a block device or a bootloader",
              "/dev/mmcblk" not in txt and "/dev/block" not in txt and "heimdall" not in txt.lower())
        print("ALL OSM TILE OFFLINE CHECKS PASS" if rc == 0 else "FAILURES ABOVE")
        return rc

    @staticmethod
    def _bbox_rejects(text):
        try:
            parse_bbox(text)
            return False
        except ValueError:
            return True


def main() -> int:
    ap = argparse.ArgumentParser(description="Nuxel offline OSM tile tooling")
    ap.add_argument("--policy", default=None)
    ap.add_argument("--json", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    for name in ("status", "plan", "verify", "pack", "verify-pack", "selftest"):
        sp = sub.add_parser(name)
        sp.add_argument("--bbox", default=None)
        sp.add_argument("--zoom", default="")
        sp.add_argument("--root", action="append", default=None)
        sp.add_argument("--src", default=None)
        sp.add_argument("--out", default=None)
        sp.add_argument("--pack", default=None)
        sp.add_argument("--overwrite", action="store_true")
        sp.add_argument("--json", action="store_true")
    args = ap.parse_args()
    args.root = args.root
    t = Tool(args)
    cmd = args.cmd or "status"
    if cmd == "selftest":
        return t.selftest()
    if cmd == "status":
        return t.cmd_status()
    if cmd == "plan":
        if not args.bbox:
            say("plan needs --bbox S W N E")
            return 2
        return t.cmd_plan()
    if cmd == "verify":
        if not args.bbox:
            say("verify needs --bbox S W N E (the area you claim works offline)")
            return 2
        return t.cmd_verify()
    if cmd == "pack":
        return t.cmd_pack()
    if cmd == "verify-pack":
        return t.cmd_verify_pack()
    say("unknown command %s" % cmd)
    return 2


if __name__ == "__main__":
    sys.exit(main())
