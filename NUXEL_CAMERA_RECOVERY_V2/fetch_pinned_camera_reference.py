#!/usr/bin/env python3
"""Optionally fetch hash-pinned public camera firmware reference to a HOST directory.
Does NOT deploy to a phone. Public blobs are NOT assumed compatible with stock.
"""
from __future__ import annotations
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import sys
import tempfile
from urllib.error import HTTPError, URLError
from urllib.request import urlopen
from camera_firmware_audit import CAMERA_FILES, manifest_hashes, sha256_file

PIN="05c9ef8f16e0ad5ab274e408c120dfd99fd5c628"
BASE=f"https://raw.githubusercontent.com/Linux4/proprietary_vendor_samsung/{PIN}/"
SOURCE_DIRS=("beyond2lte/proprietary/vendor/firmware",
             "exynos9820-common/proprietary/vendor/firmware")
MAX_DOWNLOAD=16*1024*1024

def get(url: str, tmp: Path) -> int:
    count=0
    with urlopen(url,timeout=30) as response, tmp.open("wb") as dest:
        if not response.geturl().startswith("https://"):
            raise RuntimeError("Unexpected non-HTTPS redirect")
        while chunk := response.read(256*1024):
            count+=len(chunk)
            if count>MAX_DOWNLOAD:
                raise RuntimeError("File exceeds size limit")
            dest.write(chunk)
    return count

def fetch_one(name:str, expected: str, dest:Path, transport=get) -> tuple[bool,str]:
    if name not in CAMERA_FILES:
        raise ValueError("Name outside allowlist")
    if dest.exists() or dest.is_symlink():
        if dest.is_symlink():
            return False,"Existing destination is a symlink"
        try:
            sha,_=sha256_file(dest)
        except (ValueError,OSError) as exc:
            return False,str(exc)
        return (sha==expected,"Already present and hash-valid" if sha==expected
                else "Destination occupied by different content; will not overwrite")
    dest.parent.mkdir(parents=True,exist_ok=True)
    errors=[]
    for dirname in SOURCE_DIRS:
        url=BASE+dirname+"/"+name
        fd,temp=tempfile.mkstemp(prefix=".camera-fetch-",dir=str(dest.parent))
        os.close(fd)
        tmp=Path(temp)
        try:
            transport(url,tmp)
            actual,_=sha256_file(tmp,MAX_DOWNLOAD)
            if actual==expected:
                tmp.replace(dest)
                return True,f"Downloaded and verified from {url}"
            errors.append(f"{dirname}: SHA mismatch {actual}")
        except (OSError, HTTPError, URLError, RuntimeError, ValueError) as exc:
            errors.append(f"{dirname}: {exc}")
        finally:
            tmp.unlink(missing_ok=True)
    return False,"; ".join(errors)

def main(argv=None)->int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest",type=Path,required=True)
    parser.add_argument("--dest",type=Path,required=True)
    parser.add_argument("--download",action="store_true",
                        help="explicit opt-in to networking and host-only download")
    parser.add_argument("--only",choices=CAMERA_FILES,action="append")
    args=parser.parse_args(argv)
    expected=manifest_hashes(args.manifest)
    target=args.only or CAMERA_FILES
    if not args.download:
        print("PLAN ONLY: No network or file changes. Source",BASE)
        for name in target:
            print(f"{name}\tSHA256={expected[name]}")
        return 0
    if args.dest.is_symlink():
        parser.error("destination may not be a symlink")
    failures=0
    for name in target:
        ok,msg=fetch_one(name,expected[name],args.dest/name)
        print(("OK" if ok else "FAILED"),name,msg)
        failures+=not ok
    return 0 if failures==0 else 3

if __name__=="__main__":
    sys.exit(main())
