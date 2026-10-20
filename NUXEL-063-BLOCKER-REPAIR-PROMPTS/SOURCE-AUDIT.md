# Nuxel v0.6.3-beta — Independent completeness audit

Date: 2026-10-20

**Verdict: NOT COMPLETE. Not production-grade under the acceptance contract in `final(1).md`.**

## Audited inputs

- Owner's `final(1).md` (13 phases plus verification, hardware test, packaging criteria; 27-row acceptance matrix).
- `nuxel-v0.6.3-beta-FULL-dropin.zip` as previously generated and available in the active conversation sandbox.
- The archive opens successfully (`zipfile.testzip() == None`); 11,912 entries and approximately 193 MiB uncompressed source/evidence content. Valid ZIP integrity is not a hardware-functional result.

### Tests rerun in this environment

- `python3 tools/s10plus/a43/test-a43-source.py`: **PASS**. This explicitly checks static source contracts, not functionality.
- `python3 tools/s10plus/a39/tests/test_a39_assets.py`: **PASS**. BG1 and BG2 are present and byte-identical to their source images, and expected references/manifests exist.
- `node --check` on `pwa/nuxel-apps/settings/wifi-settings.js`, `pwa/nuxel-home/js/launcher.js`, and `pwa/nuxel-apps/files/js/files.js`: **PASS** syntax checks.
- No access to physical S10+, USB shell, ALSA devices, Broadcom radio, GitHub Actions, or the published release. No physical, image-boot, GitHub-remote, or downloaded-artifact acceptance test was executed here.
- The archive's own `A43-VERIFICATION.md` lists the local release-tool suite as **TIMEOUT** and the physical acceptance areas as **UNVERIFIED**. Its historical pass claims for A34 were not rerun in this audit.

## Highest-confidence findings

### P0 — Absent production acceptance gates

1. **Speaker/audio is not brought up.** `configs/alsa-ucm/beyond-madera/HiFi.conf` contains empty `EnableSequence`/`DisableSequence` blocks for the verb, Speaker, Headphones and Headset. The file explicitly states the physical Madera/CS35L40 route is not programmed. Audible startup cue, volume cue, and normal playback cannot be certified. `docs/beta-finalization/manual-proof/06-audio.md` says `NEEDS_OWNER_TEST`.
2. **Wi-Fi hardware and internet are not certified.** A real NetworkManager-backed scan/connect/disconnect API exists in `services/nuxel-bridge/src/bridge.py` and a Wi-Fi tab in `pwa/nuxel-apps/settings/`, but no supplied result proves the S10+ kernel binds its Broadcom radio, loads firmware, associates, obtains IP/DNS or passes HTTPS. `docs/beta-finalization/manual-proof/04-wifi.md` says `NEEDS_OWNER_TEST`. UI controls are not radio bring-up.
3. **Quick Settings is only genuinely wired for Wi-Fi.** `pwa/nuxel-home/js/qs.js` `_toggle()` invokes `_setWifiEnabled()` only for `wifi`; for Bluetooth, mobile, location, DND, flashlight and rotate, it explicitly displays “control is unavailable on this build.” This fails `final.md` Phase 13.
4. **Files application does not operate as a complete real-filesystem explorer.** `pwa/nuxel-apps/files/js/files.js` loads a bridge `storage.list-dir` once, initializes `currentPath='/'`, and `_navigateTo()` simply updates the selected path and rerenders cached entries. `_createFolder()`/`_deleteItem()` only mutate an array/localStorage rather than making real filesystem mutations. Image and text previews are placeholder `alert()`s. There is no complete ZIP create/extract/copy/move/trash implementation in this UI. Default directory is not the logged-in user's home as required. Additionally, file metadata is interpolated into `innerHTML` without text escaping; treat untrusted filename/metadata injection as a potential security issue for a real filesystem portal.
5. **Browser is not a full browser.** `pwa/nuxel-apps/browser/index.html` embeds content in an iframe and `browser.js` uses `els.view.src = target`, a local/offline page-viewer architecture. Sites that disallow framing will fail. There is no full native top-level WebKit multi-tab/download/private-session implementation meeting Phase 4. This is acknowledged in `CHANGELOG.md` and `A43-VERIFICATION.md`.
6. **GPU metric service is not present in the fresh S10+ rootfs build path.** `services/nuxel-metrics/` contains real C daemon and systemd units, while `tools/s10plus/a40/package-live.sh` and `install-live.py` separately build/install them. `images/s10plus/build-phone-rootfs-inside-fedora.sh` has no reference installing/enabling `nuxel-metricsd` or its socket. Fresh image parity with the A40 live payload is therefore not established. Additionally, `services/nuxel-metrics/nuxel-metricsd.c` deliberately reports `gpu_memory_kib:null`, and `pwa/nuxel-home/js/system-monitor.js` always renders GPU MEM as N/A. This is an honest fallback, not a measured GPU-memory feature.
7. **Custom artwork is source-ready but not phone-verified.** BG1/BG2 bytes and references pass source tests, and `pwa/nuxel-home/css/launcher.css` contains A43 `.dock::before` corrections. No running WebKit computed-style inspection, device HTTP evidence, or real framebuffer acceptance proves the backgrounds render. The updated owner's `final(1).md` explicitly reports **no dock background and inability to switch**.

