# FULL-PWNAGE-65000 — Make NFC genuinely work on Nuxel / Galaxy S10+ (beyond2lte)

**Mission type:** repository-specific implementation, hardware bring-up, protocol integration, security review, and physical-device validation  
**Target device:** Samsung Galaxy S10+ SM-G975F, Exynos 9820, codename `beyond2lte`  
**Target OS:** Nuxel native Linux; preserve the current Fedora-based S10+ userspace and the existing Linux4 4.14.253 kernel port unless evidence proves a change is necessary  
**Primary objective:** move NFC from “kernel/controller/firmware detected” to a real, repeatable, user-controlled NFC tag reader with trustworthy Nuxel UI and diagnostics  
**Required execution style:** inspect first, implement the smallest correct bridge, test in layers, and report evidence honestly. Do not produce another research-only report.

---

## 0. Mission statement

Finish the S10+ NFC path that is already substantially brought up. Do not start over, install random NFC packages, or claim success because `/dev/sec-nfc` exists. The remaining work is principally the userspace transport/protocol integration between Samsung's vendor NFC character device and a native Nuxel NFC service, followed by tag discovery and safe NDEF reading.

Deliver a functioning, maintainable NFC feature that can:

1. Report truthful hardware, driver, firmware, transport, protocol, and tag-reader state.
2. Be switched ON and OFF from Nuxel's existing Quick Settings NFC tile and Settings UI.
3. Start a bounded discovery session on demand, detect a supported physical tag, and show its type and identifier only where appropriate.
4. Read supported NDEF records (initially NFC Forum Type 2 / NTAG21x where proven) without executing content or leaking tag data.
5. Stop discovery, release the controller, and return the device to the defined low-power/OFF state reliably.
6. Survive repeated start/stop, lock/unlock, suspend/resume, app restarts, daemon failures, and reboot without wedging the NFC controller or destabilizing the phone.
7. Provide diagnostics that distinguish a simulated test, a software/transport test, a controller test, and a real physical tag test.

The intended first milestone is **real read-only NFC tag detection and NDEF reading**. NFC writing may be implemented only after the read path is proven and must remain a separately gated, explicitly confirmed operation. Do not implement payments, card emulation, secure-element access, transit credentials, or wallet functionality as part of this mission.

## 1. Repository-specific baseline: use these facts, then re-check them on the actual phone

The supplied Nuxel repository and its live bring-up report already establish substantial progress. Treat the following as the starting hypothesis, not as a substitute for a fresh live check:

### 1.1 Hardware and live kernel state already observed

- Device: Galaxy S10+ SM-G975F / `beyond2lte`, Exynos 9820.
- NFC controller family is reported as Samsung `sec-nfc` / S3FWRN5-family hardware on I²C address `0x27`.
- The live report records the bound controller at `/sys/bus/i2c/devices/7-0027` and a successful Samsung driver probe.
- `CONFIG_NFC`, `CONFIG_NFC_DIGITAL`, `CONFIG_NFC_NCI`, `CONFIG_SAMSUNG_NFC`, `CONFIG_SEC_NFC`, and `CONFIG_SEC_NFC_LOGGER` were enabled in the tested kernel build. Recheck the active config on the phone; do not infer it from a source fragment alone.
- `/dev/sec-nfc` was observed, with character device permissions `root:root` and mode `0600` (reported major/minor `10:107`; verify dynamically rather than hardcoding major/minor).
- `/sys/class/nfc` exists for the generic Linux NFC core.
- `/sys/class/sec_nfc/nfc_support` exists after the vendor class collision workaround.
- Kernel log included `nfc: nfc_init: NFC Core ver 0.1` and `[sec_nfc] probe() success`.
- A previous duplicate-class panic occurred when generic NFC core and the Samsung driver both attempted to create `/sys/class/nfc`. Patch `kernel/s10plus/patches/0007-sec-nfc-class-name.patch` changes the vendor class name to `sec_nfc`. Preserve the distinction and regression-test it.

The latest known live evidence is in:

`docs/beta-finalization/live/PWNAGE-53000-REPORT.md`

Read that report completely before changing the hardware path. Reconcile its date, active kernel hash, image state, and evidence with the actual target phone.

### 1.2 Firmware identity and licensing

The known firmware candidate is:

`sec_s3nrn82_firmware.bin`

The repository manifest entry is in `firmware/s10plus/manifest.yml`, category `nfc`, with expected destination:

`/lib/firmware/nfc/sec_s3nrn82_firmware.bin`

Recorded SHA-256:

`d315cd8bf47d90b7537aa978cb52299b7f2a56e8748588fb980b83ee823c0bfb`

The manifest marks this proprietary firmware as optional because it is not included in a clean source archive or ordinary release image. The live report says it was pulled from the owner's matching vendor partition and copied into the phone's firmware directory, with the hash matching the manifest.

Important rules:

- Recompute the SHA-256 on the phone and on any staged copy. Do not trust the filename alone.
- Do not commit, redistribute, or silently embed the proprietary firmware binary in Git, a public ZIP, a container, or a release image.
- Use the existing owner-controlled firmware extraction/staging flow in `firmware/s10plus/install-firmware.sh` and `firmware/s10plus/gen-manifest.py` where appropriate.
- Confirm the exact source device, build, and firmware provenance before using the blob. Never pull a random firmware blob from an unrelated S10/S10e/S10+ variant.
- A file being present in `/lib/firmware` does **not** prove it has been uploaded to, accepted by, or is running on the NFC controller. Determine the actual firmware initialization path and report firmware file presence separately from controller firmware runtime/version proof.
- Do not substitute the older aspirational filename `sec_s3fwrn5_firmware.bin` merely because an older prompt mentions it. The live manifest/report identify `sec_s3nrn82_firmware.bin` as the tested candidate for this device. Only change that choice if hardware revision and Samsung HAL evidence prove a different image is required.

### 1.3 Critical driver architecture finding

The pinned Samsung kernel source is:

`https://github.com/Linux4/android_kernel_samsung_exynos9820/tree/f7194c1d15eded1c2a1a4dc63825b26103435cc0`

Inspect at least:

- `drivers/nfc/sec_nfc.c`
- `drivers/nfc/sec_nfc.h`
- relevant Kconfig/Makefile entries
- the exact device-tree node used on `beyond2lte`
- the exact Nuxel kernel patch set and its sidecar/required-patch metadata

The Samsung `sec_nfc` driver currently exposes a **misc character device** named `/dev/sec-nfc`. It provides raw device operations through `open`, `read`, `write`, `poll`, and Samsung-specific `ioctl` calls, with I²C work and IRQ/wait-queue handling below it. The driver registers a `miscdevice` (`misc_register`) rather than registering a standard Linux NCI adapter with the generic NFC core (`nci_register_device` / equivalent API for this kernel).

That distinction is central to this mission:

