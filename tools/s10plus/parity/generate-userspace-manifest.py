#!/usr/bin/env python3
"""Generate the in-image SBOM/hash manifest for the S10+ userspace.

The manifest is written into the staged rootfs before the ext4 image is made.
It contains exact file hashes, source-tree digests, unit enablement links and
the installed RPM NEVRAs.  It is deterministic when SOURCE_DATE_EPOCH is set:
callers pass the source commit timestamp, never the wall clock.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
SCHEMA = "nuxel.userspace-manifest/1"


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def target_path(root: Path, absolute: str) -> Path:
    return root / absolute.lstrip("/")


def file_row(root: Path, absolute: str, source: str | None, kind: str) -> dict:
    path = target_path(root, absolute)
    if not path.is_file() or path.is_symlink():
        raise SystemExit(f"missing regular file for manifest: {absolute}")
    data = path.read_bytes()
    return {
        "target": absolute,
        "source": source,
        "kind": kind,
        "mode": f"{stat.S_IMODE(path.stat().st_mode):04o}",
        "bytes": len(data),
        "sha256": sha_bytes(data),
    }


def tree_digest(rows: list[dict], prefix: str) -> str:
    h = hashlib.sha256()
    for row in sorted(rows, key=lambda r: r["target"]):
        rel = row["target"][len(prefix):].lstrip("/")
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update(row["sha256"].encode("ascii"))
        h.update(b"\n")
    return h.hexdigest()


def source_tree_rows(repo: Path, root: Path, source: str, target: str,
                     exclude: set[str] | None = None) -> list[dict]:
    src = repo / source
    if not src.is_dir():
        raise SystemExit(f"missing source tree: {source}")
    exclude = exclude or set()
    rows = []
    for path in sorted(src.rglob("*")):
        if path.is_symlink():
            raise SystemExit(f"source tree contains a symlink: {path.relative_to(repo)}")
        if not path.is_file():
            continue
        rel = path.relative_to(src).as_posix()
        if rel in exclude:
            continue
        absolute = target.rstrip("/") + "/" + rel
        rows.append(file_row(root, absolute, path.relative_to(repo).as_posix(), "source-tree"))
    if not rows:
        raise SystemExit(f"empty source tree after excludes: {source}")
    return rows


def rpm_packages(root: Path) -> list[str]:
    fmt = "%{NAME}\t%{EPOCHNUM}:%{VERSION}-%{RELEASE}\t%{ARCH}"
    cp = subprocess.run(["rpm", "--root", str(root), "-qa", "--qf", fmt + "\n"],
                        text=True, capture_output=True)
    if cp.returncode != 0:
        raise SystemExit("rpm --root failed while building package SBOM: " + cp.stderr.strip())
    return sorted(line.strip() for line in cp.stdout.splitlines() if line.strip())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, type=Path, help="staged rootfs")
    ap.add_argument("--repo", type=Path, default=ROOT)
    ap.add_argument("--inventory", type=Path, default=ROOT / "tools/s10plus/parity/required-payload.json")
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--version", default=None)
    ap.add_argument("--source-commit", default=os.environ.get("NUXEL_SOURCE_COMMIT", ""))
    ap.add_argument("--source-date-epoch", type=int,
                    default=int(os.environ.get("SOURCE_DATE_EPOCH", "0")))
    ap.add_argument("--no-rpm", action="store_true", help="test-only: omit the RPM SBOM")
    args = ap.parse_args()

    repo = args.repo.resolve()
    root = args.root.resolve()
    inv = json.loads(args.inventory.read_text())
    version = args.version or (repo / "VERSION").read_text().strip()
    source_date_epoch = args.source_date_epoch
    rows: list[dict] = []
    tree_digests: dict[str, str] = {}
    symlinks = []
    enablement = []

    for item in inv["source_trees"]:
        if not item.get("required", True):
            continue
        tree_rows = source_tree_rows(repo, root, item["source"], item["target"],
                                     set(item.get("exclude", [])))
        rows.extend(tree_rows)
        if item.get("tree_digest", True):
            tree_digests[item["id"]] = tree_digest(tree_rows, item["target"])

    for item in inv["source_files"]:
        rows.append(file_row(root, item["target"], item["source"], "source-file"))

    for item in inv["built_elf"]:
        rows.append(file_row(root, item["target"], item["source"], "built-elf"))

    for item in inv.get("webroot", []):
        if any(r["target"] == item for r in rows):
            continue
        rows.append(file_row(root, item, None, "webroot"))

    for item in inv.get("symlinks", []):
        path = target_path(root, item["path"])
        if not path.is_symlink():
            if item.get("required", True):
                raise SystemExit(f"missing required symlink: {item['path']}")
            continue
        points_to = os.readlink(path)
        if item.get("required", True) and points_to != item["points_to"]:
            raise SystemExit(f"symlink target drift: {item['path']} -> {points_to}, expected {item['points_to']}")
        symlinks.append({"path": item["path"], "points_to": points_to})

    for item in inv.get("enablement", []):
        path = target_path(root, item["path"])
        if not path.is_symlink():
            if item.get("required", True):
                raise SystemExit(f"missing required enablement symlink: {item['path']}")
            continue
        points_to = os.readlink(path)
        if item.get("required", True) and points_to != item["points_to"]:
            raise SystemExit(f"enablement target drift: {item['path']} -> {points_to}, expected {item['points_to']}")
        enablement.append({"path": item["path"], "points_to": points_to})

    # Later explicit installs override an earlier tree copy (the builder does
    # exactly that for the canonical app registry and service-owned configs).
    by_target = {}
    for row in rows:
        previous = by_target.get(row["target"])
        if previous and previous["kind"] == "source-tree" and row["kind"] != "source-tree":
            pass
        elif previous and previous["sha256"] != row["sha256"]:
            raise SystemExit(f"conflicting manifest target: {row['target']}")
        by_target[row["target"]] = row
    rows = list(by_target.values())

    manifest = {
        "schema": SCHEMA,
        "release": version,
        "device": "s10plus",
        "codename": "beyond2lte",
        "architecture": "aarch64",
        "base_os": "fedora-43",
        "source_commit": args.source_commit or None,
        "source_date_epoch": source_date_epoch,
        "inventory": str(args.inventory.relative_to(repo)) if args.inventory.resolve().is_relative_to(repo) else str(args.inventory),
        "inventory_sha256": sha_bytes(args.inventory.read_bytes()),
        "files": sorted(rows, key=lambda r: r["target"]),
        "file_count": len(rows),
        "tree_digests": tree_digests,
        "symlinks": sorted(symlinks, key=lambda r: r["path"]),
        "enablement": sorted(enablement, key=lambda r: r["path"]),
        "packages": [] if args.no_rpm else rpm_packages(root),
    }
    manifest["packages_sha256"] = sha_bytes("\n".join(manifest["packages"]).encode("utf-8"))
    body = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    out = root / args.output.as_posix().lstrip("/") if args.output.is_absolute() else args.output
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body)
    print(f"WROTE {out} files={manifest['file_count']} packages={len(manifest['packages'])} sha256={sha_bytes(body.encode())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
