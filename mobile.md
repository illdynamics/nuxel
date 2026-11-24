# LTE OR DIE — QRONIQQLES IV
## THE RFS RESURRECTION PROTOCOL
### STAGE 06 — FINAL MODEM, LTE DATA, SMS & VOICE COMPLETION

**MISSION: Make the Samsung SM-G975F (beyond2lte / Shannon S5000AP) a fully functional Nuxel Linux phone with working LTE, cellular Internet, SMS and voice telephony.**

There is one objective: physically working Stage 06.

No research-only rounds. No architectural essays. No speculative success. No endless reports describing the same blocker.

**EXECUTE → IMPLEMENT → BUILD → TEST → DEPLOY → OBSERVE → FIX → RETEST.**

Continue until the actual hardware acceptance criteria pass.

A genuine external dependency must be identified honestly, but never declare something unrecoverable before exhausting the available software, firmware, transport and hardware avenues.

---

# PART I — PRESERVE AND ESTABLISH BASELINE

Repository: `~/x/nuxel`

Target: Samsung SM-G975F, beyond2lte, Shannon S5000AP.

Management connection: ZeroTier, currently known as `10.11.12.99`.

Previously used branch: `cs/mob-round35-stage06`.

Important known assets:

- `./packs/SAMFW.COM_SM-G975F_TNL_G975FXXS9DTK9_fac/`
- `./packs/android_device_samsung_beyond2lte-lineage-23.2/`
- `./.vendor-ro/`

Do not assume previous commit hashes or branch state remain current.

FIRST:

1. Inspect Git HEAD, branch, status, staged changes and untracked files.
2. Preserve all existing modifications, including `mobile.md`.
3. Create a recoverable checkpoint.
4. Inspect the complete Stage 06 implementation.
5. Run the existing test suite.
6. Establish SSH connectivity through ZeroTier.
7. Verify CP ONLINE, SIM READY and KPN registration.
8. Record current RFS, IPC41, data-call and modem states.
9. Verify Wi-Fi, USB, ZeroTier, SSH and radiod.

Never destroy existing work or interrupt the management connection.

# PART II — THE IMMEDIATE BREAKTHROUGH
## RFS DIRECTIONALITY AND AP-ORIGINATED NV OPERATIONS

This is the first engineering priority.

Recent investigation established:

- `rfs_proto.c/h` implements RFS parsing.
- `rfs_respond.c/h` implements the CP-request response path.
- `rfs_policy.c/h` controls permitted operations.
- `radiod.c` integrates transport and protocol handling.
- RFS operation `0x15` (`NV_WRITE_ALL`) is currently explicitly refused.
- Previous investigations recovered the Samsung NV processing operations and their underlying write semantics.
- The physical item-360 representation remains insufficiently established.

**Do not confuse a CP-originated RFS request with an AP-originated RFS transaction.**

Investigate the actual transaction architecture.

### Mandatory actions

1. Trace every RFS request and response direction in the current implementation.
2. Determine how AP-originated messages are framed and transmitted, if supported.
3. Inspect the SIPC transport and FMT/RFS integration.
4. Determine whether the modem accepts AP-originated NV operations.
5. Recover the actual command identifiers from vendor code and firmware.
6. Establish transaction IDs, response correlation, framing, lengths and error handling.
7. Determine whether `RFS_NV_WRITE_ITEM` is genuinely an exposed operation or merely a name used in documentation.
8. Distinguish `NV_WRITE`, `NV_WRITE_ALL`, buffering and restore semantics.
9. Identify whether the AP must initiate a transaction or respond to a CP request.
10. Implement the missing transaction mechanism where supported.

Inspect the actual Samsung implementations in `libsec-ril.so`, matching firmware and recovered CP binaries.

Do not invent opcodes, directions or transaction formats.

### Required result

A reproducible, independently verified understanding of the NV transaction path, including a successful read-only transaction against the live modem where possible.

