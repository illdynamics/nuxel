# NFC completion report — Galaxy S10+ (`beyond2lte`)

## 1. Executive verdict

`BLOCKED_KERNEL` at the **kernel NFC subsystem** stage. The controller transport `/dev/sec-nfc` exists, the S3NRN82 firmware is present and hash-verified, and `nuxel-nfcd` is running with NFC **OFF**, but the kernel NFC class/netlink is not populated (`/sys/class/nfc` has no entries) and no protocol exchange or physical tag read has been verified.

## 2. Target identity

- SM-G975F `beyond2lte`, Exynos 9820.
- Controller: Samsung `sec-nfc` at I2C address `0x27`, live I2C device `/sys/bus/i2c/devices/7-0027`, name `sec-nfc`.
- Silicon identity: **S3NRN82** per the verified firmware filename and repo policy (`configs/nuxel/nfc/nfc.json`). “S3FWRN5-family” is a driver-family label in older comments; it is not proof of a different part.
- Transport: Samsung `sec_nfc` misc character device `/dev/sec-nfc` (raw vendor transport, not a generic NCI adapter).
- Confidence: **high** for bus/transport/firmware; **medium** for exact silicon revision until a chip-ID read is proven.

## 3. What already exists

| Area | Source/path |
|---|---|
| Policy | `configs/nuxel/nfc/nfc.json` (S3NRN82 path/hash, OFF-by-default, tag procedure) |
| Native daemon | `services/nuxel-nfc/nuxel_nfc/{daemon,transport,nci,ndef,abi,inventory}.py` |
| Service | `services/nuxel-nfc/systemd/nuxel-nfcd.service` |
| Bridge provider | `services/nuxel-bridge/src/nfc_provider.py` |
| Udev | `services/nuxel-nfc/90-nuxel-nfc.rules` |
| Diagnostics/tests | `tools/s10plus/a33/nuxel-nfc-diag.sh`, `tests/pwnage65000` |
| Firmware | `/lib/firmware/nfc/sec_s3nrn82_firmware.bin` (also `/vendor/firmware/nfc/...`) |

## 4. Latest evidence

| Check | Result | Tier |
|---|---|---|
| `nuxel-nfc-diag.sh status --json` (after policy refresh) | `controller=chardev:/dev/sec-nfc`, `firmware=found:/lib/firmware/nfc/sec_s3nrn82_firmware.bin`, `subsystem=down`, `stack=client:nuxel-nfc`, `state=BLOCKED_KERNEL`, `first_failing_stage=subsystem` | `PASS_DEVICE_RUNTIME` |
| I2C identity | `/sys/bus/i2c/devices/7-0027` name `sec-nfc` | `PASS_DEVICE_RUNTIME` |
| Character device | `/dev/sec-nfc` (`10:107`) | `PASS_DEVICE_RUNTIME` |
| Firmware file | 151,852 bytes, SHA-256 `d315cd8bf47d90b7537aa978cb52299b7f2a56e8748588fb980b83ee823c0bfb` | `PASS_DEVICE_RUNTIME` |
| Kernel NFC class | `/sys/class/nfc` exists but has no entries | `PASS_DEVICE_RUNTIME` |
| Daemon state | `nuxel-nfcd` active; `/run/nuxel/nfc/state.json` = `state: OFF`, `enabled: false` | `PASS_DEVICE_RUNTIME` |
| Protocol verified | false | `BLOCKED_HARDWARE` |
| Physical tag read | not performed | `NOT_TESTED` / `NEEDS_OWNER_TEST` |

**Important correction:** an earlier live `/etc/nuxel/nfc/nfc.json` was stale and lacked the `firmware_expected` entry, so the diagnostic falsely reported “firmware missing.” The repo policy was deployed (config-only, backed up). With the correct policy the firmware is found and the first real blocker is the kernel NFC subsystem, not firmware.

## 5. Full dependency chain

| Stage | Current state |
|---|---|
| S3NRN82 controller + antenna | controller transport present; antenna not independently proven |
| I2C bus / IRQ / reset / power | I2C device `7-0027` bound; `/dev/sec-nfc` exists |
| Kernel sec-nfc driver | `/dev/sec-nfc` present; `CONFIG_NFC=y`, `CONFIG_SEC_NFC=y` |
| Kernel NFC class/netlink | **down** (`/sys/class/nfc` empty; no `/dev/nfc0`) |
| Firmware load | file present and hash-verified; runtime acceptance not proven |
| NCI/NDEF protocol | native daemon code exists; no protocol exchange verified |
| Userspace daemon | `nuxel-nfcd` active, NFC OFF |
| Bridge/UI | provider reports OFF/BLOCKED; Quick Settings safety preserved |
| Physical tag | not read |