- `CONFIG_NFC=y` proves the generic NFC core was compiled/initialized. It does not prove a controller has registered as a standard `/dev/nfc*` device or generic NFC netlink endpoint.
- `/dev/sec-nfc` being present proves the Samsung transport endpoint exists. It does not prove its framing, firmware initialization, NCI command sequencing, tag discovery, or NDEF stack.
- Installing `neard`, `nfc-list`, or a generic libnfc package alone is not a valid fix. The standard `neard` path expects the normal Linux NFC subsystem/socket/netlink integration. The current Samsung misc-device driver does not provide that adapter by itself.
- Do not route an arbitrary application directly to `/dev/sec-nfc`. The device is exclusive, privileged, and stateful; a single service must own it.

The current Samsung header defines the ABI. Re-read the exact header from the pinned kernel source and do not copy ioctl numbers from an old blog or invent them. The observed definitions include:

- `SEC_NFC_DRIVER_NAME` = `"sec-nfc"`
- `SEC_NFC_MAX_BUFFER_SIZE` = `512`
- `SEC_NFC_MAGIC` = `'S'`
- `SEC_NFC_GET_MODE`, `SEC_NFC_SET_MODE`, `SEC_NFC_SLEEP`, `SEC_NFC_WAKEUP`, `SEC_NFC_SET_NPT_MODE`, and `SEC_NFC_DEBUG`
- mode values include OFF, FIRMWARE, and BOOTLOADER

The header's ioctl macros use Linux `_IOW` encoding. Inspect how each ioctl is implemented in `sec_nfc_ioctl`; do not assume a named ioctl is implemented correctly or that its encoded direction/size matches its name. In particular, do not call `GET_MODE` unless the implementation is present and has been validated. Use the exact ABI and types from the pinned header.

`sec_nfc_open()` enforces exclusive access and the driver's close path returns the NFC mode to OFF. This should be reflected in service lifecycle and `EBUSY` handling.

### 1.4 Existing repository files and integration points

Inspect and build on these existing paths rather than creating parallel, disconnected implementations:

**Kernel and device**

- `kernel/s10plus/configs/nuxel-drm-kbase.fragment`
- `kernel/s10plus/patches/0007-sec-nfc-class-name.patch`
- `kernel/s10plus/build-kernel.sh`
- `device/s10plus/nuxel-beyond2lte.conf`
- `device/s10plus/90-nuxel-beyond2lte.rules`
- actual `beyond2lte` device-tree source and compiled DTB/DTBO selection

**Firmware**

- `firmware/s10plus/manifest.yml`
- `firmware/s10plus/gen-manifest.py`
- `firmware/s10plus/install-firmware.sh`

**Policy and UI contract**

- `configs/nuxel/nfc/README.md`
- `configs/nuxel/nfc/nfc.json`
- `pwa/nuxel-home/index.html` (existing `qs-nfc` tile)
- `pwa/nuxel-home/js/qs.js` (existing NFC status/toggle logic)
- `pwa/nuxel-home/js/status-bar.js` (existing NFC status polling/icon)
- the existing Nuxel Settings app and privacy/settings navigation

**Bridge/backend**

- `services/nuxel-bridge/src/nfc_provider.py`
- `services/nuxel-bridge/src/api.py`
- existing RPC namespace and authorization patterns
- system service packaging and service graph tests

**Diagnostics and tests**

- `tools/s10plus/a33/nuxel-nfc-diag.sh`
- `tools/s10plus/a33/tests/hw-subsystems/test-nfc-diag.py`
- `docs/beta-finalization/manual-proof/12-nfc.md`
- hardware subsystem fixtures and existing packaging/regression tests

The current `nfc_provider.py` is a truthful stub but its docstring/status assumptions are stale: it says the current kernel has NFC disabled, even though the later live report confirms the NFC core and Samsung driver are enabled and bound. It currently checks for generic NFC paths and `neard`/libnfc tools, returns a blocked verdict, and its enable/tag-read operations intentionally fail because no verified backend is configured. Update it to reflect the actual architecture and provide a real backend contract.

The current `nfc.json` and diagnostic script have stale firmware candidate lists that do not consistently include the verified exact name `sec_s3nrn82_firmware.bin`. They may list older generic names. Fix this without treating a wildcard or a test fixture as proof that the live firmware is correct.

The diagnostic script may currently choose `nfc-list`/`nfc-emulate-forum-tag4` paths if it sees a stack binary. Do not use these tools as a fake or unverified backend for the Samsung misc device. `nfc-emulate-forum-tag4` is an emulator, not a real physical tag reader. A command being installed is not proof of transport support.

Quick Settings already has an `qs-nfc` tile and bridge interactions. Preserve its public state contract where possible, but extend it truthfully rather than simply flipping `supported=true` when a file exists.

---

## 2. Non-negotiable engineering and security rules

1. **No pretending.** Never report READY or tag detection based on a node, firmware filename, package, mock frame, empty read, or test fixture alone.
2. **No speculative wire protocol.** Do not invent NCI framing, vendor bootloader commands, firmware download sequences, packet lengths, or tag activation sequences. Extract them from the exact Samsung userspace HAL/source, the matching vendor image, reputable protocol references, or confirmed hardware traces. Mark unknowns as unknown.
3. **No unrelated kernel replacement.** Keep the current known-booting `Linux4` 4.14.253 base unless a specific, justified driver fix is essential. Do not migrate to a different kernel as part of this NFC task.
4. **No routine use of bootloader mode.** `SEC_NFC` BOOTLOADER mode is a recovery/firmware-update path, not normal discovery. Do not enter it without a validated update procedure, matching firmware, explicit owner approval, and recoverability evidence.
5. **No NPT/test mode in normal operation.** Do not use `SEC_NFC_SET_NPT_MODE`, proprietary sysfs test hooks, NFC test class writes, or undocumented ioctl calls for normal bring-up.
6. **No arbitrary raw I²C access.** Keep all controller operations through the bound kernel driver. Do not use `i2cget`, `i2cset`, `/dev/i2c-*`, or ad-hoc GPIO toggles against a live controller.
7. **One device owner.** Only one daemon/service may own `/dev/sec-nfc`. Apps, PWA code, bridge HTTP handlers, and diagnostic scripts must not race to open the character device.
8. **Least privilege.** Do not change the node to `0666`, grant blanket `uaccess`, expose it to every process, or run an entire UI stack as root. Restrict access to the dedicated NFC service.
9. **OFF by default.** Preserve the policy's default-off behaviour. Do not power the antenna/controller at every boot or silently resume scanning after reboot. An explicit user toggle or scan action authorizes operation.
10. **Bound every operation.** All waits, discovery loops, service calls, reads, firmware actions, shutdown, and scan sessions need explicit timeouts and cancellation. No UI-thread blocking and no unbounded process reads.
11. **Read-only first.** Do not write to tags until real read/discovery works repeatedly and there is a separate reviewed write implementation. Never write irreversible lock bits, format tags automatically, or alter access-control bytes.
12. **No payments or eSE access.** The embedded secure element is not the basic tag-reader path. Do not claim EMV, Google/Samsung Wallet, payment, transit, HCE/card emulation, credentials, or secure-element access. Do not access secure-element APDUs or change secure-element provisioning.
13. **No auto-execution of tag data.** Never launch a URL, open a file, import a contact, run a command, or render untrusted HTML automatically from a tag. Display escaped data and ask for an explicit action.
14. **No secret/PII logging.** Do not persist tag UID, NDEF contents, device identifiers, location, or raw packet dumps by default. Diagnostics should redact tag data and only capture packet traces with explicit opt-in and a clear path to delete them.
15. **No vendor binary redistribution.** Preserve proprietary firmware licensing/provenance. Do not include the binary in source-control or public artifacts.
16. **No live kernel flash without explicit owner approval.** Build and test kernel changes in the build environment. User-space deployment can be staged safely, but do not reboot/flash a kernel partition or perform firmware updates on the physical phone without explicit approval and a documented rollback.
17. **Keep Nuxel Android-dependency-zero.** Do not introduce the Android framework, Android runtime, Binder services, or a booted Android container to make NFC work. Reuse a small, auditable native Linux component or a carefully ported standalone Samsung HAL component where licensing and dependencies permit.
18. **Accurate completion status.** Mark software tests, protocol simulation, device transport, physical tag discovery, NDEF reading, and owner acceptance as separate evidence levels.

