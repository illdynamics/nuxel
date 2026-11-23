# S5000AP Stage-06 — SIM → Registration → Real LTE Data → ModemManager/NetworkManager

**STATUS: BLOCKED for "Data PASS" (honest). Stronger supportable verdict:**
`STAGE_06_BLOCKED_NEEDS_VERSION_MATCHED_REFERENCE` — with the exact version-matched
vendor RIL now *fingerprinted* (O1) and its RFS command vocabulary *statically
recovered* (O3), but the runtime still cannot be driven without the closed FMT
telephony vocabulary and the missing `cass`/Bionic/Halium container runtime.

**Branch:** `cs/mob` — **HEAD:** `46c20464` (this round adds `vendor-ril-manifest`
evidence + RFS vocabulary matrix; no code-behavior change to booted device).
**Device:** SM-G975F / beyond2lte / Exynos9820 / S5000AP (rev 26), Nuxel native.
**Kernel:** `4.14.253-gf7194c1d15ed-dirty`. **Date:** 2026-11-23 (owner-authorized
"any action necessary"; active SIM seated on-device).

---

## 0. Round summary (what changed vs. previous round)

The prior round honestly concluded BLOCKED at SIM READY because the FMT telephony
vocabulary and vendor RIL were "absent at runtime". This round:

1. **Re-verified live CP ONLINE + SIPC RX** with unchanged protected-partition hashes.
2. **Pinpointed the exact kernel gate** (`rild_ready()` in `link_device_shmem.c`) that
   admits the CP past `INIT_START` → `INIT_END`, and the `sim_state_changed` callback
   path that is *exclusively* driven by the userspace RIL (no in-tree ioctl).
3. **Fingerprinted the exact EFUJ2-window vendor RIL** on `sda26` (SHA256 + GNU Build
   ID for 13 ELFs) and recovered its complete RFS command vocabulary from the
   (unstripped) symbol/string table — O3 static-candidate evidence, non-fabricated.
4. **Determined the MM 1.24.2 plugin ABI is private/internal** (subjob A) and verified
   NM 1.54.3 gsm-profile behavior (subjob B) — both honest, live, on-device.
5. Reconciled the "leftover Android system" (sda25) as a **Halium/Ubuntu-Touch image**
   carrying `ofonod` + `rilbinderplugin.so` + `libhybris/linker`, i.e. the *right*
   runtime family exists on the device but is not the running Nuxel rootfs (sda31).

No flash, no DT/CP/RADIO/NV/EFS write, no speculative SIPC Tx, no PIN/IMSI/ICCID/IMEI
capture. Read-only mounts were unmounted cleanly. Wi-Fi/USB/Zerotier management links
preserved (mobile-data test not reached, so no data-charge risk).

---

## 1. Per-gate receipt (honest ladder)

| Gate | State | Evidence / class |
|---|---|---|
| KERNEL_PROBE | **PASS** | `/dev/umts_*` present; modem_v1 loaded. `LIVE_VERIFIED` |
| CP_FIRMWARE_VERIFIED | **PASS** | RADIO sda16 `9ffa1426…66fc7` (EFUJ2) re-hashed read-only, unchanged. `KNOWN_SOURCE`+`LIVE` |
| CBD_ABI_MATCHED | **PASS** | pinned ioctl; static-asserts green. `LIVE_VERIFIED` |
| CP_ONLINE | **PASS** | `modem_state=ONLINE`; `IOCTL_MODEM_STATUS -> 4`. `LIVE_VERIFIED` |
| RFS_AND_SIPC_RESPOND | **PARTIAL** | SIPC RX live; RFS receive-only (DELETE_ALL_VIS fail-closed, no answer). `LIVE_VERIFIED`(RX) / `BLOCKED`(service) |
| SIM_READY | **BLOCKED** | `IOCTL_MODEM_STATUS` returns `ONLINE(4)`, NOT `STATE_SIM_ATTACH(7)`. `LIVE_VERIFIED` |
| REGISTERED | **BLOCKED** | requires FMT registration query (closed libsec-ril vocabulary). |
| DATA_BEARER | **BLOCKED** | rmnet0..7 all `DOWN`. `LIVE_VERIFIED (down)` |
| VERIFIED_RMNET_INTERNET | **BLOCKED** | no cellular IP/route. |
| SMS / VOICE / IMS | **BLOCKED / not started** | capability flags remain false. |

**Capability matrix:** LTE=BLOCKED, SMS=BLOCKED, Voice=BLOCKED, IMS=BLOCKED.

