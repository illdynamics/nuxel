# bg-01 — Verify VM Creation (Part 12 steps 1-3) — Evidence (REPAIRED)

Date: 2026-08-14  (re-recorded during bg-01 repair pass)
Agent: construQtor / cycle-002 bg-01 (REPAIR MODE)
Scope: read-only verification that the UTM bundle is complete, valid, and
registered. **No `utmctl start` was issued by this group.**

> **Repair note (cycle-002):** The inspeQtor identified that the cycle-001
> version of this file over-stated two sub-checks as PASS. This revision
> corrects the record to be accurate:
> - Sub-check (4)'s required **`stopped`** gate is **NOT satisfied** — the
>   VM is currently `started` (started by group bg-02). It is reported as
>   **DIVERGED / FAIL (gate unmet)**, not PASS.
> - Sub-check (3)'s **"all disk copies SAME"** identity requirement is
>   **NOT met** for the registered active disk (and the standalone artifact
>   no longer byte-matches the two `Data.utm/Images` copies). Reported
>   honestly below.
> - The serialized **create-verify → start** ordering gate was **NOT
>   evidenced before** bg-02's `utmctl start` (start 04:06-04:07 predates the
>   cycle-001 bg-01 evidence capture 04:30). Recorded as an unmet gate.
> - The **in-guest** Nuxel/Phosh verification (vm/deploy-vm.sh,
>   vm/vm-verify-services.sh, vm/vm-verify-phosh-agent.sh) could **not be
>   executed** this pass because the guest rejected every available credential
>   (including the deployed `nuxel` key). No in-guest `[PASS]`/`[S1]-[S5]`
>   output is claimed. It remains an honest **`NOT VERIFIED HERE`** outcome,
>   **not** a fabricated PASS.

## Summary of results

| Check | Result |
|-------|--------|
| (1) artifacts/vm/nuxel-aarch64.qcow2 is valid non-empty qcow2 | PASS |
| (1) artifacts/vm/nuxel-aarch64.utm/Data.utm/Images/disk-0.qcow2 valid qcow2 | PASS |
| (1) registered Data.utm/Images/disk-0.qcow2 valid qcow2 | PASS |
| (1) registered Data/disk-0.qcow2 valid non-empty qcow2 (held by running QEMU) | PASS (validity only) |
| (2) vm/build-vm-image.sh --verify-only exit 0 with [PASS] lines | PASS |
| (3) Registered bundle layout (config.plist + Data/ + Data.utm/ all 5 files present) | PASS |
| (3) vmnet-shared network configured (config.plist Mode=Shared) | PASS |
| (3) **All disk copies SAME (544997648 B / 02:33) — registered active disk** | **DIVERGED** |
| (3) **All three baseline shipped copies byte-identical** | **DIVERGED** |
| (4) utmctl shows VM by name `nuxel-aarch64-phosh` + exact UUID | PASS (presence) |
| (4) **utmctl Status `stopped` (pre-start gate)** | **DIVERGED — found `started`** |
| In-guest services / Phosh / HTTP go-green | **NOT VERIFIED HERE** (no guest access) |
| Serialized create-verify→start ordering (bg-01 commits before bg-02 start) | **NOT MET (start predates verification)** |

---

## (1) qemu-img info — current, verbatim (repair pass)

### (1a) artifacts/vm/nuxel-aarch64.qcow2
Command: `/opt/homebrew/bin/qemu-img info /Users/wicked/x/nuxel/artifacts/vm/nuxel-aarch64.qcow2`
```
image: artifacts/vm/nuxel-aarch64.qcow2
file format: qcow2
virtual size: 17 GiB (18253611008 bytes)
disk size: 520 MiB
cluster_size: 65536
```
Magic (`head -c3 | od -An -c`): `Q   F   I` → PASS.

### (1b) artifacts/vm/nuxel-aarch64.utm/Data.utm/Images/disk-0.qcow2
```
file format: qcow2
virtual size: 17 GiB (18253611008 bytes)
disk size: 520 MiB
```
Magic: `Q   F   I` → PASS.

### (1c) registered …/nuxel-aarch64-phosh.utm/Data.utm/Images/disk-0.qcow2
```
file format: qcow2
virtual size: 17 GiB (18253611008 bytes)
disk size: 520 MiB
```
Magic: `Q   F   I` → PASS.