## 6. First failing stage

**Kernel NFC subsystem/netlink.** The character transport exists, but the kernel NFC class is empty. Without the NFC core netlink/class, the native daemon has no supported packet interface and cannot complete an NCI exchange. The firmware is present, so “missing firmware” is no longer the blocker.

## 7. Why prior attempts have not completed the feature

- PWNAGE-65000 reported a native daemon, `/dev/sec-nfc`, a verified firmware blob, and passing offline ABI/NCI/NDEF tests, but `device_open=false`, `protocol_verified=false`, and no physical tag read.
- The vendor transport is not a generic NCI adapter; the kernel class is not exposed.
- A detected controller or a matching firmware hash was never promoted to “NFC works.”

## 8. Best recommended architecture

**Primary:** a native sec-nfc transport provider that speaks the exact vendor command/NCI framing directly over `/dev/sec-nfc`, loads/validates the firmware, and exports a standard NCI/NDEF interface to the Nuxel daemon. This avoids depending on the missing kernel NFC class.

**Fallback:** a narrowly scoped kernel adaptation that registers the NFC class/netlink for this controller, if the vendor ABI can be documented safely.

**Not recommended:** treating a chardev as a standard NCI socket, copying a different part’s firmware, or writing tags during bring-up.

## 9. Required work inventory

| Area | Work |
|---|---|
| Kernel/DT | Confirm IRQ/reset/wake GPIO, regulators, firmware mode, and why the NFC class is not registered |
| Firmware | Keep hash verification; prove runtime acceptance by the real controller |
| Userspace | Vendor transport framing, NCI state machine, firmware download, error recovery |
| Service/API | Bounded scan, OFF on exit, permissions, suspend/resume |
| UI | NFC toggle OFF-by-default, tag read status, no payment claim |
| Tests | physical NDEF tag read, repeated scans, cancellation, daemon restart |

## 10. Source/upstream research

- No upstream mainline driver for this exact Samsung sec-nfc vendor transport in the tree.
- The repo's `nuxel_nfc` package is the native protocol candidate; it is not yet proven against the live controller.
- The firmware provenance is the owner’s SM-G975F vendor partition; it is not redistributable.

## 11. Buildability

- Native daemon and transport code build from repo sources.
- Firmware is present on this device but license/provenance remains an owner-supplied artifact.
- No kernel/firmware/partition writes are authorized in this mission.

## 12. Risks and constraints

- Wrong firmware/part revision → controller brick or stuck IRQ.
- Raw I2C/vendor commands can disturb secure-element state.
- NFC must remain OFF by default; no tag writes or payment claims.
- Suspend/resume and screen-lock behavior must be tested.

## 13. Phased roadmap

| Phase | Goal | Gate |
|---|---|---|
| 0 | Identify why `/sys/class/nfc` stays empty; capture a bounded chardev open/close trace | No tag claim |
| 1 | Prove firmware download/acceptance on the real controller | Controller log/response |
| 2 | Implement transport framing + NCI discovery | Protocol evidence |
| 3 | Read one known NDEF tag | UID/content matches physical tag |
| 4 | Repeated scans, suspend/resume, cancellation, OFF-on-exit | Runtime matrix |
| 5 | Separate HCE/eSE/payment roadmap | Security review |

## 14. Acceptance test matrix

| Test | Required evidence |
|---|---|
| Controller power/firmware | real controller accepts firmware, no stuck wakeup |
| NDEF tag read | known physical tag UID/content, timestamp, bounded scan |
| Repeated scan | two different tags yield different UIDs |
| Cancellation | scan stops and controller releases |
| Daemon restart | clean restart, NFC OFF |
| Suspend/resume | scan resumes correctly |
| OFF default | boot state OFF |

## 15. Owner inputs required

- A physical NDEF tag (NTAG213/215/216 or MIFARE Classic).
- Confirmation that the vendor firmware may be used for this device.
- A decision on native transport vs kernel-class work if the vendor ABI is unavailable.

## 16. Confidence and gaps

- **Proved:** controller I2C/chardev, firmware present + hash, daemon OFF, kernel NFC class down, no tag read.
- **Inferred:** native vendor transport over `/dev/sec-nfc` is the least invasive route.
- **Unknown:** exact chip revision, firmware acceptance behavior, vendor frame format details, secure-element capabilities.
