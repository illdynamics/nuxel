# Area 24 — NFC (S10+ / beyond2lte)

**Status: NEEDS_OWNER_TEST** (repository side: OFFLINE_TESTED for config + diagnostic).
Owner action required? **Yes** — an NFC read needs a physical tag.

**Device truth used by this document.** Samsung Galaxy S10+ (SM-G975F, Exynos
9820): the NFC controller is a Samsung **sec-nfc (S3FWRN5-family)** part at
**I2C 0x27** with an embedded secure element (beyond2lte DTS, see
`docs/hardware-ids.md`). Which of controller node / firmware / kernel NFC
subsystem / userspace stack are actually present is **enumerated per stage** by
`nuxel-nfc-diag.sh`. **Configuration alone is never a working NFC**, and no UID
is ever fabricated — the honest verdict may well be `BLOCKED_KERNEL` or
`NOT_SUPPORTED_ON_DEVICE` on this vendor kernel.

---

## 1. Feature

* `configs/nuxel/nfc/nfc.json` — evidence sources, the stage order
  (`controller → firmware → subsystem → stack → tag`), the verdict set and the
  owner tag procedure.
* `tools/s10plus/a33/nuxel-nfc-diag.sh` — `status`, `firmware`, bounded `read`,
  `report`, `selftest`.

## 2. Why this matters

NFC is used for tags, transit and pairing, and it is exactly the subsystem where
a vendor kernel most often exposes *nothing usable*. The mission's evidence rule
forbids inventing a UID or claiming a read: this diagnostic names the **first
failing stage** with the evidence that produced it, and the terminal verdict
stays `NEEDS_OWNER_TEST` until a real tag is tapped and its UID matches a second
read of a different tag.

## 3. Preparation

1. Handset booted into Nuxel, screen on, **not** in charger-mode.
2. **Any NFC tag**: an NTAG213/215/216 sticker or a MIFARE Classic card, whose
   UID you know (printed on the tag, or readable with any other NFC phone).
   Have a **second, different tag** available for the cross-check.
3. Console/SSH or the on-device terminal.
4. Snapshot first:

   ```sh
   nuxel-nfc-diag.sh status          # per-stage evidence + first failing stage + verdict
   nuxel-nfc-diag.sh status --json
   nuxel-nfc-diag.sh firmware        # firmware candidate inventory
   ```

   * `BLOCKED_KERNEL` (stage `controller`) → no controller node and no NFC
     module. This is kernel/driver-side (offline work). If the vendor kernel
     offers no supported path at all, record `NOT_SUPPORTED_ON_DEVICE` — do not
     retry.
   * `BLOCKED_FIRMWARE` → deploy the blob into `/lib/firmware/nfc` (a
     repository-only step; **never** a partition write).
   * `BLOCKED_EXTERNAL_RESOURCE` (stage `stack`) → no `neard`/`nfc-list` on the
     image; nothing can talk to the controller, so stop and record it.

## 4. Exact action

Only continue when the verdict is `READY_FOR_TAG`.

1. **Start the reader** (bounded): `nuxel-nfc-diag.sh read 15` — it runs the real
   client (`nfc-list`) and prints whatever it reports.
2. **Tap tag #1:** place it flat on the **upper back** of the phone, near the
   camera, and hold for ~2 s. The reader must report one tag with a **UID**.
3. **Compare the UID** with the physical tag's known UID:
   `04:A1:B2:C3:D4:E5:F6` is only the *format* — the digits must be *your* tag's.
4. **Cross-check with tag #2** (different tag): repeat step 2–3; the UID must be
   **different**. A reader that returns the same UID for two different tags has
   not read anything.
5. **Remove the tag** and repeat the read; no tag must be reported (a phantom
   tag is a failure, not a success).
6. Save the evidence: `nuxel-nfc-diag.sh report` plus the module/`dmesg` lines
   from §7.

## 5. Expected result

