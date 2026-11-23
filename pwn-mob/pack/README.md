# Nuxel S5000AP — Stage 06 Protocol Reference & Evidence Pack

Research date: 2026-11-23. Prepared for `cs/mob` at reported HEAD `c050c75c`.
Target: Samsung Galaxy S10+ SM-G975F (beyond2lte), Exynos 9820, S5000AP/Shannon CP, pinned Linux 4.14 kernel.

## Purpose

Help DeepSeek recover *verifiable* RIL/FMT telephony and RFS protocol knowledge from open references and **owner-authorized** local firmware files. This is a **research and offline-analysis pack**, not a finished radio driver or a source of verified SIM/LTE commands.

**Not included:** Samsung proprietary ELF binaries, baseband firmware, third-party code, credentials, private cellular identifiers, speculative AP-to-CP commands, modem-writing utilities.

## Start here

1. Read `FINDINGS.md` (ranked discoveries and pitfalls).
2. Read `SOURCES.md` (source URLs, exact variants, limitations).
3. Follow `REFERENCE-RECOVERY-WORKFLOW.md` (static analysis of a lawfully obtained S10+ vendor image).
4. Inspect `RFS-FORENSICS.md` and `TRACE-CONTRACT.md` before changing the RFS parser.
5. Give `PROMPT-06-RESEARCH-TO-INTEGRATION.md` to DeepSeek Pro Thinking.
6. Run offline tools from the **host**, not as active radio probes:

```bash
python3 scripts/decode_observed_frames.py --self-test
python3 scripts/inventory_vendor.py /path/to/your/extracted/vendor --json > /tmp/vendor-inventory.json
python3 scripts/triage_elf.py /path/to/your/extracted/vendor/lib64/libsec-ril.so --json > /tmp/ril-triage.json
python3 scripts/scan_repo_contract.py /path/to/nuxel/repo --json > /tmp/contract-scan.json
python3 scripts/check_stage06_gates.py data/stage06-gates.json
python3 -m unittest discover -s tests -v
```

Use an authorization-approved copy of your *own* stock S10+ firmware. The source lists only identify likely filenames and variant constraints. The binary may be named under `vendor/lib`, `vendor/lib64`, or extracted partition paths. The inventory script never touches a device node.

## Ground-truth limitations

- No Nuxel repo, `/dev/umts_*` endpoints, or Samsung vendor `.so` was directly available for inspection during production of this ZIP. All Nuxel state is **user-supplied agent report**, not independently reproduced.
- The 25-byte `DELETE_ALL_VIS` capture was supplied by the user; no external S5000AP-specific RFS semantic specification was located.
- `libsec-ril.so` is a strong place to *investigate*, not proof that specific SIM command IDs are known.
- The FMT and RFS vectors in this pack are non-sensitive examples copied from the user's reported observations for *offline validation only*.
- Stage 06 is not passed by decoding `AST_POWERON`, compiling `radiod`, or matching a string in a vendor ELF. A documented safe bidirectional request/response and real modem-reported SIM/data states still need to be demonstrated.

## Safety invariants

- Never automatically invoke the CP bootstrap, reset radio, or flash anything.
- No speculative or fuzzed commands to a live modem. Do not use the `automatic-testing` or attack discovery tools bundled with third-party research projects on the device.
- Preserve BOOT/DTB/DTBO/RADIO, NV/EFS and SIM credentials. Treat `/efs` and related modem storage as protected.
- Keep native `nuxel-radiod` clean-room and source-traceable. Do not redistribute or load proprietary vendor RIL components without rights/review.
- Distinguish `observed`, `structurally parsed`, `semantic corroboration`, `live request-response`, and `functional outcome` in all reports.

## Suggested handoff

Attach this ZIP to DeepSeek Pro Thinking **in addition to the latest Nuxel repository state**, then supply `PROMPT-06-RESEARCH-TO-INTEGRATION.md`. DeepSeek must ground device-specific conclusions in the repo and recorded live evidence, not treat this research pack as a tested patch.