Add regression tests for every recovered protocol contract.

# PART III — COMPLETE ITEM 360 / QBR CONTRACT

Known information:

- Persistent key: `NASU.LTE.ATTACH.APN.INFO`
- Dual-SIM variant: `DS_NASU.LTE.ATTACH.APN.INFO`
- Previously recovered numeric ID: `360` (`0x168`)
- Expected KPN APN: `internet`
- NV write semantics recovered from vendor code: seek, write, fsync and MD5 handling.
- Existing modules: `nv_items.{c,h}` and `qbr_items.{c,h}`.

However, do not confuse a recovered numeric ID with a fully recovered physical storage contract.

### Actions

Recover and independently validate:

1. Numeric ID to registry mapping.
2. Item descriptor.
3. Physical storage offset.
4. Payload length.
5. APN field representation.
6. QBR record framing.
7. Alignment and padding.
8. Serialization and deserialization.
9. MD5 handling.
10. RFS transaction representation.
11. Read-back behavior.
12. Persistence across reboot.

Inspect:

- CP `modem.bin`.
- `modem_debug.bin.lz4`.
- Samsung firmware TOC.
- MAIN and BOOT regions.
- QBR and NV handlers.
- `PDNMGR_SET_STATELESSINFO_ATTACHINFO`.
- `NASU.LTE.ATTACH.APN.INFO`.
- Existing extracted vendor libraries.
- Matching Samsung firmware and source.

Use the TNL CSC to validate carrier configuration.

**Important:** The current `nv_apn_record` unit tests do not independently prove that the generated structure matches the physical QBR record.

Recover a genuine golden vector or equivalent authoritative evidence.

# PART IV — IMPLEMENT THE COMPLETE NV PROVISIONING PATH

Once the physical record contract and transaction mechanism are independently established:

Implement the missing provisioning path.

Requirements:

- Correct item ID.
- Correct descriptor.
- Correct physical offset.
- Correct serialization.
- Correct MD5 integrity.
- Complete original backup.
- Backup integrity verification.
- Read-before-write verification.
- Explicit transaction logging.
- Post-write read-back.
- Byte-for-byte verification.
- Rollback capability.
- No modification of unrelated NV items.

Protect IMEI, RF calibration, radio configuration, SIM configuration, boot configuration and unrelated NV records.

Never guess offsets or write fabricated records.

Do not modify persistent modem storage until the complete contract is proven and the backup and rollback path has been tested.

Then execute the verified provisioning operation and establish the initial-attach APN.

# PART V — GET THE ACTUAL LTE DATA PATH WORKING

After provisioning, immediately investigate live modem behavior.

Do not assume the APN was the only failure.

Capture actual responses and rejection causes.

Implement and verify:

1. CP initialization.
2. SIM initialization.
3. Network registration.
4. Packet-switched registration.
5. LTE attach.
6. EPS bearer establishment.
7. Default data-call management.
8. Cellular interface creation.
9. Address assignment.
10. Routing.
11. DNS.
12. HTTPS.
13. Disconnect.
14. Reconnect.
15. Recovery after network loss.
16. Reboot persistence.

Use the actual Samsung modem interfaces and recovered IPC41 commands.

Implement missing Nuxel-side functionality rather than introducing Android framework dependencies.

Test cellular connectivity independently of Wi-Fi.

Verify actual route selection and interface usage.

# PART VI — SMS AND VOICE

Once LTE data works, continue directly into telephony.

Do not stop at an operational data connection.

### SMS

Implement:

- Modem SMS transport.
- Outgoing SMS.
- Incoming SMS.
- PDU encoding/decoding where required.
- Message storage.
- Delivery reporting.
- Notifications.
- Error handling.
- Recovery after reconnection.

### Voice

Implement:

- Incoming calls.
- Outgoing calls.
- Answer and reject.
- Hang-up.
- Call-state reporting.
- Audio routing.
- Microphone routing.
- Call recovery.
- IMS/VoLTE integration where supported.

