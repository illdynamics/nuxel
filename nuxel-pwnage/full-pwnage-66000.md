# FULL-PWNAGE-66000 — NUXEL S10+ ULTRASONIC FINGERPRINT AUTHENTICATION

**Mission:** turn the already-detected Qualcomm QBT2000 ultrasonic in-display fingerprint hardware on the Samsung Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820) into a real, secure, native Nuxel fingerprint-enrollment and lock-screen authentication feature — or establish the precise remaining external dependency without ever faking biometric success or weakening the lock screen.

**This is an implementation mission, not a research-only exercise.** Read this entire specification, inspect the live repository, implement every part that can be implemented safely, build and test it, and deliver a complete deployable patch plus an evidence-based report. Do not stop after writing another investigation document. The hardware and kernel driver have already been detected; the principal challenge is the trusted fingerprint userspace/TEE path and its integration with Nuxel's existing security provider.

---

## 0. Non-negotiable outcome and safety boundary

The desired end state is:

1. Nuxel detects the real QBT2000 sensor and its driver accurately.
2. A trusted, device-compatible provider can request enrollment and authentication using the exact QBT2000 protocol and matching secure-world components.
3. Fingerprint capture, feature extraction, matching, and template storage stay inside the trusted hardware/TEE boundary. Normal-world Nuxel processes receive only documented progress/status and a cryptographically authenticated match result — never raw fingerprint imagery, minutiae, templates, or an unauthenticated `matched=true` boolean.
4. The owner can enroll, label, test, and delete fingerprints from Nuxel Settings.
5. The lock screen can request a scan and unlock only after validating a fresh, non-replayable secure authentication assertion. PIN remains a reliable fallback and remains mandatory after reboot/strong-auth events.
6. All APIs, indicators and Settings states describe actual hardware/provider readiness. No simulated success, dummy enrollment, fake scan event, generic libfprint assumption, or optimistic UI.
7. Boot, suspend/resume, shutdown, normal touchscreen input, power management, and the existing PIN/pattern lock remain fully functional.

**If the required vendor trusted application, signed firmware, secure-world service, signing chain, or protocol is unavailable, do not bypass the TEE or synthesize a success.** Complete all safe detection, diagnostic, integration, packaging, UI, tests and PIN-fallback work, then report the exact missing artifact and the safe owner-supplied action required. A correct `BLOCKED_SECURE_PROVIDER` result is preferable to a security bypass. However, exhaust the repository, the pinned kernel source, available local/vendor partitions, lawful stock firmware sources, and compatible open implementation references before declaring it blocked.

### Absolute prohibitions

- Never export, log, cache, serialize, copy, upload, or expose raw fingerprint images, feature vectors, minutiae, templates, calibration secrets, TEE keys, or vendor secure-app memory into the normal world.
- Never treat the finger-detect IRQ, touch presence, QBT IPC IRQ, a sensor wake event, a successful `open()`, or an ioctl return code as a fingerprint match.
- Never use `/dev/qbt2000_fd` or `/dev/qbt2000_ipc` directly from browser JavaScript, a PWA, a regular desktop app, or an untrusted session-user process.
- Never grant the entire `nuxel` session user broad read/write access to the QBT device nodes. Do not use `0666`, world-writable device nodes, broad `input` group access, or blanket permissive policies.
- Never remove Samsung secure-boot, TrustZone, TEE, RPMB, Keymaster, Gatekeeper, anti-rollback, Knox, or sensor security checks to make a test pass.
- Never patch bootloader, TrustZone OS, secure monitor, TEE firmware, RPMB, or device fuses. Never attempt to create or load an unsigned TA where the verified boot/security chain rejects it.
- Never downgrade or replace the current working kernel casually. Never flash automatically. Do not write to BOOT, recovery, vendor, modem, EFS, or other partitions as part of an unattended agent run.
- Never claim FIDO certification, spoof resistance, liveness, anti-presentation-attack, or payment-grade assurance based solely on the sensor model or its historic certification. State only what the complete deployed Nuxel stack has demonstrated.
- Do not add face unlock or fall back to camera-based biometrics.
- Never weaken the PIN, rate limit, lockout, lock-state authority, or app-launch lock enforcement to make fingerprint unlock appear functional.

---

## 1. Exact project/device baseline — use this, verify it, do not reinvent it

### 1.1 Target

- Device: Samsung Galaxy S10+ **SM-G975F** (`beyond2lte` / `beyond2ltexx`), Exynos 9820 / universal9820.
- Running kernel evidenced in the repository: Linux **4.14.253**, downstream Samsung kernel.
- The authoritative kernel source wrapper is `kernel/s10plus/build-kernel.sh`.
- Its pinned source is `https://github.com/Linux4/android_kernel_samsung_exynos9820` at commit `f7194c1d15eded1c2a1a4dc63825b26103435cc0`, defconfig `exynos9820-beyond2lte_defconfig`.
- Preserve the repository's existing kernel fragment and sorted/idempotent patch-application workflow. Inspect the exact checked-out source commit; do not assume the source code is already vendored in this ZIP.

The S10+ uses a Qualcomm **QBT2000 ultrasonic in-display fingerprint sensor**. This is not the Goodix GF3636 optical sensor listed for the separate Pixel 10 Pro XL device profile. Do not copy the Pixel fingerprint driver/configuration or write a Goodix/libfprint implementation for the S10+.

### 1.2 What is already present

The repo's historical physical-device evidence in `docs/beta-finalization/live/PWNAGE-45000-REPORT.md` records:

- QBT2000 kernel driver detected/bound.
- `/dev/qbt2000_fd` present.
- `/dev/qbt2000_ipc` present.
- Kernel threads/workqueue names including `qbt2000_debug_w` and `irq/440-qbt_ipc`.
- IRQ labels `qbt_finger_detect` and `qbt_ipc` were recorded in captured kernel state.
- The driver emits `fps_qbt2000_work_func_debug` diagnostics.
- The fingerprint provider intentionally reports `BLOCKED_SECURE_PROVIDER` because there is no verified trusted enrollment/authentication provider in the current Nuxel rootfs.
- No fingerprint template was read, imported, exported, or exposed.

