# FULL PWNAGE — Samsung Galaxy S10+ QBT2000 Fingerprint, TEEGris, Nuxel Biometric Broker & Permission Manager

the full finger pack with everything you need to fix the fingerprint scanner is locataed in ./finger

**Project:** Nuxel native Linux phone OS  
**Device:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`)  
**SoC:** Samsung Exynos 9820  
**Secure OS family:** Samsung TEEGris 3.1 (verify current runtime; do not assume)  
**Sensor:** Samsung/QCOM-labelled QBT2000 ultrasonic under-display fingerprint sensor  
**Kernel baseline:** Samsung-derived Linux 4.14.253 (verify exact build/commit)  
**Existing kernel interfaces:** `/dev/qbt2000_fd`, `/dev/qbt2000_ipc`, `/sys/class/fingerprint/fingerprint`  
**Acquisition location:** `./fingerprint-acquisition/` (or a timestamped sibling if that directory already exists)  
**Reflash policy:** One coordinated future A/B batch with NFC and other kernel/vendor-gated work. No standalone fingerprint flash.

---

# 0. MISSION — MAKE THE REAL FINGERPRINT SENSOR WORK SECURELY

Your mission is to bring up real fingerprint enrollment and authentication on the S10+ under Nuxel, using the actual QBT2000 sensor and the device's legitimate Samsung secure execution environment.

This is not a request to create a fake fingerprint API, a userspace matcher, or an Android-looking UI. It must use a cryptographically trusted, device-compatible Samsung TEEGris path. Keep PIN/password fallback working throughout.

The repository already reports the sensor and kernel driver present. Do not waste time writing a replacement sensor driver unless fresh evidence proves the existing QBT2000 driver/ABI is defective. The hard blocker is the verified secure provider/TEE application and the runtime/API/security integration above it.

**Security is a hard acceptance gate.** Do not bypass secure boot, TrustZone, TEEGris signature checks, anti-spoof/liveness checks, secure storage, rate limits, lockout, or the PIN fallback. Do not build an untrusted matcher from raw fingerprint data. Do not export, read, copy, decode, infer, or write biometric templates, images, feature vectors, or enrollment databases outside the TEE.

## 0.1 Definition of DONE

The mission is complete only when all applicable items are verified:

- [ ] Correct target hardware/variant confirmed: SM-G975F / Exynos 9820 / `beyond2lte`.
- [ ] QBT2000 sensor, its real kernel driver, power/IRQ/SPI path and ioctl ABI inspected and physically evidenced.
- [ ] TEE identity and runtime fully characterized for this exact firmware build; QSEE/Qualcomm artifacts excluded.
- [ ] The existing `startup.tzar` / `libtzld.so` hash-error evidence reconciled against a current boot. No integrity check bypassed.
- [ ] Exact QBT2000 Trusted Application (TA), vendor client/HAL and associated firmware/config are identified and their provenance, signature and ABI verified.
- [ ] A legitimate Samsung/OEM-authorized TA/provider is available and callable from Nuxel; if it is not available, report the exact external dependency and leave the feature blocked. Never fabricate a replacement TA or signing key.
- [ ] Acquisition, enrollment, comparison, secure template storage, anti-spoof and authentication proof all remain within the trusted path.
- [ ] Native Nuxel provider/broker is implemented with strict process and caller authorization.
- [ ] Authentication yields a fresh, cryptographically verifiable, single-use result/token bound to the active OS challenge/session—not a browser-supplied `matched=true` flag.
- [ ] Lock screen can authenticate via the real provider and still accepts the existing PIN/password fallback.
- [ ] Fingerprint enrollment, test, deletion, lockout, reboot persistence and fallback are physically validated.
- [ ] Nuxel permission manager contains the correct biometric capability/capabilities, canonical mapping, app-declaration display, grant/deny/revoke behavior and backend enforcement.
- [ ] Only authorized system components can manage enrollment/deletion; ordinary apps cannot open the QBT device nodes or invoke management verbs.
- [ ] Userspace provider/API/Settings/Permission Manager updates are deployed live over the existing SSH mechanism where safe, then hash-verified and tested on the running OS.
- [ ] All TEE/vendor/kernel changes are recorded for the one combined reflash batch; no independent flash is performed during this mission.
- [ ] Reports, test logs, hashes, integration manifest and rollback plan are saved.

A device node, driver probe, `tz:1` log flag, TEE OS banner, library presence, `fprintd` process or Settings tile is not proof of working authentication.

## 0.2 Status vocabulary

Use these statuses and preserve the distinctions:

- `PASS`: verified with the appropriate test and evidence.
- `PARTIAL`: one or more layers work, but the real authentication acceptance criteria are incomplete.
- `BLOCKED_SECURE_PROVIDER`: sensor path is present but no verified secure provider can authenticate.
- `BLOCKED_VENDOR_TA`: required OEM-signed/authorized TA is unavailable or cannot be lawfully deployed.
- `BLOCKED_TEE_INTEGRITY`: secure runtime/container/signature/ABI integrity fails.
- `BLOCKED_COMPATIBILITY`: existing Android vendor components cannot be used from Nuxel without a supported adapter/runtime.
- `FAIL`: tested and failed.
- `NOT TESTED`: no physical/authoritative test was run.
- `UNSUPPORTED`: verified hardware/firmware/API limitation prevents the feature.

Never turn a blocked state into READY by changing a boolean or returning mocked values.

---

# 1. REPOSITORY SAFETY AND ONE-REFLASH COORDINATION

Start with:

```sh
git status --short --branch
git log -1 --oneline
sed -n '1,220p' REFLASH-PLAN.md
sed -n '1,260p' REPORT-FINGERPRINT.md
```

Inspect the live worktree; files in this pack are reference snapshots from the uploaded repository, not authority over newer concurrent changes.

- Identify the active NFC agent's branch/worktree and every modified/untracked file.
- Do not reset, stash, clean, revert, overwrite or broadly reformat shared files.
- Keep fingerprint work isolated to its owned paths or use a dedicated worktree where the project's build workflow permits.
- Coordinate all edits to `REFLASH-PLAN.md`, kernel patch order, permission registry and shared Settings/API files with the other agent.
- Preserve NFC, USBNET, GPS/SSP, camera, display/GPU/MFC, modem, audio and existing deployed userspace changes.
- Do not run `dd`, `heimdall`, `fastboot flash`, TWRP flash commands, raw partition writes or a reboot for this task. Do not switch A/B slots.
- The owner's plan is one controlled future reflash after all kernel/vendor-gated work is ready. Prepare the complete coherent payload and manifest; request owner review before the combined flash.

`REFLASH-PLAN.md` explicitly says fingerprint requires a vendor/TEE trusted application plus system provider and may require boot/vendor payload. The QBT2000 kernel driver appears to be present already; do not add a kernel patch unless the exact QBT driver or secure-world transport is proven deficient.

---

# 2. FACTS FROM THE CURRENT REPOSITORY — REVERIFY, DO NOT BLINDLY TRUST

The current `REPORT-FINGERPRINT.md` records:

- Target: SM-G975F `beyond2lte`, Exynos 9820.
- Sensor identity: QBT2000 ultrasonic under-display sensor; sysfs reports `name=QBT2000`, `vendor=QCOM`, `type_check=7`.
- Nodes: `/dev/qbt2000_fd` (`237:0`) and `/dev/qbt2000_ipc` (`237:1`).
- Sysfs: `/sys/class/fingerprint/fingerprint` with identity/diagnostic attributes.
- Node permissions at capture: `root:root`, mode `0600`.
- Driver/probe evidence exists; no verified QBT2000 secure userspace provider is implemented.
- Existing provider returns `BLOCKED_SECURE_PROVIDER`, intentionally refuses enroll/delete/test, and does not fabricate a match.
- Existing image did not demonstrate a usable `fprintd`/`libfprint` QBT2000 backend.

The driver log contains repeated lines like:

```text
fps_qbt2000_work_func_debug: ldo:0,ipc:0,wuhb:0,tz:1,type:qbt2000,int:0,0
```

The `tz:1` field is a driver diagnostic only. It is not proof that a valid QBT TA has initialized, that trusted matching works, or that the sensor is operational for enrollment.

Freshly recheck all of this on the actual currently running Nuxel build before changing code.

---

# 3. CRITICAL PLATFORM DISTINCTION: EXYNOS TEEGRIS, NOT QUALCOMM QSEE

This phone is the Exynos 9820 Galaxy S10+. Samsung's S10+ security environment is variant-specific.

A Samsung SCrypto validation security policy lists the Galaxy S10+ with Exynos 9820 under **TEEGRIS 3.1 (32-bit and 64-bit)** and the Qualcomm SM8150 Galaxy S10+ under **QSEE 5.2** as separate platforms. Do not mix QSEE drivers, Trustonic/Mobicore components, Qualcomm TA binaries, vendor libraries, firmware, or device-tree assumptions into this Exynos target.

The repo's captured boot log reports:

```text
Samsung Secure OS Release Version 3.1.0.0
build date: 2021-08-12
binary version: 6b39a86d
Handler: jenkins-BFHandler-exynos9820-106 ... exynos9820 ... sdk30
```

It also records a potentially important integrity failure in one boot sequence:

```text
TZDEV> ... tzar size = 5044890, old_tzar size = 5048986
startup_loader check_file_hash(): Incorrect hash for bin/libtzld.so
startup.tzar unpacking failed, error = 22
TZDEV> ... startup load result, ret=22
```

A later boot excerpt in the same capture reports a `startup.tzar` size of `5048986` and a later `Startuploader complete` line. These are distinct log sequences/boot attempts; do not infer that one cancels the other. Reconcile the exact boot attempt, file versions, loaded image and secure-world state.

## 3.1 TEE integrity investigation

Identify from read-only evidence:

- running kernel release and exact kernel commit/build ID;
- `tzdev` and `tziwsock` driver versions and relevant device nodes;
- TEEGris secure OS version and binary/build ID;
- `startup.tzar` path, size and SHA256, if available through a normal vendor/system path;
- `libtzld.so` path, architecture, build ID and SHA256;
- any corresponding signed manifest/version metadata;
- TEE client libraries and their exact dependencies;
- trustlet/TA inventory and signing metadata, where these are ordinary files in a readable vendor/system partition;
- actual TEE/secure channel initialization and error return codes;
- consistency between kernel, vendor, system and secure OS images.

If the current boot shows a hash mismatch, stop provider work at that gate until the cause is resolved. The secure environment may reject all TAs or the relevant services. Do not edit the archive, replace a file in a signed container, disable checking, patch a hash comparison, or inject an unsigned TA to get past the failure.

A secure OS banner proves only that the secure OS reports its version. It does not prove that startup containers loaded, a fingerprint TA is registered, or the QBT2000 channel works.

## 3.2 Correct ABI and architecture

Inspect every candidate ELF with `file`, `readelf -h`, `readelf -l`, `readelf -d`, symbols/build IDs and dependency tracing. Determine 32-bit vs 64-bit TEE client ABI and userland ABI independently. Do not infer ABI from device CPU alone.

Do not assume Android/Bionic vendor binaries can run directly on Fedora/glibc. Map their actual dependencies: Binder/HIDL, Android properties, init, vendor services, `libteecl`/TEE client libs, `tzdev`/`tziwsock`, `libtzld`, SCrypto, Keymaster, secure storage and vendor runtime. Use a narrow, auditable adapter only if the real protocol and dependencies are understood. A complete Android framework is not the default answer.

---

# 4. READ-ONLY ACQUISITION OF MISSING OEM MATERIAL

The uploaded source ZIP contains no QBT2000 TA, no proven fingerprint HAL/service binary, no TEE trustlet image, and no authorized signing material. The firmware blob folder is effectively empty for this feature. The included acquisition helper is intended to collect a narrow inventory and ordinary vendor/system artifacts from the already-mounted read-only partitions of the exact handset.

Run it only when the operator has connected the exact phone in TWRP/ADB or another already-authorized root shell. The script is read-only on the phone; it writes only to the workstation. It does not mount partitions, write any device path, flash anything, reboot or access user biometric storage.

```sh
bash scripts/acquire-s10plus-fingerprint-evidence.sh
```

Review its output in `./fingerprint-acquisition/` (or the timestamped output directory it reports). The script may not find all components. If `/vendor` or `/system` is not mounted in TWRP, do not mount read-write; document the missing mount and use an existing read-only recovery procedure approved for this device. Do not guess a partition or mount point.

Collect only normal files from verified readable `/vendor`, `/system/vendor`, `/odm` or `/system` locations whose names indicate fingerprint/QBT/TEE/TrustZone/keymaster/gatekeeper. Record paths, metadata, hashes, ELF details and provenance. Keep the phone's original files unchanged.

**Never access, dump, pull, parse or copy:**

- enrolled fingerprint templates, raw images, feature maps or biometric databases;
- `/data` private biometric/user storage;
- `/efs`, `/persist`, RPMB, keystore secure storage, key material, TEE RAM or secure-world memory;
- bootloader/secure boot keys, signing keys, OEM private material;
- raw partitions or block devices for the purpose of searching for secrets.

Do not run `dd` on sensitive partitions. Do not access `/dev/qbt2000_fd` or `/dev/qbt2000_ipc` from the collector; do not send experimental ioctl commands or dump binary sensor frames. Hardware probing must be performed only through documented vendor driver/provider operations.

If the TA is present as a signed file in a normal vendor partition, preserve an unmodified acquisition copy and hash for analysis, but do not repack, modify, resign or redistribute it. The ZIP contains no proprietary TA, and you must not manufacture one.

## 4.1 If the OEM TA/provider is genuinely absent

Find the exact stock Samsung firmware for the same model, SoC, product region/carrier and build family and identify the vendor package that legitimately supplies the QBT2000 service and TEE application. Do not mix a different S10+ variant, region, Exynos SKU, Android release or firmware revision without ABI/TA compatibility proof.

If it is not lawfully obtainable/redistributable or requires Samsung-only signing/deployment authorization, stop at `BLOCKED_VENDOR_TA` and state what OEM-authorized input is required. A TEEGris SDK overview does not grant access to Samsung's private product TA source, signing certificates or permission to deploy Samsung's production TA.

---

# 5. QBT2000 KERNEL/SENSOR PATH

The QBT2000 driver and nodes appear to exist, so begin with source/device evidence, not a new driver.

Inspect:

- exact QBT2000 driver source in the pinned Samsung kernel;
- device-tree node and compatible string;
- SPI controller, chip select, bus frequency and transfer constraints;
- power rails, regulators, GPIOs, reset, IRQ/wake IRQ and pinctrl;
- clock/power gating and runtime PM;
- `qbt2000_fd` and `qbt2000_ipc` major/minor registration and ioctl ABI;
- secure-world channel setup and trusted client handshake;
- normal interactive mode vs charger/LPM mode;
- error, reset, suspend/resume and shutdown paths;
- ownership and mode of device nodes after `nuxel-device-permissions.service` runs.

Do not run uncontrolled SPI reads/writes, change frequency, toggle reset/power GPIOs, alter interrupt configuration, or write sysfs controls without a documented, bounded test and recovery path. Do not expose QBT device nodes to the `audio` group or any general user group. The current mode is root-only `0600`; preserve or tighten that policy.

A kernel patch is justified only if evidence proves a defect in the exact pinned tree (for example a wrong DT property, broken secure IPC transport or missing required config). If one is needed, write the smallest unique patch, prove it applies in the normal patch order, add a regression test, and include it in the single combined batch. Do not patch kernel code just to make a fake provider appear ready.

---

# 6. LEGITIMATE SECURE PROVIDER ARCHITECTURE

Target architecture:

```text
QBT2000 ultrasonic sensor
   ↓ (vendor-owned sensor transport / trusted path)
