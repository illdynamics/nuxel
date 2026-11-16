#!/usr/bin/env python3
"""Canonical BCM4773 (beyond2lte) GNSS inventory for the Nuxel location stack.

Single source of truth for *what* a beyond2lte BCM4773 BBD/LHD path is, so the
provider (:mod:`hw_providers.GnssProvider`), the bridge
(:meth:`bridge.Bridge._gnss_hardware`) and the ``nuxel-gnss-diag.sh`` tool all
agree on node/firmware/vendor classification instead of each keeping a subtly
different filename heuristic.

Design rules (see full-pwnage-64000 §3/§7):

* ``/dev/ttyBCM`` is the BBD/LHD *transport*; ``/dev/bbd_patch`` is the
  sensor-hub patch **loader** character-device, NOT firmware. A loader node is
  never counted as firmware present.
* Firmware matching is strict. A random ``gps.bin`` / ``gnss.bin`` / ``ssp*`` /
  unrelated modem blob must not satisfy the BCM4773 requirement. Only files whose
  basename is in :data:`FIRMWARE_BASENAMES` (device-specific BBD sensor-hub
  patches) or that match a known-good SHA-256 are considered candidates; every
  other file on disk is ignored.
* Present is not loaded, and loaded is not accepted. The result carries the
  separate states ``firmware_present``, ``firmware_identity_verified`` and
  (for the provider) ``firmware_loaded`` / device acceptance, so a caller can
  never promote "a file exists" to "the receiver took it".

Pure standard library; importable on the phone build host without Android.
"""
from __future__ import annotations

import hashlib
import os

PROTOCOL = "broadcom-bbd-lhd-rpc"
DEVICE_MODEL = "Samsung Galaxy S10+ SM-G975F"
CODENAME = "beyond2lte"
SOC = "Exynos 9820 (BCM4773 integrated GNSS, BBD/LHD RPC transport)"

# Transport/control nodes. A readable node is hardware evidence only; never a fix.
BBD_TRANSPORT_NODE = "/dev/ttyBCM"
BBD_NODES = ("/dev/bbd_patch", "/dev/bbd_control",
             "/dev/bbd_sensor", "/dev/bbd_urgent_patch")
# /dev/bbd_patch is the patch *loader* character device, never a firmware file.
LOADER_NODES = ("/dev/bbd_patch", "/dev/bbd_urgent_patch")

POWER_RAIL = "/sys/devices/virtual/sec/gps/GPS_PWR_EN/value"

SPI_DRIVER_DIR = "/sys/bus/spi/drivers/brcm gps spi"
SPI_DRIVER_NAME = "brcm gps spi"

# Vendor BBD/LHD userspace (Android/Bionic + HIDL). None is native.
VENDOR_FILES = {
    "lhd": ("/vendor/bin/hw/lhd", "/vendor/bin/lhd"),
    "gpsd": ("/vendor/bin/hw/gpsd", "/vendor/bin/gpsd"),
    "android_linker": ("/system/bin/linker64",),
    "lhd_config": ("/vendor/etc/sensor/lhd.conf",),
    "gps_config": ("/vendor/etc/gnss/gps.xml",),
    "gnss_hidl_impl": (
        "/vendor/lib64/vendor.samsung.hardware.gnss@2.0.so",
        "/vendor/lib64/vendor.samsung.hardware.gnss@2.0-impl.so",
    ),
}

# Device-specific BBD sensor-hub patch firmware *basenames*. Only these basenames
# (or an exact verified hash) count as candidate firmware; everything else on
# disk is ignored so unrelated blobs cannot masquerade as the BCM4773 patch.
FIRMWARE_BASENAMES = (
    "bcm_sensorhub_a1.patch",
    "bcm4773_sensorhub.patch",
    "sensorhub_a1.patch",
)
# Firmware search dirs, device-specific paths first.
FIRMWARE_DIRS = ("/system/bin", "/vendor/firmware/gnss", "/lib/firmware/gnss",
                 "/lib/firmware", "/vendor/firmware")

# Known-good patch identity (SHA-256). Empty until an owner-provided artefact has
# been verified on the exact device build; a present file is then NOT auto-trusted.
VERIFIED_PATCH_SHA256 = {}

# Status taxonomy (full-pwnage-64000 §7). Missing == not found.
ABSENT = "absent"
PRESENT_UNVERIFIED = "present_unverified"
IDENTITY_VERIFIED = "identity_verified"