Investigate actual KPN and device support for the required voice technology.

Do not simulate SMS acceptance or call states.

If a carrier-side limitation exists, establish it with actual evidence and complete every software-controlled component.

# PART VII — FIX EVERYTHING DISCOVERED

This is mandatory throughout the campaign.

Whenever a failure occurs:

1. Reproduce it.
2. Capture logs and actual responses.
3. Identify the root cause.
4. Fix the underlying implementation.
5. Add a regression test.
6. Rebuild.
7. Rerun affected tests.
8. Rerun the complete suite.
9. Deploy the corrected implementation.
10. Verify actual hardware behavior.

Do not merely document defects.

Do not repeatedly retry unchanged failing operations.

Do not assume earlier reports are infallible.

Revalidate previous assumptions against actual evidence.

Acquire matching firmware, vendor binaries, debug artifacts and public source where they materially help resolve a specific implementation blocker.

# PART VIII — BUILD AND DEPLOYMENT

Every implementation must pass:

- Host compilation with `-Wall -Wextra -Werror`.
- Full unit test suite.
- New regression tests.
- 3,000-iteration fuzzing.
- ASan/UBSan.
- AArch64 cross-compilation.
- Actual target execution.
- Live modem verification.

Use `set -o pipefail` for build pipelines.

Do not mistake a successful downstream `head` command for a successful compilation.

Deploy with backups and rollback.

Keep these working:

- `wlan0`
- `usb0`
- ZeroTier
- SSH
- radiod
- Existing Nuxel services

No unnecessary rebooting.

TWRP flashing is permitted only when a verified requirement genuinely necessitates a partition modification and a tested recovery path exists.

# PART IX — PHYSICAL ACCEPTANCE

Stage 06 is complete only when every applicable criterion has been physically demonstrated.

| Acceptance criterion | Required result |
|---|---|
| CP initialization | PASS |
| SIM READY | PASS |
| KPN registration | PASS |
| PS registration | PASS |
| LTE attach | PASS |
| EPS bearer | PASS |
| Cellular IP | PASS |
| Cellular routing | PASS |
| Cellular DNS | PASS |
| Cellular HTTPS | PASS |
| Outgoing SMS | PASS |
| Incoming SMS | PASS |
| Outgoing voice | PASS |
| Incoming voice | PASS |
| Call audio | PASS |
| Disconnect/reconnect | PASS |
| Reboot persistence | PASS |
| Wi-Fi regression | NONE |
| USB regression | NONE |
| ZeroTier/SSH regression | NONE |
| Full regression suite | PASS |

Every network test must identify the actual interface and route.

SMS and voice must be tested using genuine network interactions.

No mocks, fabricated responses or simulated connectivity.

# PART X — EXECUTION DISCIPLINE

- Actions first.
- No research-only rounds.
- No half implementations.
- No premature blocker declarations.
- No blind NV writes.
- No speculative protocol structures.
- No unnecessary flashing.
- No destructive Git operations.
- No loss of existing work.
- No Android dependencies.
- No disabling management connectivity.
- No fake acceptance.

Do not stop at the first new blocker.

Do not stop after implementing the RFS transaction mechanism.

Do not stop after provisioning the APN.

Do not stop after LTE data works.

Continue into SMS, voice, audio and reboot persistence.

Do not spend the entire round writing reports. Spend it implementing and testing.

# FINAL DELIVERABLES

When physically complete, deliver:

1. Complete Stage 06 source.
2. All necessary modem drivers and supporting modules.
3. Correct NV provisioning implementation.
4. Reproducible builds.
5. Complete passing tests.
6. AArch64 target binaries.
7. Actual LTE connectivity.
8. Working cellular Internet.
9. Working incoming and outgoing SMS.
10. Working incoming and outgoing voice.
11. Working call audio.
12. Reboot-persistence evidence.
13. Regression evidence.
14. Git commits.
15. Updated documentation.
16. Final engineering acceptance report.

