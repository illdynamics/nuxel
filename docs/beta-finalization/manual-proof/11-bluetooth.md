# Area 23 — Bluetooth (S10+ / beyond2lte)

**Status: NEEDS_OWNER_TEST** (repository side: OFFLINE_TESTED for config + diagnostic).
Owner action required? **Yes** — pairing needs a second device (a peer).

**Device truth used by this document.** Samsung Galaxy S10+ (SM-G975F, Exynos
9820): Broadcom **BCM4375** (Wi-Fi 6 + **BT 5.0**) behind the Samsung glue; the
Samsung vendor HCD is **`bcm4375B1_semco.hcd`**. Adapter presence, rfkill state,
module binding, HCD presence and the bluetoothd unit are reported per stage by
`nuxel-bluetooth-diag.sh` — a registered module is **not** proof that the radio
works, and configuration alone is **not** a pairing. Nothing powers the adapter
at boot (`AutoEnable = false`).

---

## 1. Feature

* `configs/nuxel/bluetooth/bluetooth.json` — evidence sources, the stage order
  (`adapter → rfkill → module → firmware → service → pairing`), the verdict set
  and the owner pairing procedure.
* `configs/nuxel/bluetooth/main.conf.d/60-nuxel.conf` — BlueZ drop-in:
  `AutoEnable = false`, `ControllerMode = dual`, `Privacy = device`,
  `JustWorksRepairing = confirm`, no stored credentials.
* `tools/s10plus/a33/nuxel-bluetooth-diag.sh` — `status`, `firmware`, `on`,
  `off`, bounded `scan`, `report`, `selftest`.

## 2. Why this matters

