"""Nuxel Home — App Launcher

Handles launching PWAs via 'chromium --app=URL' and
showing a toast for native-placeholder apps.
"""

import asyncio
import logging
import os
import shutil
import socket
import subprocess
from typing import Optional

logger = logging.getLogger(__name__)


def find_chromium() -> Optional[str]:
    """Locate the chromium-browser or chromium binary on PATH."""
    for binary in ("chromium-browser", "chromium", "google-chrome", "google-chrome-stable"):
        path = shutil.which(binary)
        if path:
            return path
    return None


def launch_pwa(app_name: str, url: str) -> bool:
    """Launch a PWA in a dedicated Chromium app window.

    Uses 'chromium --app=URL' which creates a frameless window
    that acts like a standalone app. Returns True if launched.
    """
    chromium = find_chromium()
    if not chromium:
        logger.error("No Chromium binary found — cannot launch PWA")
        return False

    # Per-app isolated Chromium profile
    safe_id = app_name.replace(" ", "-").lower()
    user_data_dir = os.path.expanduser(f"~/.cache/nuxel-apps/{safe_id}")
    os.makedirs(user_data_dir, exist_ok=True)

    # Check port 8000 is up before launching
    ok = _check_port(8000)
    if not ok:
        logger.warning("Port 8000 not available — PWA runtime may be down")

    cmd = [
        chromium,
        f"--app={url}",
        "--new-window",
        "--no-first-run",
        "--disable-infobars",
        "--disable-session-crashed-bubble",
        f"--user-data-dir={user_data_dir}",
        "--ozone-platform=wayland",
    ]

    logger.info("Launching PWA '%s': %s", app_name, url)
    try:
        subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except FileNotFoundError:
        logger.error("Chromium binary not found at %s", chromium)
        return False
    except OSError as exc:
        logger.error("Failed to launch PWA '%s': %s", app_name, exc)
        return False


def _check_port(port, host="127.0.0.1", timeout=2):
    """Check if a TCP port is listening."""
    try:
        s = socket.create_connection((host, port), timeout=timeout)
        s.close()
        return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def launch_pwa_async(app_name: str, url: str) -> asyncio.Future:
    """Async wrapper for launch_pwa()."""
    return asyncio.get_event_loop().run_in_executor(None, launch_pwa, app_name, url)
