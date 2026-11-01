# PWNAGE-49000 — implementation ledger

Target: Samsung Galaxy S10+ SM-G975F (`beyond2lte`), Nuxel/Fedora ARM64.
Run started 2026-10-31. This checkout is authoritative for source; the live
handset was **not reachable** in this run (see
`evidence/pwnage-49000/physical-access.txt`).

Status vocabulary: **SOURCE_DONE**, **PASS_HEADLESS**, **PASS_AUTOMATED_ONLY**,
**BLOCKED_KERNEL**, **BLOCKED_FIRMWARE**, **BLOCKED_SECURE_PROVIDER**,
**PHYSICAL_BLOCKED** (no handset path), **NOT_SUPPORTED_ON_DEVICE**.

## Direct owner follow-up (this run)

| # | Item | Status | Evidence |
|---|------|--------|----------|
| A | Remove the second top bar (native overlay clock/%/Wi-Fi over the proper Home bar) | SOURCE_DONE + PASS_HEADLESS | `nuxel-statusbar.c` now shows its layer surface only when the compositor reports an activated/unminimized non-Home toplevel; otherwise `bar_hide()`. Home screenshot has only the DOM bar. |
| B | Restore the proper full top bar | SOURCE_DONE + PASS_HEADLESS | DOM `#status-bar` owns Home; Wi-Fi/Bluetooth/Location use one local icon-pack mask each; cache `v73-p49000`. |
| C | Move lockscreen console-transport penguins up between the primary penguin row and the background Nuxel wordmark | SOURCE_DONE + PASS_HEADLESS | `.lockscreen-transports { top: 258px }` (was 286px), 6px below the 184..252 primary row. |

## Required outcomes