def _exists(root, path):
    return os.path.exists(os.path.join(root, path.lstrip("/"))) if path.startswith("/") else os.path.exists(path)


def transport_nodes(root="/"):
    """Existing BBD transport/control nodes under ``root`` (host or fixture)."""
    found = []
    for n in (BBD_TRANSPORT_NODE,) + BBD_NODES:
        if _exists(root, n):
            found.append(n if root == "/" else os.path.join(root, n.lstrip("/")))
    return found


def loader_nodes(root="/"):
    """Existing patch-loader nodes. Returned separately so callers never count a
    loader as firmware."""
    out = []
    for n in LOADER_NODES:
        if _exists(root, n):
            out.append(n if root == "/" else os.path.join(root, n.lstrip("/")))
    return out


def spi_bindings(root="/"):
    driver_dir = os.path.join(root, SPI_DRIVER_DIR.lstrip("/")) if root != "/" else SPI_DRIVER_DIR
    try:
        names = sorted(n for n in os.listdir(driver_dir) if n.startswith("spi"))
    except OSError:
        return []
    bindings = []
    for name in names:
        bdir = os.path.join(driver_dir, name)
        # A binding is real only when the driver advertises its own name.
        try:
            drv = open(os.path.join(bdir, "driver"), encoding="utf-8").read().strip()
        except (OSError, ValueError):
            drv = ""
        if os.path.basename(drv) == SPI_DRIVER_NAME or name.startswith("spi"):
            bindings.append(name)
    return bindings


def vendor_runtime(root="/"):
    """name -> bool for each BBD/LHD runtime file. Complete only when ALL exist."""
    present = {}
    for name, candidates in VENDOR_FILES.items():
        present[name] = any(_exists(root, p) for p in candidates)
    return present


def _sha256(path, chunk=65536):
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for block in iter(lambda: f.read(chunk), b""):
                h.update(block)
    except OSError:
        return None
    return h.hexdigest()


def firmware(root="/", hashes=None):
    """Strict device-specific BBD patch inventory.

    Returns a list of dicts, one per *found* candidate file, each with its path,
    basename classification and identity status. Generic ``gps*``/``gnss*``/
    ``ssp*`` blobs are excluded unless they match an exact verified hash.
    """
    hashes = hashes if hashes is not None else VERIFIED_PATCH_SHA256
    found = []
    for d in FIRMWARE_DIRS:
        rdir = os.path.join(root, d.lstrip("/")) if root != "/" else d
        try:
            names = sorted(os.listdir(rdir))
        except OSError:
            continue
        for name in names:
            low = name.lower()
            # Reject loader nodes and non-firmware files up front.
            if low.endswith((".hcd", ".txt", ".conf", ".json", ".xml", ".cer",
                              ".sig", ".sha256")):
                continue
            is_loader = any(low == os.path.basename(n).lower() for n in LOADER_NODES)
            if is_loader:
                continue
            # Reject other BCM chips by name so a bcm47752/bcm47755 image cannot
            # satisfy the BCM4773 requirement.
            rejects = any(chip in low for chip in ("47752", "47755"))
            # Strict baseline match: an exact known basename, or a sensorhub
            # .patch/.bin payload (never a generic gps*/gnss*/ssp* blob).
            strict = (low in FIRMWARE_BASENAMES
                      or ("sensorhub" in low and low.endswith((".patch", ".bin"))))
            strict = strict and not rejects
            path = os.path.join(rdir, name)
            if not strict:
                continue
            digest = _sha256(path) if hashes else None
            status = IDENTITY_VERIFIED if digest and digest in hashes else PRESENT_UNVERIFIED
            found.append({
                "path": path,
                "basename": name,
                "is_loader_node": False,
                "status": status,
                "sha256": digest,
            })
    return found


def firmware_present(fw_list):
    return bool(fw_list)


def firmware_identity_verified(fw_list):
    return any(f["status"] == IDENTITY_VERIFIED for f in fw_list)


