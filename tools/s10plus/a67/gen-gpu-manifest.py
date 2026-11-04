#!/usr/bin/env python3
"""Generate release/s10plus/gpu/gpu-manifest.json and SHA256SUMS.

PWNAGE-60000: the image builder must fail closed.  This manifest is the single
canonical list of GPU assets, pinned source commits, ELF build IDs, install
paths, symlinks and the production profile.  Run from the repository root.
"""
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GPU = ROOT / "release/s10plus/gpu"
PINS = ROOT / "tools/s10plus/a67/gpu-build-pins.env"

FILES = [
    ("libEGL_mesa.so.0.0.0", "/usr/lib64/libEGL_mesa.so.0.0.0", "0644",
     "elf-shared-library", "libEGL_mesa.so.0", True),
    ("libgallium_dri.so", "/usr/lib64/libgallium_dri.so", "0755",
     "elf-shared-library", None, True),
    ("libwlroots-0.19.so", "/usr/lib64/libwlroots-0.19.so", "0644",
     "elf-shared-library", "libwlroots-0.19.so", True),
    ("nuxel-graphics-profile", "/usr/lib/nuxel/nuxel-graphics-profile", "0755",
     "python-helper", None, True),
    ("graphics-profile.json", "/etc/nuxel/graphics/graphics-profile.json", "0644",
     "json-policy", None, True),
    ("egl-kbase.json", "/etc/nuxel/egl-kbase.json", "0644",
     "glvnd-vendor-json", None, True),
    ("50_mesa.json", "/usr/share/glvnd/egl_vendor.d/50_mesa.json", "0644",
     "glvnd-vendor-json", None, True),
    ("nuxel-gpu-status", "/usr/lib/nuxel/nuxel-gpu-status", "0755",
     "diagnostic-helper", None, True),
    ("nuxel-wayland-gpu-wrapper.sh",
     "/usr/lib/nuxel/nuxel-wayland-gpu-wrapper.sh", "0755",
     "session-script", None, True),
    ("nuxel-session.sh", "/usr/lib/nuxel/nuxel-session.sh", "0755",
     "session-script", None, True),
]

SYMLINKS = [
    ("/usr/lib64/libEGL_mesa.so.0", "libEGL_mesa.so.0.0.0"),
    ("/usr/lib64/dri/panfrost_dri.so", "../libgallium_dri.so"),
    ("/usr/lib64/dri/exynos_dri.so", "../libgallium_dri.so"),
]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build_id(path):
    try:
        out = subprocess.run(["readelf", "-n", str(path)], capture_output=True,
                             text=True, check=True).stdout
        m = re.search(r"Build ID:\s*([0-9a-fA-F]+)", out)
        return m.group(1).lower() if m else None
    except Exception:
        return None


def parse_pins():
    pins = {}
    for line in PINS.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        pins[key.strip()] = value.strip().strip('"')
    return pins


def main():
    pins = parse_pins()
    files = []
    sums = []
    for source, install, mode, kind, soname, required in FILES:
        path = GPU / source
        if not path.is_file():
            raise SystemExit("missing release GPU asset: %s" % path)
        digest = sha256(path)
        entry = {
            "source": source,
            "install": install,
            "sha256": digest,
            "mode": mode,
            "kind": kind,
            "required": required,
        }
        if soname:
            entry["soname"] = soname
        if kind == "elf-shared-library":
            entry["arch"] = "aarch64"
            entry["build_id"] = build_id(path)
        files.append(entry)
        sums.append("%s  %s" % (digest, source))

    manifest = {
        "schema": "nuxel.gpu-manifest/1",
        "mission": "PWNAGE-60000",
        "generated_by": "tools/s10plus/a67/gen-gpu-manifest.py",
        "target": {
            "device": "Samsung Galaxy S10+ SM-G975F",
            "codename": "beyond2lte",
            "soc": "Exynos 9820",
            "gpu": "Mali-G76 MP12",
            "arch": "aarch64",
            "abi": pins.get("TARGET_ABI"),
            "fedora_release": pins.get("FEDORA_RELEASE"),
        },
        "build": {
            "mesa": {
                "repo": pins.get("MESA_REPO"),
                "commit": pins.get("MESA_COMMIT"),
                "version": pins.get("MESA_VERSION"),
                "patch": {
                    "path": pins.get("MESA_PATCH"),
                    "sha256": sha256(ROOT / pins["MESA_PATCH"]),
                },
                "configure": [
                    "platforms=wayland", "gallium-drivers=panfrost",
                    "egl=enabled", "gles2=enabled", "gbm=disabled",
                    "glx=disabled", "unversion-libgallium=true",
                ],
            },
            "wlroots": {
                "repo": pins.get("WLROOTS_REPO"),
                "tag": pins.get("WLROOTS_TAG"),
                "commit": pins.get("WLROOTS_COMMIT"),
                "patch": {
                    "path": pins.get("WLROOTS_PATCH"),
                    "sha256": sha256(ROOT / pins["WLROOTS_PATCH"]),
                },
                "configure": [
                    "renderers=gles2", "backends=drm,libinput",
                    "allocators=gbm,udmabuf",
                ],
            },
            "glvnd": {"package": pins.get("GLVND_PACKAGE")},
            "toolchain": {
                "note": "Recorded from the live Fedora 43 aarch64 builder; "
                        "byte-identical rebuilds require the same toolchain.",
                "gcc": "15.3.1 20260722 (Red Hat 15.3.1-1)",
                "libc": "glibc 2.42",
                "meson_ninja": "Fedora 43 packages",
            },
        },
        "profile": {
            "path": "/etc/nuxel/graphics/graphics-profile.json",
            "default_profile": "gpu-rendered-shm-presented",
            "fallback": "software-safe",
            "unavailable": ["gpu-rendered-dmabuf-presented", "fully-accelerated"],
        },
        "probe": {
            "source": "tools/s10plus/a67/nuxel-kbase-egl-probe.c",
            "sha256": sha256(ROOT / "tools/s10plus/a67/nuxel-kbase-egl-probe.c"),
            "install": "/usr/lib/nuxel/nuxel-kbase-egl-probe",
            "required": True,
        },
        "files": files,
        "symlinks": [{"path": p, "target": t} for p, t in SYMLINKS],
        "verification": {
            "sha256sums": "SHA256SUMS",
            "image_verifier": "tools/s10plus/a67/nuxel-gpu-image-verify.sh",
        },
    }
    (GPU / "SHA256SUMS").write_text("\n".join(sums) + "\n")
    (GPU / "gpu-manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print("wrote", GPU / "gpu-manifest.json")
    print("wrote", GPU / "SHA256SUMS")


if __name__ == "__main__":
    main()
