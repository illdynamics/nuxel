# Nuxel v0.6.3-beta — safe S10+ userspace deployment

The A43 payload updates only WebKit launcher/Settings resources and the
NetworkManager bridge Python implementation. It is **not a bootable image**.
Do not flash, write partitions or replace the kernel while the console is live.

## On the MacBook (repository root)

```sh
python3 tools/s10plus/a43/test-a43-source.py
python3 tools/s10plus/a43/package-live.py
python3 tools/s10plus/a43/verify-live.py build/out/nuxel-v0.6.3-beta-live-userspace.tar.gz
```

## On the USB-connected phone

1. Confirm USB console, root privilege and a separate emergency recovery path.
2. Record active nuxel-web DocumentRoot using `systemctl cat nuxel-web` and verify
   it with `curl -I http://127.0.0.1:8000/pwa/nuxel-home/index.html`.
   Nuxel images may serve `/usr/share/nuxel` or `/home/nuxel/nuxel`.
3. Capture read-only evidence with
   `sh tools/s10plus/a43/s10plus-readonly-check.sh` (copy script to phone first).
4. Copy the payload over the existing verified USB connection, e.g. `scp` over
   USB networking or your existing USB serial file-transfer mechanism.
5. Back up the exact current files, launcher preferences and service status.
6. Verify payload manifest and hashes **on the phone** before touching files.
7. Copy `pwa/*` + `assets/*` from payload files to the verified active static
   webroot, atomically per file; copy `services/nuxel-bridge/src/*.py` to
   `/usr/lib/nuxel/nuxel-bridge/`. Do not blindly copy into an unused webroot.
8. Restart `nuxel-bridge` + `nuxel-http-bridge` and the actual `nuxel-web` service;
   confirm each is active. Preserve the USB console. Refresh WebKit/service
   worker script caches without removing localStorage or desktop layout.
9. Confirm HTTP 200, effective CSS dock background, and source/deploy SHA256.
10. Test Wi-Fi radio, scan, association, DHCP, DNS, HTTPS, and the Browser.
11. Diagnose audio with the existing A33 `nuxel-audio-diag.sh pipeline`; do not
    force undocumented amplifier or mixer controls. Ask owner to confirm sound.
12. Roll back per-file backups and restart services on failures.

## Physical verification checklist

- Home: BG1/BG2 changes visibly; dock icons stay tappable; no Home zoom.
- Gesture: upward swipe beginning in bottom half opens All Apps; upward again
  opens Settings; upper-half gestures expand/collapse Quick Settings.
- Browser is visible in All Apps and opens locally. An actual HTTPS page loads
  only if Wi-Fi, DNS and iframe embedding permit it.
- Wi-Fi Settings shows real NetworkManager radio and scan results, completes
  a real join. `connected` and `internet verified` are separate verdicts.
- Volume/boot audio and actual speaker playback: owner audible confirmation.

Full raw S10+ image is produced by the GitHub Actions `release.yml` workflow,
not by this userspace-only bundle. No image should be flashed during this deploy.
