# Exynos 5500 + ModemManager — status & engagement notes

This file is the "people / plugin status" reference for the **Samsung Exynos
5500** modem in Nuxel. It is the companion to `docs/driver-status.md` and
`configs/modem/nuxel-modem-setup.sh`.

## 1. ModemManager plugin status

> **The roadmap's claim that ModemManager "detects the modem" as a completed
> item is aspirational and is now corrected.** Truth:

The **Exynos 5500 has no plugin in mainline ModemManager**. ModemManager plugins
cover Samsung 5G modems largely through the generic MHI/PCIe port and the
open-source `mmcli` "samsung-generic" handling only when the modem exposes a
standard `+CPIN`/`+CFUN`/AT set via the transport. The Exynos 5500 (PCIe
vendor `0x144d`, device `0x0a80`) needs:

* the MHI bus to enumerate the modem's PCIe endpoint (kernel support),
* the baseband firmware (`modem.bin` ~200 MB from the `modem` partition)
  loaded and the CP booted,
* an AT transport (ATS over MHI) visible to ModemManager.

Until those three hold, `mmcli -L` returns nothing and the modem is "not
detected". This is expected until Phase-2 hardware bring-up.

### Corrections applied to `docs/driver-status.md`

* The "ModemManager plugin" row is marked **❌ TODO** (no Exynos 5500 plugin).
* The "MHI plugin" row is corrected (no `CONFIG_MHI_SAMSUNG_EXYNOS5500` in
  mainline; MHI is a **generic** PCIe transport).
* Everything else (calls, SMS, LTE, 5G, VoLTE) is re-marked honestly as Pending
  / not yet reached hardware.

## 2. What Nuxel actually uses today (VM)

* `nuxel-messages` → ModemManager **Messaging** API (SMS) in the VM is served
  by the **mock ModemManager** in `nuxel-bridge`, not a real MM plugin.
* `nuxel-dialer` → ModemManager **Voice** API, likewise mocked in the VM.

None of this implies the Exynos 5500 plugin exists — it does not.

## 3. People to engage upstream (`docs/upstream-engagement.md`)

* **Freedesktop ModemManager** — report missing Samsung Exynos 5500 plugin and
  request EDS/ATS transport support.
* **Google / Android** — the modem's closed-source CP is controlled by Google's
  `vendor` partition; upstream can only ever see the MHI netlink, not the CP.
* **pmOS** — Exynos 5500 (Tensor G5) is not yet in pmOS device support (no
  mustang device); helpful place to track.

## 4. Actions before hardware

1. Obtain a valid **per-device Exynos 5500 key** (blocked on vendor).
2. Extract `modem.bin` etc. via `firmware/install-firmware.sh`.
3. Confirm the MHI bus reaches the modem with
   `configs/modem/nuxel-modem-setup.sh`.
4. Only then open a ModemManager issue / add a real plugin.

## 5. Related

* `docs/driver-status.md` — the authoritative, corrected state table.
* `docs/volte-carrier-strategy.md` — VoLTE/IMS carrier roadmap.