---

## 3. Phase 0 — Establish an immutable baseline and reproduce the current state

Before modifying code:

### 3.1 Repository baseline

- Record repository commit, branch, dirty state, submodules, build configuration, target device, image version, kernel source commit, and active kernel build identity.
- Run `git status --short` and preserve pre-existing user modifications. Never reset, clean, checkout, or overwrite uncommitted work.
- Read the complete `PWNAGE-53000-REPORT.md`, current NFC policy/README, provider, diagnostic script, kernel patch, manifest and target udev rules.
- Map every current NFC path from image build to installed phone: kernel config/driver -> DT -> `/dev/sec-nfc` -> firmware staging -> service -> bridge API -> Quick Settings/Settings.
- Identify the actual init system and packaging model in the current S10+ image. Do not copy a service unit for a different distribution/init manager.

### 3.2 Live device inventory

Use read-only inspection first. Gather and timestamp:

- `uname -a`, `/proc/cmdline`, active kernel build ID/hash if available.
- `/proc/config.gz` or the exact active `/boot/config-*`; record each relevant CONFIG value.
- `dmesg` filtered for `nfc`, `sec_nfc`, I²C bus/address, firmware, probe, IRQ and regulator failures.
- `ls -l /dev/sec-nfc`, `stat`, `udevadm info --query=all --name=/dev/sec-nfc`, `udevadm info --attribute-walk --name=/dev/sec-nfc` where supported.
- `/sys/bus/i2c/devices/7-0027` or the dynamically discovered `*-0027` node, its `driver` symlink, `name`, `modalias`, `uevent`, compatible/device-tree properties and power state.
- `/sys/class/nfc`, `/sys/class/sec_nfc`, `/sys/class/sec_nfc/nfc_support`, plus any actual NCI device nodes, but do not infer a working adapter from these alone.
- firmware path, owner, size, permissions, SHA-256 and manifest match. Do not output the binary itself.
- currently loaded/active NFC-related services and all open file descriptors for `/dev/sec-nfc` (`lsof`/`fuser` if installed; use safe alternatives if not).
- power/clock/IRQ/regulator information exposed by the driver, without changing hardware state.
- SELinux/AppArmor/systemd restrictions if present.

Store sanitized output in a diagnostic report. Redact serial numbers, MAC addresses, tag identifiers, user names and other unnecessary personal identifiers.

### 3.3 Establish what is and is not already proven

The baseline report must use this matrix:

| Layer | Evidence required | Allowed current status |
|---|---|---|
| Kernel configuration | Active running kernel config | PRESENT / MISSING / UNKNOWN |
| Kernel driver | Driver bound to the correct I²C device and probe succeeded | BOUND / UNBOUND / UNKNOWN |
| Character transport | `/dev/sec-nfc` major/minor matches the registered misc device and can be opened by the designated service | PRESENT / OPENABLE / BUSY / ERROR |
| Firmware file | Exact path/hash/size/provenance | MATCH / MISSING / MISMATCH |
| Runtime firmware | Controller confirms valid running firmware/version, or verified Samsung init sequence reaches operational state | VERIFIED / NOT_VERIFIED / FAILED |
| Raw transport | Bounded request/response or known controller event is transferred correctly | PASS / FAIL / NOT_TESTED |
| Protocol adapter | Controller initialization/discovery protocol is interoperable | PASS / FAIL / NOT_TESTED |
| Tag discovery | Real tag event from physical tag | PASS / FAIL / NOT_TESTED |
| NDEF read | Valid known NDEF payload read and independently checked | PASS / FAIL / NOT_TESTED |
| UI integration | ON/OFF/scan/status works through normal Nuxel UI | PASS / FAIL / NOT_TESTED |

Do not collapse these into a single boolean called `supported`.

---

## 4. Phase 1 — Audit and harden the existing Samsung kernel ABI

### 4.1 Read the exact pinned driver and header

Inspect `sec_nfc.c` and `sec_nfc.h` at the exact pinned kernel revision. Confirm all of the following directly from source:

- misc-device registration and exact device node name;
- open exclusivity and close semantics;
- read/write buffer handling, maximum transfer length, return values and packet boundaries;
- poll readiness semantics, wait-queue wakeup conditions, IRQ handling and cancellation behaviour;
- ioctl command encoding, argument type, direction, and implemented behaviour;
- OFF, normal/FIRMWARE, BOOTLOADER state transitions;
- VEN/FIRM/IRQ/clock/LDO/regulator sequence and delays;
- what firmware is loaded by the kernel, if any;
- whether reads return complete NFC protocol frames or raw/chunked I²C bytes;
- which errors (`-EBUSY`, `-EAGAIN`, `-EINTR`, `-ETIMEDOUT`, `-EIO`, etc.) can occur and how the userspace caller must handle them.

Do not infer the transport protocol from function names. Follow the data path from userspace `write()` to I²C transmit and from IRQ to `read()` in detail.

### 4.2 Fix the existing class lifecycle bug safely

Review `kernel/s10plus/patches/0007-sec-nfc-class-name.patch`. In the pinned source, there is a suspicious error check of the form `IS_ERR(&nfc_class)` after `class_create()`. Verify the exact declaration and type. If confirmed, correct it to check the pointer returned by `class_create()` (normally `IS_ERR(nfc_class)`), handle `PTR_ERR(nfc_class)`, and ensure partial initialization is unwound correctly.

Also verify:

- `class_create_file()` failures are handled and unwind safely;
- the `sec_nfc` class is destroyed/cleaned up in the correct remove/error path where applicable;
- repeated probe/unbind or module lifecycle cannot leak or duplicate class objects;
- the class rename continues to prevent `/sys/class/nfc` collision when `CONFIG_NFC=y`;
- the patch remains applicable to the pinned `Linux4` source and its required sidecar metadata remains correct.

Do not rename the generic NFC core class and do not remove `CONFIG_NFC` merely to hide the duplicate registration. The known workaround must be tested with both generic NFC core and Samsung `sec_nfc` enabled.

