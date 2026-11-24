# S5000AP Mobile Networking — Final Acceptance (Operation WONQ)
## Phase A/B complete-on-device; LTE/telephony/SMS NOT YET PASS

**Branch:** cs/mob
**Date:** 2026-11-24 CET
**Device:** SM-G975F / beyond2lte / Exynos 9820 / Shannon S5000AP (native Nuxel Linux)

---

## 1. Exact device-tree defect and permanent correction

### Root cause (proven on-device, not assumed)

The booted Nuxel BOOT image carried an **all-zero appended device tree**. The
`dt_size` field in the legacy-contract repacker was being honored, but the
payload written behind it was 9,394,176 bytes of `0x00` (SHA-256
`a46939acd9aa3fceca6c07100658dee9e2f5886af896be30958db21a3e5bf517` — the hash
of 9,394,176 zero bytes). Every prior "candidate" (boot-0020/0028/0029) and
the deployed image shared this identical zero-DTB.

Because S-Boot selects the device tree from the BOOT image's appended DTB (not
the separate `dtb`/`dtbo` partitions in this configuration), the Nuxel kernel
booted with no modem io-device tree, `mif_pdata/iodevs` had zero children,
`create_io_device()` / `sipc5_init_io_device()` never ran for `umts_ipc0` /
`umts_rfs0` / `umts_boot0`, and radiod had no transport → boot fell back to
TWRP (kernel 4.14.113).

### The earlier "malformed DTBO / stripped iodevs" hypothesis was WRONG

The DTBO partition (sda13) was verified byte-level: all 10 Samsung DTBO entries
(except the 352-byte null entry 0) contain the full 22 io-device definitions
with the correct channel IDs. The device's `androidboot.dtbo_idx=9` selects the
`beyond2lte` (board id 26, rev 255) entry, which contains `umts_ipc0`=0xeb,
`umts_ipc1`=0xec, `umts_rfs0`=0xf5, `umts_boot0`=0xd7, rmnet0..7. The base
`dtb` partition (sda12) correctly contains no `mif_pdata` (it is supplied by
the overlay). The DTBO is NOT the defect and was never modified.

### Permanent correction

The correct appended DTB is the **merged base+overlay**:
`fdtoverlay(exynos9820.dtb + exynos9820-beyond2lte_eur_open_26.dtbo)`.

This was regenerated on-host and verified **byte-identical** (SHA-256
`6974a57c39d351c2e20a35f54094f315968d6c5e0e619116f09ef1e2c6db8abd`) to the
known-good reference `docs/beta-finalization/live/evidence/pwnage-51000/kernel/appended.dtb`.

Two permanent source fixes were implemented:

1. `boot/s10plus/pack-boot-v1.sh` — fail-closed: reject any `--dtb` whose first
   4 bytes are not the FDT magic `d00dfeed`, any DTB < 1024 bytes, or any DTB
   whose first 64 bytes are all zero. This makes the zero-DTB defect impossible
   to silently repack.

2. `tools/s10plus/check-modem-dt.py` (new) — build-time regression gate: walk
   the appended FDT and require `mif,num_iodevs=0x16` (22), `umts_ipc0`=0xeb,
   `umts_ipc1`=0xec, `umts_rfs0`=0xf5, `umts_boot0`=0xd7, and 8 `rmnet*`
   devices. Wired into `boot/s10plus/build-candidate.sh` as a mandatory gate
   after the existing release gate.

---

## 2. Image build and deployment identity

| Field | Value |
|---|---|
| Deployed BOOT image | `nuxel-beyond2lte-boot-wonq-fixedtb.img` |
| Image SHA-256 | `cad4c27a8a704033f5045c5cdcdc5ed810fd1cdaab30c21269ab2566be962ca8` |
| Kernel | `4.14.253-gf7194c1d15ed-dirty` (arm64, unchanged) |
| Kernel SHA-256 | `90265d386683b86519a46326082accb02555995ca8e1ea9a24e0fdcf91fb9ccd` |
| Appended DTB SHA-256 | `6974a57c39d351c2e20a35f54094f315968d6c5e0e619116f09ef1e2c6db8abd` (376,101 B) |
| Ramdisk | lzma-alone, 2,424,832 B on-disk |
| Target partition | `boot` → `/dev/block/sda14` (57,671,680 B) |
| Flash method | fail-closed `scripts/nuxel-adb-flash-pack` (BOOT-only, full SHA-256 readback) |

Deployment was performed in TWRP 3.7.0_9-2 (device `R58M75KDB2X`, beyond2lte)
following `pwn-mob/09_TWRP_A_ONLY_RECOVERY_AGREEMENT.md`. Two independent
verified rollback copies of the prior BOOT were stored on-host before flash;
readback confirmed the deployed partition SHA-256 matched the candidate exactly.
`dtb` (sda12), `dtbo` (sda13), `recovery` (sda15), and `radio`/`sda16` were
never touched.

---

## 3. Actual live modem device registration (verified after reboot)

| Node | Present | Channel ID |
|---|---|---|
| `/dev/umts_boot0` | yes | 0xd7 |
| `/dev/umts_ipc0` | yes | 0xeb (FMT) |
| `/dev/umts_ipc1` | yes | 0xec |
| `/dev/umts_rfs0` | yes | 0xf5 (RFS) |
| `/dev/umts_cass/csd/dm0/router/ramdump0` | yes | — |
| `/dev/multipdp`, `/dev/s5p-smem` | yes | — |
| `rmnet0..7`, `umts_dm0` netdevs | yes | — |

