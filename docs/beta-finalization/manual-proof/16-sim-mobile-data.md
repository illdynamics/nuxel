# Manual area 16 — SIM, modem and mobile data (S10+ / beyond2lte)

**Status: NEEDS_OWNER_TEST for the physical SIM; BLOCKED_FIRMWARE /
NOT_SUPPORTED_ON_DEVICE for cellular service** (repository side:
OFFLINE_TESTED for detection + diagnostic). Owner action required? **Yes** — a
SIM must be inserted by hand, and no cellular service can be claimed until a real
modem path exists.

**Device truth used by this document.** Samsung Galaxy S10+ (SM-G975F, Exynos
9820) with an integrated **Samsung Shannon LTE** modem (Cat 20, no 5G). There is
**no upstream ModemManager plugin for the Shannon LTE interface**, and the vendor
CP transport is not exposed to a mainline modem stack by this 4.14 vendor kernel.
The default verdict is therefore **NOT_SUPPORTED_ON_DEVICE / BLOCKED_FIRMWARE**.
Pixel / Exynos-5500 / Qualcomm modem instructions **must not** be applied to this
device. **EFS, IMEI, calibration and modem firmware are never read, written or
flashed.**

---

## 1. Feature

`configs/nuxel/modem/modem.json` + `tools/s10plus/a33/nuxel-modem-diag.sh`:

* **host-transport enumeration** (`/dev/cbd*`, `/dev/umts*`, `/dev/gsmtty*`,
  `/dev/wwan*`, `/dev/ttyUSB*`, `/dev/ttyACM*`) and possible **data netdevs**
  (`rmnet*`, `wwan*`, `pdp*`);
* **stack hop reporting** — ModemManager plugin dirs/globs and `mmcli`
  availability, with the missing Shannon plugin named as the blocker;
* **SIM presence from a real source only** (ModemManager modem list, or a
  detection state file); anything else is reported as *unknown*, never assumed;
* the **truthful registration contract**: `signal_quality`, `operator` and
  `registration_state` are printed **only** from a live ModemManager query and
  are `null` otherwise — never guessed;
* **redaction** of IMSI/ICCID/IMEI/ESN/MEID/MSISDN/SPN/PIN/PUK on every modem
  line (`nuxel-modem-diag.sh redact`);
* a **refused-by-default AT channel**: off unless the owner passes `--yes-at`
  with an allowlisted read-only command; radio-state, NV/EFS and raw-APDU
  commands are refused outright; nothing runs at boot;
* the protected-partition denylist (`modem`, `efs`, `efsg`, `sec_efs`, …) and the
  flashing-tool denylist (Heimdall/Odin/fastboot/Download Mode/TWRP).

## 2. Why this matters

Cellular is the subsystem where a fake is most tempting and most harmful: a
signal bar drawn from a config file, or a "registered" flag with no bearer
behind it, would make every later claim about this phone untrustworthy. The
mission is explicit — the modem is a known-unresolved subsystem with no upstream
plugin, so the honest deliverable is *detection, a named blocker and a diagnostic
that says which stage is missing*, plus a SIM workflow the owner can run the
moment a supported stack exists. Calls, SMS and mobile data are **not** claimed.

## 3. Preparation

1. Handset booted into Nuxel, screen on, **not** in charger-mode
   (`nuxel-power-diag.sh status`).
2. Console/SSH or the on-device terminal.
3. A nano-SIM (an active one is not required for detection) and the SIM tool to
   open the hybrid tray. **Never** touch EFS/IMEI/calibration, and never enter
   Download Mode for this test.
4. Snapshot first:

   ```sh
   nuxel-modem-diag.sh status          # transport, plugins, SIM source, verdict
   nuxel-modem-diag.sh status --json   # machine-readable
   nuxel-modem-diag.sh interfaces      # CP nodes + possible netdevs
   nuxel-modem-diag.sh plugin          # plugin dirs, mmcli, suitability note
   ```

   `NOT_SUPPORTED_ON_DEVICE` and `BLOCKED_FIRMWARE` are **expected** on this
   device today. They are recorded verdicts, not failures to retry — and they do
   not gate any other area.

## 4. Exact action

1. **SIM absent first:** with no SIM in the tray, run `nuxel-modem-diag.sh sim`.
   It must report `absent` **or** `unknown` — and it must never invent a SIM.
2. **Insert the SIM:** power off, pull the tray with the SIM tool, seat the
   nano-SIM in the tray's SIM position, reseat the tray, power on.
3. **Detect:** `nuxel-modem-diag.sh sim` and `nuxel-modem-diag.sh status`. On a
   supported stack the state moves to `present`; on this device the expected
   outcome is that the *transport/plugin* stages are still missing, and the
   verdict names the first missing stage. Record it verbatim.
4. **Carrier identity / signal / registration:** these are printed only if a live
   ModemManager query returns them:
   `mmcli -L`, `mmcli -m 0 --signal-get`, `mmcli -m 0` (when `mmcli` exists).
   If they are unavailable, record **"unavailable — no supported modem stack"**,
   not "no signal".
5. **Privacy check:** confirm the redaction path:
   `printf 'IMSI: 310150123456789\n' | nuxel-modem-diag.sh redact` must print a
   masked value. Then search any log you generated for a full IMSI/ICCID:
   there must be none.
