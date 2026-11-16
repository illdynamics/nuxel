# FULL PWNAGE — NUXEL S10+ SHANNON MOBILE NETWORKING

the full pwnage pack of mobile networkign with all you need is located in ./mobile

**Mission ID:** `PWNAGE-MOBILE-S5000AP`

**Target:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`), Exynos 9820, Samsung Shannon S5000AP LTE CP, Nuxel Fedora ARM64, downstream Linux `4.14.253`.

**Goal:** turn the physical SIM in this handset into working, truthful native cellular service: SIM detection, modem state, network registration, 2G/3G/4G access-technology reporting, mobile-data bearer/APN/IP/DNS, working Phone/Messages/Contacts integration where the network and carrier support it, robust Permission Manager policy, and live status-bar indicators. Deploy and verify on the actual phone. Continue through genuine fix/rebuild/reflash/retest cycles; never convert a blocker into a fake PASS.

**Owner setup:** handset starts in TWRP, connected over USB. The SIM remains inserted throughout this mission. Do not ask the owner to remove/reseat it. Build/deploy/flash scripts are in `./scripts`. When Nuxel boots, the required Wi-Fi SSH target is `root@192.168.178.167` using `~wicked/.ssh/wicked_wqn_id_rsa`.

---

## 0. Non-negotiable engineering and safety rules

1. **Inspect first.** Start by reading this prompt, `REFLASH-PLAN.md`, `REPORT-MOBILE-NETWORKING.md`, the exact-device S5000AP report `docs/Samsung S5000AP - Exynos 9820 Native Linux Modem Bring-up for Nuxel.md`, `configs/s10plus/modem/README.md`, `configs/nuxel/modem/README.md`, `configs/nuxel/modem/modem.json`, the current diagnostics/tests, Permission Manager capability catalogue, status-bar source, and the phone apps. Reconcile contradictions using current live evidence.
2. **Do not treat the plugin as the first missing layer.** The deep source audit says the existing 4.14.253 kernel already includes and has historically probed `sec_sipc_modem_if`, `modem_v1`, S5000AP control, SHMEM/SBD/SIPC5, mailbox signalling, `umts_boot0`, `umts_ipc0/1`, `umts_rfs0`, and `rmnet0…rmnet7`. The older `REPORT-MOBILE-NETWORKING.md` says its tested runtime had no `rmnet*` and no working transport. These are different evidence snapshots. Confirm the current boot; do not assume the transport is missing and do not assume the old captured nodes are live now.
3. **The real dependency order is:** kernel/DT transport (verify) → exact SM-G975F CP firmware/bootstrap (cbd replacement) → RFS/NV service (strictly constrained) → S10 SIPC5 radio backend → SIM/registration/signal → PDP bearer/rmnet/IP/DNS → ModemManager plugin → NetworkManager → status bar/Settings/apps. ModemManager comes after the backend works.
4. **No speculative CP boot.** Exact G975F `MODEM_ON`/boot/download/confirmation order, firmware container offsets/sections, `modem_firmware` structure use and secure-boot handshake are explicitly unresolved in the supplied audit. Do not guess ioctl order, structures, image offsets, addresses, checksums, command IDs or timeouts. Do not transplant Pixel, Exynos 5500, Exynos 9825, Qualcomm, G7 Power, Calliope audio, or unrelated Samsung board instructions.
5. **Protected data invariants:** never write/flash the `modem` partition. Never read/write EFS, EFSG, SEC_EFS, persist, NV, calibration, carrier provisioning, IMEI, RPMB, key storage, or any protected per-device radio data. Never format, erase, restore, clone or “repair” these areas. The current repo explicitly denies these paths. Do not add a bypass to the denylist. Do not perform raw AT mutations, APDUs, bootloader unlocks, modem NV updates, or modem firmware updates.
6. **Privacy:** never print, persist, send to logs, include in evidence or display IMSI, ICCID, IMEI, ESN, MEID, MSISDN, SPN, PIN or PUK. Do not collect SIM contents unless the owner explicitly invokes the Contacts app's SIM phonebook view. If SIM PIN entry is needed, use a secure on-screen prompt with a protected input buffer; never write PIN/PUK to disk, shell history or logs.
7. **No fabricated success:** a CP node is not a booted modem; `rmnetN` is not a bearer; an active network interface is not proof of Internet; an MM modem object is not proof of Voice/SMS; a local SIM mirror is not a SIM phonebook; a test/mock path is not a carrier path. Never draw green bars or `2G/3G/4G` from a config default, stale cache, Wi-Fi, ethernet, network route or fake fixture.
8. **No emergency testing.** Never dial an emergency number. Never place a real test call or send a chargeable SMS without an owner-approved non-emergency destination. Don't send bulk messages or run paid traffic loops.
9. **Preserve current user data and recovery.** Back up files before replacement. No userdata/rootfs overwrite, format, wipe, partition-table change or data migration without explicit owner approval. Inspect any script default that targets `userdata`. Keep a known-good rollback image and recovery console.
10. If a task cannot be completed safely because a required OEM binary, exact protocol trace, carrier setting or approval is missing, keep implementing independent layers and produce a precise blocked report. Do not claim `FULLY_DONE` until all acceptance tests actually pass.

## 1. Start state and device workflow

### 1.1 We start in TWRP over USB

- Assume the phone is already in TWRP and attached by USB when the task starts. Do not reboot just to re-enter TWRP.
- Verify `adb devices -l` shows exactly the expected one device. Do not act on multiple ADB devices.
- Capture an immutable baseline before changing anything: device model/codename, boot/recovery identity, current kernel and relevant boot logs, partition topology metadata, current boot image backup using only the repository's documented safe backup mechanism, and checksums. Do not dump protected modem/EFS partitions.
- Run the pack's read-only collector:
  `python3 tools/acquire-s10plus-modem-evidence.py --transport adb --profile twrp`
  (or copy it into the repo and use the local path). This collector is diagnostic only; it does not mount partitions or flash anything.
- In TWRP, only inspect currently available read-only evidence. Do not mount or remount arbitrary partitions. Do not run `dd`, `heimdall`, `fastboot`, `odin`, or hand-written raw block writes. Existing repo scripts are authoritative; read each script and its help before use.

### 1.2 Reflash policy

Cellular software will eventually need to enter the system image. A kernel/DT reflash is needed **only** if live evidence proves the current kernel lacks an essential S5000AP/CP transport feature or the separate NFC/USBNET batch needs a kernel change. The detailed S5000AP source audit suggests the current kernel already has the main transport drivers, so do not rebuild/flash the kernel merely because no ModemManager plugin exists.

If a kernel change really is required, batch it with the already-planned NFC and any independently verified USBNET kernel fixes in one coherent image, using only the existing Nuxel build/deploy/flash scripts under `./scripts` and the documented boot scripts. Do not invent alternate flashing commands.

Before flash:

- verify the exact device target is `beyond2lte` / SM-G975F / Exynos 9820;
- inspect the active slot/partition map rather than assuming A/B topology;
- build reproducibly and inspect the final boot image/DTB contents;
- compare kernel config and DT changes against the baseline;
- confirm the packer is passed the uncompressed `Image` if it expects raw `Image` (the repo previously had an Image.gz/raw-Image compatibility trap);
- create and verify rollback material; keep the old slot/image intact;
- produce a manifest listing every target partition and exact payload hash;
- prove that the manifest does not mention modem, EFS, EFSG, SEC_EFS, persist, param, carrier, RPMB, userdata, or other denylisted partitions.

### 1.3 After a flash/reboot — exact owner semantics

- **If the phone reboots and lands back in TWRP:** treat that as a failed Nuxel boot (bootloop, hang or crash). Do not call it success. Collect boot logs/last-kmsg if available, recovery logs, DTB/boot-image hashes and the exact failing stage. Find and fix the root cause, rebuild with a meaningful change, reflash through the existing repo script, and reboot again.
- **If the phone reaches Nuxel:** that is the successful boot transition. Verify the launcher/display/input and a healthy boot. Then connect to the root console over Wi-Fi SSH as shown below.
- Never repeat an identical failed flash blindly. Make at most three attempts for the same unchanged failure signature; each further attempt must have a documented root-cause correction. If the third attempt fails, preserve TWRP/recovery, stop the flashing loop, and report the evidence/root cause. Do not risk a destructive loop.

### 1.4 Nuxel SSH connection

Once the Nuxel userspace is up and Wi-Fi is available:

```sh
ssh -i ~wicked/.ssh/wicked_wqn_id_rsa -o IdentitiesOnly=yes root@192.168.178.167
```

Use that identity path and target. Never print, copy, upload, paste, or modify the private key. Do not use `StrictHostKeyChecking=no` as a workaround. If the path is not resolved by the host shell, locate the account's home directory and ask the owner only if the key genuinely cannot be found; do not substitute another key.

Continue all on-device userland bring-up and verification from the root console. The pack's SSH evidence collector is read-only:

```sh
python3 tools/acquire-s10plus-modem-evidence.py --transport ssh --profile nuxel \
  --target root@192.168.178.167 --key '~wicked/.ssh/wicked_wqn_id_rsa'
