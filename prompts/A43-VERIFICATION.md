# A43 verification record (2026-10-20)

**Scope:** File-based source checks, not an actual S10+ hardware acceptance test.

- `tools/s10plus/a34/tests/run-a34-tests.sh`: PASS on this source snapshot.
- `tools/touchable/run-tests.sh`: PASS; fixed null-safe Home layout lock when constructed by isolated harness.
- `tools/s10plus/a39/tests/test_a39_assets.py`: PASS, original BG1/BG2 SHA-256 unchanged.
- `tools/s10plus/a43/test-a43-source.py`: PASS.
- `tools/s10plus/a33/verify-app-registry.py`: 0 FAIL, 6 WARN, 2 DEFER; browser registered correctly.
- New Python bridge: `python3 -m compileall`: PASS.
- New JavaScript: `node --check` Wi-Fi Settings and Home launcher: PASS.
- Release workflow: local YAML parse and version/tag/branch/source-gate inspection PASS.
- `tools/beta/tests/test-release-tools.sh`: TIMEOUT locally. Not a PASS.
- GitHub Actions release and image build: NOT RUN in this sandbox.
- Physical audio output: UNVERIFIED. Existing UCM sequences require real device route evidence.
- Physical S10+ Wi-Fi (AP association, IP, DNS, TLS): UNVERIFIED.
- Actual visual dock/UI/sensors/camera/NFC/GNSS/Bluetooth: UNVERIFIED.

## Detailed existing component coverage

`final.md` describes 18 engineering phases; its acceptance matrix has 27
surfaces. Source modules for launcher graphics, metrics, NetworkManager,
Browser, File Explorer, sound, Bluetooth, NFC, GNSS/Maps, Camera, buttons,
status bar and Quick Settings already exist in the uploaded repository.
Existence is not proof of functional integration. This patch addresses the
rooted dock stacking issue, Wi-Fi Settings RPC/UI, Browser app registry, Home
gestures and PR-to-release automation. **It does not implement and prove all
remaining hardware phases** and does not replace the kernel, firmware or
speaker-amplifier state on the live handset.

## Specific on-device blockers and next evidence

1. **Speaker**: beyond-madera UCM has empty speaker enable/disable sequences;
   capture ALSA/DAI/DAPM/firmware state and establish a safe verified path.
   No guessed CS35L40 register writes or amplifier safety bypasses.
2. **Wi-Fi**: S10+ Broadcom BCM4375-class radio needs verified driver,
   firmware/NVRAM, rfkill, NM management and successful real scan/association.
3. **Browser**: a WebKit iframe-based shell cannot display external sites that
   forbid framing; a native top-level WebKit view is needed for full browser
   compatibility (and should enforce TLS, downloads and portal permissions).
4. **Bluetooth, NFC, GNSS, Camera**: owner live tests and platform-driver
   evidence are still needed; unsupported toggles must report unavailable.
5. **Release**: Github Actions `release.yml` is structurally updated, but
   CI remote execution, source-built S10+ image bootability and actual release
   URL cannot be verified in this offline workspace.
