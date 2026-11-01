#!/usr/bin/env python3
"""Software-center capability report (native RPM vs blocked Flatpak).

GNOME Software + PackageKit/DNF is the native transaction surface.  Flatpak is
only reported usable when user namespaces, bubblewrap, portals and a runtime
are all genuinely present.  On the S10+ the running kernel advertises
CONFIG_USER_NS=y, but the vendor create_user_ns() LOD/root gate can still deny
unshare(CLONE_NEWUSER); that live result, not the config flag, decides status.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from typing import Any, Dict, List, Optional


def _cmd(name: str) -> Optional[str]:
    return shutil.which(name)


def _user_ns_ok() -> Dict[str, Any]:
    try:
        with open("/proc/sys/kernel/unprivileged_userns_clone") as fh:
            if fh.read().strip() == "0":
                return {"ok": False, "detail": "kernel.unprivileged_userns_clone=0"}
    except OSError:
        pass
    try:
        p = subprocess.run(["unshare", "-U", "true"], capture_output=True,
                           timeout=3, text=True)
        if p.returncode == 0:
            return {"ok": True, "detail": "unshare -U succeeded"}
        return {"ok": False, "detail": (p.stderr or "unshare -U failed").strip()[:240]}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"ok": False, "detail": str(exc)}


class SoftwareProvider:
    def status(self) -> Dict[str, Any]:
        native = {
            "dnf5": bool(_cmd("dnf5")),
            "dnf": bool(_cmd("dnf")),
            "rpm": bool(_cmd("rpm")),
            "packagekitd": bool(_cmd("packagekitd") or os.path.exists("/usr/libexec/packagekitd")),
            "gnome_software": bool(_cmd("gnome-software")),
            "nuxel_software": os.path.exists("/usr/lib/nuxel/nuxel-software"),
            "appstream": os.path.isdir("/usr/share/app-info") or os.path.isdir("/usr/share/metainfo"),
        }
        flatpak = {
            "flatpak": bool(_cmd("flatpak")),
            "bwrap": bool(_cmd("bwrap")),
            "portal": bool(_cmd("xdg-desktop-portal") or os.path.exists("/usr/libexec/xdg-desktop-portal")),
            "user_namespace": _user_ns_ok(),
        }
        flatpak_ok = all([flatpak["flatpak"], flatpak["bwrap"], flatpak["portal"],
                          flatpak["user_namespace"]["ok"]])
        native_ok = native["rpm"] and (native["dnf5"] or native["dnf"])
        return {
            "success": True,
            "schema": "nuxel.software-status/1",
            "native": native,
            "native_ready": native_ok,
            "native_backend": "DNF5" if native["dnf5"] else ("DNF" if native["dnf"] else None),
            "native_ui": ("/usr/lib/nuxel/nuxel-software" if os.path.exists("/usr/lib/nuxel/nuxel-software") else ("/usr/bin/gnome-software" if native["gnome_software"] else None)),
            "polkit": os.path.exists("/usr/bin/pkexec"),
            "flatpak": flatpak,
            "flatpak_ready": flatpak_ok,
            "flatpak_blocker": None if flatpak_ok else (
                ("user namespace creation denied by the kernel"
                 + ("" if not flatpak["user_namespace"].get("detail") else ": " + flatpak["user_namespace"]["detail"]))
                if not flatpak["user_namespace"]["ok"] else
                "missing Flatpak/Bubblewrap/portal prerequisite"),
            "source_policy": "local/NuxTore only for this mission; native RPM uses configured Fedora repos",
            "source": "software_provider",
        }


_PROVIDER: Optional[SoftwareProvider] = None


def get_provider() -> SoftwareProvider:
    global _PROVIDER
    if _PROVIDER is None:
        _PROVIDER = SoftwareProvider()
    return _PROVIDER


def handle(verb: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    if verb in ("status", "get"):
        return get_provider().status()
    return {"success": False, "error": "unknown software verb", "verb": verb}