### 4.3 Device-tree and GPIO audit

Confirm the live DT has the correct Samsung NFC properties and GPIO assignments:

- `sec-nfc,ven-gpio`
- `sec-nfc,firm-gpio`
- `sec-nfc,irq-gpio`
- optional `sec-nfc,nfc_ap_clk`
- optional `sec-nfc,clk_req-gpio`
- optional `sec-nfc,ldo_control`
- optional `sec-nfc,nfc_pvdd`

Trace each phandle to the correct GPIO controller/pin and polarity. Verify IRQ trigger type and wake capability from the actual device tree and hardware report. Check that no other subsystem owns/reconfigures these pins. Do not toggle any GPIO manually during live operation.

### 4.4 Kernel regression gate

If a kernel code/DT change is justified:

- build against the exact pinned source and current Nuxel fragment;
- run the repo's full kernel patch applicability checks;
- verify `CONFIG_NFC`, `CONFIG_NFC_DIGITAL`, `CONFIG_NFC_NCI`, `CONFIG_SAMSUNG_NFC`, `CONFIG_SEC_NFC`, and `CONFIG_SEC_NFC_LOGGER` remain set as intended;
- verify no duplicate class registration;
- inspect the resulting kernel log and sysfs tree in a controlled boot test;
- keep the known-good bootable kernel/image untouched until explicit deployment approval.

Do not flash a new kernel just because a source patch changed. A user-space service can and should be developed independently first.

---

## 5. Phase 2 — Find the real Samsung userspace initialization and protocol implementation

This is the decisive investigation. The firmware file may be present but the controller may still require vendor initialization, download, NCI reset/configuration, or a particular command sequence.

### 5.1 Search the matching original vendor environment

Use the owner's matching S10+ vendor partition, extracted vendor image, or previously acquired device-side files. Search only the matching device/build where possible. Look for:

- Samsung NFC HAL libraries (`libnfc-sec*`, `libnfc-nci*`, related vendor libraries);
- NFC HAL service binaries and init service definitions;
- vendor NFC configuration (`libnfc-sec-vendor.conf`, `libnfc-nci.conf`, XML/JSON/etc.);
- firmware loader/updater components;
- kernel headers shipped with the matching vendor image;
- Android HAL source or published Samsung/Linux NFC implementation matching S3NRN82/S3FWRN5 family;
- exact firmware search path and expected firmware name;
- firmware version query/response and controller reset/init logic;
- `open()`/`ioctl()`/`poll()`/`read()`/`write()` use of `/dev/sec-nfc`;
- required permissions, SELinux rules, power sequencing, clock and IRQ expectations.

Use static inspection first. Do not run unknown vendor binaries as root on the live phone. If runtime instrumentation is necessary, do it on a controlled matching system or under explicit owner approval, with bounded logs and no firmware update commands.

### 5.2 Establish provenance and compatibility

For every reused Samsung component or protocol description, record:

- exact source/device/build/version;
- checksum and license/provenance;
- ABI compatibility with the active kernel header;
- whether it requires Android Binder, Android properties, Android `libhardware`, vendor services, SELinux domains, or other Android runtime services;
- which dependencies can be replaced with native Linux interfaces and which cannot;
- whether porting is permitted by the component's license.

Do not copy a prebuilt Android HAL into Nuxel and call it native. If a small protocol component is reusable and license-compatible, port the minimum necessary logic into a standalone native daemon. If the only possible implementation requires Android framework services or an incompatible proprietary interface, report that precisely rather than hiding the dependency.

### 5.3 Prove the firmware boot/update path

Answer these questions from evidence:

1. Is the NFC controller firmware already persistent in the controller's nonvolatile storage, or must a userspace HAL upload it at each power-on?
2. Is `sec_s3nrn82_firmware.bin` the exact blob loaded by the matching HAL for this controller revision?
3. Does the driver itself call `request_firmware()`? If not, which exact userspace process reads the file and sends it?
4. Is the blob a raw image, patch, signed package, or container with a header/version/checksum?
5. Which reset, bootloader, status, chunking, ACK/retry and verification commands are required?
6. What happens if the upload is interrupted or the checksum fails?
7. Does controller firmware persist after power-off, or must the procedure repeat?

Do not implement a firmware uploader until the correct protocol is proven. Do not issue arbitrary bytes to the controller. Do not use BOOTLOADER mode to “see what happens.” If the firmware file is merely a candidate and is not needed for normal operation, keep it staged but do not force an update.

### 5.4 Decision record: choose the right integration architecture

Write a brief architecture decision record in the repository before implementation. Evaluate these options:

**Option A — Native Nuxel userspace controller service (preferred starting point if raw Samsung protocol can be established).**

- One native daemon owns `/dev/sec-nfc`.
- It implements the confirmed Samsung transport, required firmware/normal-mode initialization, NCI/vendor protocol commands, tag polling, and NDEF handling for a clearly scoped set of tag types.
- It exposes a small versioned local API (prefer the existing Nuxel system bridge/D-Bus or a root-owned Unix socket with explicit peer authorization).
- `nuxel-bridge` talks to that service through a narrow client interface; web apps never receive the device FD.
- It is self-contained and does not claim to register a generic kernel NFC adapter.

This option is acceptable for Nuxel's built-in reader and provides the most direct path to working tag detection while preserving the current vendor driver.

**Option B — Kernel NCI adapter/shim.**

- Only choose this if the controller transport and NCI framing are proven and a native Linux NFC kernel adapter is materially better for interoperability.
- Investigate the exact Linux 4.14 NFC/NCI API available in the pinned kernel; do not copy a current upstream API blindly.
- The adapter must own/present the correct NCI transport to the kernel NFC core and handle power, IRQ, framing, and state transitions safely.
- Avoid two drivers owning the same I²C address or competing with the existing Samsung `sec_nfc` misc device. If the kernel shim replaces or wraps the current driver, define one owner and one lifecycle; never open the raw misc device from one side while the other also drives I²C.
- Test generic NFC core/netlink registration and an actual device instance before integrating `neard` or standard tools.

**Option C — Standard `neard`/libnfc stack without an adapter.**

This is **not acceptable**. Do not install it and mark NFC ready merely because it is available in Fedora repositories. It can only be adopted after a compatible standard Linux NFC device/transport has been registered and proven.

The architecture decision must state why the chosen option is correct and what evidence supports its protocol/ABI assumptions. If a userspace implementation must speak a vendor-specific protocol directly, clearly document that and do not label it generic NCI compatibility.

---

## 6. Phase 3 — Implement one safe, native NFC controller service

### 6.1 Service boundaries

Implement a dedicated service with the smallest reasonable attack surface. Use the repo's existing language/build conventions unless there is a strong reason not to. Preferred architecture:

`Nuxel UI -> nuxel-bridge NFC provider -> authenticated local service API -> nuxel-nfc service -> /dev/sec-nfc -> kernel Samsung driver -> controller`

Required boundaries:

- the native NFC service is the sole owner of `/dev/sec-nfc`;
- `nuxel-bridge` does not perform raw I/O and does not execute unbounded shell commands;
- PWA/GTK/native apps do not open the device node directly;
- service API exposes semantic operations, not arbitrary ioctl, arbitrary bytes, raw I²C, or arbitrary NCI command pass-through;
- all service responses are versioned and typed;
- authorization distinguishes status, enabling/disabling, scanning, reading payloads, and writing payloads;
- errors are structured and mapped to truthful UI states.

If the repository has a D-Bus service convention, use a restricted system-bus API. Otherwise use a root-owned Unix-domain socket with filesystem permissions and `SO_PEERCRED`/equivalent peer credential validation. Do not bind an unauthenticated TCP port or listen on Wi-Fi/LAN.

### 6.2 Device ownership and permissions

The live `/dev/sec-nfc` was observed as root-owned mode `0600`. Preserve the least-privilege principle.

- Inspect the actual `udevadm info` result to learn subsystem, kernel name and attributes. Do not assume the node is `SUBSYSTEM=="nfc"`; the driver is a misc device.
- Add a narrowly matched rule for this exact device if needed (for example based on the verified kernel node name/subsystem/driver attributes). Do not invent a rule that never matches.
- Prefer a dedicated `nuxel-nfc` system group/service account or systemd `DeviceAllow=/dev/sec-nfc rw` where supported.
- Avoid `MODE="0666"`, broad `TAG+="uaccess"`, and user-session access to raw transport.
- If the NFC daemon needs root for device access, drop privileges after opening only if this is safe and supported; otherwise confine it with `DevicePolicy=closed`, `DeviceAllow`, `NoNewPrivileges`, `ProtectSystem`, `ProtectHome`, restricted address families, private temp, resource limits, and no unnecessary capabilities.
- Restrict its writable paths to explicit state/log locations; never make firmware directories writable by the daemon.
- Handle systemd/OpenRC/service packaging according to the actual image, not both indiscriminately.

### 6.3 Native device I/O correctness

The controller service must:

- open the node only after an explicit enable/scan request;
- handle exclusive-open `EBUSY` clearly and diagnose any stale owner;
- use exact ioctl values and types from the pinned Samsung header;
- distinguish normal/FIRMWARE mode from BOOTLOADER mode;
- apply normal mode only after the correct power/firmware initialization sequence has been verified;
- use `poll()` with bounded timeouts and cancellation;
- respect kernel maximum transfer size and header-defined message sizes;
- handle short reads/writes, interrupted calls, `EAGAIN`, `EINTR`, `EIO`, device removal, power loss and daemon shutdown;
- ensure transaction serialization and one outstanding command when required by the protocol;
- parse packet boundaries exactly; never assume one `read()` equals one full packet unless driver source proves that;
- avoid busy loops and uncontrolled retries;
- drain/flush stale events only according to documented protocol rules;
- close the fd and return to OFF on disable, fatal error, service stop, and controlled shutdown;
- never call the driver from a PWA/UI thread or HTTP request handler.

Create a small dedicated transport abstraction that can run against both the real file descriptor and a deterministic mock. Unit-test ioctl encoding against C constants compiled from the pinned header. If the service uses Python/Rust and re-creates `_IOC` encoding, test exact numeric values against a tiny C helper built from the same header. Do not hand-copy numeric ioctl constants without this test.

### 6.4 Protocol implementation requirements

Only implement the packet protocol after the exact Samsung HAL/driver evidence has clarified framing.

If NCI is confirmed:

- follow the correct NCI version supported by the controller/firmware;
- implement CORE_RESET/CORE_INIT or the actual documented activation sequence;
- validate response group/opcode, status byte and payload lengths;
- implement command timeouts and retries only where the protocol permits;
- handle notifications separately from command responses;
- handle packet fragmentation/reassembly if required by the device transport;
- implement discovery map/routing for only the tag technologies proven;
- parse RF discovery and activation notifications safely;
- handle field loss/tag removal and repeated discovery sessions;
- reject malformed/oversized packets before allocation/copy;
- avoid hardcoded assumptions about RF interface, bitrate, technology or NCI version without controller capability discovery.

If the transport uses Samsung vendor framing or a non-NCI boot protocol:

- model it as a distinct, documented layer below any NCI parser;
- do not mislabel vendor frames as NCI;
- implement exact lengths, checksums, sequence IDs, ACK/NACK and reset semantics from evidence;
- provide protocol version and controller identity diagnostics;
- keep raw vendor commands private to the daemon and expose only semantic operations to clients.

### 6.5 Initial supported tag scope

Start narrow and prove each feature:

1. NFC-A tag detection only if supported by actual controller/firmware protocol.
2. NFC Forum Type 2 / NTAG213/215/216 detection and NDEF reading where physically verified.
3. UID/type/ATQA/SAK or other identifiers only if obtained through standard supported discovery data; never fabricate absent fields.
4. Basic NDEF Text and URI records with strict length and encoding validation.
5. Unknown NDEF record types are displayed as metadata/raw bounded data only if safe; never execute.

Then, only if proven by the hardware/controller stack, investigate:

- ISO-DEP / NFC Forum Type 4;
- NFC-A/B/F/V technology support;
- additional NDEF record types.

Do not claim MIFARE Classic support unless authentication, key handling, and protocol compatibility have actually been implemented and tested. Do not claim support for every NFC tag standard because the controller is detected.

### 6.6 NDEF parser hardening

The parser is exposed to untrusted physical input. It must:

- check every offset, record length, payload length, chunk flag, TNF, type length and ID length before reading;
- cap maximum frame, message and aggregate record sizes;
- guard integer overflow and nested-length arithmetic;
- reject malformed MB/ME/CF/SR/IL flag sequences and illegal TNF combinations;
- handle UTF-8/UTF-16 text encoding safely and reject invalid encodings without crashing;
- sanitize URI schemes and display unknown schemes as inert text;
- escape HTML/Markdown/terminal controls;
- never invoke a URL handler automatically;
- never parse vCard/calendar/contact payloads into privileged system actions without a separate explicit import flow;
- include fuzz tests and sanitizer-enabled tests where supported.

---

## 7. Phase 4 — Runtime state, power, suspend and failure recovery

### 7.1 One explicit state machine

Implement and document a deterministic state machine. Suggested states:

- `UNAVAILABLE`
- `DISABLED`
- `STARTING`
- `INITIALIZING`
- `READY_IDLE`
- `DISCOVERING`
- `TAG_DETECTED`
- `READING_NDEF`
- `STOPPING`
- `BUSY`
- `ERROR`

Do not conflate `DISABLED` with `UNAVAILABLE`, or `READY_IDLE` with `TAG_DETECTED`. Add an `UNKNOWN`/`NOT_TESTED` diagnostic stage where appropriate.

Transitions must be idempotent. A second enable while already enabled must not reinitialize the controller. A second scan request must either join the current scan or return a clear busy state. Disable during discovery must cancel and release the active operation. Daemon restart must clean up and return the controller to a safe state.

### 7.2 Default-off policy

