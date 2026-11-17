# S5000AP radio endgame — 2026-11-17

## Current gate

**BLOCKED_OEM_CP_ARTIFACT at CP secure bootstrap.** This is not a claim that
the radio, SIM, LTE data, SMS, voice, or IMS works.

Fresh read-only evidence at `2026-11-17T12:37:13Z` establishes that the live
SM-G975F (`beyond2lte`) runs
`4.14.253-gf7194c1d15ed-dirty`, reports model `Samsung BEYOND2LTE EUR OPEN 26
board based on EXYNOS9820`, and has the built-in S5000AP transport configuration
enabled. `/dev/umts_boot0`, `/dev/umts_ipc0`, `/dev/umts_ipc1`, and
`/dev/umts_rfs0` exist; `rmnet0` through `rmnet7` exist but are down.

The audited `MODEM_STATUS` ioctl (`_IO('o', 0x27)`) on an `O_RDONLY` handle to
`/dev/umts_boot0` returned `OFFLINE` (0). It did not send power, reset, boot,
download, RFS, SIPC, SIM, or RF commands. ModemManager 1.24.2 is active but
`mmcli -L` reports no modems. The sole Wi-Fi session remained connected.
The installed generic `libmm-plugin-samsung.so` is not an S5000AP/Shannon
backend and does not cause ModemManager to enumerate a modem; it is excluded
from the capability gate.

## Evidence classification

| Finding | Classification |
| --- | --- |
| Exact running board/kernel, nodes, `rmnet*`, ModemManager result, status `OFFLINE` | PROVED_LIVE |
| Kernel sources at `f7194c1d15eded1c2a1a4dc63825b26103435cc0`; S5000AP/SIPC/SBD support and status ioctl | PROVED_IN_PINNED_SOURCE |
| October boot capture cited by the supplied pack | HISTORICAL_LIVE |
| Claimed missing host transport in `REPORT-MOBILE-NETWORKING.md` | HISTORICAL_LIVE and superseded by fresh evidence |
| Matching G975F CP firmware container, matching `cbd`, secure boot trace, RFS operation set, command dictionary | UNKNOWN / absent from supplied material |

The collector report SHA-256 is
`2d388766a104bf789c234ddbd494e47bff829af9aa0ecbc798231aa8e4c11af3`.
The device-built read-only probe SHA-256 is
`8c2430decc2bf9bba3b5f170d41c489b81ab457471b246fc9214a2d56f2a541c`.
The installed diagnostic and policy hashes are respectively
`ab4d8aa1c80bd599d9043917571c541e270b771fdd5119dd0311abc66378bcea`
and `a1921afb8cdaab652ed238095138655735708d9f36c0994d8a7d956530686116`.

## First-failure chain

| Gate | Observable | Result |
| --- | --- | --- |
| AP kernel transport | nodes, config, rmnet creation | PASS (transport only) |
| CP power/secure boot | `MODEM_STATUS` | FAIL: `OFFLINE` |
| CP boot confirmation / SHMEM IPC / RFS | CP-ready evidence | BLOCKED, cannot test safely |
| SIPC SIM/registration/PDP | verified response | BLOCKED |
| ModemManager backend / bearer | real modem and bearer | BLOCKED |
| LTE data, SMS, voice, IMS | physical end-to-end tests | NOT_TESTED |

## Candidate decision

| Candidate | Decision | Reason |
| --- | --- | --- |
| Rewrite `modem_v1` | Reject | Exact built-in driver and device nodes are present; no kernel defect was demonstrated. |
| Generic AT/QMI/MBIM/PPP plugin | Reject | No matching transport or protocol evidence. |
| New `nuxel-cpbootd` | Deferred | Secure firmware/container layout and exact transaction are absent; guessing is unsafe. |
| Matching Samsung `cbd` plus matching stock vendor runtime in a constrained Bionic adapter | Preferred if owner supplies lawful, matching artifacts | Preserves vendor-specific secure boot and RFS semantics. |
| Native SIPC5 radio daemon and ModemManager backend | Deferred after a verified CP boot trace and documented RFS/SIPC control dictionary | Link-layer header definitions alone do not specify telephony messages. |

## Required lawful input and rollback

Provide an owner-authorized, exact SM-G975F/beyond2lte stock firmware build
metadata plus its matching `cbd`/radio userspace artifacts or an authorized
trace of their CP bootstrap. Required metadata: model, region/build identifier,
CP build identifier, SHA-256, license/source authorization, board revision,
and kernel ABI. Do not supply or request EFS/NV/calibration/IMEI/SIM contents.

No boot/system partition was written and no reflash occurred. Rollback is
therefore not applicable; the unchanged known-good boot remains active.

## Safe regression checks

`make -C packs/mobile/tools test`, `bash packs/mobile/tests/test-pack.sh`, and
`python3 tools/s10plus/a33/tests/hw-subsystems/test-modem-diag.py` pass. The
diagnostic now correctly expands policy-controlled glob paths, reports the
live transport, and refuses to mistake a generic Samsung plugin for a Shannon
backend. It was deployed reversibly as ordinary userspace only. Pre-change
copies are at `/var/lib/nuxel/rollback/s5000ap-radio-endgame-20261117T1345Z/`
and `/var/lib/nuxel/rollback/s5000ap-radio-endgame-20261117T1350Z/`; restoring
their `nuxel-modem-diag.sh.pre` and `modem.json.pre` reverses this deployment.
