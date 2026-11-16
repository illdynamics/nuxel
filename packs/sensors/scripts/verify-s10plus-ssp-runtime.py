#!/usr/bin/env python3
"""Verify the collected S10+ SSP runtime pack without executing vendor files."""
import argparse, hashlib, json, os, struct
from pathlib import Path

REQUIRED = [
    "vendor/bin/hw/lhd",
    "vendor/etc/sensor/lhd.conf",
]
OPTIONAL = [
    "vendor/lib64/sensors.sensorhub.so", "vendor/lib/sensors.sensorhub.so",
    "vendor/lib64/hw/sensors.exynos9820.so", "vendor/lib/hw/sensors.exynos9820.so",
    "system/bin/linker64", "system/bin/linker",
]

def elf_info(p):
    b = p.read_bytes()
    if len(b) < 20 or b[:4] != b"\x7fELF": return None
    cls = b[4]
    endian = "<" if b[5] == 1 else ">" if b[5] == 2 else None
    if not endian: return None
    machine = struct.unpack_from(endian + "H", b, 18)[0]
    return {"class": 32 if cls == 1 else 64 if cls == 2 else cls,
            "machine": machine, "machine_name": {183:"AArch64",40:"ARM"}.get(machine,"unknown")}

ap=argparse.ArgumentParser(); ap.add_argument("--root",required=True); a=ap.parse_args()
root=Path(a.root)
files=[]; missing=[]
for rel in REQUIRED:
    if not (root/rel).is_file(): missing.append(rel)
for rel in OPTIONAL:
    if not (root/rel).is_file(): pass
for p in sorted(x for x in root.rglob("*") if x.is_file()):
    h=hashlib.sha256(p.read_bytes()).hexdigest()
    info=elf_info(p)
    files.append({"path":str(p.relative_to(root)),"size":p.stat().st_size,"sha256":h,"elf":info})
conf=root/"vendor/etc/sensor/lhd.conf"
config_text=conf.read_text(errors="replace") if conf.is_file() else ""
markers={k:(k in config_text) for k in ("LhePatch", "LheBbdPacket", "LheBbdControl", "LheBbdSensor", "GpioNPowerPath")}
result={"target":"Samsung Galaxy S10+ SM-G975F / beyond2lte / Exynos 9820",
        "required_missing":missing,"files":files,"lhd_conf_markers":markers,
        "status":"READY_FOR_AGENT_REVIEW" if not missing else "INCOMPLETE_COLLECTION",
        "warning":"This is a collection/integrity check only. It does not prove ABI compatibility or sensor streaming and is NOT a flash-ready image."}
(root/"reports").mkdir(exist_ok=True)
(root/"reports/manifest.json").write_text(json.dumps(result,indent=2)+"\n")
print("SSP runtime collection:",result["status"])
print("Required missing:",", ".join(missing) if missing else "none")
print("lhd.conf markers:",", ".join(k for k,v in markers.items() if v) or "none")
print("Collected files:",len(files))
print(result["warning"])