Additional diagnostic capture in `scripts/s10plus-debug-pack/captures/20261015T164357Z-A20-live-run/last_kmsg4.txt` contains the QBT IRQ threads and a `tzdev_iwi_event` IRQ. This proves that a TZDev-related kernel interface was observed in that capture; **it does not prove that the correct fingerprint trusted application is installed, loaded, callable, or compatible.** Confirm the TEE implementation and live state on the phone. Do not identify the TEE OS from one IRQ label alone.

The same kernel may gate touchscreen, fingerprint and Wacom input in low-power/charger (`lpcharge` / `androidboot.mode=charger`) boots. Existing evidence is documented in:

- `docs/s10plus-autonomous-boot-repair/BETA-HARDWARE-FINALIZER/12-REMAINING-HARDWARE-BLOCKERS.md`
- `docs/s10plus-autonomous-boot-repair/BETA-HARDWARE-FINALIZER/01-TOUCHSCREEN-ROOT-CAUSE.md`
- `docs/beta-finalization/touch/CHARGER-MODE-ROOTCAUSE.md`
- `tools/s10plus/a33/nuxel-bootmode-guard.py`

Fingerprint support is a normal interactive-session feature. Do not remove the LPM gate or try to make fingerprint unlock active in charger mode. Detect and report the boot mode; if the device is in LPM, state that a normal interactive reboot is required.

### 1.3 Existing Nuxel code to inspect and extend

Authoritative files in the supplied source tree include:

- `services/nuxel-bridge/src/fingerprint_provider.py`
- `services/nuxel-bridge/src/security_provider.py`
- `services/nuxel-bridge/src/api.py`
- `configs/nuxel/security/biometric-unlock.json`
- `pwa/nuxel-home/js/security-lock.js`
- Nuxel Settings UI source under `pwa/nuxel-home/` (discover the actual active files; do not assume names or edit unused copies).
- `tests/pwnage45000/test_pwnage45000.py`
- `docs/beta-finalization/live/PWNAGE-45000-REPORT.md`
- `docs/beta-finalization/live/PWNAGE-45000-TODO.md`
- `kernel/s10plus/build-kernel.sh`
- `kernel/s10plus/defconfig`
- `kernel/s10plus/configs/live-required.config`
- `kernel/s10plus/patches/`
- `images/s10plus/build-phone-rootfs-fedora.sh`
- `images/s10plus/build-phone-rootfs-inside-fedora.sh`
- the S10+ systemd units, udev rules, image staging scripts and test harnesses discovered during inspection.

Do not blindly edit similarly named files for G7 Power or Pixel 10 Pro XL. Keep the provider abstraction reusable where practical, but this mission's physical acceptance target is the S10+ QBT2000.

### 1.4 Known placeholder behavior and a lock fallback defect to investigate

`fingerprint_provider.py` is deliberately a capability broker/placeholder. It currently searches for `/dev/fingerprint*`, `/dev/fp*`, `/dev/qbt*` and QBT sysfs/driver paths, but contains the explicit hard-coded expression equivalent to `secure = bool(devs) and False`. It always refuses enrollment, deletion and test operations. Replace this with a truthful, evidence-backed capability model; do not simply change `False` to `True`.

`security_provider.py` controls the authoritative lock state at `/run/nuxel/security/lock-state.json`; its credential file defaults to `/var/lib/nuxel/security/lock.json`; biometric preference defaults to `/etc/nuxel/security/biometric-unlock.json`. PIN/pattern verification is root-owned, salted scrypt with constant-time comparison and persistent failure throttling. Preserve these existing guarantees.

**Audit and fix this specific code path:** `_set_secret(mode="fingerprint")` currently stores a `fallback_pin_salt` and `fallback_pin_verifier` separately, while the generic `_verify_locked()` helper checks `salt` and `verifier`. `unlock()` must be inspected to verify whether it has a dedicated fingerprint-mode PIN-fallback branch. Do not assume it works: add regression tests proving the mandatory fallback PIN can actually unlock when mode is fingerprint, including rate-limit and failure persistence. Do not duplicate or accidentally compare against an absent normal PIN verifier.

The current `security-lock.js` treats `mode === "fingerprint"` as a PIN-fallback prompt. It has no complete trusted fingerprint enrollment or asynchronous scan flow. The new implementation must add that flow only after provider proof exists, while always retaining the PIN prompt.

### 1.5 External hardware/security facts to respect

- Qualcomm QBT2000 is the ultrasonic sensor in the Exynos Galaxy S10+ fingerprint assembly; use the exact sensor-specific stack, not a generic optical sensor driver.
- Standard Android fingerprint architecture separates the hardware-specific HAL from the trusted application in the secure environment. The trusted component performs enrollment/matching and returns authenticated results; raw biometric data must not be moved into ordinary userspace. Follow the same trust boundary even though Nuxel is not Android.
- The existence of the sensor, IRQs and a TZDev kernel interrupt is not enough to assert that an equivalent Linux user-space path is available.

Useful primary/technical references for the investigation:

1. Samsung S10+ teardown identifying the Qualcomm QBT2000 ultrasonic component: `https://www.techinsights.com/blog/samsung-galaxy-s10-teardown`
2. AOSP biometric authentication model and trusted-app flow: `https://source.android.com/docs/security/features/authentication`
3. AOSP fingerprint HAL security requirements: `https://source.android.com/docs/security/features/authentication/fingerprint-hal`
4. Samsung Knox hardware-backed security / TrustZone description: `https://docs.samsungknox.com/admin/fundamentals/whitepaper/samsung-knox-mobile-security/system-security/hw-backed-security/`
5. Samsung Knox biometric protection model: `https://docs.samsungknox.com/admin/fundamentals/whitepaper/samsung-knox-mobile-security/system-security/biometric-authentication/`
6. Qualcomm open-source QBT handler / QBT1000 driver may be useful as an architectural lead only: `https://android.googlesource.com/kernel/msm/+/3ac79f3f3b9d80342a4640012c0e4b1b5f8009c2/drivers/soc/qcom/qbt_handler.c`

