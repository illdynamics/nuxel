# S5000AP — Round 05: Verified RFS + SIPC5 Control + Native Radio Daemon (groundwork)

**STATUS: SAFE-OFFLINE GROUNDWORK COMPLETE. NO live CP protocol claim.**
**Branch/HEAD:** `cs/mob` (work begun at `5e2b16ce…`; see §Commit).
**Round window:** `2026-11-23`.

The decisive engineering truth for Stage-05 is that the SIPC5 **framing** is fully
reconstructable from the pinned open kernel source, but the RIL/RFS **message
vocabulary** is closed (Samsung `libsec-ril.so`). This run delivered the complete
lawful, safe, host-testable portion — a robust SIPC5+FORMAT parser with fuzz and
ASan gates, a fail-closed RFS path validator, and a versioned D-Bus contract —
and did **not** fabricate any radio/SIM/registration/bearer state.

Categorization: `PROVED_LIVE`, `PROVED_IN_PINNED_SOURCE`, `DOCUMENTED_ONLY`,
`UNKNOWN`, plus explicit `OFFLINE_TESTED` for host suites.

---

## 1. Mandatory per-round reply

### 1.1 HEAD / branch / clean-state
- `HEAD` = `5e2b16ceb4048ca560fb2a06e2603c6afd2cf6e9` on `cs/mob` (worktree clean
  before this run). New Stage-05 source added under `tools/s10plus/s5000ap-05/`,
  uncommitted at the time of drafting (see §8).

### 1.2 Live kernel / BOOT / DT / CP state
- Kernel: `4.14.253-gf7194c1d15ed-dirty` (matches pinned `f7194c1d…`).
- `modem_state` sysfs = **OFFLINE** (fresh boot; CP not re-armed this run).
- `nuxel-cp-status` read-only probe = `{"state":"OFFLINE","state_code":0}`.
- Boot/DTB/DTBO hashes: NOT re-flashed; boot/DT frozen (no write this run).
- SIM slot detect: `/sys/.../sim/ds_detect` = **1** (single-SIM card present).

### 1.3 Files studied + first failing gate
Studied (pinned, present on host): `drivers/misc/modem_v1/{include/sipc5.h,
modem_prj.h, modem_v1.h, modem_io_device.c, link_device_shmem.c,
link_device_memory_main.c}` under `kernel/s10plus/.build/src.polluted.case-
insensitive/`; vendor `proprietary-files.txt`; `cpboot_v3/{ProtocolSipc.*,
Protocol.h, Type.h}`; stock-cbd `init.*.rc`; Replicant `libsamsung-ipc` tree
(via API) for the FOSS-alternative refusal.

**First failing gate (truthful):** real SIM/registration/bearer population.
CP is OFFLINE and — decisively — the RIL message vocabulary is `UNKNOWN`
(closed). No live IPC request/response was possible or performed.

### 1.4 Source changes + verified build/test
See §8. `./build.sh` (27 SIPC5 assertions + 18 RFS assertions + 3000×fuzz +
3000×ASan/UBSan fuzz) all PASS, host-tested.

### 1.5 Staged files / installs / flash
Stage-05 source is uncommitted/staged-local only; **no device install, no
systemd/udev change, no flash, no /dev write** this run.

### 1.6 Hardware vs simulation
Hardware: read-only SSH live inventory of `/dev/umts_*`, sysfs `modem_state`,
`ds_detect`, kernel config, `mmcli -L`, `ip link` rmnet state. Simulation:
all parser/policy/fuzz tests are synthetic fixtures, clearly labelled
`OFFLINE_TESTED` and never treated as radio success.

### 1.7 Capability matrix (independently assessed, unchanged truth)

| Capability | LTE data | SMS | Voice | IMS/VoLTE |
|---|---|---|---|---|
| Status | **BLOCKED** | **BLOCKED** | **BLOCKED** | **UNSUPPORTED_IMS** |
| First blocker | CP OFFLINE + closed RIL vocab | same | same | same + no IMS stack |

---

## 2. Live endpoint map (PROVED_LIVE)

| Endpoint | Major/minor | DT channel | SIPC5 class | Role |
|---|---|---|---|---|
| `/dev/umts_boot0` | 10,108 | 0xd7 | BOOT | CP boot/control |
| `/dev/umts_ipc0`  | 10,118 | 0xeb | FMT/control | principal formatted IPC |
| `/dev/umts_ipc1`  | 10,117 | 0xec | FMT/control | secondary formatted IPC |
| `/dev/umts_rfs0`  | 10,116 | 0xf5 | RFS (245) | RFS/NV service transport |
| `/dev/umts_cass`  | 10,119 | 0x23 | CASS (35) | vendor CASS channel |
| `/dev/umts_csd`   | 10,113 | 0x01 | CSD | circuit-switched data |
| `/dev/umts_router`| 10,114 | 0x19 | — | vendor router |
| `/dev/umts_dm0`   | 10,115 | 0x1c | DM | diagnostic |
| `/dev/umts_ramdump0`| 10,108| 0xe1 | DUMP | CP dump |
| `rmnet0..7`       | —      | 0x0a..0x11 | PDP 10..17 | packet data (all DOWN) |

