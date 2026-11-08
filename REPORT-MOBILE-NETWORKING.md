# Mobile networking report — Galaxy S10+ (`beyond2lte`)

## 1. Executive verdict

`NOT_SUPPORTED_ON_DEVICE` / `BLOCKED_FIRMWARE` at the **host transport + ModemManager plugin** stage. The S10+ has an integrated Samsung Shannon LTE modem, but the vendor CP character devices are exposed only as opaque `umts_*` nodes, ModemManager finds no modem, no Shannon plugin exists, and no SIM/registration/data bearer is available. This is not a Wi-Fi problem and not an AT-command problem.

## 2. Target identity

- SM-G975F `beyond2lte`, Exynos 9820.
- Modem: Samsung Shannon LTE (integrated; Cat 20 LTE, no 5G).
- Live CP nodes: `/dev/umts_boot0`, `umts_cass`, `umts_csd`, `umts_dm0`, `umts_ipc0`, `umts_ipc1`, `umts_ramdump0`, `umts_rfs0`, `umts_router` (all `10:*` misc devices).
- ModemManager: `mmcli -L` → `No modems were found`; no Shannon/Samsung plugin loaded.

## 3. What already exists

| Area | Source/path |
|---|---|
| Policy/config | `configs/nuxel/modem/modem.json` |
| Bridge/dialer/messages | `shell/nuxel-shell/nuxel-dialer`, `nuxel-messages`; bridge call/SMS stubs |
| Diagnostics | `tools/s10plus/a33/nuxel-modem-diag.sh`, `tests/pwnage65000` |
| ModemManager | installed and running, but no Shannon plugin |
| Protected paths | EFS/IMEI/NV/calibration are never read or written by Nuxel diagnostics |

## 4. Latest evidence

| Check | Result | Tier |
|---|---|---|
| `nuxel-modem-diag.sh status --json` | `state=NOT_SUPPORTED_ON_DEVICE`, `first_failing_stage=host_transport` | `PASS_DEVICE_RUNTIME` |
| CP host nodes | `/dev/umts_*` enumerate, but no supported host interface/plugin | `PASS_DEVICE_RUNTIME` |
| `mmcli -L` | `No modems were found` | `PASS_DEVICE_RUNTIME` |
| ModemManager plugins | no `*shannon*`, `*samsung*`, `*sec*modem*`, `*exynos*modem*` | `PASS_DEVICE_RUNTIME` |
| Data netdevs | none (`rmnet*`, `wwan*`, `pdp*`) | `PASS_DEVICE_RUNTIME` |
| SIM | `absent` (no supported modem API) | `PASS_DEVICE_RUNTIME` |
| Signal/operator/registration | unavailable; never invented | `PASS_DEVICE_RUNTIME` |
| Data connection | none | `NOT_TESTED` / unavailable |
| Voice/SMS/IMS | not implemented | `NOT_TESTED` |

## 5. Full dependency chain

| Stage | Current state |
|---|---|
| Shannon modem/CP | physically present, but no supported host protocol |
| Shared memory/IPC/CPIF/SIPC | vendor `umts_*` nodes only; ABI not documented in repo |
| Kernel modem driver | vendor nodes exist; no mainline ModemManager-compatible interface |
| Modem firmware/boot handshake | not proven; no CP boot/ready evidence |
| Userspace protocol/plugin | **missing** (no Shannon ModemManager plugin) |
| NetworkManager bearer | cannot be created |
| SIM/operator/registration | unavailable |
| Data/APN/DHCP/DNS | unavailable |
| SMS/voice/IMS | not implemented |

## 6. First failing stage

**Host transport + plugin.** The `/dev/umts_*` nodes are vendor CP channels, not a documented modem API. ModemManager has no Shannon plugin and finds no modem. Without a supported CP protocol and bearer interface, SIM/registration/data/SMS/voice cannot be brought up.

## 7. Why prior attempts have not completed the feature