**Important compatibility warning:** QBT1000/QBT handler source from a Qualcomm Snapdragon kernel is not the QBT2000 driver or necessarily the S10+ Exynos TEE ABI. It may help explain event/IPC patterns, but do not transplant its QSEE calls, ioctl structures, firmware identifiers, or assumptions into the Exynos target without source-level evidence.

---

## 2. Phase 0 — freeze baseline and inventory the active device

Before modifying anything:

1. Read this file completely, read `pwnage-66000.md`, then inspect the entire repository structure and git status.
2. Record the current HEAD, uncommitted changes, device target, image/kernel version, build scripts, tests and current release metadata. Do not overwrite another active agent's work.
3. Confirm the deployed system is the intended SM-G975F / `beyond2lte` / Exynos 9820 normal boot, not a different variant or charger-mode boot.
4. Capture a non-destructive baseline from the actual phone where the owner has made the existing SSH/debug transport available. Never invent live results when only archived logs are available.
5. Collect read-only evidence for:
   - `/proc/cmdline`, kernel release, device model/board, uptime and current boot mode;
   - `ls -l /dev/qbt*`, major/minor, owner/group/mode and open file holders;
   - relevant `/sys/class`, `/sys/bus`, `/sys/devices`, driver symlinks and uevents;
   - `/proc/interrupts` entries matching `qbt`, finger, IPC, TZDev and relevant IRQ counters;
   - kernel log entries for qbt probe, DT parsing, IRQ setup, regulator/clock/power, IPC, secure-world/TZDev, TUI and errors;
   - loaded modules and kernel config for QBT, TZDev/TEE, SPI, secure memory, DMA and relevant IOMMU support;
   - installed package state, systemd units, service users/groups, udev rules, filesystem mount points and current SELinux/AppArmor status if any;
   - `/vendor`, `/vendor/tee`, `/vendor/lib*`, `/vendor/bin*`, `/vendor/etc/init`, `/system/vendor`, `/mnt/vendor`, firmware mounts and any lawful local copy of the matching stock firmware/vendor partition.
6. Use read-only probes. Do not send experimental binary commands to the sensor, toggle its power rail, load unknown firmware or write calibration files during inventory.
7. Save redacted, minimal evidence under a new directory such as `docs/beta-finalization/live/evidence/pwnage-66000/baseline/`. Do not include fingerprint data, PINs, keys, auth tokens or personal files.

### Required baseline report

Create `docs/beta-finalization/live/PWNAGE-66000-BASELINE.md` with:

- confirmed hardware variant;
- driver and device-node findings;
- the exact captured qbt IRQ names/counters;
- TEE implementation evidence and confidence level;
- vendor app/HAL/library/trustlet evidence or absence;
- current service/user/device permissions;
- boot mode/LPM state;
- current Bridge and lock-state behavior;
- a clear distinction between **driver detected**, **finger present**, **TEE reachable**, **provider initialized**, **enrollment available**, and **authentication verified**.

---

## 3. Phase 1 — inspect the exact QBT2000 kernel implementation

The kernel source is fetched by `kernel/s10plus/build-kernel.sh`. Clone/fetch the exact pinned commit into the existing build source location or a separate read-only worktree. Do not switch the repository's pinned commit simply because another fork has extra features.

Perform a source audit:

1. `git grep -n -i 'qbt2000\|fps_qbt\|qbt_finger_detect\|qbt_ipc\|qbtspi'` across the exact kernel commit.
2. Identify the precise driver source file(s), Kconfig/Makefile entry, compatible strings, platform/device-tree node and bound driver.
3. Identify every device node created by the driver and the exact major/minor numbers, `file_operations`, ioctl definitions, `poll`/`read`/`write` semantics, blocking behavior and event queues.
4. Identify which node carries finger-detect events, which carries secure-world IPC events, and whether additional SPI, sysfs or misc nodes are required.
5. Trace the complete path from QBT interrupt to workqueue to userspace notification and secure application call. Determine whether `qbt_finger_detect` reports only physical presence or whether any secure match result is available through a different event.
6. Document every power, regulator, GPIO, IRQ, clock, reset, pinctrl, SPI configuration and display/touch coordination dependency from the device tree and driver.
7. Identify any `lpcharge`, `androidboot.mode`, `sec_bat_is_lpm_check`, `current_chrooted`, TUI or secure UI gates. Keep the existing safety/power gates unless a specific normal-mode bug is proven and fixed with a narrow patch.
8. Check driver error handling: probe success vs firmware/TA initialization, IRQ enable/disable, suspend/resume, runtime PM, wake-lock behavior, timeouts, file lifetime, mutexes, event queue overflow and stale handles.
9. Audit debug logging. Ensure debug output cannot include biometric payloads, template material, secrets or secure IPC buffers.
10. Check whether qbt device nodes can be created while the required trusted app is absent. If so, reflect that explicitly in provider states; device-node presence is not provider readiness.

Produce a concise `docs/beta-finalization/live/evidence/pwnage-66000/qbt-kernel-interface.md` with the actual interface definitions and source line references/commit hash. Do not guess ioctl numbers or binary structures.

### Kernel modification threshold

Do not modify the kernel if all required QBT interfaces already work in the current `4.14.253` build. The desired first approach is a userspace secure-provider path using the exact existing kernel driver.

Only patch the kernel when a source-proven problem prevents safe operation, for example a required event is not surfaced or a normal-mode power transition is broken. Any patch must be minimal, isolated, justified by evidence, covered by a test/review, built with the pinned wrapper, and verified against the live device. No LPM bypass, no broad driver rewrite, and no unverified ioctl ABI additions.

---

## 4. Phase 2 — identify the matching secure-world / vendor fingerprint stack

This is the main mission-critical phase.

### 4.1 Inventory the real TEE, do not infer it

Determine which secure OS and client transport the running SM-G975F firmware uses. The kernel's `tzdev_iwi_event` log observation is a useful clue, not a conclusion. Inspect:

- kernel config and drivers for `tzdev`, `mobicore`, `mc`, `tee`, `qseecom`, `smcinvoke`, `trusty`, secure monitor calls and secure shared memory;
- live device nodes and sysfs endpoints (`/dev/tzdev*`, `/dev/mobicore`, `/dev/qseecom`, `/dev/tee*`, `/dev/tz*`, `/sys/class/tee`, and actual names discovered from the kernel);
- relevant kernel log initialization and trusted-OS version messages;
- `/vendor/tee`, `/vendor/app`, `/vendor/firmware_mnt`, `/vendor/lib64`, `/vendor/bin`, service init files, XML manifests and properties from a matching stock SM-G975F firmware partition if lawfully available;
- TEE client libraries, daemons, trustlet/TA registries, app identifiers, secure storage services and fingerprint-specific configuration;
- the stock fingerprint HAL service and all transitive dependencies, including exact ABI/architecture, Android runtime/Binder/HIDL dependencies, required properties, service manager, SELinux rules and trustlet loading method.

Do not assume the device uses QSEE simply because the sensor is Qualcomm. This is an Exynos model. Determine the actual TEE implementation from evidence.

### 4.2 Search locally and remotely with provenance

- Search all repository content and the local workspace for `fingerpr`, `qbt`, `fps`, `biometrics`, `fingerprint HAL`, `tzdev`, `mobicore`, `TEEGRIS`, `Kinibi`, `trustlet`, `TA`, `keymaster`, `gatekeeper`, `qseecom`, `secure storage`, and vendor fingerprint paths.
- Inspect any attached/debug-pack files, locally mounted vendor partitions and legitimate backups available in the project environment.
- Use matching SM-G975F Exynos stock firmware/vendor data, not a Snapdragon G975U/G9750 package or an unrelated Galaxy model.
- Confirm exact binary hashes, build fingerprint, Android release, security patch, ABI and dependency closure. Document the extraction method and licensing/provenance. Do not blindly bundle proprietary blobs into the public Nuxel repository.
- Search upstream Samsung/Exynos kernel and public Android sources for exact symbols, HAL names, service names and TA IDs. Keep results for QBT1000, QBT2000, later QBT1500, optical sensors, or unrelated TEE OS separate.
- If source is inaccessible, inspect symbols/strings and dynamic dependencies only in a lawful locally available vendor library. Do not dump live biometric buffers or reverse engineer secrets. Protocol reverse engineering must not break the TEE trust boundary or security checks.

### 4.3 Candidate integration routes — evaluate in this order

**Route A: supported vendor stack already available on the handset/vendor partition.**

Determine whether an exact-match Exynos G975F vendor fingerprint HAL/daemon + trusted app can be used with the running kernel/TEE. Check the actual vendor files, app IDs, service manifests, ABI and TEE client runtime. If the working device's vendor partition or stock firmware is available, create a staged extraction/installation method that verifies hashes and license/provenance. Preserve proprietary files outside the public source tree unless redistribution rights are clear.

**Route B: minimal native Linux client around a documented TEE client API.**

If Samsung's vendor HAL calls a TEE client API that can be safely used from Fedora Linux without Android's full framework, implement a narrow native adapter or binding. The adapter must call the matching trusted application and retain the hardware/TEE's enrollment and matching operations. It may not emulate the TEE or reimplement fingerprint matching in userspace.

**Route C: isolated compatibility wrapper for the vendor HAL.**

If the only working vendor interface is an Android fingerprint HIDL/AIDL HAL and it can be supported with a controlled minimal compatibility environment, quantify the required components and security implications. Do not install a whole Android framework or silently introduce an Android dependency into the Nuxel base. A compatibility layer is acceptable only if the service remains isolated, the TEE and trusted app remain authoritative, it can be packaged reproducibly, and all lifecycle/security properties are tested. Document every runtime dependency.

**Route D: no compatible trusted path exists.**

If the trustlet is unavailable, signed for an incompatible TEE OS, cannot be legitimately loaded, requires an absent per-device root-of-trust secret, or only emits Android Gatekeeper/KeyMint AuthTokens that Nuxel cannot securely validate, stop before enabling unlock. Complete all safe provider-status, diagnostics, UI-state and PIN fallback work, then set `BLOCKED_SECURE_PROVIDER` with the exact missing artifact/ABI/action. Do not make a generic Linux boolean stand in for a TEE-authenticated assertion.

### 4.4 Signing, trust and license rules

- Do not generate dummy trustlets, unsigned test TAs, arbitrary TA identifiers, fake signatures or fake `mobicore`/TEE registry entries.
- Do not use a TA from a different model or SoC just because it has a similar filename.
- Do not bypass secure boot, anti-rollback or the TEE's authentication of trusted applications.
- Do not depend on an undocumented stock Android service that is absent from the Nuxel boot path without packaging and lifecycle proof.
- Do not redistribute proprietary Samsung/Qualcomm firmware/HAL/TA unless its license permits redistribution. Provide a reproducible, user-authorized extraction/install step where appropriate.

Deliver `docs/beta-finalization/live/evidence/pwnage-66000/tee-provider-research.md` describing the selected route, evidence, dependency graph, hashes and unresolved facts.

---

## 5. Phase 3 — implement a secure Nuxel fingerprint provider

Keep the Bridge as the single public owner of security state. The UI must not communicate with QBT nodes or TEE devices directly.

### 5.1 Provider architecture

Use the simplest safe architecture that matches the vendor stack:

- Either a well-contained Bridge provider if the TEE calls are fast, safe and cancellation-capable;
- Or a dedicated root-owned `nuxel-fingerprintd` service for blocking driver/TEE operations, exposing a narrow authenticated local IPC API to the Bridge.

Do not create an always-on polling daemon that holds the sensor awake. Prefer demand-driven operations and event subscriptions. If a dedicated service is necessary, add a systemd unit with bounded startup time, restart policy, sandboxing and explicit device access.

Suggested interface boundary (adapt to repo conventions):

- `status`
- `capabilities`
- `begin-enrollment(label, authorized_session)`
- `enrollment-progress(operation_id)` or event stream
- `cancel-enrollment(operation_id)`
- `finish-enrollment(operation_id)`
- `list-enrollments()` — labels/opaque IDs/count only; never templates
- `delete-enrollment(opaque_id)`
- `begin-authentication(challenge, lock_epoch)`
- `cancel-authentication(operation_id)`
- `authenticate`/`wait-authentication` returning a verified assertion, not a client-supplied match field
- `diagnostics` with no payloads or secrets.

