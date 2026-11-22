# Nuxel SM-G975F NFC — source and evidence audit

**Date:** 2026-11-22. **Scope:** extracted `nuxel-ds-ssp (1)(1).zip` (20,860 ZIP entries, ~796 MB uncompressed; no `.git`, `reports/`, or kernel `s10plus/.build/src`/`out` found). **Analysis method:** inspect code, patches, hardware history, dated evidence and run offline unit tests. **No SSH, no physical device action, no flash, no live NFC read** was performed for this audit. Distinguish **ZIP present**, **historically observed live**, **inferred**, **unverified current live**.

## Bottom line

**45% engineering maturity (indicative 35–50%)** for owner-initiated **read-only NFC-A/Type-2 tag scanning**. **0% of the final physical-acceptance gate** because no two-tag UID/NDEF read has been demonstrated. The stack is materially developed, but **the NCI layer is not proven operational** and the present userspace implementation has deterministic blockers even if hardware were made ready. This does NOT mean a card can be read 45% of the time. It means roughly that much of the integration and investigative workload appears completed, with uncertainty concentrated in the riskiest hardware stages.

## Evidence and timeline

| Date | Finding | Evidence class and source |
|---|---|---|
| Oct 16–18 | NFC config, diagnostic fixture tests, daemon, NCI/NDEF parsers, local socket, permission-mediated bridge/Settings hooks developed. NFC default OFF. No physical tag success. | ZIP + historical report `docs/beta-finalization/live/PWNAGE-65000-NFC-REPORT.md` and `manual-proof/12-nfc.md` |
| Nov 9 | Downstream `sec_nfc` successfully probes board I2C path, logs IRQ=10, VEN=188, FIRM=189, clock-request GPIO=22. NFC core registered. | Historical live journal `evidence/pwnage-100000/live/initial/journal-current-kernel.txt` |
| Nov 12 (referenced, report absent) | S3FWRN5-derived kernel NCI path once registered `/sys/class/nfc/nfc0`; GET_BOOTINFO reported `82.00.01.00`, 4,096-byte sectors, 512-byte pages and nonstandard 23-byte layout; `CORE_RESET` got no response; `oscclk_nfc` was reported 0 Hz. | SECONDARY reference in `hw/NUXEL_01_NFC_S3NRN82_STANDALONE.md`, **not directly independently verifiable from missing `reports/NFC-STATUS-20261112.md`** |
| Nov 14 | Three reproducible kernel panics after an NFC-triggered firmware download on kernel `#95`, trace `sha1_ce_transform -> ... -> s3fwrn5_fw_download -> nci_dev_up`; device went to TWRP. | Historical direct `evidence/live-20261114/BOOTLOOP-ROOT-CAUSE.md` and last_kmsg |
| Nov 15–16 (referenced) | Back to legacy `/dev/sec-nfc` fallback, daemon default OFF; `nfc0` generic class previously seen but no tag read; known software/clock blocker. | `final-state-components.md`, `hw/00_AUDIT_AND_EXECUTION_ORDER.md`. `reports/final-summary.md` is **not present** in this ZIP |
| Nov 22 ZIP | Patches and code are included, but there is no proof which precise kernel/DT/firmware is currently **running**. NFC prompt files `pwn/nfc*.md` do not exist. | ZIP inventory |

## Implementation inventory