- `device/s10plus/deviceinfo` labels the modem driver `UNKNOWN_NOT_MM_READY`.
- `docs/beta-finalization/manual-proof/16-sim-mobile-data.md` records no upstream ModemManager Shannon plugin and no usable CP transport.
- No AT channel has been verified; read-only AT commands are disabled by default and never mutate radio/NV state.

## 8. Best recommended architecture

**Primary:** a narrow, documented Shannon CP transport implementation (matching the vendor kernel's shared-memory/IPC ABI) plus a ModemManager plugin or a native cellular daemon integrated with NetworkManager. Start with SIM detection and LTE data; add SMS, voice, then IMS/VoLTE only after the bearer path is stable.

**Fallback:** a legally isolated vendor runtime only if the required Bionic/HIDL components can be packaged safely and the security model is acceptable.

**Not recommended:** QMI/MBIM/PPP assumptions, Pixel/Qualcomm instructions, raw AT mutation, or any EFS/IMEI/NV/partition write.

## 9. Required work inventory

| Capability | Required work |
|---|---|
| SIM presence | supported CP transport + SIM API; safe removal detection |
| Modem power/state | CP boot handshake, firmware readiness, crash recovery |
| Scan/registration | operator selection, roaming, signal/registration API |
| LTE data | bearer/APN, netdev, DHCP/DNS, routing |
| SMS | SMS PDU send/receive, storage, notifications |
| Voice | call control, audio route, dialer integration |
| IMS/VoLTE | carrier provisioning, IMS stack, regulatory review |
| Emergency | compliance/regulatory work only; never test-dial |

## 10. Source/upstream research

- No upstream ModemManager Shannon LTE plugin in the repo or Fedora package set.
- The vendor CP protocol is not QMI/MBIM/PPP by default; it must be derived from the matching Samsung kernel/DT.
- `ofono` suitability for Shannon LTE is not demonstrated.

## 11. Buildability

- A native transport/plugin can be built from public sources only if the CP ABI is documented.
- The modem firmware and protected calibration are vendor/OEM material; they are not in the repo.
- No modem/EFS/IMEI partition writes are authorized.

## 12. Risks and constraints

- Never read/write EFS, IMEI, NV calibration, modem partitions, or carrier provisioning.
- Never print IMSI/ICCID/IMEI/PIN/PUK/MSISDN/APN credentials.
- No mutating AT commands, raw APDUs, unlock attempts, or emergency test calls.
- Radio state changes can affect emergency/service availability; require owner authorization.

## 13. Phased roadmap

| Phase | Goal | Gate |
|---|---|---|
| 0 | Read-only CP ABI/DT/transport inventory; identify first usable channel | No mutation |
| 1 | SIM presence detection via a real modem API | Real SIM/absent state |
| 2 | Modem power/registration | Operator/registration API |
| 3 | LTE data bearer/APN/routing/DNS/HTTPS | Real active SIM + data test |
| 4 | SMS send/receive | Real SMS test |
| 5 | Voice call control/audio | Real call test |
| 6 | IMS/VoLTE | Carrier/regulatory validation |

## 14. Acceptance test matrix

| Test | Required evidence |
|---|---|
| SIM | real presence/absence; safe removal |
| Registration | operator/registration from modem API |
| LTE data | active bearer, IP route, DNS, HTTPS |
| SMS | real send/receive |
| Voice | real call control/audio |
| IMS/VoLTE | carrier-provisioned real test |
| Protection | no EFS/IMEI/NV access in logs or code |

## 15. Owner inputs required

- A real active SIM and carrier plan.
- Lawful modem firmware/CP documentation or OEM authorization.
- Owner authorization for any radio/registration test; no emergency calls.

## 16. Confidence and gaps

- **Proved:** `umts_*` nodes, no ModemManager modem/plugin, no data netdev, no SIM/registration, Shannon LTE identity.
- **Inferred:** the missing CP protocol/plugin is the primary blocker.
- **Unknown:** exact CP ABI, firmware readiness, SIM interface, whether public documentation is sufficient.