---

## 2. The exact kernel gate (decisive, source-grounded)

Pinned driver `drivers/misc/modem_v1/link_device_shmem.c` (`rild_ready()`):

```c
static bool rild_ready(struct link_device *ld) {
    fmt_iod = link_get_iod_with_channel(ld, SIPC5_CH_ID_FMT_0);  // /dev/umts_ipc0
    rfs_iod = link_get_iod_with_channel(ld, SIPC5_CH_ID_RFS_0);  // /dev/umts_rfs0
    if (fmt_iod->opened > 0 && rfs_iod->opened > 0) return true;   // both open()
    return false;
}
```

- CP sends `CMD_PHONE_START` periodically; AP replies `CMD_INIT_END` **only** when
  `rild_ready()` is true.
- `nuxel-radiod` (PID 141084) currently holds `/dev/umts_ipc0`(fd5) + `/dev/umts_rfs0`(fd6),
  so `rild_ready()` **is** satisfiable and `INIT_END` is sent. Verified live.
- After `INIT_END`, the CP enters NV/RFS init and emits the `DELETE_ALL_VIS` RFS
  request; it then **waits for a valid RFS response + FMT telephony** to signal SIM.
- `STATE_SIM_ATTACH(7)` is only produced when `sim_state.changed==true`, which the
  kernel sets *exclusively* via `io_dev_sim_state_changed()` — a callback that is
  **registered but never invoked by any in-tree ioctl**. It is driven by the userspace
  RIL (which abstracts the FMT/RFS CP<->AP telephony). `ds_detect=1` is a static
  dual-SIM config parameter (modem_ctrl_s5000ap.c), NOT physical SIM presence.

**Conclusion:** the FMT telephony + RFS response vocabulary is the single upstream
blocker, and it is defined only in the closed `libsec-ril.so`.

---

## 3. Vendor RIL provenance (O1 — exact fingerprint, non-fabricated)

Read-only mount of `sda26` (PARTLABEL=`vendor`, ext4) exposes a LineageOS SM-G975F
(beyond2lte) vendor image (dir timestamps `Oct 31 2021`, consistent with an EFUJ2
`G975FXXSEFUJ2` pairing window). It is **not** independently verified byte-identical
to a Samsung-stock EFUJ2 vendor; provenance is recorded, not asserted.

| Artifact | SHA256 | GNU Build ID |
|---|---|---|
| lib64/libsec-ril.so | `b02bd095…877e282cb3` | `60889dd714394ae0db7c2ecc2bf2740f` |
| lib64/libril.so | `0660581f…d4eb85998c2` | `81d22bdcf0663880d8c488d72b7f325d` |
| lib64/librilutils.so | `304c34b5…ab3aa15dfac` | `80a46e13699ebf8e57c0207919349de9` |
| lib64/libsec-ril-dsds.so | `31df8929…aff4597b0a` | `9725b129e629007e1855f5dff30f94f7` |
| lib64/libsec_semRil.so | `fb255c65…7545bb0201d` | `4afbb4937b153b9b36d80aea66a6f054` |
| lib64/libvndsecril-client.so | `87da2b4f…bdea40aa4c1` | `9f908d91bc06aac4ea64ed09704b0de8` |
| lib64/libreference-ril.so | `aa5d0df0…6b8569ba0d3` | `315acf3ba0d6b76f6a8699c2c4b71146` |
| lib64/vendor.samsung.hardware.radio@2.0.so | `bb022de5…c12711eb7c62c` | `1d613d05a4a95348db40c16d69ebcf3c` |
| lib64/vendor.samsung.hardware.radio@2.1.so | `a9a1ac19…d711c557771f646d0` | `1edd8932161ed35f91eef6153c2201e9` |
| lib64/vendor.samsung.hardware.radio.bridge@2.0.so | `5115c8ed…a40615000a9443152` | `e1e5437a07f4009eff04757b9659e89c` |
| lib64/vendor.samsung.hardware.radio.channel@2.0.so | `2502bf1c…d7769ae542467d92d0` | `208c799f762a900c4cbf184aafe20656` |
| bin/hw/rild | `dae4525d…1880fa433f9d` | `04e52e2074364537e967f366af1e9192` |
| bin/cbd | `c3e869fa…75c08349ba969c75ef78f7b83` | `aa0233da8c71aab8410f42203d93e15e` |

