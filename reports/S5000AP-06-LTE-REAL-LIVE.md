# S5000AP Stage-06 — SIM → Registration → Real LTE Data → ModemManager/NetworkManager

**STATUS: BLOCKED for "Data PASS" (honest).** Physical CP is ONLINE; SIPC5 is
alive; the truthful state machine and MM/NM integration determination are
delivered; but SIM registration and real LTE data cannot be completed because
(a) the closed FMT telephony vocabulary is absent from all open sources, (b) the
vendor RIL (`rild`/`cass`/`libsec-ril.so`) is not present on the device, and
(c) the CP therefore does not progress to a protocol-backed SIM attach
(`STATE_SIM_ATTACH`). No result below is fabricated; every live claim has a
redacted capture in `evidence/s5000ap-06-live/`.

**Branch:** `cs/mob` — **HEAD:** `c050c75c7e0bc86450061e0a130fbbb516ba08fd` (clean except `mob.md`).
**Device:** SM-G975F / beyond2lte / Exynos9820 / S5000AP (rev 26), Nuxel.
**Kernel:** `4.14.253-gf7194c1d15ed-dirty`. **Date:** 2026-11-23.

---

## 1. Per-gate receipt (honest ladder)

| Gate | State | Evidence / class |
|---|---|---|
| KERNEL_PROBE | **PASS** | `/dev/umts_*` present; kernel modem_v1 loaded. `LIVE_VERIFIED` |
| CP_FIRMWARE_VERIFIED | **PASS** | RADIO sda16 `9ffa1426…66fc7` (EFUJ2) read-only. `KNOWN_SOURCE`+`LIVE` |
| CBD_ABI_MATCHED | **PASS** | pinned ioctl `_IO('o',0x27)`; `nuxel-cp-status` static-asserts. `LIVE_VERIFIED` |
| CP_ONLINE | **PASS** | `modem_state=ONLINE`; `IOCTL_MODEM_STATUS -> state_code=4`. `LIVE_VERIFIED` |
| RFS_AND_SIPC_RESPOND | **PARTIAL** | SIPC RX live (AST_POWERON, DELETE_ALL_VIS); RFS receive only, never answered (RFS opcode vocab closed). `LIVE_VERIFIED` (RX), `BLOCKED` (service) |
| SIM_READY | **BLOCKED** | `IOCTL_MODEM_STATUS` returns `ONLINE`, NOT `STATE_SIM_ATTACH`. `LIVE_VERIFIED` |
| REGISTERED | **BLOCKED** | requires RIL FMT registration query; no RIL. `BLOCKED` |
| DATA_BEARER | **BLOCKED** | requires PDP setup FMT; rmnet0-7 all `DOWN`. `LIVE_VERIFIED (down)` |
| VERIFIED_RMNET_INTERNET | **BLOCKED** | no cellular IP/route. Wi-Fi/USB/Zerotier are management paths only. `BLOCKED` |
| SMS / VOICE / IMS | **BLOCKED / not started** | capability flags remain false. |

**CM:** LTE=BLOCKED, SMS=BLOCKED, Voice=BLOCKED, IMS=BLOCKED.

## 2. Corrected SIM-state truth (important)

Stage-05 reported `SimPresent=true` from kernel `sim/ds_detect=1`. This round
corrects that: **`ds_detect` is a static dual-SIM *config* module parameter
(default `1`), NOT a physical SIM-presence or SIM-attach signal.** The
authoritative, protocol-backed SIM state is the modem_state enum path:

- `IOCTL_MODEM_STATUS` (`_IO('o',0x27)`) returns, when `mc->sim_state.changed` is
  true, `STATE_SIM_ATTACH (7)` / `STATE_SIM_DETACH (8)`; otherwise the base
  `phone_state`.
- Live `nuxel-cp-status` (4 readings) returns `ONLINE` (state_code=4), i.e.
  `sim_state.changed == false` and no SIM attach has been signaled.
- Kernel `sim_state.online` is set only via `io_dev_sim_state_changed()`, which
  is invoked by the userspace **RIL** — which is absent. Therefore **SIM READY is
  NOT established** and the UI must show "SIM missing" (or "CP offline"), never
  "registered"/"attached"/"data active".

No IMSI/ICCID/IMEI/PIN/PUK was read or printed at any point.

## 3. Live CP/SIPC observation

The native `nuxel-radiod` holds `/dev/umts_ipc0` + `/dev/umts_rfs0` exclusively
and reports (D-Bus `nl.nuxel.Radio1.GetDiagnostics`, twice, ~10s apart):

```
RxFrames=1  RxBytes=76662   TxFrames=0
RawFrames=39 RawBytes=76637 RfsOps=1  RfsDestructive=1  RawUnclassified=38
```

Interpretation (honest): exactly one FMT frame (`AST_POWERON` boot notify) and
one RFS request (`DELETE_ALL_VIS`, destructive, fail-closed) plus 38 opaque
2040-byte bulk blobs (closed, UNKNOWN) were received. **`TxFrames=0`** — the AP
has never answered the CP. On radiod restart the CP re-booted
(ONLINE→OFFLINE→BOOTING→ONLINE) and re-sent the same boot/RFS requests, i.e. the
CP is **waiting on RFS/FMT service that is not present**, so it stalls before
registration. This is the first concrete data blocker (upstream of the FMT
vocabulary gate).

