# PWNAGE-49000 — final report (source + headless pass)

Date: 2026-10-31
Handset: Samsung Galaxy S10+ SM-G975F (`beyond2lte`) — **not reachable in this
run**. Physical items below are deliberately not claimed.

## What was actually fixed

### 1. One proper top bar; duplicate native bar removed
The duplicate was the native `nuxel-statusbar` layer surface, which rendered
clock, battery % and Wi-Fi unconditionally while unlocked. It now asks the
compositor (`nuxel-foreign-toplevel list`) whether a non-Home toplevel is
activated/unminimized and only then creates its layer surface. On Home and on
the lockscreen it tears the surface down.

Evidence: `browser-layout.txt`, `home-single-topbar.png`,
`lockscreen-dom-topbar.png` (top strip is the DOM bar's `rgba(26,26,46,.95)`;
below it is Home/lockscreen background).

### 2. Proper top bar visible on the lockscreen
`body.lockscreen-active .status-bar` now uses `display:grid !important;
z-index:520`, above `#lockscreen` (500) and below the connection-mode dialog
(600). The pull-down QS gesture remains disabled while locked.

### 3. Recognisable radio icons
Wi-Fi and Bluetooth no longer use CSS pseudo-art. Each is a single local
icon-pack mask (`01-wifi.png`, `04-bluetooth.png`). Bluetooth OFF is a muted
rune; UNKNOWN/error is hidden rather than invented. Location already used the
provider-backed pin and now also shows a muted pin for an explicit disable,
while `fixed`/`satellite` remains a separate provider state.

### 4. Console transport penguins moved up
`.lockscreen-transports` moved from `top:286px` to `top:258px`, placing the row
in the gap between the charging/PC/live row (184..252) and the wallpaper's
Nuxel wordmark.

### 5. Back/Home semantics and long-Back haptics
- Native dock: 700 ms long-press is timer-driven while the finger is held;
  emits **one** `long` haptic and one `back-long` action, suppresses the release
  tap, and cancels on >24 px movement or pointer cancel.
- Short Back at a PWA/native root is now a no-op instead of silently
  minimising. Home remains the distinct minimise action.
- Long Back still uses the compositor's foreground-only close path.

### 6. False “unlock first” refusal
The launch gate now reconciles the local LockScreen cache with the authoritative
Bridge `security.status()` once. It retries only when the provider says
`locked:false`; a genuinely locked session remains blocked. No check was removed.

### 7. USB MTP + SD
The existing real `f_mtp` + `nuxel-mtp-server` path is retained and now exports
a mounted removable card as `Shared/SD Card/` via a bind mount (detected from
`/sys/block/*/removable`), removed on mode exit. No mass-storage LUN and no live
root/home export. CDC-ACM remains in the composition. Host enumeration/copy was
not tested (no handset/cable path here).

### 8. NuXtore Live Console
Added the legacy alias `org.nuxel.Console -> org.nuxel.LiveConsole`; runtime
inventory continues to override catalog `state_hint`.

### 9. Authenticator QR + vault defects
- Local Apache-2.0 `jsQR` bundled (no CDN/network at runtime).
- Camera scan and QR-image import with explicit preview/confirm.
- Camera tracks stopped on success/cancel/background/pagehide.
- Removed the OTP-printing clipboard fallback.
- Per-iteration closure fix for Copy/Delete.
- Random opaque account IDs (no secret fragment).
- Save failure is reported; lock/pagehide clears key and decrypted accounts.
- Entra guidance added with truthful Microsoft Authenticator limits.

## Verification performed

- `tests/pwnage49000/*`: ALL PASS.
- `tests/pwnage45000`: ALL PASS (updated for the new top-bar contract).
- Authenticator RFC 6238 vectors: 32/32 pass.
- Vault suite: 39/39 pass.
- JS syntax, shell syntax, Python compile: pass.
- Headless Chrome layout and local QR decode: pass.
- Handset SSH probe: `Can't assign requested address` (no route). No physical
  claim is made.

## Still blocked / not done

| Item | Status |
|---|---|
| Physical lockscreen/top-bar/haptic test | PHYSICAL_BLOCKED |
| Native app launch + Archive Manager comparison | PHYSICAL_BLOCKED |
| MTP enumeration/copy with macOS OpenMTP | PHYSICAL_BLOCKED |
| SD card export on real mounted card | SOURCE_ONLY |
| Drawer/lockscreen performance + gesture arbitration | NOT DONE in this pass |
| Flatpak runtime | BLOCKED_PACKAGE_SOURCE (`CONFIG_USER_NS=n`, no verified bwrap/portal/runtime) |
| NFC tag read | BLOCKED_KERNEL (`CONFIG_NFC` not set) |
| Fingerprint enrollment | BLOCKED_SECURE_PROVIDER (no verified TEE/fprintd provider) |
| Face unlock | NOT OFFERED (no liveness/anti-spoof) |

Rollback and deployment commands: `PWNAGE-49000-DEPLOYMENT.md`.