Kernel config confirmed live: `CONFIG_SEC_SIPC_MODEM_IF=y`,
`CONFIG_SEC_MODEM_S5000AP=y`, `CONFIG_UMTS_MODEM_S5000AP=y`,
`CONFIG_LINK_DEVICE_SHMEM=y`; `CONFIG_LINK_DEVICE_WITH_SBD_ARCH` **not set**
(SHMEM link, not SBD).

---

## 3. Protocol coverage table

| Protocol element | Status | Evidence / provenance |
|---|---|---|
| SIPC5 start nibble (0xF8) | `KNOWN` | `include/sipc5.h` |
| SIPC5 config/ext/padding/ctl bits | `KNOWN` | `include/sipc5.h` |
| SIPC5 header size (4/5/6) | `KNOWN` | `include/sipc5.h` |
| SIPC5 length field (u16/u32 le) | `KNOWN` | `include/sipc5.h` |
| SIPC5 multi-frame ctrl (more/id) | `KNOWN` | `modem_prj.h` (0x80/0x7F) |
| SIPC5 padding (8-byte align) | `KNOWN` | `include/sipc5.h` |
| Channel-id enum (PDP/CASS/FMT/RFS/BOOT/DUMP) | `KNOWN` | `modem_v1.h` |
| Reserved channels 0,5,6,27,255 | `KNOWN` | `modem_prj.h` |
| SIPC FORMAT header (sipc_fmt_hdr, 7B) | `KNOWN` | `modem_prj.h` |
| Kernel strips link hdr / gathers fragments | `KNOWN` | `modem_io_device.c` |
| SIPC5 link-header parse | `IMPLEMENTED_TESTED_HOST` | `src/sipc5_fmt.c` |
| SIPC FORMAT parse (len/seq/ack/cmd) | `IMPLEMENTED_TESTED_HOST` | `src/sipc5_fmt.c` |
| Truncated/overflow/bad-start/reserved-ch | `IMPLEMENTED_TESTED_HOST` | unit + fuzz |
| RFS path/access fail-closed policy | `IMPLEMENTED_TESTED_HOST` | `src/rfs_policy.c` |
| Versioned D-Bus API + polkit | `IMPLEMENTED_TESTED_HOST` (contract) | `dbus/*` |
| RFS file-operation opcodes | `UNKNOWN` (closed Samsung) | no open source |
| RIL command vocabulary (main/sub cmd) | `UNKNOWN` (closed Samsung) | no open source |
| Real SIM/registration/bearer fields | `UNKNOWN` (not yet LIVE_VERIFIED) | CP OFFLINE |
| Any live CP IPC request/response | `LIVE_VERIFIED = none this run` | CP OFFLINE |

---

## 4. Source lineage & license

| Source | Path | License | Role |
|---|---|---|---|
| Samsung downstream kernel | `kernel/s10plus/.build/.../modem_v1` (pinned `f7194c1d…`, 4.14.253) | GPL-2.0 | framing reference (clean-room transcription) |
| Samsung cbd `cpboot_v3` | `~/.local/share/nuxel-s5000ap/…/cpboot_v3` | Apache-2.0 | boot-only; confirms boot path, NOT runtime RFS/RIL |
| Vendor RIL blobs (rild/cass/libsec-ril/libril_sem/libsecril-client) | `exynos9820-common` `proprietary-files.txt` (hashes pinned) | proprietary, owner-local | closed vocab (NOT redistributed) |
| Replicant libsamsung-ipc | GitHub ius/libsamsung-ipc + manoedinata fork | GPL-2.0+ | rejected: pre-S5000AP (XMM616/626) |
| Stage-05 code this run | `tools/s10plus/s5000ap-05/` | GPL-2.0 (code), CC-BY-SA (docs) | parser/policy/contract |

**No proprietary blob was committed, copied into the repo, or redistributed.**

---

## 5. Unit + fuzzer receipts

### 5.1 SIPC5/FMT unit tests — `tests/test_sipc5_fmt.c` (27 assertions, PASS)
ABI sizes (`sipc_fmt_hdr==7`), 4/5/6-byte link headers, multi-frame/ext-len
decode, bad-start, truncated link, FMT complete/truncated/overflow/partial.