- At boot NFC starts disabled; no antenna power, firmware upload, discovery or polling until requested.
- The daemon may be socket-activated or start idle, but it must not claim NFC is ready or open the hardware before an explicit user action unless a verified lifecycle requirement makes this unavoidable.
- Persist the user's preference only if existing Nuxel privacy policy explicitly allows it; default preference remains OFF on a fresh install.
- Do not auto-enable after reboot or suspend/resume without an explicit current policy decision.

### 7.3 Power sequencing and cleanup

Follow the proven driver and vendor HAL sequence. Do not duplicate GPIO/clock/IRQ handling in userspace.

- Enable: acquire exclusive fd -> verify current state safely -> perform verified normal-mode initialization -> wait for bounded controller readiness -> publish `READY_IDLE`.
- Scan: start bounded discovery -> publish `DISCOVERING` -> parse events -> detect removal/timeout -> return to `READY_IDLE`.
- Disable: cancel scan -> stop RF field/discovery using documented operation -> send sleep/off if verified -> close fd -> confirm driver returned mode OFF -> publish `DISABLED`.
- Fatal I/O/protocol error: attempt only documented safe recovery; otherwise close, mark `ERROR`, and require a fresh bounded initialization.
- Service exit or SIGTERM: bounded cleanup, close descriptor, release any lock, and never leave the controller in bootloader mode.

Check battery impact with NFC disabled and enabled-idle. Avoid polling continuously just to render a Settings icon.

### 7.4 Suspend/resume and lockscreen

Coordinate with the existing Nuxel power/session manager:

- decide whether an active scan is cancelled on suspend (default should be yes);
- release or place the controller into a verified low-power state before suspend;
- resume only when the user-requested NFC preference and policy authorize it;
- avoid duplicate IRQ wake configuration;
- ensure lockscreen privacy hides payload/identifier details while locked;
- do not expose tag contents in lockscreen notifications;
- check screen-off scans only if an explicit future product requirement asks for them.

### 7.5 Crash recovery

- If daemon crashes, system manager may restart it with rate limiting; the bridge must report unavailable/starting accurately.
- A restart must not race an old FD/process. Check process and device ownership, wait bounded time for release, and return `BUSY` if an external owner remains.
- Never force-kill random processes holding the device.
- Do not automatically enter bootloader to recover.
- Provide an owner-visible diagnostic/recovery step that is safe and non-destructive.

---

## 8. Phase 5 — Nuxel bridge API, authorization, Quick Settings, and Settings UI

### 8.1 Backend provider

Replace the stub behaviour in `services/nuxel-bridge/src/nfc_provider.py` with a real client for the NFC service.

Requirements:

- status must be read from the actual daemon/hardware state, not only file presence;
- `set_enabled` must perform a bounded service request and return the resulting state;
- `test_tag`/`read_tag` must perform a bounded discovery/read operation, or return a precise unsupported/error reason;
- bridge handlers must not block the HTTP event loop or shell out to `nfc-list`;
- timeouts/cancellation must propagate;
- preserve existing API route and RPC shape where practical, version any schema expansion, and add compatibility handling;
- map errors such as firmware-missing, driver-unbound, permission-denied, busy, controller-init-failed, unsupported-protocol, scan-timeout, no-tag, malformed-tag, and service-unavailable to stable structured responses.

Do not let status queries implicitly enable NFC.

### 8.2 Authorization and app boundary

Audit `services/nuxel-bridge/src/api.py` and existing owner/permission checks. Define permissions:

- `nfc.status`: safe read of capability/state without exposing private tag content;
- `nfc.enable`: user-authorized hardware power toggle;
- `nfc.scan`: explicit reader session;
- `nfc.read`: retrieve decoded NDEF data after an explicit scan and consent;
- `nfc.write`: future separately authorized operation; denied by default until implemented.

Only trusted Nuxel Settings/Quick Settings/system surfaces may enable and scan. Other apps must not silently scan. No network clients or web content receive privileged access. Use the bridge's existing authentication/session mechanism; do not invent a weaker bypass.

### 8.3 Quick Settings tile

The existing `qs-nfc` tile in `pwa/nuxel-home/index.html` and logic in `js/qs.js` should become truthful and polished.

- Disabled: show off state; no false “unsupported” if hardware stack is available but intentionally off.
- Starting: show progress/disabled toggle to prevent double starts.
- Ready: show NFC enabled, with clear indication that no scan is currently in progress.
- Discovering: show scan progress and an obvious cancel action if UI design permits.
- Tag detected: show a privacy-safe banner/entry and let the user open the NFC reader detail view.
- Error/unavailable: show a useful reason and a link to diagnostics, not a fake toggle.
- Preserve keyboard/accessibility and touchscreen behaviour.
- Do not poll the device at high frequency; use event notifications or modest polling and avoid duplicate requests.

### 8.4 Status bar

Update `pwa/nuxel-home/js/status-bar.js` so the NFC icon means a clearly defined state. Do not show “NFC active” merely because `/dev/sec-nfc` exists or because hardware is supported. Consider separate icon/labels for disabled, enabled-idle and scanning, but do not show tag content in status bar. Polling must be low-cost and back off when no session is active.

### 8.5 Settings page

Integrate into the existing Nuxel Settings navigation, using the repo's current style/components.

Minimum NFC Settings content:

- NFC radio toggle (default OFF on first boot);
- controller/firmware/transport status as separate rows;
- `Scan for tag` action with visible bounded scan duration and Cancel;
- tag-detected view with supported tag type and sanitized NDEF preview;
- clear No tag / scan timed out state;
- privacy explanation and a button to clear transient tag data;
- diagnostics details (copyable sanitized report) without binary dumps or private data;
- explanation when hardware is present but protocol backend is not yet verified;
- never offer payments, card emulation, secure-element or wallet claims.

The UI must be asynchronous. Hardware discovery runs in the daemon, never in a UI thread. Handle app close and navigation away by cancelling or detaching from the scan session safely. Reopening Settings must not create a second scan or device owner.

---

## 9. Phase 6 — Diagnostics and support tooling

Update `tools/s10plus/a33/nuxel-nfc-diag.sh` and its tests. Keep commands safe and bounded.

Suggested command behaviour (adapt to existing CLI conventions):

- `status`: report all independent stages and current service state, never scan implicitly.
- `firmware`: report exact known file, size, SHA-256, source/provenance if available, and whether runtime load/acceptance is actually verified.
- `transport`: perform a minimal bounded open/state/close health probe only if it can do so without racing the daemon; otherwise query the daemon.
- `scan --timeout N`: request a real bounded scan through the service; default to a short timeout (e.g. 10 seconds), with a strict maximum (e.g. 30 seconds), and require explicit execution by the owner.
- `read`: read an actual NDEF tag only after discovery; never fabricate a UID or payload.
- `report`: emit sanitised report with no tag payload or identifiers by default.
- `selftest`: run unit/mock tests and safe daemon status checks, not proprietary controller test modes or unbounded hardware loops.

Requirements:

- correct current firmware candidate `sec_s3nrn82_firmware.bin` and exact path in diagnostic candidate checks;
- report generic NFC core separately from vendor misc transport and NCI adapter;
- identify `/dev/sec-nfc` using actual device attributes, not guessed `SUBSYSTEM` alone;
- determine bound I²C driver from sysfs and dmesg;
- prove service ownership and backend reachability;
- never run `nfc-emulate-forum-tag4` as a reader;
- never claim READY because `neard` is installed;
- no writes to class test attributes, GPIOs, `/dev/i2c-*`, NPT mode or bootloader mode;
- use strict shell mode, robust quoting, timeouts and cleanups;
- return distinct exit codes for hardware missing, firmware missing, transport unsupported, daemon unavailable, no tag, and real read success.

Update `configs/nuxel/nfc/README.md` and `nfc.json` to represent the real pipeline and the exact confirmed hardware/firmware identity. The schema must differentiate `controller_present`, `firmware_file_verified`, `firmware_runtime_verified`, `vendor_transport_present`, `protocol_adapter_ready`, `tag_reader_ready`, and `last_physical_test`. Keep unknown values unknown, not false-success.

---

## 10. Phase 7 — Testing strategy (must be implemented, not merely described)

### 10.1 Unit tests for the driver ABI wrapper

- Exact ioctl numeric constants agree with the pinned `sec_nfc.h` at build/test time.
- Argument sizes and signedness are correct.
- FDs close on every error path.
- Exclusive-open `EBUSY` is mapped to a stable busy response.
- OFF/normal/bootloader enum values match header; tests assert bootloader mode is not used by normal enable flow.
- Driver maximum read/write sizes are enforced.

### 10.2 Transport tests with a deterministic mock

Test:

- partial read and partial write;
- one read containing a whole frame and a frame delivered in multiple pieces;
- poll timeout, readiness, interrupt and cancellation;
- `EINTR`, `EAGAIN`, `EIO`, `ENODEV`, `EBUSY`;
- duplicate/out-of-order events;
- malformed headers and impossible lengths;
- concurrent enable/scan/disable calls;
- daemon stop during a pending command;
- reconnect/reinit after transient I/O failure;
- ensure there is only one device owner.

The mock must be clearly marked `MOCK`; no test fixture can set physical hardware state to PASS.

### 10.3 Protocol tests

Using captured/reference protocol sequences that are licensed and redacted:

- reset/init request and matching response;
- status/version query if supported;
- discovery start/stop;
- supported technology activation;
- field lost/removal;
- NDEF read for a known synthetic record;
- unknown technology and unsupported record;
- malformed lengths, oversized frames, unsupported version and unexpected statuses;
- timeouts and retry policy.

Do not create a “golden” command sequence from guesses. If no protocol trace/source exists, keep the test blocked and continue source research.

### 10.4 NDEF parser tests and fuzzing

- valid Text, URI and empty records;
- multiple records/chunking where supported;
- valid UTF-8, UTF-16 and malformed sequences;
- unknown TNF/type;
- malicious scheme such as `javascript:`, `file:`, `data:`, `intent:` and unusual control characters;
- huge, truncated, overflow and inconsistent payload lengths;
- parser must not crash, overread or auto-open content.

### 10.5 Bridge/UI tests

- provider status for every state;
- enable/disable success and failure;
- scan success/no tag/timeout/cancel/busy/error;
- authorization denied for untrusted apps;
- tag data is not exposed to unauthorized apps or lockscreen notifications;
- Quick Settings tile shows real state;
- Settings remains responsive and scan stays off UI thread;
- app navigation/closing does not leak sessions;
- status bar does not show false active state.

### 10.6 Diagnostics regression

Extend `tools/s10plus/a33/tests/hw-subsystems/test-nfc-diag.py` with fixtures for:

- present generic core + bound Samsung driver + misc device;
- firmware exact match/missing/hash mismatch;
- generic core present but no adapter;
- device node present but unopenable;
- daemon missing/not ready;
- protocol initialized but no tag;
- physical tag and successful NDEF read evidence marker;
- mock transport test without physical test claim.

Never put a real tag UID/NDEF content in fixtures or normal CI logs.

### 10.7 Full repository gates

Run targeted NFC tests, service tests, bridge tests, JS tests, packaging checks, formatting/lint, service graph checks, image build checks and the repository's established golden/smoke gate. Record pre-existing failures separately; do not hide or silently rewrite unrelated test expectations.

---

## 11. Phase 8 — Physical S10+ acceptance tests

A physical tag test is mandatory before describing NFC as working on the S10+.

### 11.1 Required test material

Use at least one known, ordinary, rewritable NFC Forum Type 2 tag (e.g. a known NTAG213/215/216) containing a simple NDEF Text or HTTPS URI record. Have a second tag with a different known UID/content for cross-checking. Do not use a bank card, access badge, transit card, work credential or payment card for initial testing.

### 11.2 Exact test sequence

1. Boot with NFC OFF. Confirm no active discovery, no false NFC icon, no excessive NFC service polling and no controller held powered unnecessarily.
2. Open Settings -> NFC; verify controller, firmware and service states separately.
3. Enable NFC. Verify state progresses to STARTING/INITIALIZING/READY, with bounded time.
4. Start scan. Present tag A. Confirm exactly one tag event with a real supported type and available identifiers; do not invent missing fields.
5. Read NDEF. Compare decoded content against the known preloaded record. Display URI/text as inert content.
6. Remove tag. Confirm removal/field-loss or scan completion without a ghost tag.
7. Present tag B. Confirm it is independently detected and has the expected different identity/content.
8. Repeat scan/remove at least 10 cycles; check there are no stale events, duplicated tag notifications, or state-machine deadlocks.
9. Cancel a scan while no tag is present; check bounded cancellation and successful next scan.
10. Turn NFC OFF; verify FD released, driver mode OFF, scan stopped and UI reflects OFF.
11. Repeat after screen lock/unlock and suspend/resume according to policy.
12. Reboot and confirm default OFF; enable again and verify functionality.
13. Leave NFC OFF and measure idle battery/resource impact relative to baseline.

Capture only minimum necessary evidence. Tag identifiers/payloads must be redacted in reports unless owner explicitly approves temporary private evidence storage.

### 11.3 Required physical acceptance result

NFC can be marked `HARDWARE_TAG_READ_VERIFIED` only when a physical tag is detected and its NDEF data is read correctly on the actual S10+ using the new Nuxel service. It can be marked `OWNER_ACCEPTED` only after the owner repeats the test and confirms the result.

If no physical tag is available, mark the software/transport work as complete only at its actual layer and leave physical validation `NOT_TESTED`. Do not invent a successful read.

---

## 12. Optional phase after read-only success — safe NDEF writing

Do not let write support delay the first read-only release. If implementing it within this mission, require a separate explicit design and test gate:

- show current tag and NDEF contents first;
- show the exact new record and target tag;
- user must explicitly confirm the write;
- permit only known safe record types and supported tag capacity;
- check writable/capacity/lock state before write;
- write only the intended NDEF data area using a standards-compliant sequence;
- read back and verify byte-for-byte or semantically equivalent payload;
- never write permanent lock bits, password-protect, format, erase, or alter access control automatically;
- do not write to bank/access/transit/identity/payment cards;
- keep write capability disabled by default and separately permissioned;
- do not expose raw arbitrary write APDUs or arbitrary commands to apps.