Bluetooth is the wireless path for audio, file transfer and peripherals, and it
is the classic place where a repository lies to itself ("the module loaded, so
Bluetooth works"). The mission forbids that: this diagnostic names the **first
failing stage** with the evidence that produced it, and the terminal verdict
stays `NEEDS_OWNER_TEST` until a real peer pairs and a real data path is used.

## 3. Preparation

1. Handset booted into Nuxel, screen on, **not** in charger-mode.
2. A **second device** (phone, laptop or speaker) with Bluetooth on and
   discoverable, charged and within a metre.
3. Console/SSH or the on-device terminal.
4. Snapshot first — this decides whether pairing is even possible:

   ```sh
   nuxel-bluetooth-diag.sh status          # per-stage evidence + verdict
   nuxel-bluetooth-diag.sh status --json   # machine-readable
   nuxel-bluetooth-diag.sh firmware        # HCD candidate inventory
   ```

   * `BLOCKED_HARDWARE` → no adapter, no rfkill entry, no module: stop; this is
     kernel/driver-side (offline work), not a retry loop.
   * `BLOCKED_FIRMWARE` → the stack is there but the HCD blob is missing; deploy
     the HCD into `/lib/firmware/brcm` (a repository-only step — **never** a
     flash) before pairing.
   * `RFKILL_BLOCKED` → run `nuxel-bluetooth-diag.sh on` (it does not happen at boot).

## 4. Exact action

1. **Firmware evidence first:** `nuxel-bluetooth-diag.sh firmware` — note which
   candidate file is `FOUND` (or that none is).
2. **Power the adapter (explicit):** `nuxel-bluetooth-diag.sh on` → re-run
   `status`; `adapter: present:hci0` and `rfkill: unblocked:…` are required.
3. **Make the peer discoverable** on the second device (its Bluetooth settings,
   "visible to all").
4. **Bounded scan:** `nuxel-bluetooth-diag.sh scan 15` → the peer's **MAC
   address** must appear. Record it.
5. **Pair + trust + connect** (typing the confirmation on both devices if
   prompted):
   ```sh
   bluetoothctl pair <PEER_MAC>
   bluetoothctl trust <PEER_MAC>
   bluetoothctl connect <PEER_MAC>
   bluetoothctl info <PEER_MAC>        # must show Connected: yes
   ```
6. **Prove the DATA path, not just the link:** play ~10 s of audio to a Bluetooth
   speaker/headset **or** send one file to a laptop. A connected-but-silent link
   is a FAIL, not a PASS.
7. **Leave the phone as you found it:** `bluetoothctl disconnect <PEER_MAC>` then
   `nuxel-bluetooth-diag.sh off`.
8. **Persistence check:** reboot normally and confirm the adapter is *not*
   auto-powered (`AutoEnable=false`); it must only come up after `on`.

## 5. Expected result

* `status` prints each stage's real evidence and the first failing stage; with a
  healthy stack: `adapter: present:hci0`, `rfkill: unblocked:…`,
  `module: loaded:…`, `firmware: found:…`, verdict `READY_FOR_PAIRING`.
* `scan 15` lists the peer with its MAC.
* `pair`/`trust`/`connect` succeed and `bluetoothctl info` shows `Connected: yes`,
  and the exercised data path (audio or a file) really works.
* Nothing powers the adapter at boot; `off` returns it to the found state.

## 6. Failure symptoms (and what each one means)

| Symptom | Meaning |
|---|---|
| verdict `BLOCKED_HARDWARE` (stage `adapter`) | No `hci` node, no bluetooth rfkill entry and no driver module: the radio never came up. Kernel/driver work (offline). |
| verdict `BLOCKED_FIRMWARE` (stage `firmware`) | Stack present, no HCD blob in `/lib/firmware/brcm`. Deploy the blob (repository-only); never flash a partition. |
| verdict `RFKILL_BLOCKED` | A software/hardware RF kill switch is on: `nuxel-bluetooth-diag.sh on`, or check the airplane-mode/`rfkill` policy. |
| verdict `PARTIAL` | Some stages present, some missing — read the per-stage lines; do not guess. |
| Scan sees nothing | Peer not discoverable, out of range, or the adapter is not powered. Not automatically a failure — report as unproven, never PASS. |
| Pair fails with "AuthenticationFailed"/"AlreadyExists" | Remove the stale link key (`bluetoothctl remove <MAC>`) and retry once; if it fails the same way twice more, change strategy (peer-side). |
| Connects but no audio/file | Data-path failure: capture `journalctl -b -u bluetooth --no-pager | tail -100` and report FAIL. |
| Adapter powers up at boot | A real defect: `AutoEnable` was overridden. Report the effective config from `bluetoothctl show`. |

## 7. Diagnostic command / log path

* `nuxel-bluetooth-diag.sh status | firmware | on | off | scan [secs] | report`
  (`tools/s10plus/a33/nuxel-bluetooth-diag.sh`)
* Evidence log: `/var/log/nuxel/bluetooth-diag.log`
* Kernel side: `dmesg | grep -i -E 'bluetooth|hci|btbcm|bcm4375|hci_uart|rfkill'`
* BlueZ: `journalctl -b -u bluetooth --no-pager | tail -100`; `bluetoothctl show`,
  `bluetoothctl devices`
* Offline suite: `python3 tools/s10plus/a33/tests/hw-subsystems/test-bluetooth-diag.py`
  and `nuxel-bluetooth-diag.sh selftest` (4 fixtures: absent / no-firmware /
  rfkill-blocked / ready).

## 8. PASS / FAIL

* **PASS** — steps 2–8 all hold: adapter enumerated and unblocked, the peer found
  by MAC, pair/trust/connect to `Connected: yes`, and the exercised data path
  carrying real audio or a real file; the adapter is not auto-powered at boot.
* **FAIL** — any of: no adapter, no HCD, rfkill blocked, the peer never appears,
  pairing fails three ways, or the link connects but carries no data. Record the
  **exact verdict string and the first failing stage** — that names the layer and
  is what a repair cycle needs.

## Current automatic evidence (repository, this build group)

* `bash tools/s10plus/a33/nuxel-bluetooth-diag.sh selftest` → 4/4 fixtures PASS
  (`fixtures/bluetooth-absent`, `bluetooth-nofw`, `bluetooth-blocked`,
  `bluetooth-ready`).
* `python3 tools/s10plus/a33/tests/hw-subsystems/test-bluetooth-diag.py` → all
  checks PASS (stage/verdict logic, BlueZ drop-in syntax with `AutoEnable=false`,
  no credentials, bounded scan, faked-root safety, fragment completeness).
* Pairing: **not claimed** — every `status --json` emits `"pairing_verified": false`
  and the capability manifest keeps the radio at `NEEDS_OWNER_TEST` with the
  default state derived from the real stages found at runtime.