```

Do not turn Wi-Fi off while relying on this SSH session. The final Wi-Fi-off mobile-data proof must be run from a still-available USB/serial/local console or as an on-device test job whose output is saved locally before disconnecting SSH.

## 2. Phase 0 — exact baseline and live transport truth

Run and preserve the following (redacted) evidence:

```sh
uname -a
cat /etc/os-release
ls -l /dev/umts* /dev/cbd* 2>/dev/null
find /sys/class/net -maxdepth 1 -type l -printf '%f\n' 2>/dev/null | sort
zcat /proc/config.gz 2>/dev/null | grep -E '^CONFIG_(SEC_SIPC_MODEM_IF|SEC_MODEM_S5000AP|UMTS_MODEM_S5000AP|LINK_DEVICE_SHMEM|LINK_DEVICE_NAPI|CP_ZEROCOPY|CP_SECURE_BOOT|MODEM_IF_NET_GRO)='
dmesg | grep -iE 's5000ap|modem_probe|modemctl|modem_v1|shmem|SIPC|umts_|rmnet|cpif|mailbox'
mmcli --version 2>/dev/null
mmcli -L 2>&1
systemctl status ModemManager NetworkManager --no-pager
nuxel-modem-diag.sh status --json
```

Use the included `s5000ap-status` read-only probe:

```sh
make -C tools
./tools/s5000ap-status --json
```

It opens `/dev/umts_boot0` with `O_RDONLY` and issues only `MODEM_STATUS` (`_IO('o', 0x27)`). It must not issue any state-changing ioctl. `ONLINE` is a CP state, not proof of SIM/network/data.

Reconcile the runtime report with the exact S5000AP driver/capture audit. Write a new source-of-truth `REPORT-MOBILE-NETWORKING.md` with separate evidence timestamps and confidence levels: `PROVED_LIVE`, `PROVED_IN_SOURCE`, `HISTORICAL_CAPTURE`, `INFERRED`, `UNKNOWN`. Explicitly resolve whether `rmnet*` nodes and `/dev/umts_ipc*` are present in the current boot.

**Fixture correction:** the supplied archive contains empty zero-byte files named `samsung-shannon.so` in `modem-ready` / `modem-nosim` fixtures. These are placeholders only. Update tests so an empty file can never be considered an installed or loadable plugin. A real plugin must be an AArch64 ELF, resolve dependencies, load in ModemManager, match this phone, and create a real D-Bus modem object.

## 3. Phase 1 — OEM firmware/protocol source investigation

The archive does not contain a proven CP image or exact matching boot loader. Identify what the exact SM-G975F firmware build is from non-sensitive build metadata only. Do not dump the modem partition. Do not inspect EFS or protected modem storage.

Use only an owner-supplied or lawful official Samsung stock firmware package that precisely matches SM-G975F / `beyond2lte` and the device's baseband generation. Keep proprietary binaries local and out of the repo/ZIP. Verify package provenance and hashes. Do not assume a modem image from another CSC/model/generation is compatible.

Locate and reverse-engineer the **matching** Samsung `cbd` boot path and the exact kernel UAPI in the pinned 4.14.253 source. Evidence required before writing a loader:

- exact `MODEM_ON`, boot-on, download start, firmware transfer, boot done, boot confirm and online-state ordering;
- exact ioctl request numbers and structure layout/ABI width;
- firmware container/header/section offsets, lengths, address mapping and required checksums;
- secure-world/SMC interactions and required trust chain, with no bypass;
- expected RFS startup order and which operations are strictly required;
- failure state/timeouts and the exact way to stop safely.

Use a disassembly/trace of the matching stock `cbd` as the oracle, not an imagined protocol. Keep the first implementation `--dry-run`/trace-only until reviewed. The pack's `s5000ap-status` code is a read-only foothold, not a loader.

If matching firmware or a trustworthy boot sequence cannot be obtained, mark `BLOCKED_OEM_ARTIFACT` / `BLOCKED_PROTOCOL`. Continue with independent UI/permission/test improvements, but do not send guessed boot commands to the modem.

## 4. Phase 2 — CP boot service (native replacement for cbd)

Only after Phase 1 proves the boot procedure, create a narrowly scoped component such as `nuxel-cpboot` / `nuxel-cpbootd`.

Requirements:

- accept only the matched firmware source identified in the audited manifest;
- verify container metadata, exact model/build, length, section boundaries and SHA-256 before use;
- open only the expected `umts_boot0` control interface; fail if identity, kernel ABI, device node or CP state differs;
- run the verified sequence exactly; no fallback board IDs or alternate guessed offsets;
- have explicit bounded timeouts and return detailed failure stage/state;
- `--dry-run` emits the plan without issuing any ioctl;
- normal logs contain only non-sensitive image metadata/hash and CP state, never raw payload, SIM IDs or secret data;
- no automatic modem partition writes, no EFS access, no NV reset, no forced firmware update, no unbounded auto-reboot/boot loop;
- restart policy must not repeatedly power-cycle a crashing modem.

Verify with CP transitions and `MODEM_STATUS`, not a daemon `active` bit alone. Preserve kernel logs for the entire transition. Power/boot operations are allowed only through the verified S10 path and only because the owner requested mobile bring-up.

## 5. Phase 3 — RFS service and SIPC5 radio backend

Build the smallest testable protocol implementation before ModemManager. Prefer a separate library (`libsipc5-s5000`) and service (`nuxel-radiod`) with a single owner of each CP node; do not let the plugin, a diagnostic script and a second service independently open/read the same channel.

### 5.1 SIPC5 transport

Implement exact S10-specific frame encoding/decoding using evidence from the matching source and traces. Never infer that a QMI/MBIM/AT port exists. Validate every untrusted frame before parsing:

- minimum and maximum total length;
- header and payload length consistency;
- channel/format IDs;
- command group/command IDs;
- sequence IDs and outstanding-request correlation;
- fragment counts/fragment reassembly limits;
- integer overflows, alignment and endianness;
- string encoding/termination;
- unsolicited indication handling;
- timeout, cancellation, reconnect and CP crash behavior.

Fuzz malformed and truncated packets. The parser must not crash, allocate unbounded memory, block indefinitely, or leak secrets. Use deterministic captures as test fixtures; fixture values must be clearly labelled synthetic and must never be shown as live service.

### 5.2 RFS/NV boundary

`/dev/umts_rfs0` is a distinct protocol channel. Do not assume it is safe to pass arbitrary CP paths through to the host filesystem. Derive the actual request set and define a strict per-path allowlist with canonicalization, traversal refusal, size limits, ownership, atomic writes, and audit logs. Do not permit writes into EFS/EFSG/SEC_EFS, IMEI, calibration, NV, carrier or key-storage areas. Never copy those stores from another handset. If the modem refuses to boot without a forbidden operation, stop and report the exact missing OEM requirement rather than bypassing the protection.

### 5.3 Radio service API

Provide a documented, versioned API for status and operations. Every exposed field must carry an actual source and a monotonic update timestamp. Initial milestones:

1. CP ready/state;
2. SIM present / absent / PIN-required / locked / error from real protocol;
3. radio on/off and registration state;
4. access technology and signal quality;
5. operator identity only where requested by the UI and never via PII identifiers;
6. APN/PDP activation/deactivation and the associated rmnet device;
7. SMS send/receive;
8. voice only after call-control protocol and audio route are actually implemented.

Do not log IMSI/ICCID or the PIN. Do not expose raw commands to applications. Add explicit owner-confirmed handling for SIM PIN through a secure first-party UI only.

## 6. Phase 4 — real cellular data bearer

A data milestone is complete only when all of the following are true:

1. the SIM is detected from the radio backend (not a placeholder JSON file);
2. the CP is online and registered on the carrier network;
3. an APN is known from the carrier database or owner-approved setting;
4. a real PDP context activation response is received;
5. the correct `rmnetN` interface is associated with that context;
6. the assigned IP address/prefix, gateway (if provided), MTU and DNS are decoded from actual network response;
7. NetworkManager has a bearer/device/connection object representing that context, or a documented Nuxel integration uses the supported backend;
8. `ip route get` for an external IP chooses the cellular interface when Wi-Fi is disconnected;
9. DNS resolves through the cellular DNS configuration;
10. HTTPS or an equivalent safe Internet test succeeds while Wi-Fi is disabled.

Do not use static IP/DNS, fake DHCP, generic default routes or local test servers to claim cellular Internet. Do not route Internet traffic through Wi-Fi during the final mobile-data proof. Prevent a default-route race where both Wi-Fi and rmnet are present.

Use the carrier's correct APN/authentication/protocol. Keep APN credentials out of source, logs and screenshots. If APN is not provided by the carrier DB and cannot be safely inferred, request the required carrier APN from the owner instead of guessing.

## 7. Phase 5 — actual ModemManager Shannon plugin

After CP boot, RFS, SIM, registration and data operations work in the standalone backend, implement the real `samsung-shannon` ModemManager plugin.

- First identify the exact ModemManager build/version installed in Nuxel and build against that source/API. Do not compile against current upstream `main` and drop the binary into an older Fedora package ABI.
- Follow the plugin API used by the matching source package: port/device matching, plugin object creation and a vendor modem subclass for the operations that differ from generic 3GPP behavior.
- The plugin must match only this S10/S5000AP device and its real backend/ports. It must not probe arbitrary tty devices or send AT commands to a binary SIPC channel.
- Keep the SIPC/RFS implementation in a testable backend/library; the ModemManager plugin maps that backend to standard ModemManager interfaces. It must not duplicate raw CP channel readers.
- Add the narrowest udev hints/permissions needed. Do not grant app users direct access to modem device nodes.
- Implement asynchronous ModemManager operations with cancellation, timeouts and correct error mapping. Do not return static `OK` responses or export features the backend does not implement.
- Map actual SIM state, 3GPP registration, signal/access technology, SMS and bearer lifecycle. Expose Voice only if genuine voice call control is available.
- Prove AArch64 ELF, non-zero file, valid dependencies, successful plugin discovery, successful daemon load, correct device match, actual `mmcli -L` modem object and working `mmcli` queries/operations.
- Update package manifests/spec/build so the plugin survives a full image build and clean reboot. Do not place an empty `.so` in fixtures or mark a file name match as plugin availability.

## 8. Phase 6 — NetworkManager and mobile-data control

Integrate the modem/bearer cleanly with NetworkManager. Cellular connection profile is a normal Nuxel-managed profile; per-app Internet access remains controlled through existing Nuxel `network` capability/firewall policy, not by direct modem access.

- status updates come from ModemManager D-Bus and NetworkManager D-Bus, not scraping stale text;
- APN secrets are stored using the existing secrets mechanism, never world-readable config;
- radio enable/disable and mobile-data enable/disable controls are first-party Settings actions with explicit owner intent;
- reconnect/backoff must be bounded and must not continuously reboot the CP;
- on CP crash, SIM removal or bearer loss, clear stale route/address/DNS and UI state;
- disconnect must release the PDP context and remove cellular routing correctly;
- Wi-Fi remains independently managed and should not be altered until the final owner-visible test.

## 9. Phase 7 — Permission Manager integration (do this properly)

First audit `shell/nuxel-shell/nuxel-permissions/capabilities.json`, the alias map in `nuxel-permd.py`, `configs/nuxel/permissions/nuxel-settings.json`, existing portal/bridge methods, app sandbox profiles, AppArmor rules, udev rules, `verify-permissions.py` and all three native phone apps.

The archive already defines the following canonical permissions:

- `phone_status` — read-only status;
- `call` (alias `phone`) — place/answer calls;
- `sms` — send/receive SMS;
- `contacts` — local contacts database;
- `network` — app Internet access;
- `sms_send_raw` — reserved and intentionally unsupported.

Do not duplicate them under inconsistent names. Refine their descriptions/enforcement/status to reflect what truly works. Add only missing granular capabilities required by the actual UI/API:

| Capability | Scope | Consumers | Policy |
|---|---|---|---|
| `phone_status` | signal, registration state, access technology, coarse operator label | status bar, Settings, explicitly granted apps | read-only; never return IMSI/ICCID/IMEI/MSISDN/PIN/PUK |
| `cellular:manage` | radio and mobile-data on/off, APN/profile management | first-party Settings only | privileged, explicit owner action; deny third-party apps by default |
| `call` | place/answer/end normal calls | Nuxel Phone | high risk, explicit prompt/grant; only when real Voice backend exists |
| `sms` | send/receive SMS | Nuxel Messages | high risk, explicit grant; send succeeds only after real CP/MM ack |
| `contacts` | local address book | Contacts / approved apps | existing database policy |
| `sim_contacts:read` | read SIM phonebook | Contacts only initially | distinct high-risk read permission; user-visible import/preview |
| `sim_contacts:write` | write one contact to SIM | Contacts | separate high-risk write permission, per-action confirmation, never bulk overwrite |
| `network` | ordinary app network sockets | applications | existing cgroup/firewall policy; no `/dev/umts_*` device access |

Implementation requirements:

- Add capability definitions and canonical aliases in the authoritative capability registry; do not create a second permission catalogue in the PWA.
- Ensure Permission Manager lists the entries under a Telephony/Connectivity group with clear purpose, risk and current availability. Disabled/blocked capability should say why; do not look enabled when the backend is missing.
- Default deny for third-party callers. Do not silently pre-grant cellular control, SMS, call or SIM contacts to all apps.
- Keep `sms_send_raw` refused/unsupported. Do not expose arbitrary AT, SIPC, NV or APDU access through a permission.
- Route native app requests through the permission portal/bridge. Audit direct GDBus access to `org.freedesktop.ModemManager1`; deny direct app access where the permission broker should mediate. System ModemManager and radiod daemons receive only the system-level access required.
- Ensure permission checks distinguish `contacts` local store from `sim_contacts:read` / `sim_contacts:write` physical SIM actions.
- Revoking permission must stop new operations and remove subscriptions/handles where practical. Denials must be visible and logged without private identifiers.
- Update manifests for Phone, Messages, Contacts, Settings and status bar; include the minimum capabilities required.
- Add tests for granted, denied, revoked, unknown capability, alias resolution, persistence, app identity, portal result and direct-D-Bus bypass.
- Update tests/report to reflect 4.14 limitations: AppArmor/DAC/portal may be partial; never claim a kernel-enforced isolation boundary that does not exist.

## 10. Phase 8 — Phone, Messages and Contacts apps

Keep the three apps using the shared `nuxel-phone-data` model and preserve all local history/contacts. Back up stores before migrations. Remove any misleading local/mock status while retaining a clearly labelled offline mode.

### Phone / Dialer

- Discover actual ModemManager Voice interface and implement call lifecycle only if present and backed by real CP support.
- A modem object alone does not mean `voice_calls=1`. Change capability logic so calls are true only after a Voice interface and its required operations are exposed and tested.
- implement dialing, incoming-call notification, answer, reject, hang-up, call state, duration and shared call log; attach audio routing only when the S10 voice/audio path is proven.
- no emergency test calls. Ask owner for an approved non-emergency test contact before a real call.

### Messages

- Use real ModemManager Messaging interface backed by Shannon SMS protocol. Send success only after a modem send acknowledgement; receive on the real Added/new-message event and persist it atomically.
- If the backend is unavailable, keep messages as `queued`/`local-only` and visibly say “not sent — modem unavailable”. A bridge mock must never be labelled sent.
- Implement long-message/concatenation, sender resolution, duplicate handling, timestamps, failure/cancel, and lifecycle cleanup. Do not dump message contents into logs.
- Ask owner for an approved non-emergency destination before sending any real test SMS; do not initiate paid messages without approval.

### Contacts and SIM phonebook

- The current `sim_store`/SIM mirror is local simulation, not the physical SIM. Clearly identify it as such until real ModemManager SIM phonebook support is present.
- Implement SIM phonebook list/read/write through the verified SIM API only. On open, report `SIM not accessible` until actual capability is proven. For import, preview and merge only; do not delete/overwrite local contacts. For write, confirm one contact at a time, show SIM target, and preserve all other SIM entries.
- Test name/number Unicode, international E.164 numbers, duplicate numbers and contact resolution from Dialer/Messages. Do not collect phonebook records in modem diagnostic archives.

## 11. Phase 9 — top-bar and Wi-Fi/mobile indicator redesign

Inspect and extend the existing implementation, especially:

- `pwa/nuxel-home/index.html` (`#status-signal`, `#status-wifi` already exist);
- `pwa/nuxel-home/js/status-bar.js` (`_renderSignal`, `_renderWifi`, provider update and `_publishCanonicalModel`);
- `pwa/nuxel-home/css/status-bar.css` (signal bars and Wi-Fi mask styles);
- `pwa/nuxel-common/statusbar-icons.js` and `/etc/nuxel/display/statusbar-icons.json`;
- bridge status producer and any native top-bar adapter consuming `statusbar-model`.