All caller-visible responses need stable schemas, strict parameter validation, bounded string lengths, timeouts and explicit error codes. Never expose internal device file paths, raw ioctl buffers, TA memory or secure handles to the PWA.

### 5.2 Truthful capability states

Replace the current binary `secure` placeholder with an evidence-based state machine. Recommended states:

- `NOT_SUPPORTED_ON_DEVICE`
- `BOOT_MODE_BLOCKED` (LPM/charger boot)
- `DEVICE_NODE_MISSING`
- `DRIVER_NOT_BOUND`
- `DRIVER_PRESENT_TEE_UNAVAILABLE`
- `TEE_PRESENT_TRUSTED_APP_MISSING`
- `TRUSTED_APP_INCOMPATIBLE`
- `VENDOR_PROVIDER_MISSING`
- `PROVIDER_INITIALIZING`
- `READY_NOT_ENROLLED`
- `READY_ENROLLED`
- `ENROLLING`
- `AUTHENTICATING`
- `SUSPENDED`
- `ERROR_RECOVERABLE`
- `ERROR_FATAL`

Only `READY_NOT_ENROLLED` / `READY_ENROLLED` may set `supported=true` and `ready=true`, and only after a health/TEE handshake has succeeded. Add separate fields for `sensor_detected`, `driver_bound`, `tee_detected`, `tee_authenticated`, `vendor_app_loaded`, `provider_ready`, `enrollment_supported`, `authentication_supported`, and `enrolled_count`.

A detected qbt device node alone must return `supported=false`, `ready=false`. A random installed `fprintd` or `libfprint` binary must not be interpreted as QBT2000 support. Only the explicit matching provider can establish readiness.

### 5.3 Enrolment

Enrollment must follow this sequence:

1. Require the current PIN/strong credential to be re-entered immediately before starting enrollment.
2. Check the device is in normal interactive boot, screen/panel and power conditions are valid, TEE is alive, matching TA is loaded and provider state is healthy.
3. Create a provider-owned operation ID with strict timeout and cancellation.
4. Ask the trusted application to begin enrollment. All capture, feature extraction and template storage stay within the trusted app/TEE/sensor security boundary.
5. Report only trusted progress/acquired states and counts to the UI. Do not expose image data, raw feature vectors, debug frames or vendor secure buffers.
6. Handle repeated placements/lifts, poor-quality capture, finger not centered, timeout, cancel, interruption, sensor unavailable, TEE reset, suspend and service restart.
7. On success, persist only a secure-provider-owned opaque enrollment ID/label metadata if required. The biometric template itself remains protected in its secure storage; do not copy it into Nuxel's filesystem.
8. Require a separate explicit confirmation before any destructive replacement/deletion. Delete must call the vendor trusted provider, not just erase a local label.
9. Make interrupted or failed enrollment leave no half-configured unlock mode. PIN must continue to work.

### 5.4 Authentication and lock-screen unlock

This is stricter than a desktop demo:

1. At lock time, keep `/run/nuxel/security/lock-state.json` authoritative and ensure native app launches remain refused while locked.
2. On the lock screen, provide a fingerprint affordance only when the provider is actually ready and at least one enrollment exists. Show the correct in-display sensor location/animation only for the S10+ UI.
3. Do not continuously scan when unlocked. Start authentication only in response to an explicit lock-screen request or a safe, power-aware wake flow that has been proven on the physical panel.
4. Generate a cryptographically strong, unpredictable challenge/nonce in the root Bridge, bound to the current boot session, the current lock epoch, the one Nuxel user, operation ID and short expiry. Keep it server-side; the browser must not choose it.
5. Ask the trusted application/vendor provider to authenticate. It must do actual matching in trusted hardware/TEE.
6. Accept success only when the provider returns a documented cryptographic assertion that the Bridge can verify with a trusted verification path. Validate nonce, user/device identity, boot/session binding, expiry, operation state, lock epoch, provider identity and one-time use. Reject replay, stale, malformed, duplicate or cross-session assertions.
7. If the Android vendor stack returns an Android Gatekeeper/KeyMint/Hardware AuthToken, determine exactly how its HMAC key and user SID are provisioned and verified. Nuxel cannot simply accept a successful callback or verify a token without its corresponding trusted key. If the valid verification chain depends on absent Android system services or an unavailable per-boot shared secret, do not accept it as Nuxel unlock proof.
8. Only after the trusted assertion passes, let the root security provider update the lock state. A UI callback, D-Bus signal, IRQ, normal-world file or HTTP request containing `matched: true` is never sufficient.
9. Enforce PIN fallback on every provider error, timeout, cancellation, low battery/power state, TEE crash, no match, service unavailability or rate limit.
10. Require the primary PIN after every reboot/first unlock after boot and after the configured strong-auth interval or security event. Biometrics are a secondary convenience, not a replacement for the device's primary credential.

### 5.5 Anti-replay and server state

- Use a cryptographically secure random challenge of at least 128 bits (prefer 256 bits).
- Bind a challenge to a fresh per-boot identifier, lock-state generation/epoch, monotonic expiry and one operation.
- Store outstanding/consumed challenges only in root-owned runtime memory/state, not in browser storage.
- Consume a valid assertion atomically exactly once. A retry must require a new challenge.
- Reject assertions after a lock-state transition, service restart, boot change, suspend invalidation (if required by vendor protocol), expiry or lockout.
- Clear pending operations at lock, screen state transition where appropriate, reboot, suspend/resume failure, provider disconnect and user cancellation.
- Do not use wall clock alone for short timeouts; use monotonic time.

### 5.6 Rate limits and credential model

- Keep existing scrypt PIN/pattern policy, constant-time compare and persistent exponential lockout.
- Add biometric attempt rate limiting and provider-enforced lockout state if the vendor TA supports it.
- Never let repeated finger failures bypass the PIN lockout or clear it.
- After the configured number of failed biometrics, require PIN; do not automatically lower security to swipe.
- Fix and test the fallback verifier mismatch described in §1.4.
- Deleting all enrollments or losing provider readiness must automatically disable fingerprint unlock and leave the PIN credential intact.
- Changing PIN must require the current primary credential and update the fallback PIN verifier transactionally.

