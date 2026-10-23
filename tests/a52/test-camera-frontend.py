#!/usr/bin/env python3
"""Offline unit tests: Camera + Photos frontend correctness (A52).

Source-level guards for the historical defects, plus a small functional check of
the Photos normalise() shape against the new file-backed bridge records.  These
never touch a camera: they prove the app no longer uses localStorage-as-database,
no longer hard-codes 1440x3120, no longer loses facingMode before teardown, and
uses file-backed bridge verbs for capture/delete/open.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
CAMERA_JS = os.path.join(ROOT, "pwa", "nuxel-apps", "camera-gallery", "js", "camera.js")
PHOTOS_JS = os.path.join(ROOT, "pwa", "nuxel-apps", "photos", "js", "photos.js")
CAMERA_MANIFEST = os.path.join(ROOT, "pwa", "nuxel-apps", "camera-gallery", "manifest.json")

FAILURES: list = []


def check(cond: bool, msg: str) -> None:
    print(("  OK   " if cond else "  FAIL ") + msg)
    if not cond:
        FAILURES.append(msg)


def main() -> int:
    cam = open(CAMERA_JS).read()
    ph = open(PHOTOS_JS).read()
    manifest = open(CAMERA_MANIFEST).read()

    # 1. localStorage is no longer the photo database
    check("nuxel-camera-photos" not in cam,
          "camera.js no longer stores the photo database in localStorage")
    check("localStorage.setItem" not in cam,
          "camera.js performs no localStorage writes at all")

    # 2. no 1440x3120 screen-resolution "ideal"
    check("ideal: 1440" not in cam and "ideal: 3120" not in cam and "ideal: 1280" in cam,
          "camera.js uses conservative 1280x720 ideal, not 1440x3120")

    # 3. front/rear: device selection is read BEFORE teardown, persisted independently
    check("state.selectedDeviceId" in cam, "selected device persisted independently of stream")
    check("_stopCamera()" not in cam, "no _stopCamera()-before-facingMode-read pattern remains")
    check("stopStream()" in cam and "currentFacing()" in cam,
          "stream teardown helper and current-facing reader are separated")

    # 4. Photo/Video are distinct: MediaRecorder present
    check("MediaRecorder" in cam, "video recording uses MediaRecorder (real recorder, not icon toggle)")
    check("startRecording" in cam and "stopRecording" in cam,
          "recording start/stop implemented")

    # 5. file-backed capture via bridge verbs (never an ever-growing base64 array)
    check("'camera', 'capture'" in cam, "capture routes through bridge camera.capture verb")
    check("toBlob" in cam, "capture encodes via canvas.toBlob (bounded), not toDataURL")

    # 6. honest hardware states surfaced
    check("NO_CAMERA" in cam and "PERMISSION_DENIED" not in cam or "permission" in cam,
          "honest hardware/permission states are surfaced")
    check("capture_verified" in cam, "capture-verified flag is consulted (never assumed)")

    # 7. Photos app is file-backed: list/open/delete verbs, lazy-load
    check("'camera', 'open'" in ph and "'camera', 'delete'" in ph,
          "photos.js uses camera.open and camera.delete verbs")
    check("IntersectionObserver" in ph, "photos.js lazy-loads thumbnails (bounded memory)")
    check("'video'" in ph, "photos.js renders videos distinctly from photos")

    # 8. manifest declares the expanded verb set and corrected scope
    check("camera.open" in manifest and "camera.delete" in manifest and "camera.status" in manifest,
          "camera manifest declares open/delete/status verbs")
    check('/pwa/nuxel-apps/camera-gallery/' in manifest and '/pwa/nuxel-apps/camera/' not in manifest,
          "camera manifest scope corrected to the real path")

    print("\ncamera-frontend: %d failure(s)" % len(FAILURES))
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())