### 5.2 RFS policy unit tests — `tests/test_rfs_policy.c` (18 assertions, PASS)
allow/deny, non-allowlisted, dot-dot, absolute, backslash, symlink escape,
hardlink, protected `/efs` (both absolute-prefix and path-component forms),
write-downgrade, empty path, no-root lockdown, write-allowed subtree.

### 5.3 Fuzzer — `tests/fuzz_sipc5.py` + `tests/fuzz_driver.c`
- 3000 iterations plain: `crashes=0 timeouts=0 unique_coverage=495`.
- 3000 iterations ASan+UBSan (`-fsanitize=address,undefined`): `crashes=0
  timeouts=0`. No out-of-bounds read/write detected.

---

## 6. Security review

- **Parser** is parse-only; it never opens/writes a device and never prints
  payload bytes (IPC may contain IMSI/ICCID/IMEI/PIN/PUK/MSISDN).
- **RFS policy** is deny-all by default; no default-allow anywhere. Rejects
  absolute, `..`, backslash, symlink (via realpath+lstat), hardlink, block/char
  devices, non-regular/dir types, and protected components (`efs/efsg/sec_efs/
  nv*/calibration/keys/keymaster/keystore/radio/persist/pstore/proc/sys/dev/sbin/
  boot`) both as absolute prefixes and as any path component. A write verdict
  requires an explicit allow-write entry AND a write intent.
- **D-Bus** write methods require polkit `auth_admin`; bus policy denies
  method-calls to `SetRadioEnabled/CreateBearer/DeleteBearer` by default.
- **No** filesystem service exposes arbitrary host paths to the CP; if a real CP
  boot ever requires protected NV access, the policy validator DENIES and the
  report must escalate (it does not bypass).

---

## 7. Crash behavior & no-SIM negative test

- **Crash behavior (host):** the fuzzer includes CP-restart/zero-read/unavailable-
  endpoint analogues (truncated byte streams, empty inputs, hostile length
  fields forcing overflow/truncated paths). The parser returns typed negatives
  (`TRUNCATED`/`OVERFLOW`/`BAD_START`) and never loops or crashes; the stream
  driver advances by one byte on pathological tails so it cannot stall.
- **No-SIM negative (live, read-only):** `ds_detect=1` (card present). The
  daemon would report `SimPresent` only from a real modem source; with CP
  OFFLINE it reports nothing/`unknown`, not a fabricated "no SIM". A true
  no-SIM test is a later physical gate (requires CP ONLINE + modem SIM query).

---

## 8. Commit + staged source (this run)

New, focused, host-testable Stage-05 source (GPL-2.0 code + CC-BY docs):

```
tools/s10plus/s5000ap-05/
  README.md
  ARCHITECTURE-DECISION.md        (Sub-job C)
  build.sh                        (reproducible build+test+ASan gate)
  src/sipc5_fmt.h                 (SIPC5 link + FORMAT parser interface)
  src/sipc5_fmt.c                 (parser, clean-room from pinned kernel)
  src/rfs_policy.h                (RFS fail-closed validator interface)
  src/rfs_policy.c                (validator: allowlist + rejections)
  tests/test_sipc5_fmt.c
  tests/test_rfs_policy.c
  tests/fuzz_driver.c
  tests/fuzz_sipc5.py
  dbus/nl.nuxel.Radio1.xml        (Sub-job D: versioned API v1)
  dbus/nl.nuxel.radiod.policy     (polkit actions)
  dbus/nl.nuxel.radiod.conf       (bus policy)
```

Build/test receipt: `tools/s10plus/s5000ap-05/build.sh` → all green (see §5).

---

## 9. Architecture decision summary (Sub-job C)

**Primary now:** reconstructed minimal native `nuxel-radiod` (framing-safe,
reviewable, truthful). **Contingency (only path to real fields):** isolated
vendor RIL in a Bionic runtime with a D-Bus bridge, gated on (a) re-confirmed
real CP ONLINE and (b) an owner-approved redacted trace of the closed RIL/RFS
message set. **Rejected:** FOSS libsamsung-ipc/oFono (does not target S5000AP).

---

## 10. Next action + exact blocker

**Blocker:** (1) CP must be re-armed to ONLINE via the exact round-04 manifest
(`bea25f0e…` binary + EFUJ2 `/dev/sda16` read-only + canonical 12-stage
sequence) under owner re-approval; AND (2) an owner-approved, redacted live
trace of the closed Samsung RIL/RFS message vocabulary is required before any
real message semantic can be truthfully parsed — because the open kernel code
defines framing but NOT message meaning.

**Next safe task:** commit Stage-05 groundwork; then, if owner authorizes the
round-04 CP re-boot under the pinned manifest, capture a *redacted* framing-only
trace (channel/len/seq sanitized, no payload) to begin lawful vocabulary
characterization — without fabricating any SIM/registration/bearer field.