### P1 — Major incomplete hardware/app surfaces

8. **Camera:** Camera PWA attempts `getUserMedia`; that requires real V4L2/portal/sensor exposure, not proven. `docs/beta-finalization/manual-proof/15-camera.md` says `NEEDS_OWNER_TEST` and requires a real captured image.
9. **NFC:** Diagnostic/configuration exists; no controller/NCI/tag read evidence. `docs/beta-finalization/manual-proof/12-nfc.md` says `NEEDS_OWNER_TEST`.
10. **GPS/Maps:** `GeoClueConnector` and offline, opt-in tile Map UI exist. GNSS fix, per-app permission end-to-end, live location and online tile/provider compatibility remain unverified.
11. **Bluetooth:** Permissions/service groundwork exists, but live HCI initialization, pairing and A2DP output have not been verified here.
12. **Hardware button shortcuts/torch/screenshots:** Button-manager source contains gesture classification and flashlight requests; `flashlight_request()` sends a request and states that the actual LED is owned by another backend. There is no physical torch or screenshot proof in the audit evidence. Quick Settings flashlight is explicitly unavailable.
13. **Status-bar honesty:** Source status rendering exists but correctness of cellular/SIM, Wi-Fi state, sound mode, charge and absence of overlapping icons has not been established by on-screen/device evidence.
14. **Home gestures & performance:** A43 static checks and CSS changes exist; no frame-time measurements, compositor device tests, or owner confirmation of drawer/zoom/scroll/drag correctness. A static source contract is insufficient.

### P1 — Release and documentation discrepancies

15. `VERSION` is `v0.6.3-beta`, and `.github/workflows/release.yml` responds to `push` on `main`, tags `v*`, and `workflow_dispatch`. It has a conditional S10+ image build and prerelease-publishing path after builds succeed. This is **structural release automation**, not a successfully executed GitHub release. A merge without a new VERSION tag intentionally skips publication.
16. The GitHub S10+ image rootfs copies the `pwa/` tree (`images/s10plus/build-phone-rootfs-inside-fedora.sh`), but not every optional live installer component (notably metrics). An image build passing does not prove it contains/boots every live-deployed feature.
17. Documentation is partially stale: `README.md` still has a `## What's new in v0.6.1-beta` heading despite the top-level v0.6.3-beta notice. The `CHANGELOG.md` has a historical A39 section preceding its main heading. `final.md` cannot be treated as completed acceptance evidence merely because copied into the archive.

## Requirement-by-requirement matrix

Legend: **PARTIAL** = relevant implementation or configuration exists but acceptance is unmet; **MISSING** = key requested operations are absent; **UNVERIFIED** = needs live hardware/device proof; **SOURCE ONLY** = static artifact/code checks passed.

