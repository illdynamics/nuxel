# QBT2000 fingerprint — forensic archive audit and risk register

**Input** `nuxel-ds-ssp (1)(2).zip` (Nov 22, 2026 snapshot); about 20,860 ZIP members, ~796 MB uncompressed; extracted read-only for analysis. No live SSH connection attempted. `VERSION` reads `v0.9.1-beta`. Archive contains no `.git`, `reports/`, `packs/` or `pwn/finger*.md`. The existing `hw/NUXEL_02_QBT2000_FINGERPRINT_STANDALONE.md` is a comprehensive historical mission prompt, **not evidence that it was executed successfully**.

## Verdict and scoring (heuristic, not a measurement)

| Layer | Weight | Demonstrated maturity | Weighted points | Evidence and gap |
|---|---:|---:|---:|---|
| Sensor presence / identity | 8 | 100% | 8.0 | Historical QBT2000 name/vendor, kernel nodes |
| Kernel exposure and preliminary transport | 12 | 60% | 7.2 | Driver binds; no proof that secure capture/match IPC works |
| Secure OS, signed trustlet, secure storage | 25 | 0% | 0.0 | OEM-signed TA not established; historical integrity issue unverified |
| Vendor HAL / proven compatible ABI | 15 | 0% | 0.0 | No usable real fingerprint HAL service in archive |
| Native bridge / authorization policy | 12 | 30% | 3.6 | Custom Python RPC + status but critical trust-boundary gaps |
| Real enrollment, match, delete, unlock | 15 | 0% | 0.0 | Explicit `ta_enroll_not_implemented`, `ta_match_not_implemented` |
| Settings / Home lockscreen UX | 8 | 65% | 5.2 | UI and PIN fallback exist; simulated edge-touch path misleading |
| Physical acceptance / repeatable secure tests | 5 | 0% | 0.0 | No real fingerprint match evidence or dedicated secure test suite |
| **TOTAL** | **100** |  | **24.0** | **≈24% engineering groundwork; 0% demonstrated physical authentication** |

Uncertainty is at least ±10 percentage points, since current live software/TEE/firmware were not inspected. The sensor-driver half may feel 60–80% ready, but end-to-end biometric unlock is gated by secure-world signing and a completely unimplemented genuine match. Do not compare this directly with NFC/SSP progress without a common functionality-weighted rubric.

## Historical timeline / evidence classification

| Evidence | Source | Classification | Meaning |
|---|---|---|---|
| Oct 31 PWNAGE-45000 report | `docs/beta-finalization/live/PWNAGE-45000-REPORT.md` | HISTORICAL_LIVE | QBT2000 driver/devices present, no secure TEE provider, PIN flow proven |
| Nov 7 baseline | `docs/pwnage-89000/evidence/20261107T135556Z/baseline/system/fingerprint.txt` | HISTORICAL_LIVE | Linux 4.14.253-gf7194c1d15ed-dirty, Fedora 43; not a current 22 Nov boot attestation |
| PWNAGE-91000 diagnostic | `diagnostics/pwnage-91000/hardware/fingerprint-live.txt` | HISTORICAL_LIVE | `/dev/qbt2000_fd`, `/dev/qbt2000_ipc` root 0600; sysfs `name=QBT2000`, `vendor=QCOM`, `type_check=7`, position, 25 MHz SPI clock field; `tz:1` log (not a secure match) |
| Historical bridge response | `diagnostics/pwnage-91000/hardware/fingerprint-live.txt` | HISTORICAL_LIVE | `schema /1`, `BLOCKED_SECURE_PROVIDER`, no enrolled fingers, PIN fallback |
| New source provider | `services/nuxel-bridge/src/fingerprint_provider.py` | PRESENT_IN_ZIP | `schema /2`, Vault HMAC metadata ceremony, no signed enrollment/match backend |
| Nov 14 boot issue | `evidence/bootloop-0023-20261114-1002/FIX-REPORT.md` | HISTORICAL_LIVE | Raw Image needed; gzip kernel caused boot failure; appended DTB overflowed BOOT size; successful known-good reflash eventually restored Nuxel |
| Latest secure-world integrity alert | `hw/NUXEL_02_QBT2000_FINGERPRINT_STANDALONE.md` references `packs/finger/...` | UNKNOWN | Mentions `startup.tzar`/`libtzld.so` hashes, but original report and artifacts not in this ZIP; live validation mandatory |
| Actual current phone Nov 22 | Not connected | UNKNOWN | Do not infer from ZIP or old diagnostics |

