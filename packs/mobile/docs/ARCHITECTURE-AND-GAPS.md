# Nuxel S10+ mobile networking — source review and gap analysis

## Corrected architecture

The request is not just “write a Shannon ModemManager plugin”. The supplied archive contains two different levels of evidence:

1. `REPORT-MOBILE-NETWORKING.md` and the older SIM manual record a runtime where ModemManager finds no modem, no plugin exists, and the first failing stage was reported as host transport/plugin.
2. `docs/Samsung S5000AP - Exynos 9820 Native Linux Modem Bring-up for Nuxel.md` audits the exact Samsung downstream 4.14.253 kernel and cites Nuxel captures in which `sec_sipc_modem_if`, `modem_v1`, S5000AP control, SHMEM/SBD/SIPC5, `/dev/umts_boot0`, `/dev/umts_ipc0`, `/dev/umts_ipc1`, `/dev/umts_rfs0`, and `rmnet0`…`rmnet7` are created/probed.

The later runtime report and that deeper source/capture audit must be reconciled on the live phone. Do not simply assume either that the kernel transport is absent or that the captured interfaces are still available in the current boot.

The more complete bring-up chain is:

```text
Exynos 9820 / Shannon S5000AP CP
        |
        v
Samsung modem_v1 + S5000AP + SHMEM/SBD/SIPC5 kernel path
        |  (source and historical capture show this can probe)
        v
Exact G975F CP boot transaction / native replacement for Samsung cbd
        |  (not established in the archive)
        v
SIPC5 control + RFS service + SIM/registration/SMS/PDP protocol
        |  (not implemented/proven)
        v
A small tested S5000AP radio backend
        |
        v
Real ModemManager plugin mapped onto 3GPP / Messaging / Bearer
        |
        v
NetworkManager bearer + rmnet interface + IP route + DNS
        |
        v
Nuxel status bar + Settings + Phone / Messages / Contacts
```

The source doc specifically warns that exact `MODEM_ON` / boot / download / confirmation order, firmware section offsets, G975F secure-boot preparation and RFS namespace must not be guessed. It recommends CP bootstrap and S10-specific SIPC/RFS work before ModemManager integration. That is the correct sequencing.

## Conflicts the agent must resolve

- `configs/s10plus/modem/README.md` says “opaque CP transport” and “no ModemManager plugin”; it is incomplete relative to the deeper source audit.
- `configs/nuxel/modem/modem.json` describes `rmnet*` as candidates and assumes a missing plugin, but its explanatory text claims the vendor CP transport is not exposed to a mainline stack.
- `REPORT-MOBILE-NETWORKING.md` says no `rmnet*` netdev was present in its tested run, while the October kernel capture cited in the S5000AP document shows the driver creating them. Re-check on the live boot; record timestamp and kernel build.
- Two offline fixtures include empty, zero-byte files named `samsung-shannon.so`. They are placeholders and must never count as a plugin. Plugin tests must verify ELF magic, architecture, dependencies, successful ModemManager load, actual device match, and live DBus object creation.
- `nuxel-dialer` currently treats the presence of any ModemManager modem as evidence for calls, SMS, and data. This is too broad: expose each capability only when its specific interface/operation is implemented and tested.
- `nuxel-messages` has explicit local/mock fallback paths. Those may remain for offline use, but UI must label them as local/mock and never report a mock SMS as sent.
- `nuxel-contacts` has a SIM mirror. It is not a physical SIM phonebook; do not label it as such. Replace with a real SIM phonebook integration only when ModemManager exposes a genuine SIM object and list/read/write support.

## What is missing from this archive

- Exact SM-G975F-matched, legally obtained CP firmware image/source package for analysis.
- Verified matching Samsung `cbd` boot transaction or trace (ioctl ordering, `modem_firmware` structure/offsets, section mapping, secure boot handshake and completion semantics).
- Validated RFS operation set and safe pathname contract.
- S10-generation SIPC5 command dictionary and request/response/unsolicited indication definitions for SIM, registration, signal, APN/PDP, SMS and (later) call control.
- A tested native S5000AP radio service/library.
- A loadable, exact-version-built ModemManager plugin.
- Live device proof of SIM presence, network registration, LTE bearer, routed traffic, DNS, and Wi-Fi-off mobile Internet.

This pack does not include proprietary CP firmware, `cbd`, secure-world payloads, calibration/NV data, or a made-up plugin. Use only a matching official stock firmware package supplied/approved for analysis. Do not dump or flash the protected modem partition to work around missing source artifacts.

## Reflash interpretation

Mobile networking is `PARTIAL / YES` in `REFLASH-PLAN.md`: the eventual radio service/plugin belongs in the system image; a boot/kernel/DT update is needed only if live evidence proves the existing transport or required driver options are absent. The S5000AP audit suggests the kernel piece may already be present. Do not reflash solely to add a plugin before verifying the active kernel. If the separately authorised NFC/USBNET work requires a kernel update, batch genuinely required modem kernel changes into that same build.

## Minimal live evidence before any CP operation

- Exact board identity and running kernel build.
- `dmesg` probe sequence for S5000AP, modem_v1, SHMEM/SBD, mailbox, `umts_*` nodes and `rmnet*` creation.
- `/dev/umts_boot0` node type/mode and read-only `MODEM_STATUS` result via `s5000ap-status`.
- Current `mmcli -L` result, ModemManager version, actual plugin directory contents and daemon logs.
- Current network interfaces and whether rmnet netdevs exist.
- Current state of `ModemManager` and `NetworkManager`.

The evidence collector included in this pack gathers this without accessing modem/EFS/NV/calibration partitions or SIM identifiers.