**Do not create a duplicate cellular slot.** The existing `status-signal` element is the cellular indicator; evolve it to the new design and preserve user visibility preferences/safe-zone layout.

### Cellular icon requirements

- Render five ascending bars (four is acceptable only if the existing geometry makes five impossible; default to five) with actual signal quality levels.
- **Connected/registered with an actual signal sample:** bars are green; fill 1–5 according to real signal quality. Add a compact `2G`, `3G` or `4G` label beside/under the bars based on actual `access_technology` from ModemManager/SIPC: GSM/GPRS/EDGE → `2G`; UMTS/WCDMA/HSPA → `3G`; LTE → `4G`. The S10+ is not 5G-capable; never show 5G.
- **Not registered / no SIM / searching / radio off / backend unavailable / unknown:** show a white cellular glyph with a clearly visible red diagonal strike; no green bars and no fake technology label. Set accessible `aria-label` and `title` with the exact state.
- Green is allowed only when the backend confirms registration and signal quality is current and valid. Clear the state immediately on lost registration, SIM state change, timeout, CP crash, or modem removal. No stale green grace period.
- Signal bars must be derived from the raw/normalized real signal source and clamped. Do not map an unknown/null value to 0% and call it poor signal; distinguish unknown from zero.

### Wi-Fi icon requirements

