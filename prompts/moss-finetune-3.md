# NUXEL A46.3 — EXECUTION LAUNCHER

Read `NUXEL-A46.3-WARNING-SPLIT-FINAL.md` completely and execute it exactly.

Target device: Samsung Galaxy S10+ SM-G975F in TWRP mode.

Your objective is to perform a **minimal warning-screen finetune only**.

Desired final visual sequence:

1. Normal Nuxel logo
2. Fullscreen unlocked-bootloader warning replaced with `./assets/nuxel-boot-screen-warn.jpg`
3. Normal Nuxel logo again
4. Spinning penguin boot animation

Additionally, the exclamation-mark warning overlay on the later logo must be replaced with a black minimal image so it no longer visibly interferes.

Preserve everything else exactly as-is.

Mandatory requirements:
- back up the relevant partition(s) first
- use the phone's actual extracted resources to determine which image is which
- do not assume the two normal logo screens are the same resource
- do not change the already-working normal logo(s)
- do not change the spinning penguin animation
- do not install MOSS hooks
- do not broad-patch unrelated assets
- flash only the verified target resource partition
- verify by full partition readback and physical boot observation

Use `./assets/nuxel-boot-screen-warn.jpg` for the funny/fullscreen unlocked warning only.

Start with read-only investigation, partition backup, and resource mapping.
Then patch only the warning-specific assets, validate, flash once, verify, and report.

Proceed carefully and safely. 🐧🔥
