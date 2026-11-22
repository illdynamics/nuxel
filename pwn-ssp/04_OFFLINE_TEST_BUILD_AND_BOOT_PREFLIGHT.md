# 04 — EXHAUSTIVE OFFLINE VERIFICATION AND ZERO-DT-CHANGE BOOT PREFLIGHT

DeepSeek-V4-Pro-Thinking: stages 01-03 complete. DO NOT FLASH OR WRITE HARDWARE IN THIS ROUND. A candidate must first prove itself safe against the *currently booting* Nuxel donor image.

**Run and extend:**

- `make -C tools/s10plus/ssp-native OUT=/tmp/ssp-audit-build check` (host C harnesses, firmware identity, packet parser, replay). Add malformed/truncated F0..F5, version mismatch, bad ACK/NACK, wrong CRC, no reply, short read, partial transfer, cancellation, missing post-start version, reliable sequence rollover, reentrancy, duplicate/open-busy, kernel/bridge ownership, suspend-race and false-READY negative tests.
- `PYTHONPATH=services/nuxel-orientation python3 -m pytest -q services/nuxel-orientation/tests` (68 passed in provided archive, not hardware proof); add real-source-unavailable and stale-data recovery fixtures. `python3 -S -m unittest discover -s NUXEL_SSP_RECOVERY_V2 -p 'test_*.py'` (14 passed in provided archive).
- Build the **exact pinned kernel** from clean inputs after resolving all required patches; no warning-only skipped SSP patch. Check `.config`, image build ID, kallsyms and every `nuxel_ssp_dl_*` / BBD symbol, ABI, regulator and PM paths. Source/reviewer must confirm no unrelated patch changes.
- Produce an immutable source/build manifest containing full Git HEAD, dirty-diff hash, compiler, Kconfig, source kernel base, every applied patch name+SHA256, resultant `Image`, ramdisk, BOOT and DT tail hashes. Verify embedded firmware identity against real bytes, not just documentation.

**BOOT/DT immutable gate:**

1. Revalidate owner-approved Nuxel donor BOOT dump from **running handset**; do not trust historical artifacts. Verify known-good recovery copy hashes, BOOT partition capacity, selected normal-boot partition, BOOT v1 format, kernel & ramdisk offsets/load addresses and cmdline.
2. Use `tools/s10plus/pack-ssp-boot.py` only after reviewing its offset heuristics, especially FDT discovery; confirm resulting payload layout with `tools/s10plus/verify-boot-image.py` **and a second independent verifier**. Do not change ramdisk if not strictly necessary.
3. Require exact byte-for-byte equality between donor and candidate **appended/embedded DTB/hash tail**, identical ramdisk bytes when kernel-only, intact all boot header fields except required kernel length, correct address and bounds. The candidate may be smaller but must fit the actual partition. Never pass an unproven `--pad-to-partition` image to a blind writer.
4. Independently record DTB and DTBO *partition* hashes (no writes) immediately before and after any future BOOT flash; verify `androidboot.dtbo_idx` and DT selected by bootloader, and no dtc or dtbo output was changed in the deployed package.
5. Stage known-good BOOT rollback on host and in TWRP-accessible location, check size/digest on **both** endpoints, and document safe partition mapping/readback. Dry-run the exact TWRP write/readback/rollback recipe with validation only, *without* executing a write.
6. Verify device action is necessary: if the installed kernel can already be fixed in userspace, avoid a BOOT flash entirely. Never flash a new kernel merely to inspect a protocol parser.

**Preflight decision output** `reports/SSP-CANDIDATE-PREFLIGHT.json`: individually PASS/FAIL every gate; explicit hashes/paths/partition identities; rollback receipt; boot image parser comparisons; software-only alternative; known remaining hardware risks. A single FAIL means **NO FLASH**. If all pass, move to 05 under the owner's BOOT-only TWRP agreement and bounded hardware-trial authorization. No assertion of zero brick probability.