- Replace/extend the single flat mask if necessary so the Wi-Fi glyph can express actual link quality (for example, progressively filled 1–3 arcs or another clearly legible signal representation).
- If Wi-Fi is **enabled but not connected**, display a white Wi-Fi outline/glyph with no active signal arcs/bars and a red diagonal strike. This state must be visually distinct from radio disabled and from Internet-unverified.
- If connected, show actual NetworkManager AP signal quality (not generic default-route reachability) through the Wi-Fi arcs/strength levels. A connected Wi-Fi link without verified Internet must remain distinguishable from verified Internet.
- If Wi-Fi radio is off/unavailable/unmanaged, follow Nuxel's existing visibility policy consistently; do not claim disconnected/connected based on missing data.
- Use actual Wi-Fi D-Bus/AP strength values. If the provider does not supply a current reading, render unknown rather than an invented strength.

### Shared model / UI QA

- Extend the canonical status model with explicit fields for `cellular_state`, `cellular_signal_quality`, `cellular_access_technology`, `wifi_state`, `wifi_signal_quality`, `wifi_internet_state`, and provider timestamps/source where needed. Preserve backwards-compatible readers or version the schema.
- Status bar must never infer cellular from Wi-Fi/ethernet or Wi-Fi strength from overall network reachability.
- Ensure bar update and CSS do not cause overlap with battery/time icons, notch/safe zones or Quick Settings. Update service worker cache/version if the project requires it.
- Add deterministic UI tests for: no SIM; SIM inserted but no registration; searching; registered with weak/medium/strong signal; LTE/UMTS/EDGE label mapping; modem removed; CP crash; stale data timeout; Wi-Fi off; Wi-Fi enabled/disconnected; Wi-Fi connecting; Wi-Fi connected at weak/medium/strong RSSI; Wi-Fi connected without Internet; Wi-Fi Internet verified. Test all supported states and screenshots at the phone's real resolution.
- Use the actual top bar on the phone. Do not consider a desktop browser screenshot alone live verification.