## What exists / what was written

1. **Kernel:** QBT2000 hardware is registered in historical live boot. `kernel/s10plus/` has build configuration and numerous patches for NFC, SSP, display and camera; no fingerprint-specific patch in this ZIP. Full pinned Linux4 tree (`kernel/s10plus/.build/src`) is *not bundled*. Do not assert a fingerprint kernel rewrite occurred.
2. **Fingerprint service, new custom code:** `services/nuxel-bridge/src/fingerprint_provider.py` (~435 lines): `_sensor()`, `_ta()` helper status, Vault HMAC record, a two-edge-click 'ceremony', current `enroll`, `test`, `delete`, `status` routes. It refuses real enroll/match when provider absent; **not a functioning biometric driver**.
3. **Root bridge:** `services/nuxel-bridge/src/api.py` routes fingerprint/biometrics and security namespaces, plus an attempted owner allow-list, and forwards successful provider results into `security_provider`.
4. **Credential handling:** `services/nuxel-bridge/src/security_provider.py` (~650 lines) holds PIN/pattern verifier, biometric setting, fallback mode, lock state, and `unlock_biometric` method. A source test only asserting `success`+`authenticated` is not trustworthy end-to-end proof.
5. **UI:** `pwa/nuxel-apps/settings/{index.html,pwange45000-settings.js}` handles enrollment/status and settings, `pwa/nuxel-home/js/lockscreen-auth.js` handles scanner artwork and PIN fallback; the Setting screen guards real enrollment on readiness but the underlying 'two touch' protocol is entirely UI-reported.
6. **CLI/config:** `tools/a80/fingerprint-enroll.py` drives the metadata ceremony and Vault logic; `configs/nuxel/security/biometric-unlock.json` defaults to disabled. Metadata `fingerprint-enrollment.json` is in ordinary OS storage, only its *HMAC key* comes from Vault: it is not a secure sensor template and is not literally a template stored in the Vault.
7. **Absent:** proven TEEGRIS trustlet startup, matching exact signed TA, usable stock fingerprint vendor HAL and runtime, native secure client, real capture/verify/token path, authorized secure delete, real hardware scan receipt, fingerprint-specific security test suite.

## Highest-priority code risks (fix before connecting any real matcher)

- **Critical — untrusted match result boundary.** `security_provider.py` `unlock_biometric` presently decides success from ordinary dictionary fields (`success`, `authenticated`) rather than an unforgeable provider assertion; `api.py` exposes an owner-app-facing `security/unlock-biometric` verb. This is currently gated by fingerprint mode, which cannot normally activate without the absent provider; still unsafe to enable in future. Restrict all hardware auth to an internal, authenticated, nonce-bound broker result. Do not publish an exploit or accept mock auth as a hardware pass.
- **High — incomplete owner verb coverage.** `api.py` owner restriction lists `enroll`, `delete`, `remove`, `test`, `verify`, `cancel` but omits `ceremony-start`, `ceremony-touch`, `ceremony-commit`, `enroll-record` and `authenticate`. Deny by default; require local owner credential confirmation for actual mutation.
- **High — provider readiness false-positive.** `_ta()` accepts returncode zero and a case-insensitive `healthy` substring from an executable. A text string is not attestation; use an authenticated versioned secure provider handshake and separate service liveness from TA acceptance.
- **High — no real enrollment.** The simulated ceremony increments edge counts based on API strings, not sensor events. `cer_touch` and `cer_commit` permit omitted tokens. Production Settings should never treat this as registered biometric authentication; decommission or isolate demonstration metadata.
- **High — manually set enrollment and delete semantics.** `security_provider.set_biometric` accepts caller `enrolled` when provider marked ready and `fingerprint_provider.delete` always reports successful metadata deletion; it does not prove a secure TA slot was erased. Derive status/deletion from a genuine secure slot inventory.
- **Medium — misleading capability flags.** Source `status()` can return `enrollment_supported=true`, `test_supported=true`, `deletion_supported=true` while `ready=false` and no actual biometric TA exists. Break out `metadata_record_supported` from `secure_enrollment_supported` and present actual hardware readiness.
- **Medium — policy.** Current default `unlimited` attempts is an explicit legacy Nuxel PIN setting; a future biometric path needs secure retry throttles independent of that setting and signed-provider lockout. Preserve owner PIN fallback rather than silently resetting credentials.
- **High — boot/DT fragility.** A previously attempted gzip kernel and oversized appended DTB made S-Boot fail early. `device/s10plus/deviceinfo` says A-only, legacy v1, page 2048, TWRP/Heimdall; no fastboot. Preserve exact good DTB/DTBO and boot layout, prefer userspace.

