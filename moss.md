# 🐧🔥 NUXEL A46 — MOSS BOOT-SPLASH FLASH LAUNCHER (`moss.md`)

**EXECUTOR:** DeepSeek-v4-pro-thinking on the MacBook, with the Samsung Galaxy S10+ SM-G975F (`beyond2lte`) connected in TWRP recovery.

Read the complete companion file **`./NUXEL-A46-MOSS-BOOT-SPLASH-ONLY.md`** from start to finish, then execute its phases in order. Do not proceed using this short launcher alone.

**EXACT OWNER-SUPPLIED ARTWORK:** `./assets/nuxel-boot-screen.jpg` in the *current Nuxel checkout*. This is a JPEG source, not `nuxel-boot-screen.png`. Verify the actual file's presence, encoding, dimensions, visible artwork and SHA-256. Do not substitute a sample logo.

**SOLE OBJECTIVE:** Replace the earliest user-replaceable Samsung splash image with the validated Nuxel image, and boot back into the existing Nuxel installation. Use MOSS (`MOSS-main(2).zip`) for **offline source/format analysis only**, not its Magisk installer or persistent auto-flash hooks. Do not modify the A45 keyboard/lockscreen, kernel, rootfs, recovery or bootloader/security state.

**MANDATORY FIRST:** Prove device identity and the exact real splash partition from TWRP. Inventory, image and independently verify **every accessible/readable partition** onto private MacBook storage, including the complete original splash partition and critical EFS/NV data. Reconcile partition aliases, source byte lengths and SHA-256 hashes. Report genuinely unreadable protected regions rather than pretending they were backed up. If even one otherwise readable partition cannot be backed up/verified, if Mac disk space is inadequate, or if the splash image's restorable original is not available, **STOP BEFORE FLASHING**.

Analyze the original partition offline; identify the exact Samsung image filename, archive entries, metadata and trailing bytes. Build a full-size replacement image changing only the proven first-splash artwork and preserving every unrelated entry and opaque byte. Validate the image and a feasible independent restore procedure before any write.

**CONDITIONAL ONE-TIME AUTHORIZATION:** The owner explicitly requests flashing **only that verified boot-splash partition**, **after all accessible partitions are backed up and every technical gate passes**. If and only if the companion prompt's complete pre-flash checks succeed, perform **one** exact-target TWRP write, full partition readback and hash comparison, then reboot into Nuxel and verify the physical earliest displayed image. Do not repeatedly retry writes. If the actual target, format, device or backup scope differs, **STOP and request fresh specific approval**. Do not touch the unlocked-warning image or any second partition under this authorization.

If write/readback fails, do not reboot: restore the verified original splash image using the documented recovery procedure and verify its full hash. If boot fails, recover via TWRP and restore only the original splash partition; leave all other partitions untouched.

Generate detailed backup, before/after image, validation, readback, boot and rollback reports. NEVER claim the new logo appears before it is seen on the actual device.

**START WITH READ-ONLY TWRP AND MOSS INVESTIGATION. BACK UP EVERYTHING READABLE FIRST. THEN — ONLY AFTER VALIDATION — FLASH ONCE. 🐧🔥**
