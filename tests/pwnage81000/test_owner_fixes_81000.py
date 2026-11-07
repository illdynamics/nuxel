#!/usr/bin/env python3
"""Offline checks for the 2026-11-05 owner fixes.

Covers:
  * Vesktop starts through the bridge's Electron/Wayland launch profile;
  * Home/lock only minimize native apps and a second icon tap resumes the same
    live window instead of spawning another process;
  * the hardware meters are desktop-only (hidden in the Applications drawer).
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(errors="replace")


def main() -> int:
    app = read("pwa/nuxel-home/js/app.js")
    css = read("pwa/nuxel-home/css/launcher.css")
    api = read("services/nuxel-bridge/src/api.py")
    index = read("pwa/nuxel-home/index.html")
    checks = []

    checks.append((
        "Vesktop is in the Electron Flatpak launch profile",
        'dev.vencord.Vesktop' in api and 'ZYPAK_ZYGOTE_STRATEGY_SPAWN=0' in api
        and '--ozone-platform=wayland' in api,
    ))
    checks.append((
        "native apps are minimized, not retired, when Home/lock backgrounds them",
        'app:backgrounded id=${app.id} native=1 preserved=1' in app
        and 'this._httpBridge(\'POST\', \'/api/v1/apps/home\'' in app,
    ))
    lock_body = app[app.index('    _lock(reason) {'):app.index('    _unlock(reason) {')]
    checks.append((
        "the lockscreen path never closes or kills foreground apps",
        not re.search(r'_closeAppSurface|forceKill|terminateForeground|/api/v1/apps/(force-close|close-foreground)', lock_body),
    ))
    checks.append((
        "a second native launch reuses the live compositor toplevel",
        '_findLiveNativeWindow(app)' in app and '/api/v1/windows/activate' in app
        and 'native:resumed' in app,
    ))
    checks.append((
        "hardware meters are hidden while the Applications drawer is open",
        'body.app-drawer-open #system-monitor' in css
        and 'body.app-drawer-open .system-monitor' in css
        and 'display: none !important' in css,
    ))
    checks.append((
        "launcher cache version changed for the deployed JS/CSS",
        'js/app.js?v=p81001' in index and 'css/launcher.css?v=p81001' in index,
    ))

    failed = 0
    for name, ok in checks:
        print(("PASS " if ok else "FAIL ") + name)
        failed += 0 if ok else 1
    print(f"{len(checks) - failed} passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