## 12. Phase 10 — final owner-visible mobile-only test

Only attempt this after the backend, registration and bearer are proven and the owner has been informed of any possible carrier data charges.

1. Ensure root/USB/serial console is available independently of Wi-Fi. If the SSH session is Wi-Fi-only, do not toggle Wi-Fi yet.
2. Record active bearer, rmnet device, mobile IP/prefix, DNS source, routing table, registration state, signal quality and access technology (redact identifiers and secrets).
3. Start a local verification job/script on the handset and make sure its output is saved to a timestamped report before disconnecting SSH.
4. Turn Wi-Fi radio off using NetworkManager/Settings (not by removing drivers or using raw rfkill hacks). Verify `wifi_enabled=false` and that no Wi-Fi default route remains.
5. Verify `ip route get` to a public test IP uses the cellular rmnet interface. Verify DNS and an HTTPS request succeed over the mobile bearer. Keep request volume minimal.
6. On the phone screen, open a normal web page or Nuxel connectivity test app to show the real mobile Internet while Wi-Fi is off. Capture a screenshot or short on-device evidence with no private identifiers.
7. Verify top-bar cellular bars and `4G` (or 3G/2G actually negotiated) are green and match the live values; Wi-Fi icon must show off according to the Nuxel radio-off policy. For the specific **enabled-but-disconnected** state, separately test with Wi-Fi radio enabled and unassociated: white glyph, no active arcs, red strike.
8. Only leave Wi-Fi disabled at the end if mobile Internet is working and the owner-visible screen proof is ready. If cellular fails, restore Wi-Fi so the device remains usable and capture the real failure.

