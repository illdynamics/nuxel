# Nuxel SSP Recovery V2 — audited continuation toolkit

**Read this first:** this is an engineering/research kit, not a firmware flasher or a working BCM47752 driver. ZIP deliberately excludes redistributed vendor Bionic runtime and new firmware. The existing repository already contains the recovered Samsung vendor binary/HAL, plus a purported matching embedded firmware patch in a kernel build tree omitted from the ZIP.

## Files

- `01_DEEP_AUDIT_2026-11-16.md` — deep comparison, important contradictions, current blockers, source links and test results.
- `02_AGENT_CONTINUE_SSP_UNTIL_VERIFIED.md` — full standalone agent handoff; give this to your coding agent after extraction.
- `ssp_stock_collect.py` — explicit read-only ADB collection of matching stock system/vendor linker and recursive ELF dependencies. Refuses a mismatched source set. `--collect-readonly` is required for device reads; without it, plan only.
- `ssp_trial_prepare.py` — host-only hardware-denied config for existing `lhd` sandbox plus SHA-256 inventory, no daemon execution.
- `ssp_live_snapshot.py` — explicit read-only SSH sensor sample capture (`--capture-readonly`), classification with no fabricated success.
- `test_recovery_v2.py` — offline unit tests (11 passed on 2026-11-17; original kit had 9).
- `current_archive_audit/` — reproduced original audit JSON and Markdown, showing missing 14 library names across 28 dependency occurrences.

## Install on Mac (in existing working tree)

Unzip `NUXEL_SSP_RECOVERY_V2_KIT.zip` into the **existing** Nuxel Git checkout containing the first-light commits. Expected directory:

```
/Users/wicked/x/nuxel-ssp-first-light/
  NUXEL_SSP_RECOVERY_V2/
    README.md
    01_DEEP_AUDIT_2026-11-16.md
    02_AGENT_CONTINUE_SSP_UNTIL_VERIFIED.md
    ssp_stock_collect.py
    ssp_trial_prepare.py
    ssp_live_snapshot.py
    test_recovery_v2.py
```

Do not overwrite your existing Git checkout with the uploaded ZIP. Back up / commit existing work first.

```bash
cd /Users/wicked/x/nuxel-ssp-first-light
unzip -n ~/Downloads/NUXEL_SSP_RECOVERY_V2_KIT.zip
python3 -S -m unittest discover -s NUXEL_SSP_RECOVERY_V2 -p 'test_recovery_v2.py' -v
python3 -S NUXEL_SSP_RECOVERY_V2/ssp_stock_collect.py \
  --repo-root . --output /tmp/nuxel-ssp-stock-from-owner
```

The last command is a **plan only** by default. Next, hand the full prompt `NUXEL_SSP_RECOVERY_V2/02_AGENT_CONTINUE_SSP_UNTIL_VERIFIED.md` to your agent. It will select the right read-only acquisition workflow when the matching stock system image and handset connectivity are available. **Do not run firmware upload, GPIO reset or flash as the next automatic step.**

## What may prevent completion in this agent turn

The uploaded ZIP has no matching stock Android `/system/bin/linker64` or full Bionic/VNDK/APEX library closure, and no live attached phone. Web research yielded upstream compatibility references, **not** a trustworthy exact replacement firmware or an authenticated matching stock Android system image. The collector cannot invent those missing bytes; the owner must supply the version-matched stock system or mount it read-only in recovery.

## Safety and rollback

- The scripts do **not** write to device nodes or partitions; the collector uses read-only `cat`, the sample tool uses read-only `uname`/`cat`, and the trial helper writes only host staged files.
- The isolated trial helper does not make Samsung `lhd` safe to run with real hardware; it prepares a **hardware-denied config** for a separately audited sandbox.
- Full firmware upload must remain disabled until the original vendor handshake/ACK state machine and recovery strategy are verified. No guarantees of hardware success or boot safety are possible from archive-only analysis.

## Reproducible SSH capture with a dedicated key

```sh
python3 -S NUXEL_SSP_RECOVERY_V2/ssp_live_snapshot.py \
  --host 10.11.12.99 --ssh-user root \
  --identity-file ~wicked/.ssh/wicked_wqn_id_rsa \
  --output /tmp/ssp-new-samples.json --samples 12 --interval .75 --capture-readonly
```

Each sample records host UTC start/end times and the observed kernel. The key is
passed directly to SSH; its contents and path are not saved in the report.
Non-finite vectors (NaN/infinity) are rejected as invalid evidence.