6. **AT channel check (owner action only):**
   `nuxel-modem-diag.sh at --yes-at "AT+CGMI"` — it must refuse when no CP
   interface exists or when the transport is unverified, and it must refuse a
   non-allowlisted command such as `AT+EGMR=1,7`. **Never** send a radio-state,
   unlock, NV/EFS or raw-APDU command.
7. **APN/data:** confirm that the APN template exists in
   `configs/nuxel/modem/modem.json` and that the tool reports data as
   **unavailable** (`apn.state: NOT_SUPPORTED_ON_DEVICE`). Do **not** configure an
   APN and do **not** claim a data connection.
8. **VoLTE/calls/SMS:** read `docs/volte-carrier-strategy.md` and confirm the
   posture: VoLTE/IMS is not implemented; calls and SMS are **not available**.
   Do not test-dial an emergency number for this check.
9. **Remove the SIM** and confirm the state returns to absent/unknown, and that
   no error is raised by removal.

## 5. Expected result

* `status` reports the CP host interfaces, the ModemManager plugin situation, the
  `mmcli` path, the SIM state from a real source, and one verdict
  (`NOT_SUPPORTED_ON_DEVICE` / `BLOCKED_FIRMWARE` / `BLOCKED_KERNEL` / `NO_SIM` /
  `NEEDS_OWNER_TEST`) with the first failing stage named.
* `signal_quality`, `operator` and `registration_state` are `null` unless a live
  API returned them; `cellular_available` stays `false`.
* IMSI/ICCID/IMEI/PIN never appear in any output or log.
* `at` refuses without `--yes-at`, refuses non-allowlisted commands and refuses
  on a faked/offline root.
* Nothing probes the modem at boot and nothing touches a protected partition.

## 6. Failure symptoms (and what each one means)

| Symptom | Meaning |
|---|---|
| verdict `NOT_SUPPORTED_ON_DEVICE` | No CP host interface and no Shannon-capable plugin: the documented blocker. Record and move on. |
| verdict `BLOCKED_FIRMWARE` | A transport exists but the stack cannot talk to it (no plugin). This is the repair target for any future modem work. |
| verdict `BLOCKED_KERNEL` | A plugin exists but the kernel exposes no CP interface: kernel/DT work, offline only. |
| verdict `NO_SIM` | Transport + stack present but no SIM reported: insert a SIM and re-check (owner step). |
| Any signal/operator/registration value while no stack exists | **Defect**: report it, the value was fabricated. |
| A full IMSI/ICCID/IMEI in any log | **Defect**: report it immediately; redaction must mask them. |
| `at` opens a channel without `--yes-at` | **Defect**: report it; the AT channel is an explicit owner action. |
| A modem/EFS/calibration partition is read or written | **Critical defect**: report it; those are never touched. |
| Data "connects" although no bearer exists | **Defect**: report it, no data connection may be claimed. |

## 7. Diagnostic command / log path

* `nuxel-modem-diag.sh status [--json] | interfaces | plugin | sim | redact | at --yes-at <CMD> | report`
  (`tools/s10plus/a33/nuxel-modem-diag.sh`)
* Evidence log: `/var/log/nuxel/modem-diag.log`
* Kernel side: `ls -l /dev/cbd* /dev/umts* /dev/wwan* 2>/dev/null`,
  `ls /sys/class/net/`, `ip link`, `dmesg | grep -i -E 'modem|shannon|cp_|cbd'`
* Stack side (when installed): `mmcli -L`, `systemctl status ModemManager`,
  `ls /usr/lib*/ModemManager/plugins`
* Carrier posture: `docs/volte-carrier-strategy.md`
* Offline suite: `python3 tools/s10plus/a33/tests/hw-subsystems/test-modem-diag.py`
  and `nuxel-modem-diag.sh selftest` (4 fixtures: absent / transport-only /
  no-SIM / with-SIM).

## 8. PASS / FAIL

* **PASS** — the SIM workflow behaves as described (absent detected, insertion
  detected or the first missing stage named), the redaction path masks
  identifiers, the AT channel refuses without `--yes-at` and for non-allowlisted
  commands, and no fabricated signal/registration value appears anywhere. Record
  the verdict, the first failing stage, the CP node paths and the plugin/cli
  state. **Cellular service itself remains BLOCKED_FIRMWARE and is not a PASS.**
* **FAIL** — any of: a detected SIM that is not reported, a fabricated signal or
  registration value, an unmasked IMSI/ICCID/IMEI in a log, an AT channel opened
  without `--yes-at`, a protected partition touched, or a data connection claimed
  without a real bearer. Record the verdict, the stage, the exact output and the
  log path — that is what a repair cycle needs.

## Current automatic evidence (repository, this build group)

* `bash tools/s10plus/a33/nuxel-modem-diag.sh selftest` → 4/4 fixtures PASS
  (`fixtures/modem-absent`, `modem-cp-only`, `modem-nosim`, `modem-ready`).
* `python3 tools/s10plus/a33/tests/hw-subsystems/test-modem-diag.py` → all checks
  PASS (verdict chain, null signal/registration contract, `cellular_available`
  always false, redaction of IMSI/ICCID/IMEI/PIN, AT refusals, partition
  denylist, fragment completeness).
* Cellular service: **not claimed** — every `status --json` emits
  `"cellular_available": false` and `"registration_verified": false`, and the
  verdict is `NOT_SUPPORTED_ON_DEVICE` / `BLOCKED_FIRMWARE` unless a real stack
  appears.