## 13. Acceptance test matrix

### Hardware / CP

- Exact model/kernel confirmed.
- S5000AP driver probe observed live.
- `/dev/umts_boot0`, `umts_ipc0`, `umts_ipc1`, `umts_rfs0` node ownership/type/mode recorded.
- `MODEM_STATUS` read-only state valid and transitions are evidenced.
- CP boot repeatable after a normal cold boot/reboot without an uncontrolled daemon loop.

### SIM / registration / data

- Physical SIM is reported present from a real protocol source while left in the tray.
- PIN-required/locked/absent/ready states are correctly represented without exposing PIN or identifiers.
- Network registration state and operator (if exposed) come from real modem responses.
- Signal quality and 2G/3G/4G access technology come from real modem data.
- APN/PDP activation and deactivation actually work.
- Correct rmnet interface receives traffic; mobile route and DNS work.
- Wi-Fi disabled; HTTP(S) Internet works over cellular only.
- Data loss/reconnect/CP restart clears and restores state correctly.

### ModemManager / UI / permissions

- Real AArch64 plugin loads in the installed ModemManager; `mmcli -L` shows the real device.
- `mmcli` reports SIM, 3GPP registration, signal, bearer, and Messaging only when each is supported.
- NetworkManager shows an active cellular connection and correct device.
- Status-bar 2G/3G/4G and signal bars match measured quality; disconnected state has white glyph/red strike.
- Wi-Fi actual strength is visible when connected; enabled/disconnected is white/no arcs/red strike.
- Permission Manager defaults to deny and correctly allows/revokes `phone_status`, `cellular:manage`, `call`, `sms`, `sim_contacts:read`, `sim_contacts:write`, `contacts`, and `network` as applicable.
- No app can directly access CP nodes or bypass the portal.