* `status` prints each stage's real evidence and the first failing stage.
* With a usable stack, `read 15` reports exactly one tag per tap, with a UID that
  matches the physical tag, and a **different** UID for a different tag.
* Removing the tag yields no tag reported.
* If any stage is missing, the verdict is the honest `BLOCKED_KERNEL` /
  `BLOCKED_FIRMWARE` / `BLOCKED_EXTERNAL_RESOURCE` / `NOT_SUPPORTED_ON_DEVICE` —
  and **no UID is claimed**.

## 6. Failure symptoms (and what each one means)

| Symptom | Meaning |
|---|---|
| `controller : absent` → `BLOCKED_KERNEL` | No `nfc` module/char device/sysfs class and no I2C hint. Vendor kernel gap; offline driver work. If there is no supported path, mark `NOT_SUPPORTED_ON_DEVICE`. |
| `firmware : missing` → `BLOCKED_FIRMWARE` | Controller/module path present but no NFC firmware blob: deploy into `/lib/firmware/nfc`, never by flashing. |
| `stack : no-stack` → `BLOCKED_EXTERNAL_RESOURCE` | Kernel NFC is up but `neard`/`nfc-list` is absent: a package-completion issue. |
| `read` reports the tag but the UID is all zeros / constant | The read is not real; capture `dmesg | grep -i -E 'nfc|sec-nfc|s3fwrn5'` and report FAIL. |
| Tag never detected (with `READY_FOR_TAG`) | Try the documented position (upper back, flat), a different tag type, and a longer hold; after three same-mode attempts, change strategy (antenna position vs. driver) — do not loop. |
| `read` hangs | The timeout is the fix: `nuxel-nfc-diag.sh read 5`; if it still hangs, capture the client's stack and report. |

## 7. Diagnostic command / log path

* `nuxel-nfc-diag.sh status | firmware | read [secs] | report`
  (`tools/s10plus/a33/nuxel-nfc-diag.sh`)
* Evidence log: `/var/log/nuxel/nfc-diag.log`
* Kernel side: `dmesg | grep -i -E 'nfc|sec-nfc|s3fwrn5|nci|i2c.*0027'`;
  `ls -l /sys/class/nfc /dev/nfc* 2>/dev/null`;
  `cat /proc/modules | grep -i nfc`
* Userspace: `systemctl status neard --no-pager`; `journalctl -b -u neard --no-pager | tail -100`
* Offline suite: `python3 tools/s10plus/a33/tests/hw-subsystems/test-nfc-diag.py`
  and `nuxel-nfc-diag.sh selftest` (4 fixtures: absent / no-firmware / no-stack /
  ready-for-tag).

## 8. PASS / FAIL

* **PASS** — steps 1–6 all hold: two different physical tags read with two
  different, matching UIDs, and no phantom tag when the tag is removed.
* **FAIL** — any of: a missing stage (`BLOCKED_*`), a UID that does not match the
  physical tag, a constant/zero UID, or a phantom read. Record the **exact verdict
  string, the first failing stage and the two UIDs** — that is what a repair
  cycle needs. Never record a UID you did not observe.

## Current automatic evidence (repository, this build group)

* `bash tools/s10plus/a33/nuxel-nfc-diag.sh selftest` → 4/4 fixtures PASS
  (`fixtures/nfc-absent`, `nfc-nofw`, `nfc-nostack`, `nfc-ready`).
* `python3 tools/s10plus/a33/tests/hw-subsystems/test-nfc-diag.py` → all checks
  PASS (stage/verdict logic, honest `BLOCKED_KERNEL`/`NOT_SUPPORTED_ON_DEVICE`
  posture, no fabricated UID, faked-root safety, fragment completeness).
* A real tag read: **not claimed** — every `status --json` emits
  `"tag_read_verified": false`, and the capability manifest keeps NFC at
  `NEEDS_OWNER_TEST` with the default derived from the real stages found.
