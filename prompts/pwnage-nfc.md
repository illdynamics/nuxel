

# PWNAGE NFC — Execute the NFC Implementation

**Device:** Samsung Galaxy S10+ SM-G975F (`beyond2lte`)  
**Platform:** Exynos 9820 / `universal9820`  
**OS:** Nuxel Linux / Fedora 43 ARM64  
**Kernel baseline:** 4.14.253

Read and follow `full-pwnage-nfc.md` as the authoritative specification.

This is an execution task. Do not stop after producing an investigation or implementation plan.

## Starting condition

The operator will manually boot the phone into **TWRP before launching this prompt**.

The operator explicitly authorises the required boot-image flash and reboot, provided all preflight checks and safety rules in `full-pwnage-nfc.md` are followed.

If the phone boots into Nuxel after flashing, continue with NFC implementation and physical testing.

If it hangs, fails to boot, or returns to TWRP instead of Nuxel, treat that as a failed attempt. Collect diagnostics, identify the cause, fix the image and reflash. Maximum three total flash attempts. Never blindly repeat a failed flash.

Preserve a verified known-good boot image and a viable recovery route. Only flash the verified boot partition. Never touch EFS, modem, recovery, bootloader, PIT or unrelated partitions.

## Critical requirement: one combined reflash

I also have an existing USB networking implementation.

Read:

`PWNAGE-107000-USBNET-REPORT.md`

The previous USBNET candidate was:

`build/out/s10plus/debug-candidates/p107000-usbnet/boot-usbnet-ecm-ncm-fix.img`

Its reported SHA-256 was:

`4501750f5800538cd85fc6b3d314fef4350ceac62e29ffb5057450e63ee702c8`

It includes an NCM teardown fix, ECM, ECM-subset, EEM and NAT/masquerade support.

**Do not lose or regress this work.**

Build one new combined boot image containing:

- The verified USBNET changes.
- The new NFC kernel implementation.
- The correct device tree and compatible boot image components.

Do not flash the old USBNET candidate and pretend it contains NFC. Verify the combined image and rerun the USBNET regression tests before flashing.

If the changes cannot safely coexist, explain the blocker and stop before flashing.

## Execute

1. Inspect the repository, current branch and working tree.
2. Read the full USBNET report.
3. Inspect `0007-sec-nfc-class-name.patch`; determine what it actually implements.
4. Identify the actual NFC controller in this exact S10+ variant. Do not guess the chip.
5. Map its bus, GPIOs, IRQ, regulators, pinctrl, firmware and reset requirements.
6. Implement the correct kernel driver, configuration and device tree support.
7. Preserve and integrate the USBNET changes.
8. Build the combined kernel and boot image.
9. Run kernel, device tree, image and USBNET regression gates.
10. Back up the existing boot image and verify TWRP connectivity.
11. Verify the target partition, image format and SHA-256.
12. Flash the combined image using the guarded procedure.
13. Reboot and confirm that Nuxel genuinely starts.
14. If boot fails or returns to TWRP, diagnose and use the bounded recovery loop.
15. Once Nuxel boots, finish the NFC userspace implementation.
16. Integrate the service into Nuxel's hardware, settings and Quick Settings architecture as appropriate.
17. Test controller initialisation and power control.
18. Physically discover real NFC tags.
19. Read a real NDEF tag.
20. Write a simple NDEF record to an expendable writable tag and read it back.
21. Test error handling, repeated scans and reboot persistence.
22. Verify USBNET remains functional.
23. Write the final reports and test results.

## NFC implementation expectations

Nuxel is Linux-based, not an Android-framework distribution.

Prefer a suitable native Linux NFC/NCI stack and a small Nuxel service. Do not introduce an entire Android NFC framework without a demonstrated need.

The implementation must include:

- Correct controller driver.
- Kernel NFC/NCI support where applicable.
- Correct hardware description and power sequencing.
- Firmware handling where required.
- Device interface and permissions.
- Userspace discovery and NDEF handling.
- Nuxel service integration.
- Actual UI controls reflecting hardware state.
- Safe, explicit confirmation before tag writes or actions based on tag content.

Do not claim payment, secure-element access or card emulation unless those capabilities are independently demonstrated.

## Testing and completion

Automated tests are not physical NFC validation.

A device node existing is not proof that NFC works.

`FULLY_DONE` requires:

- Successful boot into Nuxel using the combined image.
- NFC driver bound to the real controller.
- Successful controller initialisation and power control.
- Physical tag discovery.
- Real NDEF read.
- Real NDEF write and read-back on an expendable writable tag.
- Working Nuxel userspace integration.
- USBNET regression tests passing.
- Reboot persistence.
- Complete build, flash and test documentation.

If any physical test cannot be performed, report it as `NOT TESTED` and leave the task `PARTIAL`.

**Start with repository reconnaissance, then implement, build, flash, recover if needed, and physically validate. Do not stop at a plan.**