Samsung QBT2000 kernel driver + secure IPC
   ↓
TEEGris 3.1 / OEM-authorized fingerprint TA
   ↓ (documented TEE client protocol / vendor HAL adapter)
root-owned Nuxel biometric broker
   ↓ (typed, authenticated, audited D-Bus or Unix socket API)
Nuxel security provider + lock screen
   ↓
verified, challenge-bound authentication result → unlock session
```

All acquisition, enrollment, matching, template storage and anti-spoof/liveness decisions must happen in the trusted provider. The rich OS must never receive raw biometric data or reusable templates.

## 6.1 Provider readiness criteria

The provider may report `READY` only if all of the following are independently true:

- QBT2000 driver and exact device are present and in the expected operational mode;
- TEEGris version/ABI is known and its integrity/startup checks pass;
- the required OEM-authorized QBT2000 TA is present, accepted and callable;
- the secure IPC/client handshake completes successfully;
- sensor firmware/config and calibration required by that TA are verified;
- secure storage is available and bound to this device/user;
- enrollment/authentication operations are supported by the TA;
- the result can be cryptographically authenticated and bound to a fresh caller-generated challenge;
- anti-spoof/liveness, lockout and deletion semantics are supported;
- the complete path has passed physical tests.

If any one is unknown, report `BLOCKED_*`, not `READY`.

## 6.2 No userspace matching, no fake HAL

Do not create a libfprint/QBT plugin that accepts a sysfs read, debug counter, ioctl response or user-supplied match Boolean as a fingerprint success. `fprintd` is not proof of support. An adapter may expose the real vendor secure provider via a Linux-native Nuxel API, but it cannot implement matching in the normal world.

If the original vendor HAL relies on Android Binder/HIDL/Bionic, document the dependencies and implement only a minimal compatibility bridge to the actual OEM service/TA if technically and legally supported. Otherwise mark `BLOCKED_COMPATIBILITY`.

## 6.3 Authentication protocol

Design the Nuxel broker around an explicit challenge/result protocol:

- The lock/security service generates a cryptographically random, single-use challenge with a short expiry.
- The challenge is bound to the active user/session and intended operation.
- The secure provider/TA performs the real sensor acquisition and match.
- It returns a documented cryptographic authentication token or attestation/HAT equivalent, not `matched=true`.
- Verify MAC/signature, challenge, authenticator identity/version, freshness/monotonic state, user binding and single-use semantics inside a privileged trusted component.
- Reject malformed, stale, replayed, wrong-user, wrong-session, wrong-operation or unverifiable results.
- Do not accept a token from JavaScript or an ordinary application process.
- Do not log token bytes, challenges beyond safe diagnostic identifiers, raw biometric frames or private data.

If the OEM TA does not issue a verifiable token suitable for OS unlock, it is not acceptable to unlock the device based on a plain Boolean. Investigate a vendor-authorized adapter/Keymaster/TEE proof path or remain blocked.

---

# 7. IMPLEMENT `fingerprint_provider.py` AS A REAL BROKER, NOT A FLAG

Current source: `services/nuxel-bridge/src/fingerprint_provider.py`.

It currently detects nodes and driver, then deliberately executes:

```python
secure = bool(devs) and False
```

and always refuses `enroll`, `delete` and `test`. Preserve that fail-closed behaviour until the secure provider truly exists. Replace it only when Sections 3–6 have passed.

Implement a clear, versioned contract with separate concepts:

- hardware detected;
- kernel driver ready;
- TEE runtime healthy;
- secure TA loaded/available;
- vendor provider handshake complete;
- enrollment available;
- enrolled state/count (only if the secure provider safely reports it);
- authentication available;
- lockout / retry state;
- provider error and diagnostic code.

Do not hardcode `enrolled: 0` if the secure provider has enrolled slots that it does not disclose; use an explicit unknown state. Never return template contents, images, IDs that reveal secrets, or raw sensor values.

Required operations, as supported by the real vendor interface:

- `status` — read-only, no sensor mutation;
- `enroll` — owner-only Settings flow, requires device credential/PIN confirmation and secure-provider enrollment ceremony;
- `authenticate`/`verify` — challenge-bound authentication request; returns only a secure token/result to the trusted broker, not to the web client;
- `delete` — owner-only TEE-side deletion/revocation;
- `cancel` — cancel an in-progress trusted operation safely;
- `test` — physical test that uses the genuine provider path and never counts as unlock unless it has a live OS challenge.

Use bounded operation timeouts, cancellation and mutexing. Ensure a failed or interrupted enrollment cannot create a phantom enrollment record. Do not let the Python bridge own direct, unrestricted access to QBT nodes if a narrow dedicated daemon can own them more safely.

---

# 8. FIX THE LOCKSCREEN/PIN FALLBACK BEFORE ENABLING FINGERPRINT

Inspect `services/nuxel-bridge/src/security_provider.py`.

There is a current inconsistency worth fixing and regression-testing:

- fingerprint mode in `_set_secret()` stores `fallback_pin_salt` and `fallback_pin_verifier`;
- `_verify_locked()` only verifies `salt` and `verifier`;
- `unlock()` unconditionally calls `_verify_locked()` for all non-swipe modes.

That means the PIN entered as the fingerprint-mode fallback may not be accepted by the existing unlock path. Do not ship fingerprint mode while this is broken.

Implement a distinct credential-mode-aware verification path:

- `pin` and `pattern` continue to use their own existing salts/verifiers;
- `fingerprint` fallback PIN verifies with `fallback_pin_salt` and `fallback_pin_verifier`;
- compare in constant time;
- preserve scrypt parameters and persistent failure accounting/lockout;
- clear failure counters only after a successful credential check;
- never let a failed biometric request bypass PIN or lockout;
- ensure a TEE/provider failure leaves the device locked and PIN fallback usable;
- preserve credential-change authentication requirements;
- no accidental downgrade to swipe or empty credential.

Add tests for successful fallback, incorrect fallback, persistent rate limit, reboot/persistence, wrong mode, missing verifier, malformed state, provider unavailable and lockout. This regression is a prerequisite for any successful biometric rollout.

---

# 9. PERMISSION MANAGER — REAL BIOMETRIC CAPABILITY AND STRICT OWNER POLICY

Canonical permission source:

`shell/nuxel-shell/nuxel-permissions/capabilities.json`

Permission manager UI:

`pwa/nuxel-apps/permissions/app.js`

Bridge permission RPC/API:

`services/nuxel-bridge/src/api.py`

Other relevant files:

- `configs/nuxel/permissions/README.md`
- `configs/nuxel/permissions/*.json`
- `shell/nuxel-shell/nuxel-permissions/nuxel-permd.py`
- `shell/nuxel-shell/nuxel-permissions/systemd/nuxel-permd.service`
- `configs/apparmor.d/usr.bin.nuxel-permd`
- `configs/apparmor.d/usr.bin.nuxel-permissions`
- `services/nuxel-s10/bin/nuxel-device-permissions.sh`
- `pwa/nuxel-apps/settings/pwange45000-settings.js`
- `pwa/nuxel-apps/settings/index.html`

## 9.1 Design two different permissions, not one broad hardware grant

Model the distinction explicitly:

1. `biometric` — allow an app to request an OS-mediated, user-consented, app-scoped biometric authentication prompt. It must receive only a short-lived, scoped proof/boolean result from the system API. It must NOT unlock the device, enroll/delete a fingerprint, access the sensor node, or receive a reusable global authentication token.
2. `biometric_manage` — system Settings management authority for enrollment, deletion and provider management. This must be owner-only/system-managed, not grantable to third-party apps through a normal permission toggle.

Recommended manifest aliases:

- `biometric:authenticate` → `biometric`
- `biometric:prompt` → `biometric`
- `biometric:manage`, `biometric:enroll`, `biometric:delete` → `biometric_manage`

Use existing registry `aliases`/`manifest_tokens` semantics and verify resolution using `nuxel-permd.py` tests. Do not introduce separate permission strings that silently resolve to the wrong base capability.

Both should be high-risk and default-deny. Do not add `biometric` to any broad default allowlist. Do not grant `biometric_manage` to all apps. Enrollment is authorized by the fixed system owner policy after credential confirmation, not by a third-party app's self-declared manifest.

## 9.2 Permission registry and UI must agree

Update the canonical capability registry with:

- unique ID;
- documented aliases/manifest tokens;
- `portal_type` only if the actual portal consumes it;
- clear title/description/risk/group;
- mechanisms that really exist on this kernel/image;
- accurate `enforceable` and `enforces_against` values;
- precise limitation (a portal is userspace mediation, not a kernel barrier against an app that bypasses the portal; root is outside the stated threat model);
- truthful `verdict` and test command.

Update `CAP_LABELS`, `CANONICAL`, `TOKEN_MAP` and any GTK Permission Manager labels/maps so the permissions app displays biometric access consistently. The canonical JSON is the single source of truth; do not add a UI-only permission.

Add/verify `biometric` display rows for apps that declare it. The management permission should be displayed as system-managed/owner-only, not as an ordinary third-party grant toggle. Permission grant/deny/revoke records must be stored through the existing `nuxel-permd` service and audit log; never hand-edit only a UI state file.

Verify `nuxel-permd` default policy: a declaration is not a grant; absent records remain denied. Confirm `resolve()` maps all aliases exactly and no prefix confusion can broaden a grant.

## 9.3 Bridge/API authorization hole

In `services/nuxel-bridge/src/api.py`, the privileged provider dispatch includes namespaces `fingerprint` and `biometrics`. The existing `_owner_ok` condition explicitly restricts `security` mutations and NFC mutations, but the current condition does not include fingerprint mutation verbs. This must be fixed.

Add explicit verb-level authorization for:

- `enroll`, `delete/remove`, provider configuration and hardware management: Settings owner only (`nuxel-settings` or the repository's verified Settings app identity); require current credential/owner confirmation and audit.
- `authenticate`: only through the trusted lockscreen/system auth flow or the OS-mediated app prompt; validate the actual caller identity and a scoped capability grant; never trust a caller-supplied `app_id` or `is_system` field from JS.
- `status`: only safe aggregate state for local UI; no sensitive enrollment metadata or token material.
- `test`: owner-only Settings diagnostic, no unlock authority.

Do not allow `org.nuxel.Nuxtore` or arbitrary Home sub-apps to enroll/delete simply because they appear in a broad existing owner list. If the OS lock surface (`org.nuxel.Home`) needs a narrow authentication path, define that separately from Settings management.

Do not infer app identity from request parameters controlled by JavaScript. Trace the authenticated bridge/session/app container identity from the actual RPC ingress. Add tests proving a malicious app cannot spoof Settings or Home caller identity.

## 9.4 Device-node policy

Current evidence shows `/dev/qbt2000_fd` and `/dev/qbt2000_ipc` as `root:root 0600`. Keep these inaccessible to web apps, the `audio` group and all ordinary users. Do not alter `nuxel-device-permissions.sh` to chmod/chgrp QBT nodes for convenience.

The permission system should grant permission to request a service-mediated action, never direct access to the biometric hardware nodes. Use a dedicated root-owned provider daemon or the existing root bridge with a strict interface, local authenticated IPC, explicit D-Bus/Unix-socket ACLs, and fixed allowlisted operations.

The permission registry documents that systemd `DeviceAllow` enforcement is not proven on this Linux 4.14 image (`CONFIG_BPF_LSM` is unset); do not claim it is enforcing QBT device isolation. Confirm actual LSMs in `/sys/kernel/security/lsm` and `/proc/config.gz` before any AppArmor claim. Use DAC (`root:root 0600`) plus the root broker/caller authorization as measured, and state limitations honestly.

---

# 10. SETTINGS, QUICK SETTINGS AND LOCKSCREEN UI

Existing UI files already contain a Fingerprint page and Quick Settings privacy tile. Extend them; do not create duplicate settings panels.

## 10.1 Settings fingerprint page

Show distinct states:

- sensor not detected;
- sensor present / driver ready;
- TEE runtime unavailable/integrity failure;
- TA/provider missing or not authorized;
- provider ready but no enrollment;
- enrolled (only if reported safely by the TA);
- enrollment in progress;
- authentication test in progress;
- locked out / retry delay;
- deletion complete;
- provider error.

Enable Enroll/Delete/Test only when secure provider readiness and owner authorization are true. Enrollment must require the user's device credential/PIN confirmation and use the genuine secure UI/TA flow if available. Do not ask the browser to handle images or raw scan data.

The page should show a meaningful blocker and a safe refresh action while blocked. Do not make it look operational merely to satisfy UI tests.

## 10.2 Quick Settings fingerprint tile

The current `qs-fingerprint` tile is a privacy/security control, not proof of hardware availability. Keep status separate from toggle state. Do not turn it ON if only the device node exists. Toggling off must disable biometric unlock while leaving PIN/password intact; if provider disable is unavailable, return an error and show the actual state.

## 10.3 Lock screen

- Default authentication remains secure PIN/password (or existing configured policy).
- Biometric unlock is opt-in only after successful enrollment and a confirmed fallback credential.
- The lockscreen requests the system broker's challenge flow; it does not access hardware or send a success boolean.
- On sensor/TEE failure, cancel, timeout, or lockout, remain locked and offer PIN fallback.
- Successful biometric result must be bound to the active lock challenge and consumed once.
- Do not permit a third-party app prompt to unlock the system session.

---

# 11. LIVE USERSPACE DEPLOYMENT — VERIFY WHAT IS REALLY RUNNING

The user explicitly wants userspace updates deployed live. The existing SSH/deploy path may be used for ordinary Nuxel userspace components only after tests pass and the exact handset/OS identity is verified.

Possible live-deployable components include:

- `fingerprint_provider.py` and security-provider changes;
- API authz and typed biometric RPC;
- permission registry and permD code;
- Settings/Permission Manager/Quick Settings PWA;
- non-TEE systemd broker unit and policy files, if a proven provider exists;
- tests and diagnostics.

Deployment rules:

1. Inspect the exact deploy tool and target; never guess an SSH address or app service path.
2. Verify the target is the S10+ running Nuxel, not TWRP or another host.
3. Back up each destination file with owner/mode/hash before replacement.
4. Deploy to staging paths where supported; validate syntax and hashes before atomic promotion.
5. Preserve permissions/ownership and do not make `/dev/qbt2000*` user-accessible.
6. Restart only the affected service(s) using the established lifecycle; capture journal/API status.
7. Verify the live Permission Manager shows the biometric permission and that grant/deny reaches the central store/audit log.
8. Verify a non-authorized app's enrollment/delete/auth requests are refused; owner Settings can view status but enrollment remains blocked until the real provider is proven.
9. Run live PIN unlock tests and ensure lock screen still works.
10. If any test regresses, atomically restore the exact previous files and verify rollback.

**Do not deploy a provider that claims READY unless a genuine signed TA and secure handshake are present.** It is acceptable and useful to deploy corrected permission UI/API and keep the hardware status explicitly blocked. This counts as live userspace deployment, not as working fingerprint authentication.

Never attempt to deploy TEE startup containers, signed TA payloads or firmware over SSH as an independent operation. Those remain part of the combined controlled image/reflash process and require verified source/signature/provenance and owner approval.

---

# 12. SYSTEM SERVICE AND HARDENING

If a separate `nuxel-fingerprintd` broker is required, implement it as a narrow root-owned systemd service. Reuse existing bridge/service patterns and keep only one owner of QBT nodes/TEE sessions.

- Open only exact required node(s); reject symlinks/device-number changes.
- Verify major/minor and expected sysfs identity at startup.
- Keep node mode `0600`; never add users to root device group.
- Restrict Unix socket to the root bridge or explicit authorized client identity.
- Use strict JSON/schema and fixed command set; no arbitrary ioctl passthrough from JS.
- Serialize enrollment/auth/delete/cancel operations.
- Use bounded timeout and safe cancellation.
- Do not log token bytes, raw frames, template data, biometric identifiers or secrets.
- Add systemd hardening (`NoNewPrivileges`, read-only filesystem, private tmp, restrictive address families, protect kernel/control group settings, dedicated runtime directory and strict file paths) where compatible with actual TEE client needs.
- Do not claim `DeviceAllow` or AppArmor protects the device until verified on the exact kernel/image.
- Fail closed on TEE disconnect, IPC reset, daemon restart, invalid token, missing TA or trust failure.

If the vendor's original service must be run, verify its ABI/dependencies and licensing first. Avoid adding a permanent broad Android init/Binder framework unless the required supported HAL unequivocally depends on it. Any compatibility layer must be minimal, documented and testable.

---

# 13. TESTING — AUTOMATED, SECURITY AND PHYSICAL

## 13.1 Repository/unit tests

Add tests in the existing test suites, not a disconnected script only:

- provider blocked when QBT device missing;
- provider blocked when TA unavailable;
- provider blocked when TEE hash/startup error occurs;
- `tz:1` diagnostic never implies provider ready;
- wrong SoC/TEE (Qualcomm/QSEE) artifacts rejected;
- wrong build ID/ABI or signature rejected;
- device nodes stay root-only;
- no raw biometric data or template fields appear in API/logs;
- unknown provider response fails closed;
- stale/replayed/invalid challenge rejected;
- authentication assertion scoped to caller and operation;
- Settings-only enroll/delete/test authorization;
- unprivileged app cannot spoof `app_id` or invoke management;
- permission registry alias resolution/default deny;
- Permission Manager UI displays capability from canonical registry;
- grant/deny/revoke is audited and effective;
- `biometric_manage` cannot be granted to ordinary apps;
- fallback PIN branch fixed and covered;
- rate limiting survives process restart/reboot;
- unlock stays locked on provider errors and authentication failures;
- enrollment deletion revokes authentication immediately.

Existing suites to extend include:

- `tests/pwnage45000/test_pwnage45000.py`
- `tests/pwnage52000/test_qs_privacy.py`
- permission-manager tests and `tools/s10plus/a33/verify-permissions.py`.

Run the project's normal test gates and record exact commands/results.

## 13.2 Physical device tests

After the combined image is approved and deployed, operator must physically enroll and test:

1. Verify model/variant, OS build, Secure OS/TEEGris status and QBT nodes.
2. Verify sensor is in normal interaction mode (not charging/LPM-only state).
3. Enroll one finger through the trusted UI/TA. No raw image/template should be visible to Linux or logs.
4. Verify enrolled state is reported from TA-backed status only.
5. Authenticate repeatedly with the enrolled finger using real lockscreen challenges.
6. Verify a different/non-enrolled finger is rejected.
7. Verify timeout/cancel and sensor-off/TEE-off failure do not unlock.
8. Verify lockout and backoff after repeated failures.
9. Verify PIN fallback works before, during and after provider outage/lockout.
10. Delete enrollment from Settings and verify the TA reports no enrollment and old finger no longer authenticates.
11. Reboot and verify secure enrollment persistence and continued PIN fallback.
12. Verify disable/enable of biometric unlock does not delete the PIN fallback or change system lock policy silently.
13. If the vendor supports an official spoof/liveness test, perform it using only that documented mechanism. Do not construct DIY spoof recipes or treat an untested anti-spoof claim as PASS.

Synthetic test providers may be used in unit tests only, with an explicit test-only build flag and fake credentials; they must not be included/enabled in production images. Tests must ensure test-only mode cannot be activated by an app or remote RPC.

If physical enrollment/verification cannot be carried out, mark these tests `NOT TESTED — OPERATOR REQUIRED`.

---

# 14. REFLASH INTEGRATION — ONE COHERENT BATCH

Update the current `REFLASH-PLAN.md` only after coordinating with the NFC/USBNET/GPS/rotation owners.

The fingerprint row must list exactly which components need:

- boot/kernel/DT (only if proven qbt/TEE transport fix required);
- vendor/secure-world package or signed TA (exact origin, version, ABI, signature/hash);
- system provider/HAL/client runtime;
- service and permission-manager userspace;
- Settings/Quick Settings/lockscreen changes.

Do not classify the whole fingerprint feature as “reflash required” if some UI/bridge permission changes are independently live-deployable. Conversely, do not claim secure-world/TA files can be delivered through ordinary SSH if the device's verified boot/partition model requires an image update.

For the single combined batch:

1. Build from one pinned source tree and one coherent matching vendor firmware set.
2. Preserve active NFC and USBNET patches; do not rewrite their source or patch order.
3. Include fingerprint's required TA/runtime only if it is a legitimate exact-device artifact with verified signature/hash/provenance.
4. Do not change trust roots, security state, bootloader state, RPMB or secure storage.
5. Keep old A/B slot and known-good PIN lock access.
6. Test the inactive slot before switching where the actual device workflow supports this safely.
7. Require physical fingerprint and fallback tests before declaring the combined batch accepted.
8. The actual flash/reboot/slot switch is owner-authorized, outside this work package; do not trigger it now.

---

# 15. REQUIRED DELIVERABLES

Create in the repository:

### `PWNAGE-FINGERPRINT-REPORT.md`

Executive verdict, hardware state, TEE state, provider state, live deployment state, exact blocker and final feature matrix.

### `PWNAGE-FINGERPRINT-TEE-ANALYSIS.md`

TEEGris 3.1 identity, `tzdev`/`tziwsock` status, secure startup integrity issue investigation, TA/HAL inventory, ABI/build IDs/signatures, dependencies and all unresolved vendor requirements.

### `PWNAGE-FINGERPRINT-PERMISSION-MATRIX.md`

Canonical capability IDs/aliases, app declarations, default decisions, owner-only management, API verbs, enforcement layers, device-node ownership and tests.

### `PWNAGE-FINGERPRINT-TEST-RESULTS.md`

Unit/security/integration/physical test outputs, with every unrun test labeled NOT TESTED.

### `PWNAGE-FINGERPRINT-REFLASH-MANIFEST.md`

Exact kernel/vendor/system/runtime/UI files, patch order, signatures and hashes, build identifiers, live-deployed files and files reserved for the single combined flash. Explicitly state no flash was performed during this task.

### Source/runtime files

- real `fingerprint_provider.py` or narrow provider client;
- root-owned TEE/vendor broker only if necessary;
- security-provider fallback fix;
- Bridge/API caller authorization;
- canonical permission registry + permission UI mappings;
- first-party config grants only where appropriate;
- Settings/Quick Settings/lockscreen changes;
- service units and device-node policy as needed;
- automated tests and a read-only diagnostic/acquisition record.

Include hashes for every vendor artifact; never include private signing keys or biometric templates.

---

# 16. FINAL REPORT FORMAT AND STOP CONDITIONS

Report:

1. Sensor/driver: `PASS/PARTIAL/FAIL` with node/driver/DT evidence.
2. TEEGris: version, startup integrity and actual secure channel evidence.
3. TA/provider: exact component, source/provenance, signature verification and ABI.
4. Enrollment/authentication: separate statuses and real test evidence.
5. PIN fallback: pass/fail and regression test names.
6. Permission manager: registry/UI/API enforcement result and unauthorized-app denial test.
7. Live deployment: exact SSH target identity, deployed file hashes, running service/API/UI verification, rollback evidence.
8. Reflash readiness: exact vendor/system/kernel payload and hashes; confirm no standalone flash/reboot/partition write occurred.
9. Remaining external requirements: Samsung SDK/signing/TA/OEM support or physical operator test.

**Stop and report BLOCKED_VENDOR_TA** if the required signed/authorized TA is not available. Do not work around that by creating an unsigned TA, disabling verification, extracting secure secrets or writing a userspace matcher.

**Stop and report BLOCKED_TEE_INTEGRITY** if the current `startup.tzar`/`libtzld.so` integrity issue or secure startup state cannot be reconciled. Do not disable hash/signature checking.

**Stop and report BLOCKED_COMPATIBILITY** if the vendor HAL cannot be used under Nuxel without an unsupported or unsafe framework/runtime. Document the exact Bionic/Binder/TEE dependencies.

The success condition is genuine, secure, physically verified QBT2000 enrollment and authentication with PIN fallback and proper permission enforcement—not merely a detected sensor, a Settings switch, or a live-deployed UI.

also the full fingerprint pack with all you need is at ./finger