## Offline checks (audit host; not phone)

- AST syntax parsed successfully for `fingerprint_provider.py`, `security_provider.py`, `api.py`, `fingerprint-enroll.py`; `node --check` succeeded for Settings and lockscreen auth JS.
- `python -m unittest -q tests/v086/test_lock_security.py`: **6 tests passed**.
- `python tests/pwnage_a84/test_a84_security_presets.py`: **failed/aborted**, including outdated expectations and a `FileNotFoundError` for a lock-state temp file; cannot count suite as passing.
- `python tests/pwnage_a80/test_a80_lockscreen.py`: **3 reported failures**, two outdated source-text contract checks and missing `jsdom` in this host environment. Tests need reconcile, not conceal.
- `bash boot/s10plus/tests/test-boot-image-gates.sh`: **exit 3 SKIP-PREREQ**, missing gitignored historical known-good build fixtures. No phone BOOT image was generated/flashed or tested.
- None of the above proves real fingerprint enrollment, TA health or match.

## External verified starting points (not compatibility proof)

- Android biometric security requirements: https://source.android.com/docs/security/features/biometric — secure isolated acquisition/recognition, encrypted templates, protection from replay, restricted hardware channel.
- LineageOS Exynos9820 common `common.mk` (`lineage-23.2`): https://github.com/LineageOS/android_device_samsung_exynos9820-common/blob/lineage-23.2/common.mk — packages `android.hardware.biometrics.fingerprint-service.samsung`; Android-specific integration, not native Nuxel proof.
- Lineage proprietary list: https://github.com/LineageOS/android_device_samsung_exynos9820-common/blob/lineage-23.2/proprietary-files.txt — lists TEEGRIS tzdaemon/teecl/trustlets and generic test libraries, with some assets explicitly from *beyond1lte*. Check SM-G975F provenance and runtime dependencies, not just filenames.
- Pinned kernel source as declared by repo: https://github.com/Linux4/android_kernel_samsung_exynos9820 (commit `f7194c1d15eded1c2a1a4dc63825b26103435cc0`). Not present under `.build/src` in this archive.

## How many rounds / likelihood of a few reflashes?

**Achievable within 2–3 careful Thinking rounds + 1–2 fast-model rounds without touching BOOT:** reconcile current source/live state, fix the authentication boundary and misleading UX, write tests, and produce a precise secure-world feasibility verdict. **Not guaranteed within a few rounds:** genuine secure enrollment, physical verification and secure deletion. They require a matching lawful OEM TA, secure OS acceptance, vendor HAL ABI or adapter and physical owner testing. If those are available and demonstrably working, a further 1–3 engineering rounds may integrate the service, followed by acceptance. Otherwise a model cannot produce vendor signing keys or a trustworthy secure enclave by reasoning longer.

**Expected device flashes for fingerprint alone: 0.** Do not touch DTB/DTBO; a BOOT reflash becomes admissible only after documented kernel root-cause proof and a complete hash-verified recovery plan. After a failed candidate, restore known-good first and require a healthy Nuxel boot, not just TWRP access.

## Completion contract

PASS = real signed provider, owner enrollment on glass, secure match, two independently successful unlocks, wrong/no finger rejected, revoked enrollment not recognized, reboot and suspend/resume, PIN fallback intact, authorization/lockout proven, no private biometric material exported, and documented stable Nuxel boot. Anything less remains BLOCKED/PARTIAL with exact cause.