| Layer | Source files | Status from ZIP/history | Assessed maturity |
|---|---|---|---:|
| Board & bus identity | `device/s10plus/deviceinfo`, config, `sec-nfc` logs | SM-G975F; S3NRN82; `7-0027`; strap/IRQ/clock-request mapping historically observed; device revision must be verified again | 90% |
| Vendor firmware provenance | `configs/nuxel/nfc/nfc.json`, `evidence/live-20261114/sec_s3nrn82_firmware.bin` | Actual bundled image SHA-256 **d315cd8bf47d90b7537aa978cb52299b7f2a56e8748588fb980b83ee823c0bfb**, 151,852 bytes matches manifest; controller acceptance NOT proved | 90% |
| Vendor sec-nfc fallback | `evidence/live-20261114/src-nfc-worktree-090558/sec_nfc.c`, patches 0017/18/19 | Probe, misc device and vendor mode control historically observed; not a proven user-readable NCI transport | 70% |
| Adapted kernel NCI path | `kernel/s10plus/patches/0007-nuxel-sec-nfc-nci-transport.patch`, `0021-nuxel-s3nrn82-nci-read-and-strap.patch` | Extensive modifications for arbitration, parity/framing, 23-byte bootinfo, strap, clock hold, setup/retries. `CORE_RESET` not proved. Current application state unknown | 40% |
| Firmware/SHA boot safety | `0023-nuxel-nfc-fw-sha1-stack-safe.patch`, crash evidence | Candidate SHA change present but not proved live, `.required` marker absent; automatic update remains in source patch and triggered by `force_fw_update=true` | 25% |
| Standard Linux NCI userspace | `services/nuxel-nfc/nuxel_nfc/kernel_nci.py` | Generic-netlink and AF_NFC client exists, but ACK, socket lifecycle, response/permission gaps prevent proper use | 35% |
| NCI + NDEF parser/types | `nci.py`, `ndef.py`, `defs.py` | Meaningful implementation; 26 applicable mocks/parsers pass offline. Not proof that live controller uses same transport | 80% |
| Daemon + permissions + UI | `daemon.py`, `policy.py`, `systemd/nuxel-nfcd.service`, bridge provider, PWA | Default-off and socket/permission concept built; permission bug, sandbox AF_NFC omission, wrong tag activation object, stale status flags | 65% |
| Real RF / owner-tag acceptance | no physical evidence | Two distinct real tags never demonstrated; no repeated verified discovery/NDEF | 0% |
| Regression and recovery | hw prompts, tests, crash report | A-only/TWRP details known; proven reproducible NFC-caused kernel panic; no verified new safe boot with NFC enabled | 25% |

These layer percentages are **subjective audit judgments**, **not** formal earned-value or probabilistic success measures. More weight is placed on NCI, RF, stability and safety than on UI/test scaffolding to obtain the 45% overall estimate.

## What was rewritten / ported

- Device-level identification and software policy: replaced guessed generic NFC description with Samsung S3NRN82, vendor firmware provenance, `7-0027`, and a default-OFF daemon/diagnostic flow.
- Kernel NFC **not wholly rewritten from scratch**: adapted native Linux `s3fwrn5` NCI driver to Samsung's board resources and bootloader protocol. `0007` is a large transport/firmware/IRQ/clock/driver-arbitration patch. `0021` changes NCI read draining, firmware/NCI reply classification, rail/FIRM strap sequencing, and failure handling.
- Separate Samsung `sec_nfc` vendor driver patches: `0007-sec-nfc-class-name` prevents a duplicate NFC sysfs class; `0017` attempts to decouple reader transport from payment/eSE check; `0018` enables reference clock; `0019` maintains clock during an active transport session.
- `0012-nuxel-nfc-s3fwrn5-board-bind.patch.retired` intentionally retired; **do not resurrect this DT patch merely because NCI is blocked**. Drivers can conflict over one I2C address; audit binding in the actual boot.
- `0023-nuxel-nfc-fw-sha1-stack-safe.patch` changes firmware SHA hashing strategy and selects `sha1-generic` preferentially. The patch is present but has no `.required` sidecar. Its comment claims a residual SHA1 finalize-tail explanation that is not established: **151,552 is divisible by 64**. Reproduce the failure mechanism from code/disassembly and prove the exact running implementation, not just trust the patch's narrative.
- Python: standalone local daemon, schema/state, NDEF parser/encoder, NCI raw fallback, generic netlink / AF_NFC client, Settings/Quick Settings API path, permission grant store, diagnostic CLI, preflight check, service unit, synthetic test fixtures. **Tag-writing functions exist** despite the source module's introductory claim that the daemon never writes tags; these must be disabled in the read-only mission.

## Code findings that must be repaired BEFORE any reflash

