# PWNAGE MOBILE — S10+ Shannon cellular quick-start

Work in `./` on the Nuxel repo for Samsung Galaxy S10+ SM-G975F / `beyond2lte`, Exynos 9820, Nuxel Fedora ARM64, kernel 4.14.253.

We start in **TWRP connected over USB**; the SIM stays inserted for the entire mission. Deploy/flash scripts are in `./scripts`. When Nuxel boots, connect with:

```sh
ssh -i ~wicked/.ssh/wicked_wqn_id_rsa -o IdentitiesOnly=yes root@192.168.178.167
```

## Mission

Fully bring up real native Shannon/S5000AP cellular service: SIM detection, CP boot, SIPC5/RFS radio backend, registration, signal/access technology, LTE/2G/3G data bearer, NetworkManager integration, real ModemManager plugin, Permission Manager, Phone/Messages/Contacts integration, and truthful status-bar indicators. Deploy live and verify on the actual phone.

## Crucial correction — plugin is not the first missing layer

Read `REFLASH-PLAN.md`, `REPORT-MOBILE-NETWORKING.md`, and especially `docs/Samsung S5000AP - Exynos 9820 Native Linux Modem Bring-up for Nuxel.md`. The deep exact-device audit says the existing kernel already contains the S5000AP modem-v1 + SHMEM/SBD/SIPC5 transport and has historically probed `umts_boot0`, `umts_ipc0/1`, `umts_rfs0` and `rmnet0…rmnet7`. The older runtime report says those data interfaces were not present in its boot. Reconcile this with live evidence before changing the kernel.

The real order is:

1. Verify live transport and read-only CP state.
2. Obtain the exact matched G975F firmware/stock `cbd` behavior and prove the CP boot transaction (never guess ioctl order or image offsets).
3. Implement the native CP bootstrap.
4. Implement constrained RFS and validated S10 SIPC5 radio backend.
5. Prove SIM, registration, signal and a real PDP/rmnet bearer.
6. Implement the genuine ModemManager plugin against the exact packaged MM version.
7. Integrate NetworkManager, Permission Manager and the three phone apps.
8. Deploy and do the final Wi-Fi-off cellular Internet test.

Do not fake a plugin. The archive contains zero-byte `samsung-shannon.so` fixture placeholders; remove/repair any tests that regard them as loadable. Do not start with guessed AT/QMI/MBIM/PPP assumptions.

## Start and recover

- Verify exactly one `adb devices -l` target. Use `python3 tools/acquire-s10plus-modem-evidence.py --transport adb --profile twrp` from this pack for read-only TWRP evidence.
- Inspect the live kernel, dmesg S5000AP probe, config, `/dev/umts*`, `rmnet*`, current `mmcli -L`, plugin files and ModemManager/NetworkManager.
- Build/flash only if the evidence proves a kernel/DT change is necessary or it is part of the NFC/USBNET batch. Use the repository's existing scripts under `./scripts`; inspect them first, backup and preserve rollback. Never touch userdata/rootfs, modem, EFS/EFSG/SEC_EFS, persist, NV, calibration, RPMB, key storage, or carrier partitions.
- If a flash/reboot returns to TWRP, that is a **failed Nuxel boot**. Capture logs, root-cause, fix, rebuild, reflash through the repo script and reboot. If it reaches Nuxel, that is success; continue over Wi-Fi SSH above. No blind identical retries; at most three tries for one unchanged failure signature, each retry requires a meaningful fix.
- Keep Wi-Fi on while the SSH session is needed. Before the final Wi-Fi-off test, keep a USB/serial/local console or a pre-launched on-device test job so disabling Wi-Fi cannot destroy the only control channel.

## Permissions

Audit the existing registry first. It already has `phone_status`, `call` (alias `phone`), `sms`, `contacts`, `network`, and a deliberately unsupported `sms_send_raw`. Do not duplicate these. Add only required granular permissions:

- `cellular:manage` — privileged first-party Settings radio/data/APN control, default deny to apps.
- `sim_contacts:read` and `sim_contacts:write` — separate high-risk SIM phonebook permissions; read preview/merge, write one confirmed entry at a time.
- `phone_status` — read-only signal, registration and access technology, never IMSI/ICCID/IMEI.
- `call` / `sms` — explicit grants and portal-mediated calls/messages; raw modem commands remain unsupported.
- `network` — app Internet permission only, not direct `/dev/umts_*` access.

Enforce through the real Nuxel permission daemon/portal; default deny; audit direct D-Bus bypasses. Do not make a capability appear available before its backend works.

## Top-bar UI

Extend the existing `#status-signal` cellular slot and `#status-wifi` implementation in `pwa/nuxel-home/js/status-bar.js`, `css/status-bar.css`, `index.html`, and canonical status model. Do not add duplicate indicators.

- Cellular: five ascending bars; green only when real modem registration + live signal quality are available. Display compact `2G`, `3G`, or `4G` from the actual access-technology field (GSM/EDGE/GPRS=2G, UMTS/WCDMA/HSPA=3G, LTE=4G; S10+ has no 5G). When not registered/no SIM/searching/unavailable/unknown, show white glyph with a red diagonal strike and no fake generation label.
- Wi-Fi: real NetworkManager AP strength drives the visible arcs/levels. When Wi-Fi is enabled but not connected, show white glyph, no active arcs/bars, and a red diagonal strike. Connected Wi-Fi shows true measured quality. Distinguish link-connected from Internet-verified.
- Handle stale/unknown data separately from zero strength. Clear green immediately when modem registration is lost. Preserve top-bar safe zones and user icon visibility settings.

## Apps and acceptance

- Dialer: only claim call capability after actual ModemManager Voice support and real call operations exist. No emergency test calls.
- Messages: real Messaging Send + receive indications. Local/bridge mock messages remain labelled local/queued and are never “sent”. Ask before any chargeable real SMS.
- Contacts: current SIM mirror is not a physical SIM. Integrate real SIM phonebook list/read/write; preview/merge reads, confirm each write, never bulk overwrite.
- Data: active SIM, real registration, correct APN/PDP response, correct rmnet device, IP/DNS/default route, DNS lookup and HTTPS must all succeed while Wi-Fi is off. Keep test traffic minimal and warn about carrier data charges.
- Verify permissions in grant/deny/revoke cases, no app bypass to CP nodes or raw ModemManager D-Bus.
- Verify the top-bar state with live device screenshots and offline fixtures.
- Never log IMSI/ICCID/IMEI/MSISDN/PIN/PUK; never touch protected partitions; never include proprietary CP firmware in the repo.

## Final verdict

Continue each real fix/rebuild/deploy/test cycle until the acceptance matrix passes. `FULLY_DONE` only after actual SIM, registration, mobile-only Internet, plugin load, permission enforcement, app integrations and reboot persistence all pass. If the exact OEM CP firmware/boot protocol, RFS protocol, or carrier/IMS support is absent, document the precise blocker instead of faking service. Produce `REPORT-MOBILE-NETWORKING.md`, protocol/backend/plugin source and tests, updated permissions/apps/UI, reflash manifest and `PWNAGE-MOBILE-REPORT.md` with live evidence and hashes.
