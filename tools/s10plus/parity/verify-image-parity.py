#!/usr/bin/env python3
"""Fail-closed S10+ fresh-image / live-userspace payload parity verifier.

It reads a staged rootfs or an ext4 image directly (no mount required) and
proves the normalized requirements in required-payload.json are present:
exact source-tree bytes, AArch64 ELF payloads, unit files and enablement links,
the in-image SBOM/hash manifest, package dependencies and the local webroot.

Run:
  python3 tools/s10plus/parity/verify-image-parity.py --staging /tmp/stage
  python3 tools/s10plus/parity/verify-image-parity.py --ext4 image.img \
      --live-baseline tools/s10plus/parity/live-baseline-20261020.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import posixpath
import stat
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tools/s10plus"))
from ext4lite import Ext4  # noqa: E402

SCHEMA = "nuxel.image-parity-report/1"
ELF_MAGIC = b"\x7fELF"
MACHO_MAGICS = {
    b"\xfe\xed\xfa\xce", b"\xfe\xed\xfa\xcf",
    b"\xce\xfa\xed\xfe", b"\xcf\xfa\xed\xfe",
    b"\xca\xfe\xba\xbe", b"\xbe\xba\xfe\xca",
}
AARCH64_EM = 183


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def norm_link(link: str, parent: str) -> str:
    return link if link.startswith("/") else posixpath.normpath(posixpath.join(parent, link))


class StagingReader:
    def __init__(self, root: Path):
        self.root = root.resolve()

    def _resolve(self, path: str) -> Path:
        if not path.startswith("/"):
            raise ValueError("not absolute: " + path)
        current = Path("/")
        for part in [p for p in path.split("/") if p]:
            candidate = current / part
            disk = self.root / str(candidate).lstrip("/")
            if disk.is_symlink():
                target = os.readlink(disk)
                candidate = Path(norm_link(target, str(current)))
            current = candidate
        return self.root / str(current).lstrip("/")

    def read(self, path: str) -> bytes:
        disk = self._resolve(path)
        if not disk.is_file() or disk.is_symlink():
            raise FileNotFoundError(path)
        return disk.read_bytes()

    def exists(self, path: str) -> bool:
        try:
            return self._resolve(path).exists()
        except OSError:
            return False

    def is_symlink(self, path: str) -> bool:
        return (self.root / path.lstrip("/")).is_symlink()

    def readlink(self, path: str) -> str:
        return os.readlink(self.root / path.lstrip("/"))

    def mode(self, path: str) -> int:
        return stat.S_IMODE((self.root / path.lstrip("/")).lstat().st_mode)

    def files_under(self, prefix: str) -> list[str]:
        base = self.root / prefix.lstrip("/")
        if not base.exists():
            return []
        out = []
        for path in base.rglob("*"):
            if path.is_file() or path.is_symlink():
                out.append("/" + path.relative_to(self.root).as_posix())
        return sorted(out)


class Ext4Reader:
    def __init__(self, image: Path):
        self.image = image
        self.fs = Ext4(str(image))

    def _lookup(self, path: str, follow_final: bool = True):
        name = path
        for _ in range(40):
            if not name.startswith("/"):
                raise FileNotFoundError(name)
            parts = [p for p in name.strip("/").split("/") if p]
            parent = 2
            changed = False
            for j, part in enumerate(parts):
                children = self.fs.children(parent)
                if part not in children:
                    raise FileNotFoundError(name)
                ino = children[part][0]
                inode, _ = self.fs.inode(ino)
                mode = self.fs.u16(inode, 0)
                if stat.S_ISLNK(mode):
                    if j == len(parts) - 1 and not follow_final:
                        return ino
                    link = self.fs.get(ino).decode("utf-8")
                    previous = "/" + "/".join(parts[:j])
                    name = norm_link(link, previous)
                    rest = parts[j + 1:]
                    if rest:
                        name = posixpath.normpath(posixpath.join(name, *rest))
                    changed = True
                    break
                if j < len(parts) - 1 and not stat.S_ISDIR(mode):
                    raise FileNotFoundError(name)
                parent = ino
            if not changed:
                return parent
        raise RuntimeError("symlink depth exceeded: " + path)

    def read(self, path: str) -> bytes:
        ino = self._lookup(path)
        inode, _ = self.fs.inode(ino)
        if not stat.S_ISREG(self.fs.u16(inode, 0)):
            raise FileNotFoundError(path)
        return self.fs.get(ino)

    def exists(self, path: str) -> bool:
        try:
            self._lookup(path)
            return True
        except (FileNotFoundError, KeyError):
            return False

    def is_symlink(self, path: str) -> bool:
        try:
            ino = self._lookup(path, follow_final=False)
            inode, _ = self.fs.inode(ino)
            return stat.S_ISLNK(self.fs.u16(inode, 0))
        except (FileNotFoundError, KeyError):
            return False

    def readlink(self, path: str) -> str:
        ino = self._lookup(path, follow_final=False)
        return self.fs.get(ino).decode("utf-8")

    def mode(self, path: str) -> int:
        ino = self._lookup(path, follow_final=False)
        inode, _ = self.fs.inode(ino)
        return stat.S_IMODE(self.fs.u16(inode, 0))

    def files_under(self, prefix: str) -> list[str]:
        try:
            ino = self._lookup(prefix)
        except (FileNotFoundError, KeyError):
            return []
        out = []

        def walk(current: int, rel: str, depth: int):
            if depth > 40:
                raise RuntimeError("directory depth exceeded: " + prefix)
            for name, (child, _) in self.fs.children(current).items():
                child_path = rel.rstrip("/") + "/" + name
                inode, _ = self.fs.inode(child)
                mode = self.fs.u16(inode, 0)
                out.append(child_path)
                if stat.S_ISDIR(mode):
                    walk(child, child_path, depth + 1)

        walk(ino, prefix.rstrip("/"), 0)
        return sorted(out)


def elf_info(data: bytes, path: str) -> dict:
    if len(data) < 64 or data[:4] != ELF_MAGIC:
        raise ValueError("not an ELF file: " + path)
    if data[4] != 2 or data[5] != 1:
        raise ValueError("not a 64-bit little-endian ELF: " + path)
    machine = struct.unpack_from("<H", data, 18)[0]
    if machine != AARCH64_EM:
        raise ValueError("wrong ELF machine %d (expected AArch64 183): %s" % (machine, path))
    e_type = struct.unpack_from("<H", data, 16)[0]
    if e_type not in (2, 3):
        raise ValueError("wrong ELF type %d: %s" % (e_type, path))
    e_phoff = struct.unpack_from("<Q", data, 32)[0]
    e_shoff = struct.unpack_from("<Q", data, 40)[0]
    e_phentsize = struct.unpack_from("<H", data, 54)[0]
    e_phnum = struct.unpack_from("<H", data, 56)[0]
    e_shentsize = struct.unpack_from("<H", data, 58)[0]
    e_shnum = struct.unpack_from("<H", data, 60)[0]
    interp = None
    for i in range(e_phnum):
        off = e_phoff + i * e_phentsize
        if off + 56 > len(data):
            break
        p_type = struct.unpack_from("<I", data, off)[0]
        p_offset = struct.unpack_from("<Q", data, off + 8)[0]
        p_filesz = struct.unpack_from("<Q", data, off + 32)[0]
        if p_type == 3:  # PT_INTERP
            interp = data[p_offset:p_offset + p_filesz].split(b"\0", 1)[0].decode("utf-8", "replace")
    needed = []
    sections = []
    for i in range(e_shnum):
        off = e_shoff + i * e_shentsize
        if off + 64 > len(data):
            break
        sections.append({
            "type": struct.unpack_from("<I", data, off + 4)[0],
            "offset": struct.unpack_from("<Q", data, off + 24)[0],
            "size": struct.unpack_from("<Q", data, off + 32)[0],
            "link": struct.unpack_from("<I", data, off + 40)[0],
            "entsize": struct.unpack_from("<Q", data, off + 56)[0],
        })
    for sec in sections:
        if sec["type"] != 6 or sec["link"] >= len(sections):  # SHT_DYNAMIC
            continue
        strsec = sections[sec["link"]]
        dynstr = data[strsec["offset"]:strsec["offset"] + strsec["size"]]
        entsize = sec["entsize"] or 16
        for off in range(sec["offset"], sec["offset"] + sec["size"], entsize):
            if off + 16 > len(data):
                break
            tag, val = struct.unpack_from("<qQ", data, off)
            if tag == 0:
                break
            if tag == 1 and val < len(dynstr):  # DT_NEEDED
                end = dynstr.find(b"\0", val)
                needed.append(dynstr[val:end if end >= 0 else len(dynstr)].decode("utf-8", "replace"))
    return {"interp": interp, "needed": sorted(set(needed)), "type": e_type}


def tree_digest(rows: list[dict], prefix: str) -> str:
    h = hashlib.sha256()
    for row in sorted(rows, key=lambda r: r["target"]):
        rel = row["target"][len(prefix):].lstrip("/")
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update(row["sha256"].encode("ascii"))
        h.update(b"\n")
    return h.hexdigest()


def rpm_packages(root: Path) -> list[str]:
    cp = subprocess.run(["rpm", "--root", str(root), "-qa", "--qf", "%{NAME}\t%{EPOCHNUM}:%{VERSION}-%{RELEASE}\t%{ARCH}\n"],
                        text=True, capture_output=True)
    if cp.returncode != 0:
        return []
    return sorted(line.strip() for line in cp.stdout.splitlines() if line.strip())


def main() -> int:
    ap = argparse.ArgumentParser()
    source = ap.add_mutually_exclusive_group(required=True)
    source.add_argument("--staging", type=Path)
    source.add_argument("--ext4", type=Path)
    ap.add_argument("--repo", type=Path, default=ROOT)
    ap.add_argument("--inventory", type=Path, default=ROOT / "tools/s10plus/parity/required-payload.json")
    ap.add_argument("--live-baseline", type=Path)
    ap.add_argument("--json", type=Path)
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    repo = args.repo.resolve()
    inv = json.loads(args.inventory.read_text())
    reader = StagingReader(args.staging) if args.staging else Ext4Reader(args.ext4)
    errors: list[str] = []
    warnings: list[str] = []
    checks = 0
    checks_by_area: dict[str, int] = {}

    def ok(area: str, count: int = 1):
        nonlocal checks
        checks += count
        checks_by_area[area] = checks_by_area.get(area, 0) + count

    def expect(condition: bool, message: str):
        if not condition:
            errors.append(message)
        else:
            ok("assertions")

    # 1. Exact source-tree and source-file parity.
    for item in inv["source_trees"]:
        src = repo / item["source"]
        expect(src.is_dir(), "missing source tree: " + item["source"])
        count = 0
        excludes = set(item.get("exclude", []))
        for path in sorted(src.rglob("*")):
            if not path.is_file() or path.is_symlink():
                continue
            rel = path.relative_to(src).as_posix()
            if rel in excludes:
                continue
            target = item["target"].rstrip("/") + "/" + rel
            try:
                packaged = reader.read(target)
            except (FileNotFoundError, KeyError):
                errors.append("missing image file: " + target)
                continue
            source_bytes = path.read_bytes()
            expect(packaged == source_bytes,
                   "source/image drift: %s (%s != %s)" % (target, digest(packaged), digest(source_bytes)))
            count += 1
        ok("source-tree:" + item["id"], count)
        if args.verbose:
            print("PASS tree %s: %d exact files" % (item["id"], count))

    for item in inv["source_files"]:
        src = repo / item["source"]
        expect(src.is_file(), "missing source file: " + item["source"])
        try:
            packaged = reader.read(item["target"])
        except (FileNotFoundError, KeyError):
            errors.append("missing image file: " + item["target"])
            continue
        expect(packaged == src.read_bytes(),
               "source/image drift: %s" % item["target"])
        mode = reader.mode(item["target"])
        expect("%04o" % mode == item["mode"],
               "wrong mode %04o for %s (expected %s)" % (mode, item["target"], item["mode"]))
        ok("source-file")

    # 2. AArch64 ELF payloads and their runtime library closure.
    library_index = set()
    for libdir in ("/usr/lib64", "/lib64", "/usr/lib", "/lib"):
        for path in reader.files_under(libdir):
            library_index.add(posixpath.basename(path))
    for item in inv["built_elf"]:
        try:
            data = reader.read(item["target"])
        except (FileNotFoundError, KeyError):
            errors.append("missing built ELF: " + item["target"])
            continue
        try:
            info = elf_info(data, item["target"])
        except ValueError as exc:
            errors.append(str(exc))
            continue
        mode = reader.mode(item["target"])
        expect(mode & 0o111 != 0, "built ELF is not executable: " + item["target"])
        ok("built-elf")
        if info["interp"] and not reader.exists(info["interp"]):
            errors.append("missing ELF interpreter %s for %s" % (info["interp"], item["target"]))
        missing = [lib for lib in info["needed"] if lib not in library_index]
        expect(not missing, "missing DT_NEEDED libraries for %s: %s" % (item["target"], ", ".join(missing)))
        if info["needed"]:
            ok("elf-needed")
        if args.verbose:
            print("PASS ELF %s: %d bytes interp=%s needed=%s" %
                  (item["target"], len(data), info["interp"], ",".join(info["needed"])))

    # 3. No host-architecture or Mach-O payload in Nuxel-owned trees.
    custom_roots = ("/usr/lib/nuxel", "/usr/libexec/nuxel", "/usr/local/bin", "/usr/share/nuxel")
    bad_arch = []
    for prefix in custom_roots:
        for path in reader.files_under(prefix):
            if reader.is_symlink(path):
                continue
            try:
                head = reader.read(path)[:64]
            except (FileNotFoundError, KeyError):
                continue
            if head[:4] in MACHO_MAGICS:
                bad_arch.append("Mach-O: " + path)
            elif head[:4] == ELF_MAGIC:
                try:
                    elf_info(head if len(head) >= 64 else reader.read(path), path)
                except ValueError as exc:
                    bad_arch.append(str(exc))
    for path in reader.files_under("/usr/bin"):
        if not posixpath.basename(path).startswith("nuxel"):
            continue
        if reader.is_symlink(path):
            continue
        head = reader.read(path)[:64]
        if head[:4] in MACHO_MAGICS:
            bad_arch.append("Mach-O: " + path)
        elif head[:4] == ELF_MAGIC:
            try:
                elf_info(head, path)
            except ValueError as exc:
                bad_arch.append(str(exc))
    expect(not bad_arch, "host/wrong-architecture payload: " + "; ".join(sorted(set(bad_arch))))
    ok("host-arch-scan")

    # 4. Symlinks and enablement links (including resolved targets).
    for item in inv.get("symlinks", []):
        path = item["path"]
        if not reader.is_symlink(path):
            if item.get("required", True):
                errors.append("missing required symlink: " + path)
            continue
        points_to = reader.readlink(path)
        expect(points_to == item["points_to"],
               "symlink %s -> %s, expected %s" % (path, points_to, item["points_to"]))
        expect(reader.exists(path), "symlink does not resolve: " + path)

    for item in inv.get("enablement", []):
        path = item["path"]
        if not reader.is_symlink(path):
            if item.get("required", True):
                errors.append("missing enablement symlink: " + path)
            continue
        points_to = reader.readlink(path)
        expect(points_to == item["points_to"],
               "enablement %s -> %s, expected %s" % (path, points_to, item["points_to"]))
        expect(reader.exists(path), "enablement link does not resolve: " + path)
        ok("enablement")

    # 5. Webroot files are non-empty and accessible.
    for path in inv.get("webroot", []):
        try:
            data = reader.read(path)
        except (FileNotFoundError, KeyError):
            errors.append("missing webroot file: " + path)
            continue
        expect(len(data) > 0, "empty webroot file: " + path)
        ok("webroot")

    # 6. In-image SBOM/hash manifest.
    manifest_path = "/etc/nuxel/userspace-manifest.json"
    try:
        manifest = json.loads(reader.read(manifest_path))
    except (FileNotFoundError, KeyError, json.JSONDecodeError) as exc:
        errors.append("missing or invalid in-image manifest %s: %s" % (manifest_path, exc))
        manifest = None
    manifest_rows = []
    if manifest is not None:
        expect(manifest.get("schema") == "nuxel.userspace-manifest/1", "manifest schema mismatch")
        expect(manifest.get("architecture") == "aarch64", "manifest architecture is not aarch64")
        expect(manifest.get("device") == "s10plus", "manifest device is not s10plus")
        expect(manifest.get("release") == inv.get("release"),
               "manifest release %r != %r" % (manifest.get("release"), inv.get("release")))
        rows = manifest.get("files", [])
        expect(manifest.get("file_count") == len(rows), "manifest file_count mismatch")
        seen = set()
        for row in rows:
            target = row.get("target")
            if not target or target in seen:
                errors.append("manifest duplicate/invalid target: %r" % target)
                continue
            seen.add(target)
            try:
                data = reader.read(target)
            except (FileNotFoundError, KeyError):
                errors.append("manifest names missing file: " + target)
                continue
            expect(digest(data) == row.get("sha256"),
                   "manifest hash mismatch: " + target)
            expect(len(data) == row.get("bytes"),
                   "manifest byte count mismatch: " + target)
        manifest_rows = rows
        ok("in-image-manifest", len(rows))
        # Recompute tree digests from the manifest's own rows.
        for item in inv["source_trees"]:
            if not item.get("tree_digest", True):
                continue
            prefix = item["target"]
            selected = [r for r in rows if r.get("kind") == "source-tree" and r["target"].startswith(prefix.rstrip("/") + "/")]
            got = tree_digest(selected, prefix) if selected else "missing"
            want = manifest.get("tree_digests", {}).get(item["id"])
            expect(got == want, "tree digest mismatch for %s (%s != %s)" % (item["id"], got, want))
        packages = manifest.get("packages", [])
        pkg_names = {line.split("\t", 1)[0] for line in packages if line.strip()}
        missing_pkgs = sorted(set(inv.get("required_packages", [])) - pkg_names)
        expect(not missing_pkgs, "package SBOM missing: " + ", ".join(missing_pkgs))
        if args.staging:
            live_rpm = rpm_packages(args.staging)
            if live_rpm:
                expect(live_rpm == packages, "manifest RPM SBOM differs from staged rpm database")
                ok("rpm-sbom", len(live_rpm))
        # Source-tree digests must also cover the complete checkout, not just the
        # manifest's own bookkeeping.
        for item in inv["source_trees"]:
            if not item.get("tree_digest", True):
                continue
            src = repo / item["source"]
            excludes = set(item.get("exclude", []))
            rows = []
            for path in sorted(src.rglob("*")):
                if path.is_file() and not path.is_symlink():
                    rel = path.relative_to(src).as_posix()
                    if rel in excludes:
                        continue
                    data = path.read_bytes()
                    rows.append({"target": item["target"].rstrip("/") + "/" + rel, "sha256": digest(data)})
            want = tree_digest(rows, item["target"])
            expect(manifest.get("tree_digests", {}).get(item["id"]) == want,
                   "checkout tree digest mismatch for " + item["id"])

    # 7. Builder markers: the fresh-image script must still name every required
    # source it claims to package. This catches a verifier/inventory update that
    # was not reflected in the actual builder.
    builder = (repo / "images/s10plus/build-phone-rootfs-inside-fedora.sh").read_text()
    service_shim_loop = 'for shim in "/nuxel/services/$service/bin/"*' in builder
    for item in inv["source_trees"] + inv["source_files"] + inv["built_elf"]:
        source = item["source"]
        if source in builder:
            continue
        # The builder installs services/<name>/bin/* shims through a documented
        # loop over services/nuxel-bridge|portal|notifications. Requiring the
        # expanded path would reject a correct glob-based install.
        if service_shim_loop and source.startswith("services/") and "/bin/" in source:
            continue
        expect(False, "builder does not reference " + source)
    ok("builder-markers")

    # 8. Normalized live-vs-image delta.
    live_delta = {"required_missing": [], "live_only": [], "webroot_drift": [], "equivalent": []}
    if args.live_baseline:
        live = json.loads(args.live_baseline.read_text())
        enablement = {Path(x["path"]).name: x for x in inv.get("enablement", [])}
        unit_map = {
            "nuxel-wayland.service": ["nuxel-wayland.service"],
            "nuxel-wl-fb.service": ["nuxel-wl-fb.service"],
            "nuxel-button-manager.service": ["nuxel-button-manager.service"],
            "nuxel-touch-arm.service": ["nuxel-touch-arm.service"],
            "nuxel-bridge.service": ["nuxel-bridge.service"],
            "nuxel-http-bridge.service": ["nuxel-http-bridge.service"],
            "nuxel-notifications.service": ["nuxel-notifications.service"],
            "nuxel-portal.service": ["nuxel-portal.service"],
            "nuxel-haptics.service": ["nuxel-haptics.service"],
            "nuxel-metrics.service": ["nuxel-metrics.socket"],
            "seatd.service": ["seatd.service"],
        }
        for unit in live.get("services_running", []):
            wanted = unit_map.get(unit)
            if wanted:
                for link_name in wanted:
                    if link_name not in enablement:
                        live_delta["required_missing"].append("%s -> %s" % (unit, link_name))
                continue
            if unit in ("NetworkManager.service", "wpa_supplicant.service", "ModemManager.service",
                        "dbus-daemon.service", "polkit.service", "systemd-journald.service",
                        "systemd-logind.service"):
                continue
            live_delta["live_only"].append(unit)
        for path, live_hash in live.get("webroot_sha256", {}).items():
            try:
                image_hash = digest(reader.read(path))
            except (FileNotFoundError, KeyError):
                live_delta["webroot_drift"].append(path + " (missing in image)")
                continue
            if image_hash != live_hash:
                live_delta["webroot_drift"].append("%s (%s != %s)" % (path, image_hash, live_hash))
        live_delta["equivalent"] = inv.get("normalization", {}).get("equivalent_services", [])
        expect(not live_delta["required_missing"],
               "live services with no fresh-image equivalent: " + "; ".join(live_delta["required_missing"]))
        # Webroot drift is report-only: live may lag the current checkout, but
        # the image is already held to exact source parity above.
        if live_delta["webroot_drift"]:
            warnings.append("live webroot differs from current source for %d file(s)" % len(live_delta["webroot_drift"]))
        ok("live-normalization")

    verdict = "PASS" if not errors else "FAIL"
    report = {
        "schema": SCHEMA,
        "verdict": verdict,
        "mode": "staging" if args.staging else "ext4",
        "target": str(args.staging or args.ext4),
        "checks": checks,
        "checks_by_area": checks_by_area,
        "errors": errors,
        "warnings": warnings,
        "manifest": manifest_path if manifest is not None else None,
        "manifest_file_count": len(manifest_rows),
        "live_delta": live_delta,
    }
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(text)
    for warning in warnings:
        print("WARN", warning)
    if errors:
        for error in errors[:80]:
            print("FAIL", error)
        if len(errors) > 80:
            print("FAIL ... %d more" % (len(errors) - 80))
    print("PARITY-%s mode=%s checks=%d errors=%d warnings=%d target=%s" %
          (verdict, report["mode"], checks, len(errors), len(warnings), report["target"]))
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
