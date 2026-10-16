# Nuxel S10+ Live Deployments — 2026-10-17

**Deploy tool:** `tools/beta/live/nuxel-live-deploy.py --dev /dev/ttyACM0 --apply`
**Manifest:** `tools/beta/live/deploy-manifest.json` (624 steps / 16 groups, extended full-build manifest)
**Discipline:** per-file stage -> sha256 verify -> atomic install -> smallest service restart -> health check -> auto-rollback on failure.

## Result
All **624** manifest steps applied. 608 targets already carried the repository bytes (idempotent no-op); **16 targets newly installed** this cycle. **0 failures, 0 rollbacks.**

| group | steps | result |
|---|---|---|
| launcher-pwa | 21 | applied (already matched) |
| status-bar-safe-zones | 1 | applied (already matched) |
| session-units | 6 | applied (already matched) |
| animation-handoff | 2 | applied (already matched) |
| touch-and-buttons | 3 | applied (already matched) |
| audio-and-network-config | 4 | applied (app_registry.json newly installed) |
| pwa-app-suite | 380 | applied (12 newly installed) |
| pwa-shared-runtime | 15 | applied |
| app-registry-consumers | 5 | applied |
| configs-nuxel-remaining | 50 | applied |
| s10plus-a33-runtime | 45 | applied (3 newly installed) |
| services-runtime | 24 | applied (bridge.py, D-Bus confs, http-bridge unit newly installed in a later fix pass) |
| native-shell-sources | 55 | applied |
| boot-animation-runtime | 11 | applied |
| packages-reconcile | 2 | applied (manifest + verify-packages.py) |
| console-and-kernel-side-followups | 0 | **deliberately skipped** -> BLOCKED_KERNEL (kernel/DTB touch-in-charger fix; no-flash rule) |

## Post-deploy health (real on-device reads)
- `systemctl is-system-running` = `running`; `systemctl --failed` = **0 units**.
- Active: `nuxel-wayland`, `nuxel-wl-fb`, `nuxel-web`, `nuxel-touch-arm`, `nuxel-button-manager`, `nuxel-bridge`, `nuxel-portal`, `nuxel-notifications`, `nuxel-http-bridge`, `seatd`.
- D-Bus names owned: `org.nuxel.Bridge` (nuxel-bridge), `org.nuxel.Portal` (nuxel), `org.nuxel.Notifications` (nuxel-notifications).
- `curl http://127.0.0.1:8000/pwa/nuxel-home/index.html` -> 200.
- `curl http://127.0.0.1:8080/api/v1/ping` -> 200.
- Exactly one `/dev/fb0` holder: `nuxel-wl-fb`; `display=on`, ~24 fps, failures=0.

## Service-graph fixes applied this cycle (real defects, all userspace/no-flash)
1. Provisioned `nuxel-bridge` and `nuxel-notifications` system users + `/var/lib/nuxel/permissions` + `/var/log/nuxel` (new `tools/s10plus/a33/nuxel-provision-services.sh`).
2. Installed `python3-dbus`, `python3-gobject`, `python3-gobject-base`, `python3-cairo` (aarch64 Fedora 43 RPMs pushed over the console and `rpm -i`).
3. Fixed `services/nuxel-bridge/src/bridge.py`: replaced non-existent `dbus.service.property` with standard `org.freedesktop.DBus.Properties` Get/GetAll.
4. Fixed `org.nuxel.Bridge.conf`: removed invalid `<limit name="log_level">info</limit>` that made dbus-daemon reject the whole file; added `nuxel-bridge` own policy. Added `nuxel-notifications` own policy to `org.nuxel.Notifications.conf`.
5. `nuxel-http-bridge.service` now runs as root because the Samsung 4.14 vendor `ncm` network module denies AF_INET/AF_INET6 socket creation to non-root UIDs (documented kernel limitation, not a relaxed policy choice).

## Evidence bundles
- `deploy-20261017T002230+0200/` (dry-run plan, 624 steps)
- `deploy-20261017T0024xx+0200/`, `deploy-20261017T0025xx+0200/`, `deploy-20261017T0026xx+0200/`, `deploy-20261017T0027xx+0200/` (per-group applies)
- `deploy-20261017T0037xx+0200/` (services-runtime fix pass)

## Rollback
Each overwritten target retains `<target>.nuxel-rollback` (first baseline preserved) and is restored by the deploy tool's EXIT trap on any failed step. The fallback frontend `tools/nuxel-rollback-home.sh` remains the native-home -> PWA-kiosk route.