1. **Netlink ACK/error loss.** `services/nuxel-nfc/nuxel_nfc/kernel_nci.py`, `_recv()` (~lines 163–194), discards `NLMSG_ERROR` (type 2). Linux signals ACK as `NLMSG_ERROR` with error=0 and failures via negative errno. `DEV_UP`/`START_POLL` often return ACK-only; `start_poll()` treats an empty list as failure. Decode ACK/error, verify sequence/port IDs, handle DONE for dumps, do not interpret empty payload as proof of failure or success.
2. **Polling immediately canceled on socket close.** `_command()` creates and closes a fresh netlink socket around START_POLL. The upstream NFC protocol associates the poll request with a requesting netlink portid and stops polling when the socket is closed. Keep the controlling netlink socket alive until STOP_POLL/DEV_DOWN and clean it on daemon shutdown, with start/stop ownership tests. Reference: Linux NFC userspace documentation `https://www.kernel.org/doc/html/v6.4/networking/nfc.html`.
3. **Wrong tag activation object.** `daemon._kernel_scan()` (~lines 284–289) constructs `nci.NciController(self.kernel)` and calls `active.set_target(...)`, but `NciController` has no `set_target`. `KernelNci` does. This raises `AttributeError` on the real tag path and prevents a successful scan, even if `GET_TARGET` works. A tiny import/method check reproduced this offline.
4. **Service sandbox forbids raw NFC sockets.** `services/nuxel-nfc/systemd/nuxel-nfcd.service`: `RestrictAddressFamilies=AF_UNIX AF_NETLINK` omits **AF_NFC**. The client uses `socket(AF_NFC, SOCK_SEQPACKET, NFC_SOCKPROTO_RAW)` in `KernelNci.transceive()`. Add only the necessary family (and test under the actual service sandbox); don't widen broadly. The unit also has no capabilities; verify whether the target downstream NFC netlink control ops use `GENL_ADMIN_PERM` / CAP_NET_ADMIN and design a narrowly delegated controller if needed, never give a browser broad root or CAP_NET_ADMIN.
5. **Tag policy can allow non-grants.** `policy.authorize()` (~lines 90–113) allows any NFC-shaped record unless it contains an explicit deny or `granted=False`; a record with `{ "decision": "ask", "granted": null }` is treated as allowed. This was reproduced in an offline test. Require a positive, current grant and test denied/pending/expired cases.
6. **Scan cancellation is not effective.** `daemon.scan()` holds a daemon lock during bounded sleeps; `serve()` processes one client synchronously, `cancel()` never interrupts `_kernel_scan()`'s loop, and the loop does not inspect `_cancel`. Implement cancellable worker/IPC semantics and independent service responsiveness.
7. **Additional correctness issues.** `daemon.clear()` checks `self.transport.fd` when `transport=None` (normal kernel path); repair. `status()` claims `device_open=True` when only a sysfs node is present; avoid conflating presence, open/initialized, scan-ready and tag-present. `_recv()` exits after first generic message and can truncate multipart dumps. `KernelNci.present()` tests existence, not successful NCI state. Review duration/type validation and `nci.NciController`/`KernelNci` command ownership.
8. **Read-only scope not enforced.** `daemon.write_tag` and bridge write routes exist, and `tag_writes_supported=True` is advertised. Disable write verbs/UX and reject any firmware/eSE/payment/card-emulation/NFC write for this mission. Do not erase unrelated code without review; hide or fail-closed the capability until separately authorized.

## Physical/kernel uncertainties and highest-risk items

- In `0007`, `s3fwrn5_probe()` sets `info->force_fw_update=true` and schedules NFC setup work on every probe. Firmware-update decision also checks `force_fw_update || version mismatch` and can lead to SHA1 work and controller firmware programming **without owner NFC UI action**. This contradicts the safety story that firmware updates are only explicitly requested. **First kernel fix must prohibit automatic updates and auto NCI setup at boot until a proved safe path exists**. A workqueue does not make a kernel oops nonfatal.
- Kernel panic stack from Nov 14 is firm historical evidence. The *specific* assertion that hashing 151,552 bytes entered a non-multiple-of-64 final-block path is internally inconsistent. Proof requires running image hash, exact binary disassembly, workload and stack margins, implemented patch status, plus benign failure testing. Do not replace an oops with an error return and assume it is catchable.
- `oscclk_nfc` 0 Hz was historically reported, but bootloader communication existed. **A clock framework reported rate of zero is not proof that no physical clock toggles**; examine actual board node, CLK_REQ polarity, gates/parents and rail state using bounded read-only probes. Avoid arbitrary DT changes and permanent forced-on clocks.
- The 23-byte controller bootinfo is distinct from stock 10-byte S3FWRN5 assumptions; the bootloader does not prove NCI runtime. CORE_RESET response, CORE_INIT, RF discovery and physical owner-tag UID remain unproved.
- `CONFIG_NFC_S3FWRN5_I2C=y` and `CONFIG_SEC_NFC=y` coexist; only one can own `7-0027` at a time. The 0007 patch aims for deferred vendor fallback; validate exact running driver + probe ordering. `verify-kernel-nfc.py` cannot be run against a complete build checkout in this ZIP because `.build` is absent.
- Firmware SHA matches repository manifest and bundled sample; however, it is vendor-origin and may not be redistributable. **Do not include the blob in deliverable prompt ZIP, commit it to public Git, or use unmatched binaries**.

