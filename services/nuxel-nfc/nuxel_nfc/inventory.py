"""Read-only NFC inventory.  Never opens /dev/sec-nfc."""

from __future__ import annotations

import glob
import hashlib
import json
import os
import subprocess

from . import abi


def _read(path):
    try:
        with open(path) as fh:
            return fh.read().strip()
    except OSError:
        return None


def _glob(patterns):
    out = []
    for pat in patterns:
        out.extend(glob.glob(pat))
    return sorted(set(out))


def sha256_file(path):
    try:
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def firmware_status(path=None):
    path = path or abi.FIRMWARE_PATH
    size = None
    try:
        size = os.path.getsize(path)
    except OSError:
        pass
    digest = sha256_file(path)
    return {
        "path": path,
        "present": os.path.isfile(path),
        "size": size,
        "sha256": digest,
        "size_match": size == abi.FIRMWARE_SIZE,
        "hash_match": digest == abi.FIRMWARE_SHA256,
        "runtime_verified": False,
        "note": "a matching file is not proof that controller firmware is loaded or accepted",
    }


def device_node(path=None):
    path = path or abi.DEVICE_PATH
    try:
        st = os.stat(path)
    except OSError:
        return {"path": path, "present": False, "mode": None, "uid": None, "gid": None,
                "major": None, "minor": None}
    return {
        "path": path, "present": True, "mode": oct(st.st_mode & 0o777),
        "uid": st.st_uid, "gid": st.st_gid,
        "major": os.major(st.st_rdev), "minor": os.minor(st.st_rdev),
    }


def kernel_nfc():
    for path in ("/boot/config-%s" % os.uname().release, "/proc/config.gz"):
        if path.endswith(".gz"):
            try:
                import gzip
                with gzip.open(path, "rt") as fh:
                    text = fh.read()
            except OSError:
                continue
        else:
            text = _read(path) or ""
        for line in text.splitlines():
            if line.startswith("CONFIG_NFC="):
                return line.split("=", 1)[1] in ("y", "m")
            if line.strip() == "# CONFIG_NFC is not set":
                return False
    return os.path.isdir(abi.GENERIC_NFC_CLASS)


def i2c_binding():
    link = abi.CONTROLLER_I2C
    return {
        "expected": link,
        "present": os.path.exists(link),
        "driver": _read(os.path.join(link, "driver", "module")) or None,
        "name": _read(os.path.join(link, "name")),
    }


def service_state():
    try:
        with open(abi.STATE_PATH) as fh:
            doc = json.load(fh)
        return doc if isinstance(doc, dict) else {}
    except (OSError, ValueError):
        return {}


def last_tag():
    try:
        with open(abi.LAST_TAG_PATH) as fh:
            doc = json.load(fh)
        return doc if isinstance(doc, dict) else None
    except (OSError, ValueError):
        return None


def inventory(root="/"):
    root = (root or "/").rstrip("/")

    def p(path):
        return root + path if root else path

    fw = firmware_status(p(abi.FIRMWARE_PATH))
    node = device_node(p(abi.DEVICE_PATH))
    i2c = i2c_binding()
    if root:
        i2c["present"] = os.path.exists(p(abi.CONTROLLER_I2C))
    sec_class = _glob([p(abi.SEC_NFC_CLASS) + "/*"])
    generic = _glob([p(abi.GENERIC_NFC_CLASS) + "/*"])
    return {
        "controller_present": bool(i2c["present"]),
        "i2c": i2c,
        "firmware_file_verified": bool(fw["hash_match"] and fw["size_match"]),
        "firmware": fw,
        "vendor_transport_present": bool(node["present"]),
        "transport": node,
        "kernel_nfc_core": kernel_nfc() if not root else bool(generic),
        "generic_nfc_class": generic,
        "vendor_class": sec_class,
        "protocol_adapter_ready": bool(node["present"] and fw["hash_match"]),
        "protocol_verified": abi.PROTOCOL_VERIFIED,
        "tag_reader_ready": False,
        "service": service_state(),
        "last_tag": last_tag(),
        "payment_supported": False,
        "secure_element_supported": False,
    }
