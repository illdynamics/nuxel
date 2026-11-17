#!/usr/bin/env python3
"""Host-only audit of S10+ FIMC-IS firmware provenance. Never accesses devices."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

CAMERA_FILES = (
    "fimc_is_fw_mcu.bin", "fimc_is_lib.bin", "fimc_is_rta.bin",
    "setfile_2l4.bin", "setfile_3j1.bin", "setfile_3m3.bin",
    "setfile_3p9.bin", "setfile_4ha.bin",
)

def manifest_hashes(path: Path) -> dict[str, str]:
    txt = path.read_text(encoding="utf-8")
    start = re.search(r"(?m)^  camera_isp:\s*$", txt)
    if not start:
        raise ValueError("camera_isp category absent")
    end = re.search(r"(?m)^  [a-zA-Z0-9_]+:\s*$", txt[start.end():])
    block = txt[start.end():start.end() + end.start()] if end else txt[start.end():]
    result = {}
    for match in re.finditer(r'(?m)^    - source_path: "vendor/firmware/([^"]+)"\s*$'
                             r'([\s\S]*?)(?=^    - source_path:|\Z)', block):
        name, tail = match.groups()
        if name not in CAMERA_FILES:
            continue
        hm = re.search(r'(?m)^      checksum: "([0-9a-fA-F]{64})"\s*$', tail)
        if not hm:
            raise ValueError(f"Missing SHA-256 for {name}")
        if name in result:
            raise ValueError(f"Duplicate {name} in manifest")
        result[name] = hm.group(1).lower()
    if set(result) != set(CAMERA_FILES):
        raise ValueError(f"Missing camera files in manifest: {sorted(set(CAMERA_FILES)-set(result))}")
    return result

def sha256_file(path: Path, max_bytes: int=32 * 1024 * 1024) -> tuple[str, int]:
    # Reject symbolic links and special nodes, even if they have familiar names.
    s = path.lstat()
    if not stat.S_ISREG(s.st_mode):
        raise ValueError("not a regular file")
    if s.st_size > max_bytes or s.st_size == 0:
        raise ValueError(f"invalid camera blob size: {s.st_size}")
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)
    return h.hexdigest(), s.st_size

def scan(root: Path) -> dict[str,list[Path]]:
    if not root.is_dir() or root.is_symlink():
        raise ValueError(f"Root must be real directory: {root}")
    result = {name: [] for name in CAMERA_FILES}
    for base, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = [d for d in dirs if not (Path(base)/d).is_symlink() and
                   d not in {".git", "__pycache__", "node_modules"}]
        for name in set(files).intersection(result):
            path = Path(base)/name
            if path.is_symlink():
                continue
            result[name].append(path)
    return result

def audit(manifest: Path, roots: list[Path]) -> dict:
    expected = manifest_hashes(manifest)
    output = {"manifest": str(manifest), "roots": [str(r) for r in roots], "files": {},
              "note": "SHA comparison is not provenance proof. No device operations occur."}
    matches = {}
    for root in roots:
        matches[str(root)] = scan(root)
    for name in CAMERA_FILES:
        candidates = []
        for root in roots:
            for path in matches[str(root)][name]:
                try:
                    sha, size = sha256_file(path)
                    candidates.append({"path": str(path), "size": size, "sha256": sha,
                                       "manifest_match": sha == expected[name]})
                except (ValueError, OSError) as exc:
                    candidates.append({"path": str(path), "error": str(exc),
                                       "manifest_match": False})
        output["files"][name] = {"manifest_sha256": expected[name], "candidates": candidates}
    dup = {}
    for name, data in output["files"].items():
        for c in data["candidates"]:
            if "sha256" in c:
                dup.setdefault(c["sha256"], []).append((name,c["path"]))
    output["identical_named_files"] = [
        {"sha256":sha, "files": xs} for sha,xs in dup.items()
        if len(set(n for n,_ in xs)) > 1]
    return output

def main(argv=None) -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest",type=Path,required=True)
    parser.add_argument("--root",type=Path,action="append",required=True,
                        help="one or more local extracted roots to inspect")
    parser.add_argument("--report",type=Path,help="write JSON report (host only)")
    parser.add_argument("--require-manifest-match", action="store_true",
                        help="fail unless each root has exactly one matching copy of every camera file")
    args=parser.parse_args(argv)
    result=audit(args.manifest,args.root)
    text=json.dumps(result,indent=2)
    if args.report:
        args.report.parent.mkdir(parents=True,exist_ok=True)
        args.report.write_text(text+"\n",encoding="utf-8")
    print(text)
    if args.require_manifest_match:
        for root in args.root:
            found = scan(root)
            for name in CAMERA_FILES:
                if len(found[name]) != 1:
                    return 3
                try:
                    digest, _ = sha256_file(found[name][0])
                except (ValueError, OSError):
                    return 3
                if digest != result["files"][name]["manifest_sha256"]:
                    return 3
    return 0

if __name__=="__main__":
    sys.exit(main())