### Phone-family apps

- Phone app discovers real Voice interface if it exists; app does not claim working calls solely because a modem exists.
- Messages receives real incoming SMS and sends a real owner-approved test SMS with confirmed modem ACK; local/mock messages never claim sent.
- Contacts reads actual SIM phonebook when allowed; one-contact write works only after user confirmation; local contacts remain intact.
- Shared contacts/call/message history survives app restarts and reboot.
- If Voice/VoLTE is not implemented or unavailable from the operator/network, mark it separately as `BLOCKED_VOICE/IMS`; do not claim complete telephony. Do not let this block a separately verified mobile-data result.

### Safety / privacy

- No protected partition touched; no modem partition write; no EFS/NV/calibration access.
- No PIN/PUK/IMSI/ICCID/IMEI/MSISDN in logs, DBus properties exposed to ordinary apps, report, screenshot or manifest.
- No dummy plugin, fake modem, fake SIM, fake registration, fake APN success or fake data route.
- No test emergency calls or chargeable messages without explicit approval.

## 14. Build, test, deployment and repair loop

Work in small reviewable commits/stages. At each stage:

1. implement source and deterministic tests;
2. compile with project warning/error policy and run static/security checks;
3. run parser/fuzzer/fixture tests;
4. update package specs/manifests, service units, udev, permission definitions and integration tests;
5. deploy userspace over SSH with backup/rollback first;
6. inspect live service logs and hardware state;
7. change kernel only when live evidence proves it necessary, then integrate with the planned one-flash kernel batch;
8. after any flash, apply the TWRP-vs-Nuxel success/failure rule in §1.3;
9. repeat for every failure with a new root-cause fix, not the same failed command;
10. reboot once after final installation and repeat critical smoke checks.

