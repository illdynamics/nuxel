# S5000AP Radio — Final Recovery, Regression and Honest Completion Matrix

**Date:** 2026-11-24 CET
**Branch:** cs/mob-round35-stage06
**Device:** Samsung Galaxy S10+ SM-G975F (beyond2lte, Exynos 9820, Shannon
S5000AP). Installed RADIO `G975FXXSEFUJ2` (CL2054966/QB20745891, 2021-10-20).
Carrier KPN NL (PLMN 20408).

This is the engineering handoff for rounds 07–08. It is not a green dashboard:
each modality is scored independently, and a data-only project may be fully
data-complete while voice/IMS remain zero.

---

## 1. Repeatability audit

| Item | Value |
|---|---|
| Final git HEAD | `ce0664a98a97f11907396b65943c65a4ee4d116f` |
| Tree state | clean before this round; this round adds only docs + one test-host fix + receipt script (see scoped commits) |
| Firmware provenance | `modem.bin` sha256 `1e4280d26de704281c01ddf59407fbfdfb714d3f87a55b780f6f74d1ab0e7881` (46,062,992 B); derived from installed RADIO first-46,062,992 B sha256 `d2edc55cce48fe18cd87c6f377683dc75c07f88bc2fb602a2172aaf33b99a681` |
| Kernel | `4.14.253-gf7194c1d15ed-dirty` arm64 |
| Kernel SHA-256 | `90265d386683b86519a46326082accb02555995ca8e1ea9a24e0fdcf91fb9ccd` |
| Deployed BOOT image | `cad4c27a8a704033f5045c5cdcdc5ed810fd1cdaab30c21269ab2566be962ca8` |
| Appended DTB SHA-256 | `6974a57c39d351c2e20a35f54094f315968d6c5e0e619116f09ef1e2c6db8abd` (376,101 B) |
| DTBO | `sda13` unchanged; `androidboot.dtbo_idx=9`; DTBO never written |
| RADIO/MODEM | `sda16` never written |
| Vendor RIL | `libsec-ril.so` sha256 `b02bd095ae44a991b3cb676e584b3209a947160c22e678578f8b0c877e282cb3` (read-only) |
| Source upstream | `Linux4/android_kernel_samsung_exynos9820` @ `f7194c1d15ed...` (see SSP-0025-KERNEL-SOURCE-MANIFEST.json) |

No binary firmware is redistributed; provenance is recorded by hash only.

## 2. Init order and failure behavior

- `nuxel-cpbootd` (CP boot) → `nuxel-radiod` (RFS/SIPC + `nl.nuxel.Radio1`) →
  ModemManager/NetworkManager.
- radiod fail-closed: no FMT/RFS node → opens only D-Bus/journal, never blocks
  boot; CP offline → FSM clears pending state and emits "unknown".
- No endless restarts: 30 s command deadlines, timed restart timers cancelled
  on health, low-privilege `nuxel` account for the daemon; `Requires`/`After`
  wiring documented in `nuxel-radiod.service`.

## 3. Host suites and receipts

Full radio host suite (`build.sh`) PASS: SIPC5/FMT/RFS/respond, FMT TX/RX,
data-session FSM, ipc41 command map, MBIM rule-out, QBR/NV/RFS-NV/EFS-NV,
OES cert, SMS codec/store/service, call parser/service, 3000-iter fuzz +
ASan/UBSan clean. Phone-app offline acceptance `PASS=37 FAIL=0
verdict=OFFLINE_TESTED`. Machine-readable receipt with authoritative source:
`reports/S5000AP-07-HOST-TEST-RECEIPT.json`.

`HOST PASS DOES NOT ESTABLISH A PHYSICAL LAYER.`

## 4. Capability matrix (independent, honest)

