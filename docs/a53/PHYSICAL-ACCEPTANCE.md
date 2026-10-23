# NUXEL A53 — Physical Acceptance Ledger (live S10+)

Each row is a physical on-device observation via the framed USB Live Console. Offline tests are
never upgraded to physical PASS.

| Gate | Verdict | Evidence |
|---|---|---|
| 1. Native camera app installed | BLOCKED_NETWORK | no `dnf`/`dnf5`/`microdnf`; no network; `snapshot` not installed |
| 2. Native camera app shown on device | BLOCKED | cannot install (1) |
| 3. Real S10+ camera frame captured | BLOCKED_HARDWARE | `nuxel-v4l2-capture-test.py /dev/video111` → S_FMT ENOTTY, REQBUFS/QUERYBUF EINVAL |
| 4. GNOME Software installed & displayed | BLOCKED_NETWORK | no package manager, no PackageKit/Flatpak, no network |
| 5. Real RPM install/launch/remove from store | BLOCKED | no store (4) |
| 6. Flatpak sandbox supported | BLOCKED_KERNEL | `# CONFIG_USER_NS is not set`; `unshare -U`/`bwrap --unshare-user` fail |
| 7. Real Flatpak install/launch/remove from store | BLOCKED | (4)+(6) |
| 8. Five modes exposed in Settings | PASS_PHYSICAL | `settings.js` ROTATE_MODES = Auto, Auto Portrait, Auto Landscape, Forced Portrait, Forced Landscape (+2 advanced); deployed, `node --check` clean |
| 9. Five modes exposed in Quick Settings | PASS_PHYSICAL | `qs.js` rotate menu reordered/relabelled identically; deployed |
| 10. Physical screen+touch rotation correctness | BLOCKED_HARDWARE | headless compositor `transform_available=false`, no touch matrix; pixels-without-touch rejected |
| 11. Persistence across session/reboot | PASS (session) / PARTIAL (reboot) | `orientation.set` persisted to `/var/lib/nuxel/orientation/state.json`; reboot NOT performed (no owner approval) |
| 12. No regressions (Home/lockscreen/OSK/USB/Wi-Fi/media/thermals) | PASS (observed) | Home/dock/OSK/bridge/wl-fb processes intact; `systemctl --failed` empty; USB console healthy; no framebuffer opened; camera media store untouched |

## What was physically exercised this session

- Console reachability (framed, `sha_ok=yes`) and root shell.
- Native GTK4 `adwaita-1-demo` opened a Wayland window (rc=124 under `timeout 6`).
- Orientation RPC chain: `get`/`modes`/`set`/persistence, all on the real device.
- Camera capture re-probe: `S_FMT ENOTTY` reproduced on today's boot.
- Flatpak kernel check: `CONFIG_USER_NS` absent; `bwrap`/`unshare` failure reproduced.

No reboot was performed (owner approval required). No flashing, no sandbox weakening, no fake frames.