Do not replace the running status bar or MM daemon with an untested binary without preserving the old file/config and service restart command. Do not enable the custom plugin until its device match and all capability checks pass.

## 15. Required deliverables

- `REPORT-MOBILE-NETWORKING.md` — updated source/live findings, first failing stage, confidence labels, firmware provenance and all limitations.
- `docs/S5000AP-BOOT-PROTOCOL.md` — exact G975F boot transaction with evidence and no guessed fields.
- `docs/SIPC5-RFS-PROTOCOL.md` — validated frame layouts, channels, commands, RFS whitelist and test captures (sensitive values redacted).
- `libsipc5-s5000` and `nuxel-radiod` source + unit tests/fuzz tests.
- `nuxel-cpboot` source + dry-run tests and a documented device test procedure.
- Real `samsung-shannon` ModemManager plugin source, packaging and load/device-match tests (or a precise blocker if upstream backend is not yet proven).
- NetworkManager cellular connection integration and a no-Wi-Fi route/DNS verification script.
- Updated Permission Manager capability catalogue, alias map, first-party policy, sandbox/AppArmor/udev rules and regression tests.
- Updated Phone/Messages/Contacts integrations and persistent data migration tests.
- Updated top-bar icons, status model, CSS/JS tests, cache version and phone screenshot proof.
- `REFLASH-PLAN.md` row updated with exact payload/partition and whether a kernel change is truly required.
- `PWNAGE-MOBILE-REPORT.md` with PASS/BLOCKED results, test output, live evidence paths, SHA-256 hashes, rollback instructions and owner actions.

## 16. Final verdict rules

Allowed truthful outcomes:

- `PASS_CELLULAR_DATA`: a real bearer and Internet work with Wi-Fi disabled.
- `PASS_SIM`: physical SIM state read from real backend.
- `PASS_SMS`: actual incoming and owner-approved outgoing SMS with acknowledgement.
- `PASS_SIM_PHONEBOOK`: real SIM phonebook read/write tested under permission prompts.
- `PASS_VOICE`: genuine call setup/answer/end and audio verified on this carrier/network.
- `BLOCKED_OEM_ARTIFACT`, `BLOCKED_PROTOCOL`, `BLOCKED_RFS`, `BLOCKED_KERNEL`, `BLOCKED_CARRIER`, `BLOCKED_VOICE_IMS`, or `NEEDS_OWNER_TEST` with the exact missing item and evidence.

`FULLY_DONE` is allowed only when every capability the mission claims is proven live and the reports, tests, permission enforcement, top bar, apps, and reboot behavior all agree. A compiled plugin, a D-Bus modem object, or a green icon alone is never sufficient.

**Execute this mission end-to-end. Start with TWRP USB evidence collection. Do not ask the owner to repeat already-given device/SSH details. Keep the SIM inserted. Continue fixing every independently actionable issue; stop only at a real external/owner approval boundary or when the complete acceptance matrix passes.**
