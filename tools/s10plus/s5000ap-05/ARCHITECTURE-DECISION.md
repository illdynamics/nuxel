# S5000AP Stage-05 — Reusable Stack Decision Matrix (Sub-job C)

SPDX-License-Identifier: CC-BY-SA-4.0
Status: RESEARCH COMPLETE / DECISION RECORDED (no live protocol claim)

## 1. The decisive protocol-coverage facts (verified this run)

| Fact | Evidence | Class |
|---|---|---|
| Kernel already carries SIPC5 + FORMAT framing and RFS/RIL channels | live `CONFIG_SEC_SIPC_MODEM_IF=y`, `/dev/umts_ipc0/1`, `/dev/umts_rfs0`, `/dev/umts_cass`, `/dev/umts_dm0`, `/dev/umts_router`, `/dev/umts_csd` probed; shmem `rb_ch_id=8` | `PROVED_LIVE` |
| SIPC5 link + FORMAT framing is fully defined in open kernel source | `drivers/misc/modem_v1/include/sipc5.h`, `modem_prj.h` (struct `sipc_fmt_hdr`), `modem_v1.h` (enum `sipc_ch_id`) @ pinned `f7194c1d…` | `PROVED_IN_PINNED_SOURCE` |
| Kernel strips the SIPC5 link header before userspace `read()`; gathers multi-frame fragments | `modem_io_device.c` `rx_frame_with_link_header`, `gather_multi_frame`, `skb_pull(hdr_len)` | `PROVED_IN_PINNED_SOURCE` |
| RFS **file-operation protocol** and the RIL **message vocabulary** (main_cmd/sub_cmd meanings) are **NOT** in any open source | `link_device_*` only names the RFS channel/`IPC_RFS` enum; no opcode table; `sipc_fmt_hdr` has fields but no cmd table | `UNKNOWN` (closed) |
| No FOSS libsamsung-ipc/Replicant implementation targets S5000AP (Shannon 5185) SIPC5 SHMEM | Replicant `libsamsung-ipc` = XMM616/XMM626, phonet/onedram, galaxys2/i9300/herolte; LTE fork `manoedinata/libsamsung-ipc` still XMM626-style (`_IO('o',0x53)`, `modem_firmware_partition_data`, SIPC4-era) | `PROVED_IN_PINNED_SOURCE` |
| Samsung vendor runtime = `rild` (`hw/rild`), `cass`, `libril_sem.so`, `libsec-ril.so`, `libsecril-client.so` — all closed blobs | `exynos9820-common` `proprietary-files.txt` (hashes pinned) | `DOCUMENTED_ONLY` / closed |
| ModemManager does **not** speak SIPC5 natively | MM probes AT/QMI/MBIM/PPP ports; no Samsung SIPC5 plugin exists upstream | `DOCUMENTED_ONLY` |

## 2. The three candidate architectures

### Option 1 — Narrow matching Samsung vendor RIL in isolated Bionic runtime + D-Bus bridge
- Reuse the exact `libsec-ril.so`/`rild`/`cass` blobs that speak the closed SIPC5
  format/RFS/RIL vocabulary, isolated in a Bionic (Android libc) container, with a
  narrow, authorization-checked D-Bus bridge out to the host.
- **Protocol coverage:** HIGH (the only component that actually knows the vocab).
- **Licensing:** blobs are proprietary; may only run from owner-licensed vendor
  runtime. Not redistributable, not reviewable.
- **Safety:** surface is large (full RIL), requires the RFS daemon too (highest
  privacy risk). Hard to audit. Bionic ABI mismatch risk on the Nuxel glibc/AArch64
  host (needs a real Bionic loader or an Android container).
- **Maintenance/ABI:** binary ABI pinned to the S10 vendor image; fragile across
  rootfs changes.

### Option 2 — Reconstructed minimal native SIPC5 `nuxel-radiod`
- Native glibc/AArch64 daemon that owns `/dev/umts_ipc*`, parses/validates
  SIPC5 + FORMAT framing (fully lawful, reconstructable from pinned kernel
  source), enforces RFS path policy, and exposes a truthful versioned D-Bus API.
- **Protocol coverage framing:** HIGH (link+FMT framing is 100% reconstructable).
- **Protocol coverage vocabulary:** LOW/UNKNOWN — the daemon cannot populate real
  SIM/registration/bearer fields without the closed message semantics. It reports
  `supported=false`/`unknown` honestly and never fabricates.
- **Licensing:** GPL-2.0 clean-room from pinned kernel source. Fully reviewable.
- **Safety:** BEST. Minimal surface, no proprietary code, fail-closed RFS policy.
- **Maintenance/ABI:** source-built, reproducible, no binary ABI fragility.

### Option 3 — Proven FOSS alternative (libsamsung-ipc / oFono)
- Reuse Replicant `libsamsung-ipc` + oFono. **Rejected on protocol coverage:**
  it targets pre-S5000AP Shannon (XMM616/626) and does not implement the
  S5000AP SIPC5 SHMEM telephony/RFS protocol. Any reuse would be a misleading
  "generic modem plugin" that does not actually drive this CP.

## 3. Decision

**Primary: Option 2 (reconstructed minimal native `nuxel-radiod`) for framing
safety + truthful capability reporting, now.** It is the only choice that is
lawful, reviewable, reproducible, and safe on TODAY's evidence.

**Documented contingency: Option 1 (isolated vendor RIL) is the ONLY path to
populating real SIM/registration/bearer fields**, and is explicitly deferred until
(a) re-confirmed real CP ONLINE, and (b) an owner-approved, redacted live trace of
the closed RIL message set is accepted as a lawful reference — because without that
trace the closed vocabulary cannot be safely or correctly reconstructed, and
fabricating it would violate the truth contract.

**Option 3 is rejected** as not covering this hardware generation (would be
fabricated "FOSS reuse").

## 4. Binary ABI reconciliation (sub-job C)

- `struct sipc_fmt_hdr` = 7 bytes (u16 len + 5 u8) — confirmed by `_Static_assert`
  in the host test (`sizeof == 7`).
- `sipc5_link_header` max = 6 bytes (4/5/6 depending on cfg ext bits) — matches
  `sipc5.h` `SIPC5_MIN/MAX_HEADER_SIZE`.
- Channel IDs used: PDP 10..24 (rmnet0..7 = 10..17), CASS=35, FMT=235..244,
  RFS=245..254, BOOT=215..224, DUMP=225..234. Reserved: 0,5,6,27,255.
- Little-endian length fields (u16 or u32 depending on ext-length cfg bit).
- `sipc_fmt_hdr.len` is the SIPC FORMAT **payload** length (after the 7-byte FMT
  header), NOT the SIPC5 link length.

## 5. What this run did NOT claim

- No live CP IPC request/response exchange (CP was OFFLINE at audit; real CP
  ONLINE from round 04 was not re-established, and a fresh physical boot requires
  the round-04 manifest re-run under the exact approved sequence — see report).
- No RFS opcode processing (vocab is UNKNOWN/closed); only the fail-closed path
  policy validator was built and tested.
- No ModemManager plugin that "speaks SIPC" (none exists; MM cannot be reused here).