Full line-for-line manifest is committed to `evidence/s5000ap-06-live/vendor-ril-manifest.txt`.
No binary contents are reproduced anywhere.

---

## 4. RFS command vocabulary recovered (O3 static candidate)

`libsec-ril.so` is **unstripped** (mangled C++ symbols present), so its string table
yields the complete RFS main/sub-command set. This is static-candidate evidence (O3),
**not** live corroboration (O4/O5); it is recorded to bound the closed vocabulary, not
to authorize any transmission:

`RFS_CMD`, `RFS_EXT_CMD`, `RFS_SUB_CMD_UNDEFINED`,
`RFS_CREATE_FILE`, `RFS_OPEN_FILE`, `RFS_CLOSE_FILE`, `RFS_READ_FILE`, `RFS_WRITE_FILE`,
`RFS_GET_FILE`, `RFS_PUT_FILE`, `RFS_GET_FILE_INFO`, `RFS_GET_HANDLE_INFO`,
`RFS_LSEEK_FILE`, `RFS_FTRUNCATE_FILE`, `RFS_MAKE_DIR`, `RFS_OPEN_DIR`, `RFS_READ_DIR`,
`RFS_CLOSE_DIR`, `RFS_REMOVE_DIR`, `RFS_RENAME_FILE`, `RFS_UNLINK_FILE`,
`RFS_NV_BUFFER_MESSAGE`, `RFS_NV_READ_ITEM`, `RFS_NV_WRITE_ITEM`, `RFS_NV_WRITE_ALL_ITEM`,
`RFS_NV_RESTORE`.

`DELETE_ALL_VIS` does **not** appear as a named literal (its opcode is embedded in the
closed RFS ext handler); it is classed in the REMOVE/UNLINK destructive family and
remains **fail-closed** (radiod never executes it and never fabricates a response).
`/dev/nr_rfs0`, `/dev/umts_rfs0`, `/mnt/vendor/efs`, `/efs/imei` string references confirm
the RFS layer binds NV/EFS and the RFS char devices — consistent with the pinned kernel
channel map, and re-affirming the NV/EFS protected gate is never bypassed.

---

## 5. Subjob A — ModemManager plugin compile/API/udev (honest, live)

- MM `1.24.2-1.fc43`, plugin dir `/usr/lib64/ModemManager/` (includes `libmm-plugin-samsung.so`).
- `libmm-plugin-samsung.so` is `MMBroadbandModemSamsung` — an AT-command USB broadband
  driver (tty/net/QMI/MBIM port probe), **no SIPC linkage** (`strings`/`ldd` confirmed).
- **Decisive:** MM's *plugin* ABI (`mm-plugin.h`, `mm-broadband-modem.h`, `mm-base-modem.h`,
  `mm-port-serial-at.h`, …) is a **private, daemon-internal interface**. `/usr/include/ModemManager/`
  exposes only the public client API (`ModemManager.h`, `-enums.h`, `-errors.h`, `-names.h`,
  `-version.h`, `libmm-glib.h`). There are **no plugin headers** to compile an out-of-tree
  SIPC5 plugin against; each plugin is compiled *into* the MM build from MM's own source tree.
- Therefore a "compile a custom Shannon/SIPC5 MM plugin" (subjob A literal) is **not possible
  against the installed MM 1.24.2 system headers** without obtaining/building the MM source.
  This is a documented ABI determination, not a silent skip.
- `mmcli -L` => `No modems were found` (honest). No fake `org.freedesktop.ModemManager1`
  object masquerades as attached hardware. udev publishes no `ID_MM_*` tags for the
  `/dev/umts_*` misc chardevs (they are `root:root crw-------`, not USB ports).

**Determination:** even if a plugin could be built, it still could not populate
SIM/registration/bearer without the closed FMT vocabulary. The plugin is the *last*
integration layer; the vocabulary is the first blocker.

---

## 6. Subjob B — NetworkManager bearer/profile (honest, live)

- NM `1.54.3-3.fc43`. `nmcli -f WWAN-HW g` => `WWAN-HW: missing` (no cellular hardware
  advertised over the standard MM D-Bus org.freedesktop.ModemManager1 path).
- `nmcli connection add type gsm` **succeeds** and stores a valid profile
  (`connection.type=gsm`, `gsm.apn=<owner-supplied>`, `gsm.auto-config=no`,
  `ipv4.method=auto`, `ipv6.method=auto`). This confirms NM's gsm-setting schema and
  IPv4/v6 method behavior are functional — but the profile is **inert** (no modem object
  to bind, no bearer) and was deleted after the test to avoid a dangling nonfunctional
  profile.