## 4. ModemManager / NetworkManager (exact-version, honest)

- MM `1.24.2-1.fc43`, plugin dir `/usr/lib64/ModemManager/` includes
  `libmm-plugin-samsung.so`.
- `strings`/`ldd` on the installed plugin show `MMBroadbandModemSamsung`, an
  **AT/`allowed-at` USB broadband** driver (tty/net/QMI/MBIM port probe), with no
  SIPC linkage. It cannot drive the S5000AP SIPC5 shared-memory chardevs.
- `mmcli -L` => `No modems were found` (correct, honest). No fake
  `org.freedesktop.ModemManager1` modem object was created.
- NM `1.54.3-3.fc43` lists `rmnet0..7:ppp:unmanaged` + `umts_dm0:ppp:unmanaged`
  (all DOWN). No WWAN/gsm connection is possible without a MM modem object.

**Determination:** a SIPC5 MM plugin is only the LAST integration layer; the FMT
telephony vocabulary + RFS service must be solved first. See
`tools/s10plus/s5000ap-06/docs/MM_NM_INTEGRATION.md`. No generic QMI/MBIM/PPP
code was pulled.

## 5. Deliverables added (committed)

- `tools/s10plus/s5000ap-06/src/radio_fsm.{h,c}` — pure truthful 9-state FSM
  (no modem / CP offline / SIM missing / PIN required / searching / registered /
  attached / data active / failure), monotonic gate ladder, zero side effects.
- `tools/s10plus/s5000ap-06/tests/test_radio_fsm.c` — 14 offline fixtures proving
  gate monotonicity + names; `RESULT=PASS`.
- `tools/s10plus/s5000ap-06/docs/MM_NM_INTEGRATION.md` — exact MM/NM ABI + honest
  determination.
- `tools/s10plus/s5000ap-06/build.sh`, `README.md`, `.gitignore`.
- `evidence/s5000ap-06-live/baseline.txt` — redacted live baseline.

Build/test receipt: `./build.sh` → `RESULT=PASS: 0 failures` (normal + ASan/UBSan).

## 6. Negative controls / what was NOT done

- No protected-partition write: BOOT/DTB/DTBO/RADIO SHAs unchanged (== Stage-05).
- No DT/CP modification; no flash; no `cdp`/`rild` boot; no speculative SIPC Tx.
- Wi-Fi and USB/Zerotier management links preserved; cellular data path not
  attempted because registration is not reachable (no data-charge risk).
- No PIN/PUK/IMSI/ICCID/IMEI capture. No brute-force. No roaming.

## 7. Blocker and next task

**Exact first blocker:** no protocol-backed SIM attach → CP stalls awaiting
RFS/FMT service. Root cause: closed FMT telephony vocabulary + absent vendor RIL.

**Next highest-value task (owner-gated):** extract the exact EFUJ2 vendor RIL
blobs (`rild`/`cass`/`libsec-ril.so`/`libril_sem.so`) read-only from the device
RADIO/vendor via an explicit TWRP pull (no flash), then run Option 1 (isolated
Bionic RIL + narrow D-Bus bridge) or, alternatively, produce an owner-approved
redacted FMT vocabulary trace for a clean-room `nuxel-radiod` extension. Until
then, SMS/voice/IMS remain false and LTE data remains BLOCKED with honest UI.

---

## 8. Post-investigation update: vendor RIL present, runtime absent (read-only mount)

Additional read-only partition inspection (mount `-o ro,noload`, no write, no
flash) established:

- `sda26` (PARTLABEL=`vendor`, ext4) contains the **exact vendor RIL blobs**:
  `libsec-ril.so`, `libsec-ril-dsds.so`, `libsec_semRil.so`,
  `libvndsecril-client.so`, `libril.so`, `librilutils.so`,
  `libreference-ril.so`, and `bin/hw/rild`.
- `sda25` (PARTLABEL=`system`, ext4) is the **leftover Android system image**; it
  retains Halium-style scaffolding (`/lib/systemd/system/rild.service`,
  `/etc/init/rild.conf`) that references an "Android container" + `/dev/socket/rild`
  + an oFono RIL driver (`OFONO_RIL_DEVICE`, `_OFONO_RIL_NUM_SIM_SLOTS`).
- The **running Nuxel rootfs is `sda31`** (LABEL=`nuxel-beyond2lte`); it does NOT
  contain `rild`, `cass`, a Bionic `linker64`, an LXC/Android container, or
  `/dev/socket/rild`, and no `ofonod`/`rild` process is present.
- `cass` (the Samsung RFS/NV server that the CP requires) was **not found** on
  the running rootfs (the vendor partition carries RIL, but `cass` is normally on
  the Android `system` or `vendor` `bin/`; it was not located read-only here).

Conclusion: the closed RIL vocabulary is physically available read-only in `sda26`,
but **driving it requires building the missing Bionic/container + oFono (Halium-
style) runtime and recovering `cass`**, which is a substantial, separately-reviewed
project beyond this stage's no-flash scope and cannot be safely completed here.
The read-only mounts were unmounted cleanly; no write occurred.
