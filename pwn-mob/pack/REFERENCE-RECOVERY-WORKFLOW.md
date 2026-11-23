# Reference Recovery Workflow — Practical, Offline First

## Phase 0 — Freeze the known-good phone

Reported Nuxel `cs/mob` HEAD: `c050c75c`, CP ONLINE, `nuxel-radiod` running, BOOT/DT hashes unchanged. Preserve the state. No automatic reboot/CP reset. Work on host-side copies of existing files; do not inspect/write device block partitions merely to obtain a vendor RIL.

## Phase 1 — Locate a rightful and version-matched AP-side RIL

Find a vendor image from the owner's original SM-G975F firmware backup or a legally obtained Samsung stock firmware package. A stock CP firmware `modem.bin` is **not** `libsec-ril.so`: the former runs on the CP; the latter is AP-side code. Prefer a matching AP+CP release pairing; **do not assume** `G975FXXSGHWC2` or a Note10 vendor library matches installed EFUJ2.

Inventory all of these optional variants:

- `vendor/lib/libsec-ril.so`, `vendor/lib64/libsec-ril.so`
- `vendor/lib/libsec-ril-dsds.so`, `vendor/lib64/libsec-ril-dsds.so`
- `libril_sem.so`, `libsecril-client.so`, `libsec_semRil.so`
- `rild`, `cbd`, RFS-related executable or service/init files
- `vendor.samsung.hardware.radio.*.so`
- RIL-related `init*.rc`, `vendor.prop`, stock build metadata

Use `scripts/inventory_vendor.py` on already extracted local directories. It emits metadata and hashes, not binary contents. Do **not** bundle vendor ELFs into Nuxel source.

## Phase 2 — Determine dialect, not just matching filenames

On an *authorized local copy*, collect:

- ELF class (32/64), CPU (AArch64/ARM), endianness and file hash.
- Dynamic dependencies and unresolved external dependencies (`readelf -d`, where available).
- Text/string references (`scripts/triage_elf.py`).
- Whether classes/symbols resemble `IpcProtocol41`, `IpcProtocol41*`, or something else.
- IO paths referenced (`/dev/umts_ipc0`, RFS endpoints, `ioctl`, `read`, `write`).
- Entrypoints and call relationships of SIM state, radio power, registration state, data session handling.

**Caveat:** Symbols may be stripped; strings alone are weak evidence. `Ipc41X` was seen in a later SM-G973F study sample, not verified for the installed EFUJ2 firmware.

## Phase 3 — Offline static command discovery

Use Ghidra, or BaseMirror if its prerequisites can be met. BaseMirror documents:

- `RIL_Analyzer-bw` and `RIL_Analyzer-bwfw` tools.
- Ubuntu 20.04 x86-64 / Java 11 / Ghidra 9.2.2; RAM/disk requirements.
- Difference between static commands (constant parameters) and hybrid commands with external parameters.

Recommended analysis path:

1. Identify candidate library exports, message packer and IPC send sink without executing the proprietary binary.
2. Trace only to source-owned/lawful vendor symbols or function offsets.
3. Recover message header shape and candidate command bytes **offline**; annotate exact offsets and validation path.
4. Classify each recovered command by component (SIM, network, data, system, RFS) with evidence grade.
5. Cross-check the candidate packet structure against the *pinned* SIPC5 kernel framing contract.
6. Use original corpus of safe recorded traffic for cross-validation where permitted.
7. Do not connect vendor research tooling to live modem for automatic command execution.

Avoid BaseMirror's `automatic-testing` and attack discovery sections for this task. Only static analysis is in scope.

## Phase 4 — Build a traceable command matrix

Fill `data/telephony-command-matrix.csv`. Example required provenance fields:

`feature,request_name,header_bytes,payload_layout,source_file,source_version,function_or_offset,evidence_level,live_validation,status_notes`

Evidence levels:

- `O1_LINK_HEADER`: public kernel confirms framing.
- `O2_UNSOLICITED_RX`: live CP→AP event captured, no request semantics.
- `O3_STATIC_CANDIDATE`: static vendor-RIL evidence, not corroborated.
- `O4_CORROBORATED_SEMANTICS`: two independent sources/observations support meaning.
- `O5_AUTHORIZED_BIDIRECTIONAL`: exact, safe permitted AP→CP/CP→AP exchange observed.
- `O6_FUNCTIONAL_OUTCOME`: modem-reported SIM/registration/data verified with external network outcome where relevant.

No O3-only command goes to a live CP. If a command touches SIM credentials, NV/EFS, radio-power state, transmit parameters or network attachment, separate authorization and appropriate safeguards are necessary.

## Phase 5 — RFS dependency analysis

Keep `DELETE_ALL_VIS` fail-closed. The string might be an operation label or resource name; semantic inference is not established. Check whether CP actually requires a response to progress; do **not** assume that every unsolicited RFS frame requires a reply. Do not mount or expose protected NV/EFS. Use `RFS-FORENSICS.md` for exact known/unknown fields.

Safe alternatives for research include simulator-only regression tests or read-only captured metadata already authorized for offline analysis. Do not infer ACK status bytes or fabricate OK replies.

## Phase 6 — Stage 06 gate reviews

Before enabling any AP→CP messaging, require:

- Correct original CP ONLINE with recorded boot ID.
- One daemon holding endpoints, transport and kernel UAPI contract reviewed.
- Candidate message ID and payload evidence rated O4 or stronger.
- Operation categorization and explicit owner approval for the exact live operation.
- Disconnection safety and receive/reassembly regressions green.
- Private data redaction and no writes outside authorized userspace work.

Do not treat an automatic recovery of systemd `nuxel-radiod` as a license to automatically reboot the CP.

## Phase 7 — Finished work product expected from DeepSeek

- `reports/S5000AP-06-TELEPHONY-PROTOCOL.md`: source matrix, ELF fingerprints, dialect, offsets, unknowns, error cases, no proprietary data copied into public repo.
- Unit tests for any new **source-backed** packet parser/packer.
- Verified SIM status through the modem, if possible; separate positive assertion from `ds_detect=1`.
- LTE registration and data only after verified command protocol and registration allowed by carrier/SIM.
- If a blocking unknown survives, a sharply bounded proof obligation and exact minimal owner action; do not claim Stage 06 fully passed.
