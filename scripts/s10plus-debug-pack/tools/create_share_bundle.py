#!/usr/bin/env python3
"""Make a best-effort redacted ZIP from text logs only. Originals untouched."""
import argparse
import pathlib
import re
import zipfile

PATTERNS = [
    (re.compile(r"\bR[0-9A-Z]{10,18}\b"), "<REDACTED-SAMSUNG-SERIAL>"),
    (re.compile(r"(?i)(androidboot\.serialno|ro\.serialno|ro\.boot\.serialno|serialno|Serial Number)\s*[:=]\s*[\w.:-]+"), r"\1=<REDACTED>"),
    (re.compile(r"\b(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}\b"), "<REDACTED-MAC>"),
    (re.compile(r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b"), "<REDACTED-IPV4>"),
    (re.compile(r"(?i)(imei|imsi|android_id|meid|ssid|token|password|passwd|secret)\s*[:=]\s*[^\s,]+"), r"\1=<REDACTED>"),
]
MAX_FILE = 12 * 1024 * 1024
EXCLUDED_EXTENSIONS = {".img", ".bin", ".gz", ".dtb", ".dat", ".zip", ".bak"}

def create(source, dest):
    included = 0
    skipped = 0
    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        z.writestr("PRIVACY-NOTICE.txt", "Logs are best-effort redacted. Inspect before sharing. Device identifiers and other secrets may remain. Original captures are NOT altered.\n")
        for p in sorted(source.rglob("*")):
            if not p.is_file() or p.is_symlink():
                continue
            if p.suffix.lower() in EXCLUDED_EXTENSIONS or p.stat().st_size > MAX_FILE:
                skipped += 1
                continue
            data = p.read_bytes()
            if b"\x00" in data[:4096]:
                skipped += 1
                continue
            text = data.decode("utf-8", "replace")
            for pattern, replacement in PATTERNS:
                text = pattern.sub(replacement, text)
            z.writestr(str(p.relative_to(source)), text)
            included += 1
    print(f"Created {dest}: {included} text files included, {skipped} excluded")

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("captures", type=pathlib.Path)
    ap.add_argument("output", type=pathlib.Path)
    a = ap.parse_args()
    if not a.captures.is_dir():
        ap.error("Capture directory not found")
    a.output.parent.mkdir(parents=True, exist_ok=True)
    create(a.captures, a.output)

if __name__ == "__main__":
    main()
