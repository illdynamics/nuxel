# PWNAGE-34000 KICKSTARTER — NUXEL CONNECTION MODES & INTERFACE RELIABILITY

The full pwnage 34000 prompt is located here, use it: ./full-pwnage-34000.md

You are working on the Nuxel Linux phone OS repository. Read and execute the complete specification in `pwnage-34000.md`.

## REQUIRED FIXES

**1. Bottom navigation rendering**
- Fix intermittent bad rendering of Back, Home and Tabs icons.
- Investigate why the same icons look correct on some boots but incomplete, outlined incorrectly or visibly chopped on others.
- Correct the underlying asset-loading, alpha/transparency, scaling, caching, layout or rendering race.
- Keep the existing intended artwork and visual design.

**2. Live console transport indicators**
- Use:
  - `./assets/nuxel-console-serial.png`
  - `./assets/nuxel-console-usb.png`
  - `./assets/nuxel-console-wlan.png`
- Show each icon when its corresponding live console transport is genuinely connected.
- Support simultaneous transports: for example, WLAN and serial must show both icons.
- Detect actual active sessions or listeners, not merely the presence of an interface or configured address.
- Keep the existing charging, USB-connected and live-console indicators working.

**3. File-transfer indicator**
- Use `./assets/nuxel-file-transfer.png`.
- Place it beneath the Nuxel text logo if that fits cleanly; otherwise integrate it into the status-indicator row.
- Show it only while file-transfer mode is genuinely active.
- Hide it when file transfer stops or fails.
- Make all status indicators responsive, legible and non-overlapping.

**4. Lockscreen connection-mode selector**
- Use `./assets/nuxel-connection-mode.png` as the lockscreen button.
- Position it where it fits the existing lockscreen, preferably on the right within comfortable thumb reach if central placement conflicts with the design.
- Pressing it opens an accessible overlay offering **Charging** and **File Transfer**.
- The overlay must be usable without unlocking the phone if the existing lockscreen security model permits this safe system action.
- Do not expose personal files or unlock the desktop from this control.

**5. Real USB file-transfer/storage mode**
- Charging mode must preserve charging and the existing supported console functionality.
- File Transfer mode must make Nuxel storage accessible from a connected laptop using a genuine supported USB file-transfer implementation.
- Prefer a true mounted USB Mass Storage volume when the storage architecture can support it safely.
- Do not export a mounted live root filesystem or active writable home filesystem as a raw USB block device.
- If safe Mass Storage is impossible with the current storage layout, implement MTP or another suitable supported file-transfer protocol and clearly document the difference.
- Preserve WLAN and serial console access. Handle conflicts between USB console gadget functions and storage functions deliberately.
- Show the file-transfer indicator only after the mode has successfully activated.

## EXECUTION RULES

- Inspect the repository, current Git state, assets, lockscreen, status indicators, USB gadget setup, kernel configuration, storage layout, and active console services.
- Create or update `pwnage-34000.md` with the full specification supplied by the maintainer.
- Execute the fixes; do not stop after an audit or plan.
- Preserve unrelated user changes, existing artwork, lockscreen behaviour and recovery access.
- Do not flash partitions or firmware, replace the kernel, change the bootloader, repartition storage, or perform destructive resets.
- Never claim a laptop-mounted volume works unless the host actually detects and accesses it.
- Never expose an active mounted filesystem as raw USB storage.
- Do not break charging, USB/serial recovery, WLAN console, touch input or normal phone use.
- Add tests, deploy safe userspace changes and verify actual behaviour where possible.
- Back up modified configuration and provide rollback instructions.

## EXECUTION ORDER

1. Establish baseline and inspect the assets and USB/storage architecture.
2. Fix deterministic navigation-icon rendering.
3. Implement actual multi-transport console detection.
4. Add the file-transfer indicator to the status UI.
5. Build the lockscreen mode selector and mode-state handling.
6. Implement safe USB storage/file-transfer integration.
7. Test mode switching, reconnects, failures and simultaneous console transports.
8. Deploy and verify on the actual phone and laptop where available.

Store sanitized evidence in `docs/beta-finalization/live/evidence/pwnage-34000/`.

Report changed files, root causes, test results, actual hardware/host verification, remaining blockers and rollback steps. Do not report success for a simulated transfer mode or a merely visible icon.

Begin now. Read `pwnage-34000.md`, investigate the real codebase and implement the complete mission end to end.
