# S5000AP Stage-06 — ModemManager / NetworkManager integration determination

SPDX-License-Identifier: CC-BY-SA-4.0
Status: RESEARCH COMPLETE on physical device (live), honest determination recorded.

## 1. Exact pinned versions (live, this device)

| Component | Version | Source |
|---|---|---|
| ModemManager | `ModemManager 1.24.2-1.fc43` | `ModemManager --version` (live) |
| mmcli | `mmcli 1.24.2` | `mmcli --version` (live) |
| NetworkManager | `1.54.3-3.fc43` | `NetworkManager --version` (live) |
| kernel | `4.14.253-gf7194c1d15ed-dirty` | `uname -r` (live) |
| MM plugin dir | `/usr/lib64/ModemManager/` | live listing |

## 2. ModemManager `samsung` plugin — real capability vs S5000AP

The device ships `libmm-plugin-samsung.so` (part of `ModemManager` 1.24.2).
Live `strings`/`ldd` on the installed `.so` prove it is:

- `MMBroadbandModemSamsung` — an **AT-command broadband** modem driver.
- Depends only on glib/gobject/libc (no SIPC linkage).
- Uses port props: `base-modem-physdev-path`, `base-modem-data-tty-supported`,
  `base-modem-data-net-supported`, `allowed-at`, `allowed-product-ids`.
- It discovers devices via **USB tty / net (AT/QMI/MBIM/PPP) ports**, which MM
  probes through its kernel port drivers (option/cdc-acm/qmi_wwan/cdc_mbim).

The S5000AP modem in this handset is a **Shannon 5185 over SIPC5 shared-memory**,
exposed as character devices `/dev/umts_ipc0|ipc1|rfs0|cass|csd|dm0|router|boot0`
(NOT USB tty ports). There is therefore **no USB/AT/QMI/MBIM port** for MM to
probe, and the `samsung` plugin does not speak SIPC5.

Live confirmation:
- `mmcli -L` => `No modems were found` (correct, honest result).
- `mmcli --scan-modems` => `successfully requested to scan devices` (no object).

**Conclusion (honest):** The shipped MM 1.24.2 `samsung` plugin cannot drive the
S5000AP SIPC5 CP. Building a "Shannon/SIPC5 MM plugin" would require writing a
custom `MMBroadbandModem` subclass that replaces the AT/QMI port transport with
SIPC5 FMT/RFS transport — and that subclass still cannot populate SIM/registration/
bearer without the **closed FMT telephony vocabulary** (see Stage-05 §11). A
SIPC5-MM plugin is therefore only the *last* integration layer; the vocabulary
gate must be solved first.

## 3. ModemManager plugin ABI (pinned 1.24.2)

- Plugins are `.so` modules implementing `MM_PLUGIN` GObject type with
  `mm_plugin_create()` entry point, loaded from the plugin dir at startup.
- A plugin's `create_modem()` returns an `MMBroadbandModem` (or subclass) bound
  to a `MMBaseModem` with discovered ports (`MMPortSerialAt`, `MMPortQmi`,
  `MMPortMbim`, `MMPortNet`).
- udev rules publish `ID_MM_PHYSDEV_UID`, `ID_MM_PORT_TYPE_*`,
  `ID_MM_CANDIDATE` tags so MM knows which ports to grab.
- For S5000AP there are **no udev USB port events**; `/dev/umts_*` are misc
  devices created by the `modem_v1` driver at boot and owned `root:root
  crw-------` (live). No udev MM rule tracks them, and MM's daemon does not open
  arbitrary chardevs.

## 4. NetworkManager (1.54.3) reality vs requirement

- NM device list (live `nmcli -t device`) shows `rmnet0..7:ppp:unmanaged` and
  `umts_dm0:ppp:unmanaged`. These are the S5000AP PDP netdevices, all `state DOWN`.
- No `cdc-wdm`/`qmi_wwan`/`wwan` device exists, so `nmcli connection add type gsm`
  (WWAN/ModemManager) has no modem object to bind to.
- An owner-approved APN profile and `ipv4.method/ipv6.method` behavior therefore
  **cannot be exercised** until a ModemManager modem object exists — which is
  blocked on the FMT vocabulary gate (and, upstream of it, RFS).

## 5. The actual Stage-06 data gate ladder (all kernel/vendor-sourced truth)

1. CP ONLINE ................ **PASS** (kernel `phone_state=4` via IOCTL_MODEM_STATUS).
2. SIPC alive ............... **PASS** (radiod holds `umts_ipc0`+`umts_rfs0`; real frames).
3. SIM READY (protocol) ..... **BLOCKED**. `IOCTL_MODEM_STATUS` returns `ONLINE`,
   NOT `STATE_SIM_ATTACH`. Kernel `sim_state.online` is set only when the
   userspace RIL signals SIM attach; no RIL is present. (`ds_detect=1` is a static
   dual-SIM config flag, NOT physical presence — this is corrected vs Stage-05.)
4. REGISTERED (operator/RAT) . **BLOCKED** (requires RIL FMT registration query).
5. DATA BEARER (rmnet) ...... **BLOCKED** (requires PDP setup FMT commands).

## 6. What would unblock (documented, not executed)

- **A.** Obtain the exact `rild`/`cass`/`libsec-ril.so`/`libril_sem.so` vendor
  blobs for this EFUJ2 image (from the device's RADIO/vendor partition via the
  existing TWRP read-only pull), then run them in an isolated Bionic runtime with
  a narrow, authorization-checked D-Bus bridge (Architecture Option 1).
- **B.** Or obtain an owner-approved, redacted live trace of the closed RIL FMT
  vocabulary so a minimal native `nuxel-radiod` can reconstruct SIM/registration/
  bearer requests lawfully (Clean-room).
- Neither is executed here because the blobs are not present on the running
  rootfs and their extraction touches only read-only vendor storage that requires
  a separate, explicit owner action (not silent flashing).