| # | `final.md` acceptance area | Audit verdict | Key reason |
|--:|---|---|---|
| 1 | Navigation dock background | PARTIAL / UNVERIFIED | Source assets/styles; no handset rendering proof |
| 2 | Four-app dock background | SOURCE ONLY; owner reports FAIL | Image hashes pass; owner still sees no dock artwork |
| 3 | Quick Settings panel backgrounds | PARTIAL / UNVERIFIED | Graphics and CSS present, final display unknown |
| 4 | Custom icon loading | PARTIAL / UNVERIFIED | Assets exist; not every physical rendering state proven |
| 5 | Live CPU % + MHz | PARTIAL | Collector code exists, clean image daemon install absent |
| 6 | Live RAM % + GiB | PARTIAL | Collector exists, clean image daemon install absent |
| 7 | Live GPU % + MHz | PARTIAL / UNVERIFIED | Real source conditional; N/A if hardware instrumentation absent |
| 8 | Live GPU allocated memory | NOT DELIVERED AS A NUMERIC METER | Explicit `null`/N/A shared-memory fallback |
| 9 | Wi-Fi adapter/radio | UNVERIFIED / BLOCKED | No physical driver/firmware/association evidence |
| 10 | Wi-Fi Settings | PARTIAL | NM scan/connect/power/disconnect; missing saved/forget/hidden/detail functions |
| 11 | Real internet | UNVERIFIED | No association→DHCP→DNS→HTTPS result |
| 12 | Complete browser | PARTIAL | iframe-based page viewer, not full browser |
| 13 | Full File Explorer | MISSING ESSENTIAL FUNCTIONS | localStorage mutations, placeholder viewers, no proper path reload |
| 14 | ZIP file operations | MISSING | No complete create/extract/validate UI implementation |
| 15 | Physical speaker route | BLOCKED | UCM speaker route empty, no audible confirmation |
| 16 | Boot/volume audio cues | UNVERIFIED / NOT AUDIBLE | Decoder/service code cannot replace missing physical output |
| 17 | Sound modes | PARTIAL / UNVERIFIED | Settings/config exist, system-wide enforcement unproven |
| 18 | Bluetooth | PARTIAL / UNVERIFIED | Configuration/portal scaffolding, no real pairing/A2DP proof |
| 19 | NFC | UNVERIFIED | `NEEDS_OWNER_TEST` diagnostic status |
| 20 | GNSS location | UNVERIFIED | GeoClue integration not proof of physical GPS fix |
| 21 | Nuxel Maps | PARTIAL | Offline grid + optional tile template; no GNSS/network acceptance |
| 22 | Camera capture | PARTIAL / UNVERIFIED | PWA + portal/diagnostics; real sensor frame unproven |
| 23 | Flashlight | NOT WORKING IN QUICK SETTINGS | `_toggle()` returns unavailable; actual torch unverified |
| 24 | Hardware screenshot | PARTIAL / UNVERIFIED | Request/diagnostic integration; physical screenshot unproven |
| 25 | Double Power/Bixby shortcuts | PARTIAL / UNVERIFIED | Input FSM exists, real action/electrical behavior not certified |
| 26 | Honest status bar | PARTIAL / UNVERIFIED | UI code exists, no full hardware-state verification |
| 27 | Functional Quick Settings | FAILS ACCEPTANCE | Only Wi-Fi invokes functional backend; other tiles unavailable |

## Highest-priority next engineering steps

1. **Do not publish as a production/daily-driver-complete release.** Label v0.6.3-beta a source/engineering prerelease.
2. **Fix the confirmed file-browser gap** with a real permission-scoped filesystem API, dynamic directory navigation, safe escaped rendering, copy/move/rename/trash and archive tools. Replace placeholder previews.
3. **Fix release-image parity**, installing and enabling the metrics daemon and all other live-installed services/binaries in the Fedora ARM64 S10+ rootfs path, then build and test the artifact in CI.
4. **Wire functional Quick Settings** to actual OS services with read-back and unavailable states, not only Wi-Fi, and implement the requested Wi-Fi saved/hidden/details flow.
5. **Replace iframe browser** with top-level native WebKit-backed tab/window support and proper downloads/TLS/private-data isolation.
6. **On the device:** trace actual ALSA card/PCM→Madera codec→CS35L40 amps with safe measured mixer controls, and verify real low-volume playback; separately verify Broadcom enumeration, firmware, radio scanning, association, DHCP, DNS and HTTPS.
7. **Fix and physically inspect dock rendering** using deployed asset hashes + HTTP responses + computed styles + actual framebuffer screenshot. Compare the screenshot to the source image; ask owner to confirm both BG1/BG2.
8. **Complete remaining device surfaces** (BT, NFC, GNSS, camera, torch, hardware chords) with real device evidence, not mocks; keep unsupported functions explicitly unavailable.
9. **Run real GitHub CI and remote release verification** from the merged main SHA; confirm the S10+ image archives, checksums and bootability. The YAML being present does not prove that the build/release succeeded.
10. **Update documentation from evidence** and re-audit all 27 surface rows with source, build, deployment and owner-confirmed hardware columns.

## Bottom line

Nuxel has a meaningful working foundation and reproducibility-oriented tooling. This ZIP contains a valid source tree, substantial user-interface work and several genuine service connectors. **It is not yet a production-complete daily-driver release** under the requirements in `final(1).md`. The most critical concrete issues are the empty speaker routing, unverified WLAN hardware, incomplete Quick Settings, non-production-grade File Explorer and browser, the metrics-service image-build omission, and unverified dock rendering.
