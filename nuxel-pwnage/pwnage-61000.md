# PWNAGE-61000 — Kickoff prompt: execute the full MFC mission

You are working in the Nuxel repository for the Samsung Galaxy S10+ (`beyond2lte`, Exynos 9820). Your full implementation specification is **`full-pwnage-61000.md`** in the repository root (or the exact path supplied by the operator).

**Read the entire `full-pwnage-61000.md` before editing anything. Then execute it as an implementation mission, not as a research-only exercise.** Follow its execution order and acceptance criteria exactly. Do not return only a plan.

Your target is safe, genuine Exynos MFC hardware video decoding: identify the matching driver and firmware ABI, fix kernel/DT/firmware integration and failure handling, prove the V4L2 M2M path, integrate one tested player path, preserve software fallback, benchmark real hardware decoding, and deliver evidence plus rollback.

Important repository-specific constraints:

- The pinned S10+ kernel build is Linux4 `android_kernel_samsung_exynos9820` at `f7194c1d15eded1c2a1a4dc63825b26103435cc0` unless the current checkout has an intentional documented update.
- The GStreamer guard exists because MFC `/dev/video*` opens previously hung in firmware loading and wedged processes in uninterruptible `D` state. **Do not remove it or open a suspected MFC node until the full source/firmware/DT safety gate has passed.**
- `firmware/s10plus/manifest.yml` contains an optional `mfc_fw.bin` candidate and hash, but the actual binary was not present in the supplied archive. Verify exact driver request name, version, source, hash and license; never assume the manifest entry proves availability.
- WirePlumber video capture stays disabled; MFC decode must not require camera capture monitoring.
- Existing boot/preload playback is an intentional software-safe `mpv --hwdec=no` path. Do not make boot depend on MFC.
- The existing `mpv` package is documented as an FFmpeg-free chain. Inspect real capabilities before choosing GStreamer, FFmpeg/mpv or a helper service.
- Mali GPU acceleration and MFC video decoding are independent. Do not claim DMA-BUF zero-copy just because MFC decode works.

Work in this order: inventory → exact driver/IP/DT/firmware audit → firmware acquisition/verification → safe kernel changes → build/tests → inventory-only diagnostic → owner-approved on-device open → V4L2/decode proof → single player integration → matched performance/thermal benchmark → narrow guard transition → full regression → report and rollback.

**Safety:** do not flash/reboot the phone, access protected partitions, or perform the first live open of the historically wedged MFC device without explicit owner approval in the active task. A shell timeout or child process does not make an uninterruptible kernel hang safe. Never probe every `/dev/video*` node. Keep the known-good software playback and boot path operational.

Keep `docs/beta-finalization/live/PWNAGE-61000-MFC-TODO.md` current. Implement as much as can be safely completed, run the tests, create the evidence/report files required by the full prompt, and finish with an honest status: `FULLY_DONE`, `IMPLEMENTED_NOT_PHYSICALLY_VERIFIED`, `BLOCKED_<reason>` or `FAILED`. No invented test results, no unsupported 4K claims, and no plan-only response.
