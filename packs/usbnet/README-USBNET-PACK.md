# Nuxel USBNET Pwnage Pack

This pack is a repository-grounded implementation brief for completing USB networking on the Samsung Galaxy S10+ and preparing the result for Nuxel's single controlled reflash batch.

## Contents

- `full-pwnage-usbnet.md` — binding full technical specification, kernel/lifecycle repair brief, USB Ethernet + SSH, tethering, hotspot, Bridge API, Quick Settings, firewall, test matrix and one-reflash integration.
- `pwnage-usbnet.md` — shorter agent kickstarter. Start the agent with this file and keep the full spec alongside it.
- `reference/REPORT-USBNET.md` — current USBNET audit, including compile/runtime matrix, NCM panic, RNDIS analysis, host diagnostics and current limitations.
- `reference/REFLASH-PLAN.md` — repository's controlled one-batch reflash policy.
- `reference/current-source/` — snapshots of the phone-side USB network helper, Mac/Linux host helper, existing USB mode manager, NetworkManager provider, USB mode shell owner, detach indicators, Quick Settings source and kernel build inputs.
- `reference/usb-detach/` — A73/A74/A77 source evidence and the rule against DWC3 debugfs link-state reads.
- `reference/panic-evidence/` — original NCM panic notes, pstore stack and selected kernel/gadget/host evidence.

## Firmware / binaries

**No proprietary firmware or binary blob is required or included for CDC-NCM/RNDIS USB gadget networking.** These are USB gadget kernel functions plus userspace networking/configuration. The previous failure is a Samsung 4.14.253 NCM function teardown/lifecycle panic, not a missing USB firmware image.

Do not invent/download firmware or include arbitrary kernel modules in this pack. If the agent discovers a real vendor dependency, it must prove the dependency against the exact board/kernel source and record its provenance/licence/compatibility before adding it.

## Important execution constraint

The owner wants one combined reflash, not an independent USBNET flash. The full prompt therefore directs the agent to prepare the patch, build/config updates, runtime services, UI, tests and reflash manifest **without flashing or rebooting the phone**. USBNET must be combined with the in-progress NFC and any other kernel-gated batch work. Keep CDC-ACM recovery serial intact.

## Evidence snapshot caveat

The reference files were copied from the uploaded Nuxel repo ZIP supplied in this conversation. They are evidence and implementation context, not a frozen authority. The agent must inspect the live checkout and current `git status` before editing. Parallel NFC changes may have happened since the ZIP snapshot.

## Recommended launch

Place `full-pwnage-usbnet.md` in the repo root, then start the agent with `pwnage-usbnet.md`. Ensure both files are accessible in the working directory and include the reference folder when useful.
