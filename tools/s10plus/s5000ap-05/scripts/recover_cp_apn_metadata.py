#!/usr/bin/env python3
"""Read the pinned DTK9/EFUJ2 MAIN image's APN descriptors. No device/NV access."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("main", help="MAIN segment extracted from DTK9 or live EFUJ2 RADIO")
a = p.parse_args()
b = Path(a.main).read_bytes()
tables = {
    "dd991cf657e7703ea5e0e2c0b0c3ff9cf4430246d825f05ea26bb6ad0fe22398": ("G975FXXS9DTK9", 0x4014d0a4),
    "16bfb9fef7a32dcb5feb314d96d5d56d2a496e4d5d6956f0ce840f356042213c": ("G975FXXSEFUJ2", 0x4014d084),
}
digest = hashlib.sha256(b).hexdigest()
if digest not in tables:
    raise SystemExit("wrong MAIN image; descriptor addresses are firmware-specific")
firmware, table = tables[digest]
base, stride = 0x40010000, 20
for index, expected in [(220, "NASU.LTE.ATTACH.APN.INFO"),
                        (224, "DS_NASU.LTE.ATTACH.APN.INFO")]:
    address = table + stride * index
    name, size, count, flags, dtype = struct.unpack_from("<5I", b, address-base)
    text = b[name-base:b.index(b"\0", name-base)].decode("ascii")
    if text != expected or size * count != 360:
        raise SystemExit("descriptor mismatch")
    print(json.dumps(dict(firmware=firmware, index=index, name=text, descriptor_va=hex(address),
                         element_size=size, count=count, value_size=size*count,
                         flags=flags, type_descriptor_va=hex(dtype))))