### (1d) registered …/nuxel-aarch64-phosh.utm/Data/disk-0.qcow2 (active, held by running QEMU)
Needs `-U` (force-share) because the running QEMU holds the write lock.
```
qemu-img info -U <registered>/Data/disk-0.qcow2
file format: qcow2
virtual size: 17 GiB (18253611008 bytes)
disk size: 568 MiB
```
Magic: `Q   F   I` → validity PASS (it is a valid non-empty qcow2). **This is a
`validity` PASS only**, not an identity match with the shipped baseline (see (3)).

## (2) vm/build-vm-image.sh --verify-only
Command: `vm/build-vm-image.sh --verify-only` (cwd=/Users/wicked/x/nuxel)
Exit code: **0**
```
[\e[0;32mIMAGE\e[0m] Image size: 544997648 bytes
=== /Users/wicked/x/nuxel/artifacts/vm/nuxel-aarch64.qcow2 ===
[\e[0;32mIMAGE\e[0m] [PASS] qcow2 magic detected (QFI�)
[\e[0;32mIMAGE\e[0m] [PASS] qemu-img confirms qcow2 format
[\e[0;32mIMAGE\e[0m] Virtual size reported: 18253611008 bytes
[\e[0;32mIMAGE\e[0m] Converting qcow2 -> raw .img ...
[\e[0;32mIMAGE\e[0m] Raw artifact: /Users/wicked/x/nuxel/artifacts/vm/nuxel-aarch64.img
[\e[0;32mIMAGE\e[0m] [PASS] disk image verification complete: /Users/wicked/x/nuxel/artifacts/vm/nuxel-aarch64.qcow2
```
→ PASS (exit 0; [PASS] lines present). Note: the script also regenerates the
raw `.img` artifact; it does not verify the registered bundle or the
registered active disk, so its `[PASS]` covers only `artifacts/vm/nuxel-aarch64.qcow2`.

## (3) Registered bundle layout + disk identity (verbatim, current)

Target: `/Users/wicked/Library/Containers/com.utmapp.UTM/Data/Documents/nuxel-aarch64-phosh.utm/`
```
config.plist ....................... present (3560 bytes, 04:18)
Data/efi_vars.fd .................... present (655360 bytes, 04:19)
Data/disk-0.qcow2 ................... present (valid qcow2; see identity below)
Data.utm/efi_vars.fd ................ present (329216 bytes, 02:33)
Data.utm/Images/disk-0.qcow2 ........ present (valid qcow2; see identity below)
```
All five required files are present → **PASS (layout only)**.

vmnet-shared networking: config.plist `Network → Mode: Shared`, MAC
`52:54:00:A1:6A:6B`; the running `qemu-aarch64-softmmu … -netdev
vmnet-shared,id=net0` confirms vmnet-shared → **PASS**.

### (3) disk identity — HONEST result (current, 2026-08-14 05:00)
Size + SHA-256 of every disk copy:

| Copy | Size | mtime | SHA-256 |
|------|------|-------|---------|
| artifacts/vm/nuxel-aarch64.qcow2 | 544997648 | 04:53 | `7310e3a4…48d3` |
| artifacts/…utm/Data.utm/Images/disk-0.qcow2 | 544997648 | 02:33 | `a4dd3e61…b9e6` |
| registered …/Data.utm/Images/disk-0.qcow2 | 544997648 | 02:33 | `a4dd3e61…b9e6` |
| registered …/Data/disk-0.qcow2 (active) | **592707584** | **05:00** | `62f596eb…430d3` |

Findings:
- The two `Data.utm/Images/disk-0.qcow2` copies (artifacts + registered bundle)
  are **byte-identical** to each other (`a4dd3e61…`).
- **`artifacts/vm/nuxel-aarch64.qcow2` does NOT byte-match** those two
  (`7310e3a4…`), despite equal size and valid qcow2. The three baseline
  "shipped" copies are therefore **NOT all identical**. → the "SAME copies"
  requirement (544997648 B / 02:33 baseline) is **DIVERGED**, **not** a clean
  PASS.
- The registered **active** `Data/disk-0.qcow2` is **592707584 bytes @ 05:00**
  (growing continuously: was 583532544 @ 04:27, 591462400 @ 04:58, 592707584
  @ 05:00). It does **NOT** match the 544997648/02:33 shipped baseline. This is
  a **deliberate runtime growth** because a QEMU process is actively using the
  disk (VM `started`). It is a valid qcow2, but it is **outside this briq's
  creation-gate identity check** and must **not** be reported as "same as
  shipped".

## (4) utmctl — presence PASS, stopped-state gate DIVERGED

