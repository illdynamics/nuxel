# A54 Final Status

## Summary
Five regressions were traced to their exact sources and repaired with minimal,
reversible userspace changes, deployed live over USB and SHA-256 verified.

1. **Wi-Fi** — backend was already correct (A51 `/new` fix preserved); the live
   hang was a UI state machine that never re-rendered NM truth. Fixed with honest
   per-stage labels + bounded polling. L2/IP/route/DNS/HTTPS verified live.
2. **Rotation** — seven hyphenated stable modes restored across daemon + QS +
   Settings + model, with a single legacy-key migration boundary. Menu/state/
   persistence pass; physical rotation remains gated on the absent compositor
   transform backend and sensor source (reported honestly, not faked).
3. **Status bar** — one measured right-hand cluster replaced two competing grid
   cells and duplicate CSS blocks; an on-device collision detector reports
   `overlaps=none`.
4. **Boot readiness** — battery `Full` no longer masquerades as `charging`; the
   bridge returns real numeric percent immediately; no `undefined` rotation state.
5. **Camera** — the stale A51 bridge was the reason "no camera app" persisted.
   Deployed the A52 media store + Camera D-Bus/RPC and a distinct Nuxel-owned
   native GTK4 Camera app. GNOME Snapshot install is documented as a follow-on
   (missing package manager + deps). Real frames remain BLOCKED_HARDWARE
   (FIMC-IS standard-capture ENOTTY), exactly as A52 documented.

## Verdict vocabulary used
PASS_INTEGRATION (live device evidence, integration-level), PARTIAL (policy
correct, hardware/compositor gate outstanding), BLOCKED_HARDWARE /
BLOCKED_EXTERNAL_RESOURCE (external state), NOT_TESTED (needs owner-approved
reboot). No physical PASS is claimed without physical proof; no hardware result
is fabricated.

## Remaining blockers (exact)
- Compositor transform backend (`wlr-randr`) absent → forced rotation output.
- No auto-capable gravity sensor exposed (IIO scale / iio-sensor-proxy) → auto.
- No `dnf`/`dnf5` and missing `pipewire`/`wireplumber`/`libcamera` → Snapshot.
- FIMC-IS `VIDIOC_S_FMT → ENOTTY` + no `/dev/media*` → real camera frames.

## Rollback
One command per file (`.nuxel-a54-rollback`), see DEPLOYMENT-AND-ROLLBACK.md.