---

## 6. Phase 4 — system packaging, permissions, lifecycle and power

### 6.1 Least privilege

- Identify exact device nodes and operations required by the provider. Grant access only to the single root-owned broker/service that needs it.
- Prefer root-owned nodes with restrictive mode. If using a dedicated service account is technically possible, create a dedicated `nuxel-fingerprint` group/user and restrict access to only the exact QBT nodes; do not add the full desktop user to that group.
- If the vendor TEE stack requires root or specific groups, document why and keep the public IPC surface narrow.
- Use udev/systemd device access in the actual Fedora 43 ARM64 image. Do not copy Android `/dev` ownership assumptions from a stock init script without adapting them to Nuxel.
- Protect sockets with Unix peer credentials and strict permissions. No TCP listener for biometric operations.

### 6.2 systemd service hardening

If a separate daemon is needed, provide a dedicated service with appropriate hardening, for example:

- `User=`/`Group=` limited to what vendor TEE client requires;
- `DeviceAllow=` only for exact QBT/TEE nodes; `PrivateDevices=no` only if required;
- `NoNewPrivileges=yes` where compatible;
- `ProtectSystem=strict`, `ProtectHome=true`, `PrivateTmp=true`, restricted `ReadWritePaths=` only for `/run/nuxel/fingerprint` or specific state;
- `ProtectKernelTunables`, `ProtectKernelModules`, `ProtectControlGroups` as compatible;
- bounded `TimeoutStartSec`, `TimeoutStopSec`, `WatchdogSec`, `Restart=on-failure` with rate limiting;
- no ambient capabilities unless proven necessary;
- no startup dependency that delays or blocks boot if fingerprint is unavailable.

Do not copy these directives mechanically if the TEE stack needs an exception; document every exception and minimize it.

### 6.3 Power/lifecycle

- Fingerprint should not poll continuously and should not hold the sensor or display awake when idle.
- Use the driver's documented power/runtime-PM path and vendor TEE lifecycle. No direct regulator toggling from userspace unless the driver explicitly documents it.
- Suspend/resume must close or cancel outstanding operations, invalidate pending challenges and recover the TEE provider safely.
- Screen-off scanning is not assumed. Prove whether the QBT2000 can wake the device while the display is off in this board/kernel configuration; otherwise wake the panel first and show the sensor target.
- Avoid blocking normal boot on TEE readiness. If the provider is unavailable, boot normally with PIN fallback.
- On shutdown/reboot, cancel operations and release TEE handles cleanly. No hangs in the lockscreen or Settings because the fingerprint service is absent.
- Verify temperature, CPU wakeups and battery drain with idle lock screen. No high-frequency polling loop.

### 6.4 Firmware/vendor assets

- Do not add arbitrary binaries to the source tree.
- If matching licensed firmware is required, add a manifest with filename, source/provenance, version, SHA-256, target path, ABI/TEE compatibility and redistribution status.
- Provide a safe install/extract script that validates model/build identity and hashes before writing. No cross-model fallback.
- If assets cannot be redistributed, document how an owner with the exact stock SM-G975F firmware can provide them. Fail closed when absent.

---

## 7. Phase 5 — Settings, lock-screen UI and Bridge API

### 7.1 Settings experience

Add a proper section in the existing Nuxel Settings app, under **Security & Privacy → Fingerprint unlock** (or the existing canonical security page if one exists). Keep the Nuxel pixel/arcade design and small-screen layout.

Show distinct states with honest descriptions:

- Fingerprint sensor detected; secure provider not installed.
- Driver/device node missing.
- Secure environment unavailable.
- Provider initializing.
- Ready; no fingerprints enrolled.
- Ready; N fingerprints enrolled.
- Enrollment in progress.
- Authentication provider error; PIN available.
- Temporarily disabled due to lockout/policy.

Controls:

- `Enroll fingerprint` — only enabled when provider can safely enroll and user has re-authenticated with PIN.
- `Test fingerprint` — only available after enrollment and must not unlock the session as a side effect.
- `Rename` — changes only the visible label, not template contents.
- `Delete` / `Delete all` — require PIN and a second confirmation; call secure provider deletion.
- `Use fingerprint to unlock` — only enabled when there is a verified authentication assertion provider, at least one enrollment and a PIN fallback.
- `Use PIN instead` / disable biometrics — always available.
- Diagnostic detail — non-sensitive error/state only.

Never show a fake progress bar or fabricated enrollment count. Progress must come from a real provider event. If only detector events exist, show “finger touched” as a diagnostic state, never “fingerprint accepted.”

### 7.2 Lock-screen behavior

- Keep current PIN/pattern lock prompt, rate-limit feedback and lock-state model intact.
- Add a scan action, sensor location hint and real progress only when provider status is ready and an enrollment exists.
- Preserve “Use PIN” fallback at all times.
- On no match, remain locked and give a neutral retry message.
- On timeout/service failure, fall back to PIN without silently unlocking.
- Prevent double submit, duplicate challenge consumption and stale callbacks after the lock screen is dismissed.
- Accessibility: all actions usable without relying only on animation; do not show sensitive diagnostics on the locked screen.
- Do not let the top bar, native dock, Flatpak app, web app or any other overlay cover or bypass the lock screen while authentication is active.

### 7.3 Bridge API contract

Keep the API inside the existing authenticated Bridge RPC path and preserve API namespace conventions. Existing route `/api/v1/system/fingerprint` currently reads provider status; namespace routing also exposes fingerprint/biometrics.

Extend with strict verbs for status/capabilities, enroll, enrollment cancel/progress, list metadata, rename, delete, test, begin/cancel authentication, and verified assertion consumption. Exact verbs may follow existing Bridge style, but document the schema.

Security rules:

- UI callers can request operations, not claim results.
- The Bridge creates and binds challenges; it never accepts a caller-supplied `matched=true` or arbitrary unlock token.
- Require current-credential proof before enrollment/deletion/settings changes.
- Bind operations to authenticated Nuxel session and lock epoch.
- Audit-log operation start/end/error only, with no biometric payloads, secrets, TEE buffers or raw assertions.
- Protect CSRF/session token and loopback RPC requirements consistent with current Bridge design.
- Return bounded errors; do not leak internal paths or raw TEE diagnostics to the UI.

---

## 8. Phase 6 — fix the credential and lock integration thoroughly

Perform a security review of `security_provider.py` before implementing biometric unlock.

Required checks/fixes:

1. Fingerprint mode must never become selectable unless the secure provider is ready and at least one enrolled template is present.
2. A mandatory PIN fallback must be set and verified before enabling biometric mode.
3. Fix the possible fallback-PIN storage/verification mismatch: a stored `fallback_pin_salt`/`fallback_pin_verifier` must be validated by a dedicated constant-time fallback verifier. Add no plaintext PIN fields.
4. Normal PIN mode remains unaffected.
5. Swipe mode still requires explicit downgrade confirmation and must not be reached by automatic provider failure.
6. Provider disabled/unavailable must not modify the current credential or unlock state.
7. Wrong fingerprint leaves the device locked and increments biometric-specific rate limits; wrong PIN increments primary credential failure state.
8. A valid secure assertion can unlock only the current lock epoch once.
9. A PIN unlock clears or resets failure counters according to explicit policy; a biometric success must not clear PIN failures unless policy deliberately requires and security review justifies it.
10. Require primary PIN after a reboot and define a strong-auth interval. Store only the minimum state necessary.
11. If fingerprint template is deleted from the secure side out-of-band, status must detect mismatch and disable fingerprint unlock; it must not assume the local label list is authoritative.
12. Atomic persistence and permissions must remain correct for `/var/lib/nuxel/security/lock.json`, `/run/nuxel/security/lock-state.json`, and `/etc/nuxel/security/biometric-unlock.json`.

Add a security design note to `docs/security/fingerprint-authentication.md` with sequence diagrams and threat model.

---

## 9. Phase 7 — test strategy (host, image, phone)

### 9.1 Host tests without hardware

Create a dedicated suite such as `tests/pwnage66000/` and integrate it into the repository's main test runner. Use mocks/fakes for TEE communication; fake adapters must be test-only and impossible to enable in production through config or RPC.

Test at least:

- No QBT nodes → unsupported, never ready.
- QBT nodes present but no driver bound → blocked.
- Driver bound but no TEE → blocked.
- TZDev present but TA unavailable → blocked; no false readiness.
- TEE online but wrong/incompatible TA → blocked.
- TA loads but does not provide the documented auth assertion → enrollment may be disabled/authentication must be disabled as appropriate.
- Provider health handshake succeeds → ready only if every required capability passed.
- `fprintd` installed without a QBT2000 backend → still blocked.
- QBT finger-detect event without secure match → no unlock.
- QBT IPC notification without secure match → no unlock.
- Stale, expired, replayed, altered, wrong-device, wrong-user, wrong-boot or wrong-lock-epoch assertion → rejected.
- A valid one-time TEE test assertion → exactly one unlock in test harness.
- Cancelled/expired operation → no unlock.
- Provider crash during authentication → remains locked and PIN fallback visible.
- Enrollment only after re-authentication; enrollment cancellation; timeout; duplicate labels; max slots; deletion; rename.
- Deleting the final fingerprint automatically disables biometric mode.
- Fallback PIN in fingerprint mode succeeds and wrong PIN fails with constant-time verifier path and rate limit.
- PIN and pattern modes unchanged.
- Swipe downgrade policy unchanged.
- Boot requires strong credential once after reboot.
- No secret/template payloads appear in logs, API JSON, localStorage, screenshots or saved test artifacts.
- Service/user/device permissions and systemd sandbox assertions.

### 9.2 Static/source checks

- Type/syntax checks for Python, JavaScript, C/C++ components and systemd units.
- `pytest` and the existing PWNAGE-45000 regressions.
- `git diff --check`.
- Scan for accidental `chmod 666`, world-writable qbt device rules, browser direct device access, logging of `template`, `fingerprint_image`, raw buffers, PINs or tokens.
- Verify no `secure = ... and True`, hardcoded ready, fixture-success path, mock adapter installed in production, or UI-only unlock path.
- Test package builder staging and image contents.

### 9.3 Live S10+ tests (owner/device present)

Only run when the matching physical phone is connected and the owner has explicitly made it available. Do not fabricate live test results from archived diagnostics.

1. Normal boot: verify exact model, kernel, TEE state and QBT node permissions.
2. Provider startup with no enrollment: `READY_NOT_ENROLLED` only if secure handshake genuinely succeeds.
3. PIN re-auth, begin enrollment, physically touch the sensor on the UI's target area according to real provider prompts, complete at least one enrollment.
4. Reboot and verify the fingerprint metadata persists inside the trusted provider and is still recognized. The Nuxel local state must not contain the template.
5. Successful match unlocks once. Incorrect finger remains locked. Finger presence alone remains locked.
6. PIN fallback works when sensor is covered/unavailable, TEE service stops, or authentication times out.
7. Delete one enrollment and then all; provider confirms deletion and biometric mode disables correctly.
8. Lock/unlock repeated cycles, wrong-finger sequences and rate limiting.
9. Screen-off/wake and sensor-indicator behavior; confirm battery/thermal cost. If display must be woken before scanning, document and implement that accurately.
10. Suspend/resume, power button, lock screen, native GTK app and Flatpak app overlays; no bypass.
11. Normal reboot/shutdown: no hung daemon, no leaked session, no persistent sensor power request.
12. Check logs after tests for payload-free diagnostics only.

Use safe sample data and the owner's finger only. Do not store screenshots that reveal biometric data; ordinary UI screenshots with no scan imagery are fine.

### 9.4 Quantitative acceptance

Set explicit measured targets after the first live baseline. Suggested initial criteria:

- Provider status returns within 2 seconds when ready or an actionable blocker within 2 seconds when not ready.
- Starting/cancelling enrollment does not block Bridge/UI event loop.
- No more than one concurrent QBT operation; serialize enrollment/authentication/deletion.
- Cancellation completes within the vendor API's documented timeout and leaves the device locked.
- No continuous idle polling; measure CPU wakeups/idle power before/after.
- Authentication UI gives real feedback from provider events; do not promise a fixed response time without measurement.
- PIN fallback remains available at all times.

---

## 10. Phase 8 — build, stage and deploy safely

1. Build the Bridge and UI using existing project commands and image builder integration.
2. Stage provider/daemon files, systemd units, udev rules and configs in the authoritative S10+ Fedora 43 ARM64 rootfs builder.
3. Keep the fingerprint service optional/fail-safe: missing vendor assets must not fail the build or block boot; it must produce a clear disabled state.
4. If no kernel patch is needed, do not rebuild or flash the kernel unnecessarily.
5. If a kernel patch is genuinely required:
   - add an isolated patch in `kernel/s10plus/patches/` with `.required` only when truly mandatory;
   - prove it applies against the pinned `f7194c1d...` source;
   - build with the official wrapper and exact fragment;
   - run kernel/DTB/BOOT image verifiers and partition-size checks;
   - produce a rollback image and hashes;
   - never flash unattended. Provide exact commands and require explicit owner execution/approval.
6. Prefer deploying only changed userspace files over the existing Nuxel Wi-Fi SSH workflow where possible. Back up each replaced file and provide a rollback script.
7. Do not overwrite user credentials, lock settings or biometric state during upgrade. Add a versioned migration only if needed and test it with a copy.
8. Do not enable biometric unlock by default. It stays OFF until the user enrolls a finger, sets the PIN fallback and explicitly enables it.
9. Do not enable an unsafe generic `fprintd` or PAM configuration just because a package installed successfully.
10. Preserve the existing device's ability to unlock by PIN if the new service is absent, crashes or is rolled back.

---

## 11. Expected deliverables

The mission is not complete until the agent provides:

1. **Implementation:** working secure provider integration where source/firmware/TEE support allows; all safe UI, Bridge, fallback, diagnostics and packaging work regardless.
2. `docs/beta-finalization/live/PWNAGE-66000-REPORT.md` with:
   - exact source/kernel commit;
   - precise QBT2000 driver/device node state;
   - confirmed TEE and vendor stack with binary provenance/hashes;
   - state of enroll/match/template storage;
   - trust assertion format/verification and anti-replay behavior (describe, do not reveal secrets);
   - changed files and architecture;
   - tests run with exact results;
   - live handset test evidence vs offline tests clearly separated;
   - measured enrollment/authentication latency and idle power if physically measured;
   - known limitations and remaining blockers.
3. `docs/beta-finalization/live/PWNAGE-66000-TODO.md` with honest PASS/PARTIAL/BLOCKED status per subtask.
4. `docs/security/fingerprint-authentication.md` threat model and operational design.
5. New regression tests integrated into existing runners.
6. Build outputs or exact reproducible build commands and hashes as appropriate.
7. A complete deployable userspace drop-in ZIP (and kernel artifacts only if a kernel patch is genuinely needed), excluding private keys, biometric data, proprietary blobs without redistribution rights and device-specific user credentials.
8. `DEPLOY-PWNAGE-66000.md` with Wi-Fi SSH deployment steps, preflight, backups, checks, reboot, post-deploy verification and rollback.
9. Clear user-action list for any unavoidable physical enrollment or stock-firmware extraction step.

### Final verdict labels

- `FULLY_WORKING`: proven real enrollment, matching, secure assertion verification and lock-screen unlock on the physical SM-G975F, with PIN fallback.
- `PARTIAL_PROVIDER`: device/TEE/provider is integrated but one required secure capability is not proven; fingerprint unlock remains disabled.
- `BLOCKED_VENDOR_TA`: exact trusted app/HAL/firmware or compatible TEE client is missing.
- `BLOCKED_TEE_ABI`: secure environment exists but the vendor interface is not usable from the Nuxel runtime.
- `BLOCKED_HARDWARE`: live kernel or sensor path fails before the secure provider stage.
- `SOURCE_COMPLETE_LIVE_TEST_REQUIRED`: build and tests pass, but physical enrollment/verification still needs owner/device action.

Never use `FULLY_WORKING` based on node presence, a mocked provider, finger-detect IRQ, or an enrollment UI animation.

---

## 12. Execution order — do the work in this sequence

1. Read all required code/docs and freeze the baseline.
2. Verify the actual QBT2000 kernel source/interface and normal-mode operation.
3. Identify the exact S10+ Exynos TEE OS and vendor fingerprint HAL/TA/service chain.
4. Decide and document a compatible secure route; do not assume QSEE or copy a QBT1000 ABI.
5. Implement the trusted provider and truthful state machine, or complete every safe part and report the precise external dependency.
6. Fix PIN fallback verification and add anti-replay lock integration.
7. Add Settings enrollment/manage/test UI and lock-screen authentication UI.
8. Integrate service/permissions/power lifecycle in the Fedora rootfs build.
9. Run offline, static, regression and packaging tests.
10. Perform live physical enrollment/authentication only when the owner/device is available.
11. Produce deployable artifacts, evidence, rollback and final verdict.

**Do not ask the user to repeat details already present in the repository.** Make a best-effort autonomous pass. If a decision genuinely requires owner-supplied stock firmware or a physical finger on the device, finish all other implementation and provide the exact missing action.

---

## 13. Definition of done

A user opens Nuxel Settings → Security & Privacy → Fingerprint, re-authenticates with their PIN, enrolls a finger by following real prompts, can test and delete it, and enables fingerprint unlock. When Nuxel is locked, the S10+ displays the real in-screen fingerprint affordance, the QBT2000/TEE performs the match, the Bridge verifies a fresh secure assertion, and only then does the lock state change. Wrong fingers, sensor-only touch, replayed assertions, missing TEE, failed provider, low-power mode and service crashes never unlock the phone. PIN remains functional throughout, including after reboot.

That is the result. Anything less must be labelled accurately and shipped without weakening Nuxel's existing security.