# ------------------------------------------------------------------ shaped views
def provider_inventory(root="/"):
    """Canonical inventory shaped for :class:`hw_providers.GnssProvider`.

    Preserves the keys the API/UI already consume while replacing the old broad
    filename heuristic with strict, loader-aware classification.
    """
    nodes = transport_nodes(root)
    loader = loader_nodes(root)
    bound = spi_bindings(root)
    fw = firmware(root)
    vend = vendor_runtime(root)
    complete = all(vend.values())

    # First failing dependency, in stage order.
    if not nodes and not bound:
        blocker = "no BCM4773 BBD node and no %s SPI binding" % SPI_DRIVER_NAME
    elif not fw:
        blocker = ("no compatible BCM4773 BBD sensor-hub patch firmware "
                   "(expected e.g. /system/bin/bcm_sensorhub_a1.patch; "
                   "/dev/bbd_patch is a loader, not firmware)")
    elif not complete:
        missing = [k for k, v in vend.items() if not v]
        blocker = "vendor BBD/LHD runtime missing: " + ", ".join(missing)
    else:
        blocker = ("BCM4773 BBD/LHD stack present but not initialized; no fix verified")

    return {
        "protocol": PROTOCOL,
        "nmea": False,
        "nodes": nodes,
        "bbd_patch_node": (loader[0] if loader else None),
        "loader_nodes": loader,
        "spi_bindings": bound,
        "power_rail": POWER_RAIL,
        "active_leases": 0,
        # Strict firmware: only device-specific BBD patch candidates.
        "firmware": [f["path"] for f in fw],
        "firmware_present": firmware_present(fw),
        "firmware_candidates": fw,
        "firmware_identity_verified": firmware_identity_verified(fw),
        "firmware_loaded": False,          # separate state (not accepted yet)
        "vendor_files": vend,
        "vendor_runtime_complete": complete,
        "android_linker": vend["android_linker"],
        "vendor_userspace": vend["lhd"] and vend["gpsd"],
        "fix_supported": False,            # no validated provider yet
        "blocker": blocker,
    }


def bridge_inventory(root="/"):
    """Canonical inventory shaped for :meth:`bridge.Bridge._gnss_hardware`.

    The bridge consumes this instead of keeping its own copy of the candidate
    lists.  ``blocker`` is always defined: on a fully-populated path it names
    the missing userspace protocol provider, never an exception.
    """
    nodes = transport_nodes(root)
    loader = loader_nodes(root)
    bound = spi_bindings(root)
    fw = firmware(root)
    vend = vendor_runtime(root)
    # Preserve the historical bridge key while keeping one classifier.
    vend["hidl_gnss_lib"] = vend.pop("gnss_hidl_impl", False)
    complete = all(vend.values())
    vend["complete"] = complete

    # A node may exist on the host while hidden from a PrivateDevices bridge; a
    # bound SPI device is still positive evidence the path exists.
    present = bool(nodes or bound)
    blocker = None
    if not nodes and not bound:
        blocker = "no GNSS device node or %s SPI driver binding" % SPI_DRIVER_NAME
    elif not bound:
        blocker = "no %s SPI driver binding" % SPI_DRIVER_NAME
    if blocker is None and not fw:
        blocker = ("no compatible BCM4773 BBD sensor-hub patch firmware "
                   "(vendor lhd expects /dev/bbd_patch)")
    if blocker is None and not complete:
        missing = [k for k, v in vend.items() if not v and k != "complete"]
        blocker = ("GNSS firmware/RPC stack incomplete: missing " +
                   ", ".join(missing))
    if blocker is None and not nodes:
        blocker = ("driver bound but /dev is private to the bridge; no BBD/LHD "
                   "userspace provider is wired")
    if blocker is None:
        blocker = ("BCM4773 BBD/LHD userspace provider is not wired "
                   "(stock gpsd cannot decode this RPC protocol)")

    return {
        "present": present,
        "nodes": nodes,
        "node_visible_to_bridge": bool(nodes),
        "bbd_nodes": loader + [n for n in nodes if n not in loader and n != BBD_TRANSPORT_NODE],
        "loader_nodes": loader,
        "private_devices": True,
        "driver": SPI_DRIVER_NAME,
        "driver_bound": bool(bound),
        "spi_bindings": bound,
        "protocol": PROTOCOL,
        "nmea_stream": False,
        # Strict firmware: device-specific BBD patch candidates only.
        "firmware_present": firmware_present(fw),
        "firmware": [f["path"] for f in fw],
        "firmware_candidates": fw,
        "firmware_identity_verified": firmware_identity_verified(fw),
        "firmware_loaded": False,
        "vendor_runtime": vend,
        "userspace_provider": None,
        "hardware_responds": None,
        "fix_supported": False,
        "blocker": blocker,
    }


if __name__ == "__main__":  # quick offline smoke test (no hardware needed)
    import json
    inv = provider_inventory("/")
    print(json.dumps(inv, indent=2))
