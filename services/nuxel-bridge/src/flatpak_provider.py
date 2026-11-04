#!/usr/bin/env python3
"""Nuxel Flatpak provider (PWNAGE-56000).

This module is the ONE lifecycle authority for Flatpak on Nuxel.  It is called
by the root HTTP bridge, but every subprocess invocation is an argv vector built
from an allowlisted verb and a validated Flatpak app id.  No shell is used and no
client-supplied path, command, option or remote string is ever executed.

Design rules:
  * system installs are performed by the root bridge with ``flatpak --system``;
  * user installs and all user-side probes run as the real ``nuxel`` user on the
    per-user D-Bus bus (``/run/user/1000/bus``), never on the root session bus;
  * installs/updates/uninstalls are background jobs with a bounded log so the
    UI can show progress without blocking the HTTP request;
  * status is evidence-based: a missing kernel namespace, a setuid bwrap or a
    missing portal is reported as not ready, never hidden behind a green badge.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import threading
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

FLATPAK = shutil.which("flatpak") or "/usr/bin/flatpak"
BWRAP = "/usr/bin/bwrap"
CRISPY_DOOM_APP_ID = "io.github.fabiangreffrath.Doom"
CRISPY_DOOM_WRAPPER = "/usr/lib/nuxel/nuxel-flatpak-doom"
REAL_BWRAP = "/usr/libexec/bwrap.real"
SYSTEM_INSTALL = "/var/lib/flatpak"
USER_HOME = "/home/nuxel"
USER_RUNTIME = "/run/user/1000"
USER_BUS = USER_RUNTIME + "/bus"
SESSION_BUS = "/run/nuxel-wayland/bus"
SESSION_RUNTIME = "/run/nuxel-wayland"
PORTAL_NAME = "org.freedesktop.portal.Desktop"
APP_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
ALLOWED_REMOTES = {"flathub", "fedora"}
ALLOWED_SCOPES = {"system", "user"}
MAX_LOG_BYTES = 64 * 1024


def _base_env(scope: str = "system", user_bus: bool = False) -> Dict[str, str]:
    env = dict(os.environ)
    env.update({
        "LC_ALL": "C",
        "LANG": "C",
        "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
    })
    if scope == "user" or user_bus:
        env.update({
            "HOME": USER_HOME,
            "USER": "nuxel",
            "LOGNAME": "nuxel",
            "XDG_RUNTIME_DIR": USER_RUNTIME,
            "DBUS_SESSION_BUS_ADDRESS": "unix:path=" + USER_BUS,
            "XDG_CURRENT_DESKTOP": "Nuxel",
            "WAYLAND_DISPLAY": "wayland-0",
            "GDK_BACKEND": "wayland",
            "GSK_RENDERER": "cairo",
            "LIBGL_ALWAYS_SOFTWARE": "1",
            "XDG_DATA_DIRS": "/var/lib/flatpak/exports/share:/usr/local/share:/usr/share",
        })
    else:
        env.update({
            "HOME": "/root",
            "USER": "root",
            "LOGNAME": "root",
            "XDG_RUNTIME_DIR": SESSION_RUNTIME,
            "DBUS_SESSION_BUS_ADDRESS": "unix:path=" + SESSION_BUS,
        })
    return env


def _user_argv(argv: List[str]) -> List[str]:
    """Wrap an argv so systemd executes it as nuxel.

    The HTTP bridge runs with NoNewPrivileges=yes; ``runuser`` is denied there
    even for root.  ``systemd-run --uid=nuxel`` asks the system manager to spawn
    a transient unit as the real user, which is the same mechanism the existing
    native-app launch path uses.  No shell is involved.
    """
    unit = "nuxel-fp-%s" % uuid.uuid4().hex[:8]
    return [
        "/usr/bin/systemd-run", "--unit=" + unit, "--collect", "--quiet",
        "--wait", "--pipe", "--uid=nuxel", "--gid=nuxel",
        "--property=SupplementaryGroups=audio",
        "--setenv=HOME=" + USER_HOME,
        "--setenv=USER=nuxel",
        "--setenv=LOGNAME=nuxel",
        "--setenv=XDG_RUNTIME_DIR=" + USER_RUNTIME,
        "--setenv=DBUS_SESSION_BUS_ADDRESS=unix:path=" + USER_BUS,
        "--setenv=XDG_CURRENT_DESKTOP=Nuxel",
        "--setenv=WAYLAND_DISPLAY=wayland-0",
        "--setenv=XDG_DATA_DIRS=/var/lib/flatpak/exports/share:/usr/local/share:/usr/share",
        "--setenv=XDG_DATA_HOME=" + USER_HOME + "/.local/share",
        "--setenv=LC_ALL=C",
        "--",
    ] + list(argv)


def _system_job_argv(argv: List[str]) -> List[str]:
    """Run a root Flatpak transaction in a transient system unit.

    The HTTP bridge itself is ProtectSystem=strict with PrivateTmp; it cannot
    write /var/lib/flatpak or create a log outside its ReadWritePaths.  The
    system manager's transient unit runs in the normal host filesystem view,
    exactly like the existing native-app launch path.
    """
    unit = "nuxel-fp-%s" % uuid.uuid4().hex[:8]
    return [
        "/usr/bin/systemd-run", "--unit=" + unit, "--collect", "--quiet",
        "--wait", "--pipe",
        "--setenv=HOME=/root",
        "--setenv=USER=root",
        "--setenv=LOGNAME=root",
        "--setenv=LC_ALL=C",
        "--setenv=PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        "--",
    ] + list(argv)


def _run(argv: List[str], timeout: int = 60, scope: str = "system",
         as_user: bool = False) -> Tuple[int, str, str]:
    """Run one argv vector.  Never uses shell=True."""
    env = _base_env(scope=scope, user_bus=as_user or scope == "user")
    cmd = list(argv)
    if as_user or scope == "user":
        cmd = _user_argv(cmd)
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           env=env, check=False)
        return p.returncode, (p.stdout or ""), (p.stderr or "")
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, "", str(exc)


def _flatpak(scope: str = "system") -> List[str]:
    return [FLATPAK, "--" + scope]


def _valid_app_id(app_id: Any) -> Optional[str]:
    if not isinstance(app_id, str):
        return None
    app_id = app_id.strip()
    if not APP_ID_RE.match(app_id):
        return None
    return app_id


def _parse_tsv(text: str, columns: List[str]) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    for line in (text or "").splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) < len(columns):
            parts += [""] * (len(columns) - len(parts))
        rows.append({c: parts[i].strip() for i, c in enumerate(columns)})
    return rows


def _read_kv(path: str) -> Dict[str, str]:
    """Read ONLY the [Desktop Entry] group.

    Flatpak desktop files contain many [Desktop Action ...] groups.  Reading the
    whole file makes Firefox's name become "Open Profile Manager" because the
    last Name= wins.  The launcher must show the main application name, icon and
    Exec, so parsing stops at the next group header.
    """
    out: Dict[str, str] = {}
    in_main = False
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for raw in fh:
                line = raw.strip()
                if line.startswith("["):
                    if line == "[Desktop Entry]":
                        in_main = True
                        continue
                    if in_main:
                        break
                    continue
                if not in_main or not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                # First occurrence wins inside the main group.
                out.setdefault(k, v.strip())
    except OSError:
        pass
    return out


def _icon_dirs(scope: str) -> List[str]:
    roots = []
    if scope == "system":
        roots += [
            SYSTEM_INSTALL + "/exports/share/icons/hicolor",
            SYSTEM_INSTALL + "/app",
        ]
    else:
        roots += [
            USER_HOME + "/.local/share/flatpak/exports/share/icons/hicolor",
            USER_HOME + "/.local/share/flatpak/app",
        ]
    roots += ["/usr/share/icons/hicolor"]
    return roots


def _find_icon(app_id: str, icon_name: str, scope: str) -> Optional[str]:
    """Find an installed app icon without accepting a client path."""
    names = [icon_name, app_id]
    exts = ("png", "svg", "xpm")
    sizes = ("scalable", "256x256", "128x128", "64x64", "48x48", "32x32")
    roots = _icon_dirs(scope)
    for root in roots:
        for size in sizes:
            for name in names:
                if not name:
                    continue
                for ext in exts:
                    # exports/share/icons/hicolor/<size>/apps/<name>.<ext>
                    p = os.path.join(root, size, "apps", name + "." + ext)
                    if os.path.isfile(p):
                        return p
                    # app/<id>/current/active/files/share/icons/... fallback
                    if root.endswith("/app"):
                        p = os.path.join(root, app_id, "current", "active", "files",
                                         "share", "icons", "hicolor", size, "apps",
                                         name + "." + ext)
                        if os.path.isfile(p):
                            return p
    return None


class FlatpakProvider:
    def __init__(self) -> None:
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._cache: Dict[str, Tuple[float, Any]] = {}

    # ---- read-only evidence -------------------------------------------------

    def status(self) -> Dict[str, Any]:
        present = os.path.isfile(FLATPAK) and os.access(FLATPAK, os.X_OK)
        version = ""
        arches = ""
        if present:
            rc, out, err = _run([FLATPAK, "--version"], timeout=5)
            version = out.strip() if rc == 0 else (err.strip() or "unavailable")
            rc, out, err = _run([FLATPAK, "--supported-arches"], timeout=5)
            arches = out.strip() if rc == 0 else ""
        bwrap = {
            "path": BWRAP,
            "real_path": REAL_BWRAP,
            "exists": os.path.isfile(BWRAP),
            "real_exists": os.path.isfile(REAL_BWRAP),
            "owner": None, "group": None, "mode": None, "setuid": None,
            "caps": "", "version": "",
        }
        try:
            st = os.stat(BWRAP)
            bwrap.update({
                "owner": str(st.st_uid), "group": str(st.st_gid),
                "mode": oct(st.st_mode & 0o7777), "setuid": bool(st.st_mode & 0o4000),
            })
        except OSError:
            pass
        try:
            p = subprocess.run(["/usr/sbin/getcap", BWRAP, REAL_BWRAP],
                               capture_output=True, text=True, timeout=5)
            bwrap["caps"] = (p.stdout or "").strip()
        except (OSError, subprocess.TimeoutExpired):
            pass
        if os.path.isfile(REAL_BWRAP):
            rc, out, err = _run([REAL_BWRAP, "--version"], timeout=5)
            bwrap["version"] = out.strip() if rc == 0 else ""
        # The namespace probe must be the ordinary user, not root.
        rc_u, out_u, err_u = _run(["/usr/bin/unshare", "--user", "true"],
                                  timeout=5, as_user=True)
        rc_m, out_m, err_m = _run(["/usr/bin/unshare", "--map-root-user", "true"],
                                  timeout=5, as_user=True)
        remotes = self.remotes()
        installed = self.list_installed()
        apps = installed.get("apps", [])
        bus_names = self._user_bus_names()
        portal_cache = {}
        try:
            with open("/run/nuxel-portal-ready.json", "r", encoding="utf-8") as fh:
                portal_cache = json.load(fh)
        except (OSError, ValueError):
            portal_cache = {}
        portal_ok = bool(portal_cache.get("portal")) or bool(bus_names.get(PORTAL_NAME))
        gtk_ok = bool(portal_cache.get("gtk")) or bool(bus_names.get("org.freedesktop.impl.portal.desktop.gtk"))
        # Active PID is the only truthful wlr signal.  The name is activatable
        # even when the backend immediately exits for lack of PipeWire access.
        wlr_ok = bool(bus_names.get("org.freedesktop.impl.portal.desktop.wlr"))
        screencast = "supported" if wlr_ok else "unavailable (wlr backend cannot reach PipeWire)"
        return {
            "success": True,
            "schema": "nuxel.flatpak-status/1",
            "flatpak": {"present": present, "path": FLATPAK, "version": version,
                        "supported_arches": arches, "default_arch": "aarch64"},
            "bwrap": bwrap,
            "user_namespace": {
                "unshare_user_rc": rc_u,
                "unshare_user_detail": (err_u or out_u).strip()[:240],
                "unshare_map_root_rc": rc_m,
                "unshare_map_root_detail": (err_m or out_m).strip()[:240],
                "ok": rc_u == 0 and rc_m == 0,
            },
            "remotes": remotes.get("remotes", []),
            "installed": {
                "count": len(apps),
                "system": sum(1 for a in apps if a.get("scope") == "system"),
                "user": sum(1 for a in apps if a.get("scope") == "user"),
                "apps": apps,
            },
            "portal": {
                "bus": USER_BUS,
                "name": PORTAL_NAME,
                "present": portal_ok,
                "backend_gtk": gtk_ok,
                "backend_wlr": wlr_ok,
                "screencast": screencast,
                "names": sorted(k for k, v in bus_names.items() if v),
                "activatable": sorted(k for k, v in bus_names.items() if not v),
                "cache": portal_cache,
            },
            "flatpak_ready": bool(present and bwrap["exists"] and not bwrap["setuid"]
                                  and rc_u == 0 and portal_ok),
            "timestamp": time.time(),
        }

    def _user_bus_names(self) -> Dict[str, bool]:
        """Return {bus_name: active} for the nuxel user bus.

        The NAME/PID columns distinguish an active service from a merely
        activatable one.  The wlr portal being activatable is not evidence that
        screencast works: it exits when it cannot reach PipeWire.
        """
        rc, out, err = _run(["/usr/bin/busctl", "--user", "list", "--no-pager"],
                            timeout=8, as_user=True)
        if rc != 0:
            return {}
        names: Dict[str, bool] = {}
        for line in out.splitlines():
            parts = line.split()
            if len(parts) < 2 or parts[0] == "NAME" or parts[0].startswith(":"):
                continue
            name = parts[0]
            pid = parts[1]
            names[name] = pid.isdigit()
        return names

    def remotes(self) -> Dict[str, Any]:
        if not os.path.isfile(FLATPAK):
            return {"success": False, "error": "flatpak_not_installed", "remotes": []}
        rc, out, err = _run([FLATPAK, "remotes", "--columns=name,title,url"],
                            timeout=15)
        if rc != 0:
            return {"success": False, "error": "flatpak_remotes_failed",
                    "detail": (err or out).strip()[:500], "remotes": []}
        cols = ["name", "title", "url"]
        rows = _parse_tsv(out, cols)
        return {"success": True, "remotes": rows}

    def _installed_scope(self, scope: str) -> Dict[str, Any]:
        cols = ["application", "name", "version", "branch", "arch", "origin",
                "installation", "runtime", "ref"]
        rc, out, err = _run(_flatpak(scope) + ["list", "--app", "--columns=" + ",".join(cols)],
                            timeout=20, scope=scope)
        if rc != 0:
            return {"success": False, "error": "flatpak_list_failed",
                    "scope": scope, "detail": (err or out).strip()[:500], "apps": []}
        apps = []
        for row in _parse_tsv(out, cols):
            aid = row.get("application", "")
            if not _valid_app_id(aid):
                continue
            exports = (SYSTEM_INSTALL if scope == "system"
                       else USER_HOME + "/.local/share/flatpak") + "/exports/share/applications"
            desktop_path = os.path.join(exports, aid + ".desktop")
            kv = _read_kv(desktop_path)
            icon_name = kv.get("Icon", "")
            icon_path = _find_icon(aid, icon_name, scope)
            apps.append({
                "id": aid,
                "name": kv.get("Name") or row.get("name") or aid,
                "version": row.get("version", ""),
                "branch": row.get("branch", ""),
                "arch": row.get("arch", ""),
                "origin": row.get("origin", ""),
                "scope": scope,
                "installation": row.get("installation", scope),
                "runtime": row.get("runtime", ""),
                "ref": row.get("ref", ""),
                "description": kv.get("Comment", ""),
                "icon": icon_name,
                "icon_url": "/api/v1/flatpak/icon/" + aid,
                "icon_found": bool(icon_path),
                "desktop_file": desktop_path if os.path.isfile(desktop_path) else "",
                "exec": kv.get("Exec", ""),
                "state": "installed",
            })
        return {"success": True, "scope": scope, "apps": apps}

    def list_installed(self) -> Dict[str, Any]:
        merged: Dict[str, Dict[str, Any]] = {}
        errors = []
        for scope in ("system", "user"):
            r = self._installed_scope(scope)
            if not r.get("success"):
                if scope == "system":
                    errors.append(r)
                continue
            for app in r.get("apps", []):
                aid = app["id"]
                # Flatpak's rule: a user install shadows a system install.
                if aid in merged and scope == "system":
                    merged[aid]["also_system"] = True
                    continue
                merged[aid] = app
        return {"success": True, "apps": sorted(merged.values(), key=lambda a: a["name"].lower()),
                "errors": errors}

    def installed_ids(self) -> set:
        return {a["id"] for a in self.list_installed().get("apps", [])}

    def is_installed(self, app_id: Any) -> bool:
        aid = _valid_app_id(app_id)
        return bool(aid and aid in self.installed_ids())

    def remote_ls(self, remote: str = "flathub", arch: str = "aarch64",
                  query: str = "", limit: int = 600) -> Dict[str, Any]:
        if remote not in ALLOWED_REMOTES:
            return {"success": False, "error": "remote_not_allowed", "remote": remote}
        if arch not in ("aarch64", "arm"):
            return {"success": False, "error": "arch_not_allowed", "arch": arch}
        cols = ["application", "name", "version", "branch", "arch", "origin",
                "download-size", "installed-size"]
        rc, out, err = _run([FLATPAK, "remote-ls", remote, "--app", "--arch=" + arch,
                             "--columns=" + ",".join(cols)], timeout=90)
        if rc != 0:
            return {"success": False, "error": "remote_ls_failed",
                    "detail": (err or out).strip()[:500], "apps": []}
        rows = _parse_tsv(out, cols)
        q = (query or "").strip().lower()
        apps = []
        installed = self.installed_ids()
        for row in rows:
            aid = row.get("application", "")
            if not _valid_app_id(aid):
                continue
            if q and q not in aid.lower() and q not in row.get("name", "").lower():
                continue
            apps.append({
                "id": aid,
                "name": row.get("name") or aid,
                "version": row.get("version", ""),
                "branch": row.get("branch", ""),
                "arch": row.get("arch", ""),
                "origin": row.get("origin", ""),
                "download_size": row.get("download-size", ""),
                "installed_size": row.get("installed-size", ""),
                "installed": aid in installed,
                "state": "installed" if aid in installed else "available",
            })
        total = len(apps)
        if limit and limit > 0:
            apps = apps[:limit]
        return {"success": True, "remote": remote, "arch": arch, "total": total,
                "apps": apps}

    # ---- icons --------------------------------------------------------------

    def icon(self, app_id: Any) -> Tuple[Optional[bytes], Optional[str], Optional[str]]:
        aid = _valid_app_id(app_id)
        if not aid:
            return None, None, "invalid_app_id"
        for scope in ("system", "user"):
            if scope == "user":
                base = USER_HOME + "/.local/share/flatpak"
            else:
                base = SYSTEM_INSTALL
            desktop = os.path.join(base, "exports/share/applications", aid + ".desktop")
            kv = _read_kv(desktop)
            path = _find_icon(aid, kv.get("Icon", ""), scope)
            if path:
                try:
                    with open(path, "rb") as fh:
                        data = fh.read(4 * 1024 * 1024)
                    mime = "image/svg+xml" if path.endswith(".svg") else (
                        "image/png" if path.endswith(".png") else "image/x-xpixmap")
                    return data, mime, None
                except OSError as exc:
                    return None, None, str(exc)
        return None, None, "icon_not_found"

    # ---- lifecycle jobs -----------------------------------------------------

    def _job_start(self, argv: List[str], scope: str,
                   verify: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        jid = uuid.uuid4().hex[:16]
        try:
            os.makedirs("/run/nuxel", exist_ok=True)
        except OSError:
            pass
        log_path = "/run/nuxel/flatpak-%s.log" % jid
        with self._lock:
            self._jobs[jid] = {
                "id": jid, "argv": list(argv), "scope": scope,
                "state": "running", "rc": None, "started": time.time(),
                "finished": None, "log": log_path, "verify": verify or {},
            }
        def _worker():
            rc = 127
            try:
                env = _base_env(scope=scope, user_bus=(scope == "user"))
                cmd = _user_argv(argv) if scope == "user" else _system_job_argv(argv)
                with open(log_path, "wb") as lf:
                    proc = subprocess.Popen(cmd, stdout=lf, stderr=subprocess.STDOUT,
                                            stdin=subprocess.DEVNULL, env=env)
                    try:
                        rc = proc.wait(timeout=1800)
                    except subprocess.TimeoutExpired:
                        proc.kill()
                        rc = 124
            except OSError as exc:
                try:
                    with open(log_path, "a") as lf:
                        lf.write("provider error: %s\n" % exc)
                except OSError:
                    pass
                rc = 127
            # systemd-run --wait can report rc=1 for a unit that has already
            # completed its Flatpak transaction.  The postcondition is the
            # authority: an install is done when flatpak list contains the app,
            # an uninstall is done when it no longer does.
            state = "done" if rc == 0 else "failed"
            verified = None
            v = verify or {}
            if v.get("kind") in ("install", "uninstall") and v.get("app_id"):
                try:
                    installed = self.is_installed(v["app_id"])
                    verified = bool(installed)
                    if v["kind"] == "install" and installed:
                        state = "done"
                    elif v["kind"] == "uninstall" and not installed:
                        state = "done"
                except Exception:
                    pass
            with self._lock:
                job = self._jobs.get(jid)
                if job is not None:
                    job.update({"state": state, "rc": rc,
                                "verified_installed": verified,
                                "finished": time.time()})
        threading.Thread(target=_worker, name="nuxel-flatpak-job", daemon=True).start()
        return {"success": True, "job": jid, "state": "running", "log": log_path}

    def job(self, job_id: Any) -> Dict[str, Any]:
        if not isinstance(job_id, str) or not re.match(r"^[0-9a-f]{16}$", job_id):
            return {"success": False, "error": "invalid_job_id"}
        with self._lock:
            job = dict(self._jobs.get(job_id) or {})
        if not job:
            return {"success": False, "error": "unknown_job"}
        tail = ""
        try:
            with open(job["log"], "rb") as fh:
                fh.seek(max(0, os.path.getsize(job["log"]) - MAX_LOG_BYTES))
                tail = fh.read().decode("utf-8", "replace")
        except OSError:
            pass
        job["log_tail"] = tail
        job["success"] = True
        return job

    def install(self, app_id: Any, remote: str = "flathub",
                scope: str = "system") -> Dict[str, Any]:
        aid = _valid_app_id(app_id)
        if not aid:
            return {"success": False, "error": "invalid_app_id"}
        if remote not in ALLOWED_REMOTES:
            return {"success": False, "error": "remote_not_allowed", "remote": remote}
        if scope not in ALLOWED_SCOPES:
            return {"success": False, "error": "scope_not_allowed", "scope": scope}
        if self.is_installed(aid):
            return {"success": True, "app_id": aid, "state": "already_installed"}
        argv = _flatpak(scope) + ["install", "-y", "--noninteractive", remote, aid]
        return self._job_start(argv, scope, {"kind": "install", "app_id": aid})

    def update(self, app_id: Any = None, scope: str = "system") -> Dict[str, Any]:
        if scope not in ALLOWED_SCOPES:
            return {"success": False, "error": "scope_not_allowed", "scope": scope}
        argv = _flatpak(scope) + ["update", "-y", "--noninteractive"]
        if app_id is not None:
            aid = _valid_app_id(app_id)
            if not aid:
                return {"success": False, "error": "invalid_app_id"}
            if not self.is_installed(aid):
                return {"success": False, "error": "not_installed", "app_id": aid}
            argv.append(aid)
        return self._job_start(argv, scope,
                               {"kind": "update", "app_id": aid} if app_id is not None else None)

    def uninstall(self, app_id: Any, scope: Optional[str] = None) -> Dict[str, Any]:
        aid = _valid_app_id(app_id)
        if not aid:
            return {"success": False, "error": "invalid_app_id"}
        apps = self.list_installed().get("apps", [])
        matches = [a for a in apps if a["id"] == aid]
        if not matches:
            return {"success": False, "error": "not_installed", "app_id": aid}
        if scope is None:
            scope = matches[0].get("scope", "system")
        if scope not in ALLOWED_SCOPES:
            return {"success": False, "error": "scope_not_allowed", "scope": scope}
        argv = _flatpak(scope) + ["uninstall", "-y", "--noninteractive", aid]
        return self._job_start(argv, scope, {"kind": "uninstall", "app_id": aid})

    def launch_argv(self, app_id: Any) -> Optional[List[str]]:
        aid = _valid_app_id(app_id)
        if not aid or not self.is_installed(aid):
            return None
        # Crispy Doom: the org.freedesktop.Platform 24.08 SDL2 Wayland
        # backend creates an xdg_toplevel but never presents a buffer on this
        # 4.14 vendor kernel.  The Flatpak install stays authoritative; the
        # wrapper runs the same Flathub binary with the host sdl2-compat stack,
        # which maps and plays the game.  It also opens the touch-first WAD
        # picker when launched without arguments and carries the Freedoom path.
        if aid == CRISPY_DOOM_APP_ID:
            return [CRISPY_DOOM_WRAPPER]
        # The host's Mali/kbase EGL stack is not a DRM device and cannot be
        # assumed inside a Flatpak runtime.  Force the runtime's own software
        # path so GTK/Electron/WebKit apps can create a Wayland surface; GPU
        # acceleration is a separate, explicitly reported capability.
        return [
            FLATPAK, "run",
            "--env=LIBGL_ALWAYS_SOFTWARE=1",
            "--env=GALLIUM_DRIVER=llvmpipe",
            "--env=MESA_LOADER_DRIVER_OVERRIDE=llvmpipe",
            "--env=GSK_RENDERER=cairo",
            "--env=GDK_BACKEND=wayland",
            "--env=MOZ_ENABLE_WAYLAND=1",
            aid,
        ]

    # ---- RPC surface --------------------------------------------------------

    def handle(self, verb: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        params = params or {}
        try:
            if verb in ("status", "get"):
                return self.status()
            if verb in ("list", "installed", "inventory"):
                return self.list_installed()
            if verb in ("remote", "remote-ls", "available", "search"):
                return self.remote_ls(
                    remote=str(params.get("remote", "flathub")),
                    arch=str(params.get("arch", "aarch64")),
                    query=str(params.get("query", "")),
                    limit=int(params.get("limit", 600) or 600),
                )
            if verb == "install":
                return self.install(str(params.get("app_id", "")),
                                    str(params.get("remote", "flathub")),
                                    str(params.get("scope", "system")))
            if verb == "update":
                return self.update(params.get("app_id"),
                                   str(params.get("scope", "system")))
            if verb == "uninstall":
                return self.uninstall(str(params.get("app_id", "")),
                                      params.get("scope"))
            if verb == "job":
                return self.job(params.get("job_id"))
            if verb == "launch":
                argv = self.launch_argv(params.get("app_id"))
                if not argv:
                    return {"success": False, "error": "not_installed",
                            "app_id": params.get("app_id")}
                return {"success": True, "app_id": params.get("app_id"),
                        "argv": argv, "launchable": True}
            if verb == "refresh":
                return {"success": True, "installed": self.list_installed(),
                        "status": self.status()}
            return {"success": False, "error": "unknown flatpak verb", "verb": verb}
        except Exception as exc:  # noqa: BLE001 - a provider error must not kill the bridge
            return {"success": False, "error": "flatpak_provider_error",
                    "detail": str(exc)}


_PROVIDER: Optional[FlatpakProvider] = None


def get_provider() -> FlatpakProvider:
    global _PROVIDER
    if _PROVIDER is None:
        _PROVIDER = FlatpakProvider()
    return _PROVIDER


def handle(verb: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return get_provider().handle(verb, params)