| # | Feature | Status | Notes / real blocker |
|---|---------|--------|----------------------|
| 1 | Recognisable Wi-Fi / Bluetooth / Location icons, truthful states | SOURCE_DONE + PASS_HEADLESS | `01-wifi.png` and `04-bluetooth.png` are the single renderer per cell (CSS mask, no pseudo-art). Location pin comes from provider state; `enabled` is not rendered as `fixed`. |
| 2 | Top bar visible on lockscreen | SOURCE_DONE + PASS_HEADLESS | `body.lockscreen-active .status-bar { display:grid; z-index:520 }` above `#lockscreen` (500). QS pull-down remains gated by `_coveredByLock()`. |
| 3 | Native three-button dock Back/Home/Tabs | SOURCE_DONE | Existing layer-shell dock retained; tap slop + per-gesture ownership verified in source. No physical tap test. |
| 4 | Distinct long-Back haptic, once | SOURCE_DONE | Dock now emits `long` (not `navigation`) for `back-long`, from a 700 ms timer while held, one-shot, suppressed after movement/cancel. Physical vibrator not tested. |
| 5 | Short Back navigates; Home backgrounds; long Back closes foreground only | SOURCE_DONE | `app.js` now treats PWA/native root as a no-op instead of silently minimising. Long Back still uses compositor `close-foreground` only. |
| 6 | Back/Home/Tabs for PWA/native/Flatpak | SOURCE_DONE (PWA/native), BLOCKED_PACKAGE_SOURCE (Flatpak) | App type `flatpak` routed through the same Back path. Flatpak itself remains blocked by `CONFIG_USER_NS=n`; not faked. |
| 7 | False “unlock first” refusal | SOURCE_DONE | Launch gate reconciles the local LockScreen cache with authoritative Bridge security status once, then retries only if `locked:false`; genuinely locked sessions still fail closed. Archive Manager comparison needs the handset. |
| 8 | Native top bar/dock over GTK/Flatpak windows | SOURCE_DONE + PASS_HEADLESS | Dock is already an OVERLAY layer surface. Native statusbar is now conditional on a real foreign foreground toplevel, preventing the duplicate bar. |
| 9 | USB MTP + SD, CDC-ACM preserved | SOURCE_DONE, PHYSICAL_BLOCKED | `nuxel-usb-mode.sh` uses a real `f_mtp` + `nuxel-mtp-server` path and refuses success until the UDC is configured with a host link speed. Internal storage is the explicit `/home/nuxel/Shared` root. A mounted removable card is bind-mounted as `Shared/SD Card/` (detected from `/sys/block/*/removable`, never a raw block export) and unmounted on mode exit. Host enumeration/copy not tested. |
| 10 | Lockscreen/drawer responsiveness, gesture arbitration | NOT DONE | Not touched in this run beyond the icon/row layout. Existing gesture work remains; physical frame timings not captured. |
| 11 | Unified Software (RPM + Flatpak) | PARTIAL / BLOCKED | Existing PackageKit/native Software path retained. Flatpak stays disabled: `CONFIG_USER_NS=n`, no verified bwrap/portal/ARM64 runtime. |
| 12 | NuXtore Live Console installed state | SOURCE_DONE | Added `org.nuxel.Console -> org.nuxel.LiveConsole` alias in NuXtore reconciliation; runtime inventory still overrides catalog `state_hint`. |
| 13 | Authenticator QR/manual/URI, encrypted vault, correct codes | SOURCE_DONE + PASS_AUTOMATED_ONLY | Bundled Apache-2.0 `jsQR` locally; camera + image decode; preview before add; no OTP toast leak; per-iteration account closures; random opaque IDs; vault clear on lock/pagehide. Camera/physical test not done. |
| 14 | Entra OATH/TOTP, truthful Microsoft Authenticator limits | SOURCE_DONE | In-app Entra card + `ENTRA-OATH.md`; explicitly refuses push/number matching/broker/PRT/Intune/passkey claims. |
| 15 | NFC physical read | BLOCKED_KERNEL | Prior evidence: kernel `# CONFIG_NFC is not set`. No hardware test possible. No fake toggle added. |
| 16 | Fingerprint ultrasonic sensor | BLOCKED_SECURE_PROVIDER | qbt2000 nodes exist, but no verified TEE/fprintd provider or template manager. UI must remain unsupported with PIN fallback. |
| 17 | Swipe/PIN/Pattern/Fingerprint lock | PARTIAL | Bridge `security_provider.py` has scrypt PIN/pattern, rate limiting and authoritative lock-state. Swipe remains lower-security; fingerprint is refused without a secure provider + PIN fallback. Face is not offered. Physical unlock cycle not re-run. |

## Build / deploy

- Cache version bumped to `v73-p49000` in `pwa/nuxel-home/sw.js` and
  `manifest.json`; `index.html` cache-busters updated for status bar/app/lockscreen.
- Authenticator service-worker cache bumped to `v2-p49000`, vendor QR decoder
  added to its precache list.
- The rootfs builder already stages the whole `pwa/` tree, so the new
  `authenticator/vendor/jsQR.js` is included without a new copy rule.
- No live deployment was performed: no handset network/serial path was
  available. See the deployment record for the exact staging steps and rollback.

## Verification still required on the phone

1. Reboot/deploy the staged PWA + rebuilt `nuxel-statusbar`/`nuxel-navdock`.
2. Lock the screen: confirm exactly one proper top bar, no native duplicate,
   correct icon artwork, and that the unlock drag still works.
3. Unlock: confirm the console-transport penguins sit between the
   charger/PC/live row and the Nuxel wordmark.
4. Launch Firefox/Archive Manager/another native app: confirm the native top
   strip appears only over that app and disappears on Home.
5. Hold Back: verify one distinct long pulse and foreground-only close.
6. USB: select File Transfer, enumerate with OpenMTP, copy both ways, verify
   SHA-256, confirm `ttyGS0` still works.
7. NFC/fingerprint: run diagnostics; do not mark supported without a real tag /
   secure provider.