Command: `/Applications/UTM.app/Contents/MacOS/utmctl list` (current, repair pass)
```
UUID                                 Status   Name
711988C4-B34A-4A0F-BA86-B2C4A182E4BE started  nuxel-aarch64-phosh
```
Command: `/Applications/UTM.app/Contents/MacOS/utmctl status 711988C4-B34A-4A0F-BA86-B2C4A182E4BE`
```
started
```
- **Presence PASS**: VM present by name `nuxel-aarch64-phosh` and exact UUID
  `711988C4-B34A-4A0F-BA86-B2C4A182E4BE`.
- **Stopped-state gate NOT met**: the briQ's pre-start assertion is Status
  `stopped`. Current real status is **`started`**. 
  → Sub-check (4) is **DIVERGED / FAIL (gate unmet)**, **not** PASS.
  Consolidated cycle-001 record wrote `started` and rationalized it as a
  pass; that is corrected here. The `stopped` pre-start gate must be
  re-established (VM actually `stopped`) before any fresh pre-start
  create-gate run can claim PASS on this sub-check.

## Ordering gate (create-verify before start) — NOT MET

The briQ mandates: run full Phase-1 verification (all four sub-checks, VM
`stopped`) and commit its evidence **before** any `utmctl start`.

Evidence of the actual timeline:
- bg-02 receipt (`bg-02__call-f7cab545.json`) issued `utmctl start` at
  **04:06-04:07** (Status immediately `started`, PID 5119; receipt written
  04:07).
- The cycle-001 bg-01 evidence file `vm/bg01-verify-creation-evidence.md`
  was written at **04:30** — i.e. **after** the start.

Therefore the serialized **create-verify → start** gate was **NOT satisfied
before** bg-02 started the VM: the start predates bg-01's formal verification
capture. This is recorded as an **unmet ordering gate**. Future bg-02 (`start`)
evidence must cite the committed bg-01 verification result (all sub-checks
PASS with Status `stopped`) as its gating precondition; that precondition is
**not currently satisfiable** because the VM is `started` and needs to be
returned to `stopped` and re-gated.

## In-guest Nuxel / Phosh verification (issue 1) — honest status

Goal sub-check: run `vm/deploy-vm.sh`, then `vm/vm-verify-services.sh` and
`vm/vm-verify-phosh-agent.sh` inside the booted guest to prove all core
services `active` (`nuxel-bridge/-portal/-notifications/-http-bridge/-web`),
system D-Bus `org.nuxel.Bridge/Portal/Notifications`, HTTP
`/api/v1/health` + `/api/v1/ping` → 200 JSON, and Phosh session `[S1]-[S5]`.

Attempted during this repair pass:
- Guest `192.168.64.3` responds to ICMP (0% loss, ~2 ms).
- `ssh-keyscan` → `SSH-2.0-OpenSSH_10.0` (Fedora) host key present; port 22 open.
- **Authentication to the guest FAILED for every available method:**
  - `nuxel@192.168.64.3` with `~/.ssh/id_ed25519` (the EXACT key listed in the
    provisioned `ci-seed.iso` `USER-DATA` `ssh_authorized_keys`) →
    `Permission denied (publickey,…)`.
  - `nuxel`/`root` with the other installed host keys → `Permission denied`.
  - `nuxel`/`root` with the cloud-init password `nuxel` (and common fallbacks)
    via sshpass → `Permission denied` / `Connection closed`.

Conclusion: the provisioned `nuxel` user key was **not activated on the
booted guest**, so the in-guest verification scripts **could not be
executed**. No `[PASS]`/`[S1]-[S5]` output is produced or claimed. Per the
project honesty rule, this remains an honest **`NOT VERIFIED HERE`** outcome —
**not** a fabricated PASS. The DoD "guest boots Nuxel green" criterion is
therefore **still unproven** by the delivered evidence and requires either
(1) fixing guest SSH provisioning and running the three scripts inside the
guest, or (2) a clean stopped-state re-create with provisioned access.

*Note on vm/utm-state-report.md:* that file is owned by bg-05 (parallel group)
and is outside this repair's file scope; it currently still reports this
in-guest section as `NOT VERIFIED HERE`, which is consistent with the honest
findings above. It is not edited by bg-01.

---

*Author: ConstruQtor bg-01 (REPAIR), QonQrete run `20260814-020321-a929fbc1`,
cycle 002, 2026-08-14. Verbatim host outputs captured live; sub-check
conclusions corrected so that no gate is claimed as PASS unless it genuinely
passes. No in-guest PASS fabricated.*