## Offline tests actually performed here

- `PYTHONPATH=services/nuxel-nfc python -m nuxel_nfc.daemon selftest`: **PASS**, only pure parser/ABI checks, no hardware.
- `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/pwnage65000/test_nfc_service.py -k 'not pinned_header and not uapi_numbers'`: **26 passed, 2 deselected** (the two tests read absent `kernel/s10plus/.build/src` headers). The mocks do not exercise real generic-netlink command/ACK semantics, radio permissions, actual tag discovery or kernel boot safety.
- Mini-repro: `hasattr(nci.NciController(MockTransport([])), 'set_target')` is **False**; a local pending grant `{ "nfc": {"decision": "ask", "granted": null} }` returned `allowed=True` from `policy.authorize(...)` (using a temporary test grant directory). Both bugs reproduce without the phone.
- `nuxel-nfc-diag.sh selftest` was invoked under a short timeout; no completed verdict was captured. Do **not** mark it PASS based on the historical report alone.

## Exact next milestone and expected work

**First milestone:** `nfc0` netlink GET_DEVICE and DEV_UP with decoded, positive ACK; I2C/core logs with a **real** CORE_RESET/CORE_INIT; no auto firmware download and no phone instability. This proves NCI runtime, but is **not yet a completed tag reader**. **Second milestone:** START_POLL stays active on a live netlink socket, GET_TARGET yields an actual target, AF_NFC transceive reads two benign tags with different verified UIDs and known NDEF. **Final:** permission control, OFF-by-default, restarts, reboot/sleep and RF/no-tag negative tests.

Order by reversibility: (1) verify golden boot, running kernel, binding; (2) fix pure userspace errors and tests; (3) run no-flash NCI diagnostic on the same kernel; (4) determine first physical blocker; (5) only if measured, minimal kernel patch/BOOT flash under recovery contract; (6) physical tag tests; (7) release/rollback. Budget 3–6 DeepSeek V4 Pro Thinking phases and Flash test sweeps, 0–2 measured BOOT flashes if feasible. A firmware/clock/RF calibration/signature barrier may defeat this plan without vendor specifications.

## Source inventory and limitations

Key files: `hw/NUXEL_01_NFC_S3NRN82_STANDALONE.md`; `hw/00_AUDIT_AND_EXECUTION_ORDER.md`; `final-state-components.md`; `evidence/live-20261114/BOOTLOOP-ROOT-CAUSE.md`; `evidence/pwnage-100000/live/initial/journal-current-kernel.txt`; `configs/nuxel/nfc/nfc.json`; `kernel/s10plus/patches/{0007-nuxel-sec-nfc-nci-transport.patch,0007-sec-nfc-class-name.patch,0017-nuxel-sec-nfc-ese-gate.patch,0018-nuxel-sec-nfc-force-clk.patch,0019-nuxel-sec-nfc-clk-hold-session.patch,0021-nuxel-s3nrn82-nci-read-and-strap.patch,0023-nuxel-nfc-fw-sha1-stack-safe.patch}`; `kernel/s10plus/build-kernel.sh`; `tools/s10plus/verify-kernel-nfc.py`; `services/nuxel-nfc/**`; `services/nuxel-bridge/src/nfc_provider.py`; `tests/pwnage65000/test_nfc_service.py`.

Missing here: `pwn/nfc*.md` (the user requested these; ZIP only has SSP prompts in `pwn/`), `reports/` including cited 2026-11-12/15 NFC reports, `.git` ancestry and exact live checked-out Samsung 4.14 kernel tree/build, current TWRP/BOOT backups, and direct latest physical evidence. Historical reports cannot be promoted to `PROVED_LIVE` for Nov 22 without new live traces.

Public corroboration: Linux NFC userspace netlink/PF_NFC model `https://www.kernel.org/doc/html/v6.4/networking/nfc.html`; related public kernel `net/nfc/netlink.c` listing `GENL_ADMIN_PERM` in a later common tree `https://android.googlesource.com/kernel/common/+/3a8a670eeeaa40d87bd38a587438952741980c18/net/nfc/netlink.c`. Exact 4.14.253 downstream behavior **must** be checked against the pinned source, not presumed from newer upstream. 2026 S3NRN4V support papers apply to a different controller and only suggest things to test: `https://lkml.iu.edu/2608.1/06687.html`.