Live device tree: `/proc/device-tree/mif_pdata/iodevs/` has all 22
`io_device_0..21` children; `mif,num_iodevs = 0x16`.

---

## 4. CP and SIM status

- CP state: **ONLINE** (`/sys/.../modem_state` = ONLINE, ioctl code 4), booted
  via the owner-approved one-shot `nuxel-cpbootd` (manifest
  `b6be21f5293e...`, pinned binary `d963219f424113...`). Full boot transcript:
  all stages rc=0, `verdict: online`.
- SIM: **detected/READY** (`sim/ds_detect = 1`; `SEC_PIN_STATUS READY` per prior
  rounds).

---

## 5. Real IPC transport (Phase A victory)

radiod log (live, verbatim):

```
cp_state_changed: "state":"ONLINE","code":4
startup: "cp":"ONLINE","sim":1
ep_opened: "/dev/umts_ipc0","ch":235        # FMT 0xeb
ep_opened: "/dev/umts_rfs0","ch":245        # RFS 0xf5
dbus_ready: "nl.nuxel.Radio1"
running
fmt_tx: main:8 sub:5 type:2 len:9           # first NET_REGIST query
```

Real bidirectional FMT TX/RX: every data-session command receives a GEN
response; unsolicited `DISP_RSSI_INFO`, `NET_REGIST`, `NET_SERVING_NETWORK`
indications are decoded. This is the exact condition guarded by `./wonqed`.

---

## 6. Network registration

- PS registration: **REGISTERED_HOME** (`ps:1`, `domain_sel:3`, `domain:1`,
  `reject:0`) — this supersedes the prior round-25 `NOT_REGISTERED` result.
- Serving network PLMN: **20408** (KPN NL; the device carrier is KPN per the
  device hostname/IPv6, not the T-Mobile NL 20416 assumed in earlier rounds).
- Signal strength: live RSSI frames decoded.

---

## 7. LTE bearer — NOT connected (remaining blocker, precise)

The complete data-session FSM executes:
`NET_REGIST_CHECK → SET_SERVICE_DOMAIN → SET_PREFERRED_NET → ENABLE_MOBILE_DATA
→ SET_DATA_PROFILE → SET_LTE_ATTACH → ALWAYS_ON_PDN → PS_ATTACH →
PS_REGIST_VERIFY → DATA_CALL`.

`DATA_CALL` returns `GPRS_CALL_STATUS call_state=3, pdp_state=0` (not connected);
rmnet0..7 remain DOWN; no cellular IP/DNS/HTTPS.

This is the same evidence-locked blocker documented in rounds 17–25: the default
EPS bearer is formed only during the modem's **initial LTE attach** using its
**persistent NV initial-attach APN** (`/mnt/efs_ro/nv_data.bin`). No runtime FMT
command on this S5000AP re-attaches with a new APN: `SetLteAttachProfile`
(sub=20) acks (GEN 0) but does not re-attach; `SyncProfileInfo` (sub=37, the
attach-APN push) is REJECTED (GEN 1); `DetachForIA`/`PsAttach(detach)` are
rejected. `IOCTL_MODEM_OFF` triggers a full system reboot (documented, not used
as a CP-only reset).

No NV/EFS/RADIO/BOOT/IMEI/firmware write was performed. Resolution requires
carrier/modem-supported provisioning of the persistent initial-attach APN
(owner-authorized), or a working reference SIM confirming subscription-provisioning.

---

## 8. Telephony and SMS

NOT attempted and NOT claimed. No Mo/MT call, no bidirectional audio, no SMS
path has been exercised. The call-control and SMS SIPC code paths exist in
`tools/s10plus/s5000ap-05/src/` but are not validated on hardware.

---

## 9. Regression-test results

- `tools/s10plus/check-modem-dt.py` (new): PASS on corrected image, FAIL on the
  historical zero-DTB image (intended reject).
- `tools/s10plus/verify-boot-image.py`: PASS on corrected image.
- `boot/s10plus/pack-boot-v1.sh` zero-DTB rejection: verified (refuses zero magic).
- No unit/fuzz/sanitizer changes introduced in this round; existing suite
  untouched.

---

## 10. Final acceptance

| Criterion | Status |
|---|---|
| Device tree / io-device registration | PASS |
| Real IPC/RFS/BOOT transport | PASS |
| CP online | PASS |
| SIM ready | PASS |
| Network registration | PASS (REGISTERED_HOME, PLMN 20408) |
| LTE bearer / cellular IP / HTTPS | NOT YET PASS (call_state=3) |
| Outgoing/incoming call | NOT TESTED |
| Bidirectional audio | NOT TESTED |
| Outgoing/incoming SMS | NOT TESTED |
| Reboot recovery | PASS (boots to Nuxel with modem nodes) |

**OVERALL RESULT: NOT YET PASS.**

Phase A (persistent modem device registration + real IPC transport) is complete
on the physical device. Phase B (common radio foundation: CP lifecycle,
transport discovery, FMT correlation, SIM state, network registration) is
functionally complete. Phase C (LTE bearer) is blocked at the documented,
carrier/modem-persistent-config initial-attach-APN gate. Phase D (telephony) and
Phase E (SMS) are not yet implemented/validated on hardware.
