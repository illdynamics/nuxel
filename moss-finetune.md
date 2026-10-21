# 🐧🔥 NUXEL A46.1 — Clean Penguin Boot (warning artwork only)

**Executor: DeepSeek-v4-pro-thinking.**

Read these two files in full, in this order:

1. `./NUXEL-A46-MOSS-BOOT-SPLASH-ONLY.md` — **earlier A46 reference for safety rules and backup architecture**, NOT a command to reflash the already-working first splash.
2. `./NUXEL-A46.1-WARNING-SCREENS-FINETUNE.md` — **the new operative A46.1 mission**, which extends A46 only to the two owner-requested cosmetic warning screens.

**Verified user observation:** The A46 Nuxel early boot screen ALREADY WORKS on the physical Samsung Galaxy S10+ SM-G975F. You MUST preserve the current partition contents and its working `logo.jpg` bytes. Do not rebuild, replace, or reflash the first Nuxel splash just because A46 originally asked for it.

**New objective:** Diagnose and, if the real firmware proves it safe, cosmetically customize (1) the unlocked-bootloader warning screen and (2) the exclamation/warning image shown at the top when the Nuxel logo appears a second time, so the two stages visually integrate with `./assets/nuxel-boot-screen.jpg`.

Audit both MOSS and the owner's `TWRP_Bootlogo_patcher-master(1).zip` if available, **strictly read-only**. Warning-resource candidates may be `svb_orange.jpg` and `booting_warning.jpg`; verify the actual current `up_param` and `param` structure. Do **not** execute either install script: the TWRP patcher automatically considers two partitions, and the MOSS installer has Android boot hooks.

First capture/ask for real boot-sequence evidence, reconcile successful A46 all-partition backup receipts, and make a fresh independently verified Mac-backed **current** splash partition backup. Do not accidentally restore the OLD Samsung splash or overwrite the working Nuxel `logo.jpg`. Build only a narrow warning-resource patch, validate all files/metadata/lengths and unchanged logo bytes, and prepare a full immediate rollback.

**FLASH SAFETY:** A46.1 is a NEW write. Do not interpret this launcher or the earlier A46 approval as authorization to rewrite an arbitrary partition. Present exact target partition identity, hashes, backup, visual diff and rollback; stop for owner's explicit **`APPROVE A46.1 WARNING ART FLASH: <EXACT PARTITION NAME>`** before any raw write. Distinguish `up_param` from `param`; each needs independent approval if both must be modified. After approval, do one bounded write, whole-partition readback/hash, physical Nuxel boot test, and restore CURRENT known-good image on any failure.

Cosmetic warnings are **not** security enforcement. Never modify bootloader binaries, lock state, Knox, kernel, recovery or other OS partitions. If a warning symbol comes from bootloader code rather than an editable image, STOP that stage, explain, and leave it intact.

**GO FINISH THE PENGUIN BOOT SEQUENCE — WITHOUT BREAKING THE FIRST SUCCESS. 🐧🔓🔥**
