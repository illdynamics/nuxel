# PWNAGE-52000 — responsive UI, lock privacy, privacy providers, GPU truth, LPM source repair

**Date:** 2026-11-01
**Target:** Samsung Galaxy S10+ SM-G975F / `beyond2lte` / Exynos 9820
**Kernel:** `4.14.253-gf7194c1d15ed-dirty #8` (unchanged; no BOOT flash)
**Device:** `root@192.168.178.167`, Wi-Fi SSH, ed25519 host key verified.

## Result summary

| Feature | Verdict | Evidence |
|---|---|---|
| Settings horizontal page pan | **PASS** | 320/360/384/393/430 portrait and 640/760 landscape; `scrollWidth == clientWidth`; tab rail 1568 px inside 320 px |
| Settings duplicate DOM ids | **PASS** | `screen-state`, `graphics-acceleration-state`, `external-display-state`; uniqueness test over all PWAs |
| All installed PWA responsiveness | **PASS (layout)** | 30/30 documents at 320×640 and 760×360; matrix in evidence |
| Native/Flatpak responsiveness | **PARTIAL/UNSUPPORTED** | native inventory; Flatpak sandbox blocked by kernel |
| Charger cold boot interactive | **BLOCKED_OWNER/TWRP** | exact patch prepared, not flashed; `adb devices` empty |
| Lockscreen top bar + DOM/native dock | **PASS** | live native dock hide/show + lock-state transitions; screenshots |
| Status icon truth + per-icon prefs | **PASS** | provider-state hiding; durable `statusbar-icons.json`; 11 toggles |
| Quick Settings privacy row | **PASS (plumbing) / UNSUPPORTED hardware** | NFC/fingerprint/microphone show honest disabled states; camera gate works |
| GPU utilization/clock/memory | **PASS** | 11652 KiB tracked shared allocation; 0% idle; clock units verified |
| GPU `(ACC)` suffix | **PASS (honest PARTIAL)** | Phoc kbase accelerated; WebKitGTK software |
| Graphics card in Displays | **PASS** | first block; independent 3 s request; connector request 4 s and does not block |
| Existing kbase/Phoc/wl-fb/DECON | **PASS** | Phoc 3× `/dev/mali0`, udmabuf fds; `FRAMES_OK`; `decon_pan_failed=0` |

## Root causes confirmed / corrected

1. **Settings overflow** was not one CSS line: the `.tabs` rail is intentionally
   scrollable, while document children lacked `min-width:0`/bounded grids. The
   new width contract constrains `html/body/main/.panel/.card/*` and preserves an
   isolated tab scroller.
2. **Duplicate `display-state`** made `getElementById()` write Developer state
   into the Screen card and prevented the External Display card from updating.
   All display IDs are unique now; `refreshDev()` owns only `dev-state`/`dev-input`.
3. **Lock leak** was both DOM CSS and a separate native layer-shell surface. The
   old CSS deliberately raised the top bar above `#lockscreen` (`z-index:520`).
   This pass removes that rule, hides DOM chrome before reveal, changes
   `nuxel-navdock` to start hidden, and makes it refuse `show` unless
   `/run/nuxel/security/lock-state.json` says unlocked. The host also now reads
   the real security state path instead of the never-written `/run/nuxel-lock.state`.
4. **Provider state vs. preference** are separate now. Wi-Fi hides on radio OFF,
   Bluetooth hides unless powered, Location hides unless enabled, NFC hides unless
   supported+on. Hiding an icon never changes the service.
5. **GPU memory was wrong**: the old collector read `/sys/kernel/gpu/gpu_memory`,
   which reported **0 bytes** for a live Phoc context. The authoritative kbase
   table is `/sys/kernel/debug/mali/gpu_memory` and reports **used_pages**
   (2885–2913 pages = 11.3–11.4 MiB), not bytes and not VRAM. The daemon now
   converts with the real page size, labels it `ok_shared_budget_reference`, and
   documents MemTotal as a RAM upper bound. The service gets only
   `CAP_DAC_READ_SEARCH` to traverse root-only debugfs; DynamicUser remains.
6. **LPM** root cause is the `sec_ts_init()` `-ENODEV` before
   `i2c_add_driver()`. Exact-source audit found only six `lpcharge` consumers;
   there is no qbt2000/Wacom `lpcharge` gate in this kernel tree. The prepared
   patch removes only the initcall gate; it does not clear `lpcharge`, change
   charger/thermal/PMIC policy, or bypass battery safety.

## Source changes (main)

- Settings: `pwa/nuxel-apps/settings/index.html`, `settings.css`, `settings.js`,
  `hardware-settings.js`, `graphics-diagnostics.js`.
