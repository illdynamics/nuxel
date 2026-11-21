# Verified public research, 2026-11-20

Each resource was checked via online lookup; do not blindly install third-party phone builds or vendor packages.

1. **Exact-device alternative Linux port (research priority 1):** https://github.com/gangg111/S10Plus_Linux — SM-G975F (`beyond2lte`) Droidian source and patches. Its published compatibility table *claims* working Camera2/libcamera path, cellular calls/data, sensors, and MFC H.264/HEVC video decoding. This is external author self-report, not a validated Nuxel drop-in. The Droidian implementation includes Android camera dependencies and a different kernel/userspace integration. Nuxel's **zero Android runtime** constraint means port concepts, exact sensor patch analysis and hardware sequencing may be helpful, not blind binary import.
   - Source patch series: https://github.com/gangg111/S10Plus_Linux/tree/port-2026-09-28/droidian
   - Detailed readme: https://github.com/gangg111/S10Plus_Linux/blob/port-2026-09-28/droidian/README.md
2. **Closest native-Linux comparator (different model, research priority 2):** https://github.com/butztill/s10-linux — Samsung S10 SM-G973F (`beyond1lte`), Exynos9820. Documents independent Linux camera/capture work and runtime camera tuning/table handling. Camera module population, kernel and devicetree differ from SM-G975F; no blind transplant.
   - Status: https://github.com/butztill/s10-linux/blob/main/docs/public/STATUS.md
   - Native build validation: https://github.com/butztill/s10-linux/blob/main/docs/public/BUILD-VALIDATION.md
3. **Same-model vendor firmware file map:** https://github.com/Evolution-X-Devices/vendor_samsung_beyond2lte/blob/bka/beyond2lte-vendor.mk — lists the 8 camera files in Nuxel stock, `mfc_fw.bin` may be verified via other model-specific manifests, `lhd.conf`, NFC S3NRN82, BCM4375 B0/B1 HCD candidates. The public manifest is a file inventory, not proof its contents are the same Android release as the owner's AP.
4. **Linux4 vendor reference that Nuxel already pins:** https://github.com/Linux4/proprietary_vendor_samsung at commit `05c9ef8f16e0ad5ab274e408c120dfd99fd5c628`. The uploader's archived stock set matches only 1 of this public source's eight camera SHA hashes. Existing hash-pinned host-only fetcher is under `host_tools/`. Do not silently change manifest hashes.
5. **LineageOS Exynos9820 device common:** https://github.com/LineageOS/android_device_samsung_exynos9820-common — inspect `cbd`, kernel/vendor configuration and modern firmware inventory with branch/version pinned. Branches may target different Android versions or models.
6. **libcamera architecture:** https://libcamera.org/faq.html and https://docs.libcamera.org/master/guides/pipeline-handler.html — installing libcamera alone does not supply a Samsung FIMC-IS2 pipeline handler.
7. **Firmware SDK/ABI documentation:** https://docs.kernel.org/driver-api/firmware/request_firmware.html — inspect `request_firmware()` expected search semantics and actual downstream patch.

## Practical download verdict

**Camera:** The user's archive ALREADY contains all eight camera files reported as owner-stock `G975FXXS9DTK9`; no newly purchased or random third-party camera firmware is currently justified. What is **not** verified is exact running-kernel firmware-name/path selection and ISP DDK compatibility. The external resource list supplies code and file-origin references, not an automatically approved firmware package. Do not redistribute proprietary ROM firmware in this pack.

**Mobile:** An exact-build owner CP archive was already reportedly acquired, but it is separate from uploaded ZIP. No need to hunt generic CP images unless owner package fails a verified integrity/compatibility check.

**SSP:** Kernel BBD patch appears embedded; proprietary Android `lhd` compatibility is a runtime/ABI problem, not merely a missing `.bin`.

**NFC:** Firmware exists; clock/NCI operation is the gate.

**GPU/MFC:** `mfc_fw.bin` is the clearest other firmware **deployment** candidate; historical host reference has been acquired, but target installation and decode verification remain unproved. Use a provenance-verified exact-device build and gate live testing carefully.

**Bluetooth:** Beyond2lte vendor list has several Broadcom BCM4375 HCD variants (`B0`, `B1`, semco/murata); choose only after the phone's true chip/subvendor ID is read.