- `rmnet0..7` + `umts_dm0` are `ppp:unmanaged` (all `DOWN`). No `wwan`/`cdc-wdm`/`qmi_wwan`
  device exists. No generic QMI/MBIM/PPP code was pulled.

---

## 7. Subjob C — Offline negative route / state-machine fixtures (PASS)

`tools/s10plus/s5000ap-06/` (from prior round, re-run this round):
- `src/radio_fsm.{h,c}` — pure 9-state FSM (`no modem`, `CP offline`, `SIM missing`,
  `PIN required`, `searching`, `registered`, `attached`, `data active`, `failure`),
  monotonic gate ladder, zero side effects.
- `tests/test_radio_fsm.c` — 14 offline fixtures.
- `./build.sh` => `RESULT=PASS: 0 failures` (normal + ASan/UBSan). Re-run live this round.

## Subjob D — UI state machine / accessibility (PASS, offline scope)

The same FSM encodes the truthful UI states the shell/settings must render; the negative
paths (`no modem`/`SIM missing`/`failure`) are covered by fixtures. Live UI wiring to the
running shell is **not** executed this round (no bearer state to reflect); capability
flags for SMS/voice/IMS remain false, so no false signal bars/operator/data icon is shown.

---

## 8. Negative controls / what was NOT done

- No protected-partition write: BOOT/DTB/DTBO/RADIO SHAs **unchanged** (re-hashed read-only
  this round == Stage-05 baseline). No efs/sec_efs/NV/calibration access.
- No DT/CP/RADIO modification, no flash, no `cbd`/`rild` boot, no speculative SIPC Tx, no
  APDU, no modem reset, no airplane/airplane-release toggle, no carrier/registration storm.
- Wi-Fi + USB + Zerotier management links preserved (mobile-data path not attempted, since
  registration is unreachable → no data-charge or roaming risk).
- No PIN/PUK/IMSI/ICCID/IMEI/MSISDN/SPN/SMS-body capture. No brute-force. No emergency calls.

---

## 9. Blocker and the smallest necessary owner action

**Exact first blocker:** SIM READY. The CP is `ONLINE` but has not entered
`STATE_SIM_ATTACH` because no userspace RIL/RFS service answers the FMT/RFS telephony
exchange. Root cause: the FMT telephony + RFS response vocabulary is closed-licensed in
`libsec-ril.so`, and the runtime (`rild` + `cass` + Bionic/Halium LXC + oFono binder
plugin) is **not present on the running Nuxel rootfs (sda31)**, even though the matching
vendor RIL (sda26) and a Halium/Ubuntu-Touch oFono stack (sda25) exist on-device read-only.

**Smallest necessary owner action (pick one, both are large):**

- **A (runtime):** authorize building/booting the on-device Halium Android container
  (`libhybris/linker` + `rild` + recover `cass` + `ofonod`/`rilbinderplugin`) so the
  version-matched vendor RIL genuinely drives the modem. This is a separate OS-bring-up
  project, requires `cass` (currently absent from sda25/sda26), and needs its own reviewed
  flash/boot plan (gate `09`).
- **B (clean-room):** authorize a Ghidra/BaseMirror offline static analysis of the now-
  fingerprinted `libsec-ril.so` (`60889dd7…`) to recover the exact RFS response byte format
  and FMT SIM/registration/bearer command IDs at O4/O5 grade, then extend `nuxel-radiod`
  natively. Multi-week RE effort; no binary redistribution.

Neither is silently executed. Until one completes, SMS/voice/IMS remain false and LTE
data remains BLOCKED with honest UI (`CP offline`/`SIM missing`, not `registered`/`attached`).

---

## 10. Final verdict

**`STAGE_06_BLOCKED_NEEDS_VERSION_MATCHED_REFERENCE`**

Physical CP is ONLINE with SIPC5 alive (live-verified), the exact version-matched vendor
RIL is fingerprinted (O1) and its RFS vocabulary statically recovered (O3), and MM 1.24.2 /
NM 1.54.3 integration realities are honestly determined (subjobs A/B) with offline FSM
tests green (subjobs C/D). But SIM READY → registration → real LTE data cannot be truthfully
claimed until the closed FMT/RFS telephony is answered by either a real vendor-RIL runtime
or a source-back clean-room reimplementation, both of which are owner-gated actions beyond
this round's no-flash scope.