- Home: `pwa/nuxel-home/index.html`, `js/status-bar.js`, `js/qs.js`, `js/app.js`,
  `js/system-monitor.js`, `css/status-bar.css`, `css/lockscreen.css`, `sw.js`,
  `manifest.json`.
- Shared: `pwa/nuxel-common/statusbar-icons.js`, `responsive.css`, `theme.css`;
  every PWA index now loads the responsive contract.
- Bridge: `api.py` (`graphics.status`, `graphics.test`, privacy/camera gate),
  `bridge.py` (camera privacy enforcement), `privacy_provider.py`,
  `security_provider.py` (biometric policy), service unit sandbox paths.
- Metrics: `services/nuxel-metrics/nuxel-metricsd.c` and `.service`.
- Native: `tools/s10plus/a45/nuxel-navdock.c`, `nuxel-pwa-host.c`.
- LPM: `kernel/s10plus/patches/0006-sec-ts-lpm-bind.patch(.required)`,
  `services/nuxel-s10/bin/nuxel-charger-mode-recovery.sh` + unit.
- Tests: `tests/pwnage52000/` (39 tests), updated `tests/pwnage49000`.

## Live evidence (post-reboot)

- SSH up 48 s after reboot; no `androidboot.mode` in `/proc/cmdline`.
- `nuxel-wayland`, `nuxel-wl-fb`, `nuxel-http-bridge`, `nuxel-bridge`,
  `nuxel-web`, `nuxel-charger-mode-recovery`: **active**.
- Touch: `sec_touchscreen` registered; `/sys/class/sec/tsp` present.
- Native dock: `NAV_DOCK_START visible=0 lock=unknown home=not-ready`;
  unlock → `NAV_DOCK_SHOW lock=unlocked`; lock → `NAV_DOCK_HIDE`.
- Lock state: boot unknown/absent = fail-closed; unlock writes
  `locked:false`; re-lock writes `locked:true`.
- Boot-mode guard: `BOOTMODE=NORMAL`, `SEC_TOUCHSCREEN_REGISTERED=1`,
  `allow_reboot=0`, `REBOOT_ACTION=none`.
- GPU: `PARTIAL`, Phoc `mali-kbase` accelerated, WebKitGTK
  `SOFTWARE_FALLBACK`, DECON pan failures 0.
- Metrics: `gpu_memory_kib=11652`, source
  `/sys/kernel/debug/mali/gpu_memory`, pages 2913 × 4096,
  `gpu_memory_status=ok_shared_budget_reference`.
- NFC: `BLOCKED_KERNEL` (`CONFIG_NFC` unset).
- Fingerprint: `BLOCKED_SECURE_PROVIDER` (device nodes present, no TEE provider).
- Camera: policy gate ALLOWED/BLOCKED round-trip; frame capture
  `capture_supported=false`.
- Microphone: `UNSUPPORTED_NO_CAPTURE_SOURCE` (no PipeWire source; monitor
  loopback excluded).

## Tests run

- `pytest -q tests/pwnage52000`: **39 passed**.
- `pytest -q tests/pwnage49000 tests/pwnage52000`: **53 passed** after
  updating the obsolete PWNAGE-49000 lock-bar assertion to the new privacy rule.
- `tools/s10plus/a33/tests/test-bootmode-guard.py`: **0 failing assertions**.
- Metrics compiled on the phone with `-Wall -Wextra -Werror`; `--self-test` rc 0.
- Navdock and `nuxel-pwa-host` compiled on the phone as AArch64.
- Settings layout audit: Chromium CDP at 320×640, 360×760, 384×832, 393×852,
  430×932, 640×320, 760×360: all panels PASS.
- Full `pytest tests` has a pre-existing collection abort in
  `tests/pwnage44000/test_files_send_and_render.py` (`sys.exit` at import), so
  the affected suites were run directly; 127 passed / 10 unrelated
  pre-existing audio/remote-desktop/app-registry assertions remain outside this mission.

## Deployment

Backups: `/root/pwnage-52000/backup-<UTC>/` on the phone (PWA tree, bridge,
binaries, units). Deployment was staged over Wi-Fi SSH; only affected services
were restarted. Phoc/`nuxel-wl-fb` were not restarted to refresh CSS/JS; the
final reboot verified a clean cold userspace start.

## Remaining blockers

1. **Charger cold boot**: needs TWRP + BOOT-only flash of the prepared kernel.
   The acceptance test cannot be claimed from a warm reboot.
2. Flatpak sandbox (`unshare -U` EPERM).
3. NFC kernel config; fingerprint TEE provider; microphone capture source.
4. WebKitGTK acceleration (no linux-dmabuf path); current verdict stays PARTIAL.
5. Clean ARM64 rootfs build was not run because the Mac host has 1.8 GiB free;
   ARM64 binaries were built and verified directly on the S10+ instead.
