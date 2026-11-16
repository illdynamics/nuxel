#!/usr/bin/env python3
"""Nuxel SSP offline runtime audit and LOCAL staging, never accesses the device.

Dependencies: Python 3.9+ standard library.
Sources: an owner-provided Nuxel repo ZIP or extracted repo directory,
and optionally an extracted matching stock Android filesystem tree.
WARNING: Static ELF dependency closure is NOT proof the binary can safely run.
"""
from __future__ import annotations
import argparse
import collections
import hashlib
import functools
import json
import os
from pathlib import Path
import re
import shutil
import struct
import sys
import zipfile

ACQUIRED = {
    "vendor/bin/hw/lhd": "packs/sensors/acquired/vendor-bin-hw-lhd",
    "vendor/etc/sensor/lhd.conf": "packs/sensors/acquired/vendor-etc-sensor-lhd.conf",
    "vendor/lib64/sensors.sensorhub.so": "packs/sensors/acquired/vendor-lib64-sensors.sensorhub.so",
    "vendor/lib64/hw/sensors.exynos9820.so": "packs/sensors/acquired/vendor-lib64-hw-sensors.exynos9820.so",
}
SEEDS = [
    "vendor/bin/hw/lhd",
    "vendor/lib64/sensors.sensorhub.so",
    "vendor/lib64/hw/sensors.exynos9820.so",
]
# Library lookup is deliberately explicit and deterministic. It does NOT
# assume all basenames from arbitrary trees are interchangeable.
SEARCH_DIRS = [
    "vendor/lib64", "vendor/lib64/hw", "vendor/lib64/vndk", "vendor/lib64/vndk-sp",
    "vendor/lib64/vndk-29", "vendor/lib64/vndk-sp-29",
    "system/lib64", "system/lib64/vndk", "system/lib64/vndk-sp",
    "system/lib64/vndk-29", "system/lib64/vndk-sp-29",
    "system_ext/lib64", "product/lib64",
    "apex/com.android.runtime/lib64/bionic",
]
MAX_FILE = 128 * 1024 * 1024
MAX_OBJECTS = 512