If these conditions cannot be met, ship read-only support and keep writes explicitly unavailable.

---

## 13. Build, packaging, installation, deployment and rollback

### 13.1 Packaging

- Add the native NFC service, service unit, configuration, permissions and dependencies to the actual S10+ image build path.
- Avoid installing a generic stack that cannot talk to the Samsung transport.
- Keep optional proprietary firmware separate from open-source source artifacts and release files.
- Validate architecture (`aarch64`/ARM64), ABI, dynamic linker, library versions, install paths and service user.
- Add service health check and daemon version to Nuxel diagnostics.
- Make clean-image behaviour explicit: firmware missing means `BLOCKED_FIRMWARE`, not a crash or fake ready state.
- Ensure upgrade preserves user preferences but a fresh install defaults NFC OFF.

### 13.2 Safe deployment

- Back up only the user-space files/configuration that will be replaced; record hashes and paths.
- Prefer staged SSH deployment of user-space service/provider/UI changes.
- Do not flash partitions, change bootloader, replace kernel or update NFC controller firmware without explicit owner approval.
- Deploy one layer at a time: service binary/unit -> service permissions -> bridge provider -> UI -> diagnostics.
- Verify the currently running kernel and known-good boot path remain untouched.
- Use bounded service restart and log capture. If `/dev/sec-nfc` cannot be opened or driver reports an error, roll back the user-space service and keep NFC disabled.

### 13.3 Rollback

Provide exact commands/script to:

- stop/disable the new NFC service;
- restore previous provider/UI/config/udev/service files from timestamped backups;
- remove newly created user-space files and permissions safely;
- leave existing kernel, DTB, user data, SSH and network configuration intact;
- restore NFC OFF state and verify it;
- collect a post-rollback diagnostic report.

No destructive rollback, factory reset or partition operation.

---

## 14. Acceptance criteria and definition of done

The mission is not complete until every applicable item is answered with evidence.

### Must-have for first successful NFC release

- [ ] Fresh live inventory confirms the active kernel, bound I²C driver and `/dev/sec-nfc` ABI.
- [ ] Firmware filename, checksum and provenance match; runtime state is separately reported.
- [ ] Exact Samsung initialization/protocol sequence is understood from matching source/trace or the unsupported assumptions are explicitly reported.
- [ ] Existing class collision workaround remains correct and class error handling is fixed if the pointer bug is confirmed.
- [ ] One privileged, least-privilege service owns the device.
- [ ] Device access uses exact verified ioctl ABI; no raw I²C or guessed ioctl.
- [ ] Real controller initialization and bounded transport have been proven.
- [ ] Real tag discovery works on physical S10+.
- [ ] A supported NDEF Text/URI record is read and independently checked.
- [ ] NFC Quick Settings enable/disable and Settings scan/status work.
- [ ] Default OFF is preserved.
- [ ] Disable/cancel/suspend/reboot releases the device safely.
- [ ] No regression to boot, Wi-Fi, USB/live console, touchscreen, lockscreen, GPU, audio, or other Nuxel services.
- [ ] Diagnostics never claim physical success from mocks.
- [ ] All targeted tests and repository gates have results recorded.
- [ ] A deployable full patch/drop-in ZIP and rollback instructions are delivered if requested by the project's normal workflow.

### Explicit non-goals / not to claim

- NFC payments, card emulation/HCE, bank cards, Wallet, transit passes, secure-element provisioning, credentials or eSE access.
- Broad MIFARE Classic support without genuine implementation and tests.
- Universal NFC tag compatibility.
- Generic Linux `neard` interoperability unless a compatible standard NFC adapter is actually registered and tested.
- 100% hardware readiness based solely on driver bind, firmware file presence, package install, or `/sys/class/nfc`.

---

## 15. Final engineering report required from the agent

At completion, write a report under the repo's established beta-finalization/live or hardware-bring-up documentation path. Include:

1. Executive summary and actual outcome.
2. Exact device model, kernel version/hash, source commit and image version.
3. Before/after architecture diagram.
4. Exact files changed and reason for each change.
5. Driver ABI findings and the relevant verified ioctl definitions.
6. Firmware identity, hash, provenance and runtime status (do not include the binary).
7. Protocol evidence source and any limitations/licensing notes.
8. Architecture decision record (userspace native service vs kernel NCI adapter) and why.
9. Service user, permissions, sandboxing and authorization design.
10. State machine and API schema.
11. NFC standards/tag types actually supported and not supported.
12. Unit, mock, integration, parser, UI, packaging and regression test results.
13. Physical tag test steps, anonymized results and owner-test status.
14. Performance/power implications (NFC OFF/idle/discovery where measured).
15. Build/deployment commands and rollback commands.
16. Remaining blockers, owner actions and risks.
17. Clear final verdict for each evidence layer: `SOURCE_VERIFIED`, `BUILD_VERIFIED`, `SERVICE_VERIFIED`, `TRANSPORT_VERIFIED`, `PROTOCOL_VERIFIED`, `HARDWARE_TAG_READ_VERIFIED`, `NDEF_READ_VERIFIED`, `UI_VERIFIED`, `OWNER_ACCEPTED`, `NOT_TESTED`, or `BLOCKED`.

Never use a single ambiguous “NFC working” badge if one of the physical layers remains untested.

---

## 16. Suggested execution order (follow this order unless evidence requires a documented deviation)

1. Read the full PWNAGE-53000 live report and inspect the current branch/dirty state.
2. Re-check the live S10+ kernel, controller, device node and firmware state read-only.
3. Read the exact pinned `sec_nfc.c` / `sec_nfc.h` and audit DT, ioctl, read/write/poll and class patch.
4. Inspect matching Samsung vendor NFC HAL/config/init and establish exact firmware/protocol initialization.
5. Write architecture decision record. Prefer a single native Nuxel service over premature generic stack installation.
6. Implement and test driver transport abstraction with exact ABI and a deterministic mock.
7. Implement controller initialization/protocol and tag discovery only from confirmed protocol evidence.
8. Implement safe NDEF parser and read-only tag API.
9. Add service lifecycle, permissions, OFF-by-default policy, suspend and crash handling.
10. Wire provider, bridge authorization, Quick Settings, status bar and Settings page.
11. Upgrade diagnostics and all offline/CI tests.
12. Build and deploy user-space layers safely; do not flash kernel or update controller firmware without approval.
13. Run physical tag tests on the actual S10+ and record exact evidence.
14. Run regression gates, produce full report and rollback procedure.

If the exact Samsung userspace protocol cannot be recovered, do not fake the missing stage. Finish all verified kernel/firmware/permission/diagnostic and service scaffolding work, then give a precise blocker identifying the missing protocol asset, source, or owner action. The purpose is a working NFC reader, but correctness and device safety take precedence over a green status icon.

**END OF FULL-PWNAGE-65000 SPECIFICATION**