| Capability | Status | Evidence / timestamp | Notes |
|---|---|---|---|
| AP kernel driver/probe | VERIFIED_LIVE | `/dev/umts_ipc0`=0xeb, `/dev/umts_rfs0`=0xf5 present; `modem_state=ONLINE` | round 03/04 |
| CP archive identity/signature | SOURCE_ONLY | `modem.bin` structural CRC32 PASS; signing UNKNOWN | provenance UNKNOWN (origin archive absent) |
| Samsung CBD ABI + boot | VERIFIED_LIVE | cpboot_v3 type-string; one-shot boot transcript rc=0 | round 03.5/04 |
| RFS and SIPC response | VERIFIED_LIVE | real bidirectional FMT/RFS, DISP_RSSI_INFO decode | round 05/06 |
| SIM detected/ready | VERIFIED_LIVE | `ds_detect=1`, PIN READY, KPN home | round 06 |
| Carrier registration | VERIFIED_LIVE | REGISTERED_HOME, PLMN 20408 | round 06 |
| Mobile data PDP + rmnet IPv4/v6 + DNS | VERIFIED_LIVE | rmnet0 UP, global IPv6, DNS, `ip_configured=true` | round 06 |
| Cellular HTTPS (Wi-Fi out of path) | VERIFIED_LIVE | source-bound HTTPS 200 over rmnet0 | round 06 (evidence `2c377487`) |
| Reconnection/airplane/reboot | HOST_TESTED (+ round-06 daemon-restart reconnection) | reconnection across daemon restarts verified; airplane/reboot persistence not fully re-audited this round | partial |
| SMS send/receive | HOST_TESTED (physical BLOCKED) | codec/store/service/D-Bus PASS; no physical delivery | owner consent + 2 numbers |
| Ordinary calling + two-way audio | HOST_TESTED (physical BLOCKED) | call control/FSM PASS; audio_route unconfigured | consent + number + audio path |
| IMS/VoLTE | BLOCKED | vendor IMS symbols only | IMS_BLOCKED_VENDOR_STACK/PROVISIONING/UNSUPPORTED |
| App UI/permissions + regression | HOST_TESTED (offline) | phone-app 37/0; mkdtemp host fix | live GTK UI needs sysroot |

## 5. Conservative weighted completion

| Domain | Weighted estimate |
|---|---|
| Modem foundation (driver → registered → data) | ~95% (data verified live; minor lifecycle re-audits remain) |
| SMS | ~60% (implementation complete + host-verified; physical delivery 0% pending consent) |
| Ordinary voice | ~40% (call control complete; two-way audio unconfigured and untested) |
| IMS/VoLTE | 0% (BLOCKED on vendor stack + provisioning) |
| App UI/permissions | ~80% (offline-verified honesty + data layer; live UI integration pending) |

No single all-features 100% is reported. Data is ~95%, voice ~40%, IMS 0%.

## 6. Remaining minimal prerequisites

1. **SMS physical acceptance**: owner consent + two non-premium non-emergency
   test numbers; redacted body/recipient discipline.
2. **Voice physical acceptance**: owner consent + one consenting non-emergency
   number; first wire the Exynos ABOX ALSA/UCM `VoiceCall` verb + PipeWire
   route (no microphone-recording dependency).
3. **IMS**: without Samsung `ims`/`imsservice`/`rcs` binaries (not present) and
   KPN IMS entitlement + handset approval, no code unblocks this stage. Not a
   "few more rounds" task.
4. **Full lifecycle re-audit on device**: airplane mode, SIM absent/PIN/rejected,
   suspend/resume, modem-crash restart, prolonged idle, battery/thermal budget
   (none yet re-run end-to-end this round).

## 7. Staged next prompts (realistic, not speculative)

- Prompt A: implement + validate the S5000AP ABOX `VoiceCall` UCM/PipeWire audio
  route (host CMake/meson tests + owner-approved device trial).
- Prompt B: owner-consented bidirectional SMS trial with two test numbers and
  redacted log discipline.
- Prompt C: owner-consented ordinary voice trial (dial/ring/connect/hangup +
  two-way intelligibility, earpiece/speaker).
- Prompt D: full on-device lifecycle/negative matrix (airplane/no-SIM/PIN/
  suspend/resume/crash-restart/idle).
- Prompt E (only after A–D): IMS feasibility re-scope with a present vendor IMS
  stack or a chosen FOSS client + carrier provisioning path.

## 8. Flash/recovery posture

No BOOT/RADIO/DTBO/protected write this round. If a BOOT regression ever forces
a reflash, the bounded `pwn-mob/09_TWRP_A_ONLY_RECOVERY_AGREEMENT.md` applies:
TWRP re-entry after flash = candidate failed; rollback first; never write DTBO
or protected modem partitions. A successful Nuxel return is validated by
kernel/rootfs hashes + running services, not by absence of TWRP.