The report must contain actual command output, timestamps, modem responses, interface states and test results.

Only after every physical acceptance criterion passes may `./wonqed4real` be created.

---

# FINAL DIRECTIVE

**LTE OR DIE. QRONIQQLES IV. THE RFS RESURRECTION.**

We have already recovered IPC41, SIPC5, substantial RFS functionality, the initial-attach APN identity, NV item ID 360, MD5 behavior and much of the Samsung modem architecture.

Now finish the missing transaction path.

Recover the real QBR representation.

Provision the modem correctly.

Establish the EPS bearer.

Bring up cellular Internet.

Finish SMS.

Finish voice.

Fix every newly discovered defect and retest until the physical acceptance criteria pass.

**Do not return another report telling me what needs to be done. Do the work.**

The objective is a fully functional Nuxel phone on the actual SM-G975F.

The only valid completion claim is a physically verified Stage 06 PASS.

---

# ROUND 39 STATUS APPENDIX (2026-11-24)

## Live baseline (re-verified)
- All 20+ modem IO-devices present: /dev/umts_ipc0, /dev/umts_rfs0, /dev/umts_boot0,
  /dev/umts_dm0, rmnet0..7, /dev/multipdp, /dev/s5p-smem. (Round <34 "malformed DTB"
  blocker is RESOLVED — device tree is correct.)
- radiod running `--write-enable --arm-data-path`, CP ONLINE (code 4), SIM=1,
  PS REGISTERED_HOME (PLMN 20408 KPN), live RSSI DISP frames.
- Data FSM runs the full LTE attach sequence and reaches DATA_CALL:
  `{"phase":"DATA_CALL","gen_result":0,"call_state":3,"pdp_state":0}`
  (GPRS_CALL_STATUS state=3 == default EPS bearer NOT established).

## Root cause (byte-level, now definitive)
NV item 360 (NASU.LTE.ATTACH.APN.INFO, id 0x168) is EMPTY in the persistent NV store.
Verified: "internet"/"kpn" absent from nv_data.bin (1 MiB) AND .nv_core.bak (546,304 B);
name_ptr 0x404793fc/0x404793e0 absent; nv_data.bin MD5 sidecar stale
(stored c665d4… != live f9f847…). The physical offset of item 360 is computed at
runtime by the vendor cbd NvCoreInfo list ([this+872]) which Nuxel does not run.

## Recovered + implemented (round 39, committed)
- RFS NV transaction contract (byte-exact from libsec-ril.so build 60889dd7):
  - NV item record: [u8 op][u8 seq][u8 mode][u32 offset@6][u32 length@10][data@14]
    (ProcessNvWrite/ProcessNVWriteAll/ProcessNVRead; 0x80000 length clamp).
  - AP->CP NV response: 15 bytes [u32 len][u8 type=2][u8 op][u8 result][u32 detail].
  - Storage: lseek(nv_data.bin,offset)+write+fsync + MD5 sidecar recompute.
    NO asymmetric signing (round-38 correction confirmed).
- New pure module `rfs_nv.{h,c}` + golden regression tests; wired the recovered
  15-byte NV response + (offset,length) parse into radiod dispatch_rfs (fail-closed,
  no blind write). AArch64 cross-compile clean on device.

## Remaining external dependency (honest)
Item 360 offset+length originate from vendor `cbd` (/vendor/bin/cbd -d -tss310 -bm
-mm -P .../by-name/radio, serving /mnt/vendor/efs/nv_data.bin via CP_REQ_NV_DATA).
cbd is an Android cpboot-daemon NOT running on Nuxel. Unblock requires either (a)
a known-good identical SM-G975F/KPN nv_data.bin with "internet" attach APN, or (b)
running cbd under an owner-approved, CP-safe controlled trial to obtain the runtime
item->offset map. No blind NV write is authorized until then.

`wonqed4real` NOT created (correct: LTE bearer not established).
