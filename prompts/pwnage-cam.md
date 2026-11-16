
## 2. `pwnage-cam.md` — agent kickstarter

Save this in the same directory as the full prompt. Start the agent with this shorter file.

```markdown
# PWNAGE CAM — Samsung Galaxy S10+ Camera Bring-up for Nuxel

**Read and obey `full-pwnage-cam.md` completely.** It contains the detailed hardware investigation, firmware requirements, TWRP/flash loop, SSH handoff, permission-manager work, PipeWire/XDG portal requirements, app validation, security policy and acceptance tests.

## Starting state and owner authorization

I will start you with the Samsung Galaxy S10+ SM-G975F (`beyond2lte`, Exynos 9820) already booted into **TWRP and connected over USB/ADB**.

You are authorized to:

- inspect the exact repo and device;
- acquire ordinary matching camera firmware/HAL/config files from the owner's own already-mounted stock vendor/system filesystem using the read-only acquisition script in this pack;
- build the pinned kernel and DTBs;
- build a verified boot candidate;
- flash the verified boot image using the repository's guarded TWRP script;
- reboot and diagnose failed boot attempts;
- once Nuxel boots, connect over Wi-Fi SSH with my key and continue implementing/testing/deploying camera userspace.

Do not use generic fastboot on this S10+. Inspect `boot/s10plus/flash.sh`, `build-candidate.sh`, `kernel/s10plus/build-kernel.sh`, the completed device inventory and actual partition topology before writing anything. The current plan mentions A/B, but the real S10+ partition layout must be measured; do not invent slots. Never flash userdata/rootfs, EFS, persist, modem, recovery, bootloader or PIT without an independently verified target and explicit data-impact approval.

## Critical reboot interpretation

**If you flash/reboot and the phone returns to TWRP, that means the Nuxel boot attempt failed. I did not manually return it to TWRP.** Treat it as a bootloop/hang/crash. Collect TWRP/pstore/last-kmsg/kernel/initramfs/filesystem logs, identify the root cause, fix the source, rebuild, pass the gates, reflash the corrected boot candidate and reboot again. Never repeat the same failing image blindly.

**When the phone reaches the Nuxel environment and its boot health check confirms userspace, that is a successful boot.** Then connect to the owner-provided Wi-Fi address using:

```sh
ssh -i ~wicked/.ssh/wicked_wqn_id_rsa -o IdentitiesOnly=yes root@192.168.178.167