def hash_bytes(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()

def elf_meta(blob: bytes):
    """Small bounds-checked ELF32/ELF64 parser: PT_INTERP, DT_NEEDED/SONAME/RPATH."""
    if len(blob) < 64 or blob[:4] != b"\x7fELF":
        return None
    cls, data = blob[4], blob[5]
    if cls not in (1, 2) or data not in (1, 2):
        return None
    e = "<" if data == 1 else ">"
    try:
        machine = struct.unpack_from(e + "H", blob, 18)[0]
        if cls == 2:
            phoff = struct.unpack_from(e + "Q", blob, 32)[0]
            phentsize, phnum = struct.unpack_from(e + "HH", blob, 54)
            phfmt, dynfmt = e+"IIQQQQQQ", e+"qQ"
        else:
            phoff = struct.unpack_from(e + "I", blob, 28)[0]
            phentsize, phnum = struct.unpack_from(e + "HH", blob, 42)
            phfmt, dynfmt = e+"IIIIIIII", e+"iI"
        phsz = struct.calcsize(phfmt)
        if phentsize < phsz or phnum > 10000 or phoff+phnum*phentsize > len(blob):
            return {"error":"out-of-bounds ELF program headers", "class":cls, "machine":machine}
        loads, dynamic, interp = [], None, None
        for i in range(phnum):
            p = struct.unpack_from(phfmt, blob, phoff+i*phentsize)
            typ = p[0]
            poff,pvaddr,pfilesz = (p[2],p[3],p[5]) if cls==2 else (p[1],p[2],p[4])
            if poff+pfilesz > len(blob):
                return {"error":"out-of-bounds ELF segment", "class":cls, "machine":machine}
            if typ == 1:
                loads.append((pvaddr,poff,pfilesz))
            elif typ == 2:
                dynamic=(poff,pfilesz)
            elif typ == 3:
                interp = blob[poff:poff+pfilesz].split(b"\0",1)[0].decode("utf8","replace")
        needed,soname,rpath,runpath = [], None, None, None
        if dynamic:
            doff,dsize = dynamic
            ds = struct.calcsize(dynfmt)
            tags=[]
            for off in range(doff,doff+dsize-ds+1,ds):
                tag,val=struct.unpack_from(dynfmt,blob,off)
                if tag==0: break
                tags.append((tag,val))
            strtab=next((v for t,v in tags if t==5),None)
            strsz=next((v for t,v in tags if t==10),None)
            if strtab is not None:
                for va,fo,fs in loads:
                    if va<=strtab<va+fs:
                        stroff=fo+(strtab-va)
                        cap=min(len(blob),stroff+min(strsz or MAX_FILE,MAX_FILE))
                        strings=blob[stroff:cap]
                        def s(idx):
                            if idx<0 or idx>=len(strings): return None
                            end=strings.find(b"\0",idx)
                            return strings[idx:end].decode("utf8","replace") if end>=0 else None
                        needed=[s(v) for t,v in tags if t==1 and s(v)]
                        soname=next((s(v) for t,v in tags if t==14),None)
                        rpath=next((s(v) for t,v in tags if t==15),None)
                        runpath=next((s(v) for t,v in tags if t==29),None)
                        break
        return {"class":32 if cls==1 else 64, "machine":machine,
                "machine_name":{183:"AArch64",40:"ARM"}.get(machine,str(machine)),
                "interpreter":interp,"needed":needed,"soname":soname,
                "rpath":rpath,"runpath":runpath}
    except (ValueError,IndexError,struct.error,OverflowError) as exc:
        return {"error":"malformed ELF: "+type(exc).__name__}

class RepoReader:
    def __init__(self, zip_path=None, root=None):
        self.arc=zipfile.ZipFile(zip_path) if zip_path else None
        self.root=Path(root).resolve() if root else None
        self.name_map={}
        if self.arc:
            for n in self.arc.namelist():
                for rel in ACQUIRED.values():
                    if n.endswith("/"+rel) or n==rel:
                        self.name_map.setdefault(rel,n)
    def get(self, rel):
        if self.root:
            p=self.root/rel
            if p.is_file() and not p.is_symlink() and p.stat().st_size <= MAX_FILE:
                return p.read_bytes()
            return None
        if self.arc and rel in self.name_map:
            n=self.name_map[rel]
            info=self.arc.getinfo(n)
            if info.file_size <= MAX_FILE and not n.endswith("/"):
                return self.arc.read(n)
        return None
    def close(self):
        if self.arc: self.arc.close()

class StockReader:
    """Mapping stock filesystem root. Does not follow links outside owner root."""
    def __init__(self, root=None):
        self.root=Path(root).resolve() if root else None
    def candidates(self, rel):
        # Android "system-as-root" and recovery-mounted /system_root/system.
        return [rel, "system/"+rel, "system_root/"+rel, "system_root/system/"+rel]
    @functools.lru_cache(maxsize=8192)
    def get(self, rel):
        if not self.root: return None
        for r in self.candidates(rel):
            p=self.root/r
            try:
                # Stock images may have absolute Android symlinks. Remap
                # only to the supplied offline root, never the host root.
                for _ in range(8):
                    if not p.is_symlink(): break
                    target=os.readlink(p)
                    p=(self.root/target.lstrip("/")) if target.startswith("/") else (p.parent/target)
                resolved=p.resolve(strict=True)
                if not resolved.is_relative_to(self.root) or not resolved.is_file(): continue
                if resolved.stat().st_size > MAX_FILE: continue
                return resolved.read_bytes()
            except (OSError,ValueError,RuntimeError):
                continue
        return None

def library_path(lib, stock, copied):
    if "/" in lib or "\\" in lib or lib in (".",".."):
        return None
    for d in SEARCH_DIRS:
        rel=d+"/"+lib
        if rel in copied or stock.get(rel) is not None:
            return rel
    return None

def audit(args):
    reader=RepoReader(args.repo_zip,args.repo_root)
    stock=StockReader(args.android_root)
    report=Path(args.report_dir).resolve()
    report.mkdir(parents=True,exist_ok=True)
    stage=Path(args.stage_runtime).resolve() if args.stage_runtime else None
    # A staging path cannot be an Android source tree: protection against
    # accidentally overwriting the owner's stock image or repo.
    if stage:
        protected=[p for p in [stock.root,reader.root] if p]
        if stage in protected or any(stage.is_relative_to(p) or p.is_relative_to(stage) for p in protected):
            raise ValueError("staging path must be separate from stock/repository paths")
        stage.mkdir(parents=True,exist_ok=True)
    contents={}
    origins={}
    for target,alias in ACQUIRED.items():
        data=reader.get(alias)
        if data is None: data=stock.get(target); source="owner-stock"
        else: source="uploaded-repo"
        if data is not None:
            contents[target]=data
            origins[target]=source
    interp_path="system/bin/linker64"
    interp=stock.get(interp_path)
    if interp is not None:
        contents[interp_path]=interp
        origins[interp_path]="owner-stock"
    queue=collections.deque(SEEDS)
    visited=set()
    unresolved=[]
    wrong_arch=[]
    missing_seeds=[s for s in SEEDS if s not in contents]
    while queue and len(visited)<MAX_OBJECTS:
        target=queue.popleft()
        if target in visited: continue
        visited.add(target)
        data=contents.get(target)
        if data is None: continue
        meta=elf_meta(data)
        if not meta:
            wrong_arch.append({"path":target,"reason":"not ELF"}); continue
        if "error" in meta:
            wrong_arch.append({"path":target,"reason":meta["error"]}); continue
        if meta["machine"]!=183 or meta["class"]!=64:
            wrong_arch.append({"path":target,"reason":f"Expected ELF64 AArch64; found {meta['class']} {meta['machine_name']}"})
            continue
        for lib in meta["needed"]:
            path=library_path(lib,stock,contents)
            if path is None:
                unresolved.append({"required_by":target,"library":lib})
                continue
            if path not in contents:
                contents[path]=stock.get(path)
                origins[path]="owner-stock"
            queue.append(path)
    if queue:
        wrong_arch.append({"path":"(global)","reason":"MAX_OBJECTS dependency scan limit reached"})
    manifest={}
    for rel,data in sorted(contents.items()):
        manifest[rel]={"bytes":len(data),"sha256":hash_bytes(data),
                       "origin":origins[rel],"elf":elf_meta(data)}
    conf=contents.get("vendor/etc/sensor/lhd.conf",b"").decode("utf8","replace")
    endpoints={k:bool(re.search(r"(?m)^"+re.escape(k)+r"=",conf))
               for k in ["LhePatch","LheBbdPacket","LheBbdControl","LheBbdSensor","GpioNPowerPath","GpioNStdbyPath"]}
    props={}
    for rel in ("vendor/build.prop", "system/build.prop", "system/etc/prop.default"):
        data=stock.get(rel)
        if data is None: continue
        vals={}
        for line in data.decode("utf8","replace").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k,v=line.split("=",1)
                if k.startswith(("ro.build.", "ro.vendor.", "ro.product.", "ro.system.")):
                    vals[k]=v
        props[rel]={k:vals[k] for k in sorted(vals) if k in (
            "ro.product.vendor.device","ro.product.device","ro.build.fingerprint",
            "ro.vendor.build.fingerprint","ro.build.version.sdk","ro.vendor.build.version.sdk"
        )}
    missing_interp="system/bin/linker64" not in contents
    status=("INCOMPLETE" if missing_interp or missing_seeds or unresolved or wrong_arch
             else "STATIC_ELF_DEPENDENCIES_FOUND_NOT_RUNTIME_VERIFIED")
    if stage:
        for rel,data in contents.items():
            dest=stage/rel
            dest.parent.mkdir(parents=True,exist_ok=True)
            if dest.exists() or dest.is_symlink():
                raise ValueError("refusing to overwrite staged path: "+str(dest))
            with dest.open("xb") as f: f.write(data)
            if hash_bytes(dest.read_bytes()) != hash_bytes(data):
                raise IOError("staged output hash mismatch "+rel)
    output={
        "status":status,
        "warning":"Static dependencies and hashes do NOT prove successful Android execution or sensor streaming.",
        "stock_android_root_supplied":bool(args.android_root),
        "repo_archive_supplied":bool(args.repo_zip),
        "repo_directory_supplied":bool(args.repo_root),
        "stock_build_identity_unverified":True,
        "stock_build_properties":props,
        "staged_on_host":bool(stage),
        "missing_seeds":missing_seeds,
        "missing_linker64":missing_interp,
        "unresolved":unresolved,
        "invalid_or_wrong_arch":wrong_arch,
        "lhd_config_endpoint_markers":endpoints,
        "files":manifest,
        "device_writes":0,
    }
    (report/"ssp-runtime-audit.json").write_text(json.dumps(output,indent=2,sort_keys=True)+"\n")
    summary=[
        "# Nuxel SSP Android runtime: OFFLINE audit",
        "",
        f"**Status:** `{status}`",
        "",
        f"- Available source files: **{len(manifest)}**",
        f"- Missing root executables/HALs: **{len(missing_seeds)}**",
        f"- Direct/recursive unresolved DT_NEEDED entries: **{len(unresolved)}**",
        f"- Interpreter `/system/bin/linker64` missing: **{missing_interp}**",
        f"- Invalid/wrong architecture: **{len(wrong_arch)}**",
        f"- Local staging performed: **{bool(stage)}**",
        "",
        "## Unresolved ELF dependencies",
        "",
    ]
    if unresolved:
        summary.extend(f"- `{x['required_by']}` needs `{x['library']}`" for x in unresolved)
    else: summary.append("- None under this static scan (Android services / linker namespaces remain unverified)")
    summary+=["","## Missing root files",""]
    summary.extend(f"- `{m}`" for m in missing_seeds) if missing_seeds else summary.append("- None")
    summary+=["","## Relevant lhd config endpoint names",""]
    summary.extend(f"- `{k}`: {'present' if v else 'absent'}" for k,v in endpoints.items())
    summary+=["","## Boundaries","",
        "- This tool NEVER connects to the phone, writes partitions, runs lhd, toggles GPIO, or uploads firmware.",
        "- Do not run the staged Android binaries on Fedora directly; obtain exact matching runtime and test in a separately reviewed isolated environment.",
        "- These findings cannot establish that the sensor hub's ACK/boot handshake succeeds.",
        "- Do not run GNSS power/standby controls as a workaround; past repo reports describe unexpected device resets.",
        "- Proven success requires physically changing accelerometer and gyroscope samples and reliable resume/reboot behaviour.",
    ]
    (report/"ssp-runtime-audit.md").write_text("\n".join(summary)+"\n")
    reader.close()
    print("\n".join(summary[:9]))
    print("Wrote",report/"ssp-runtime-audit.json","and",report/"ssp-runtime-audit.md")
    if stage: print("LOCAL stage:",stage)
    return 0 if status.startswith("STATIC_ELF") else 3

def main(argv=None):
    a=argparse.ArgumentParser(description=__doc__)
    source=a.add_mutually_exclusive_group(required=True)
    source.add_argument("--repo-zip",help="owner's Nuxel repo ZIP")
    source.add_argument("--repo-root",help="extracted Nuxel source directory")
    a.add_argument("--android-root",help="OPTIONAL extracted matching Android system/vendor partition tree")
    a.add_argument("--report-dir",required=True)
    a.add_argument("--stage-runtime",help="OPTIONAL local-only staging dir; must be new/empty")
    args=a.parse_args(argv)
    try: return audit(args)
    except (OSError,ValueError,zipfile.BadZipFile) as exc:
        print("ERROR:",exc,file=sys.stderr)
        return 4
if __name__=="__main__":
    sys.exit(main())
