# PWNAGE-10000 — NEXUS + NEO Phase 0 Kickstarter

**Execution prompt**  
**Authoritative specification:** `full-pwnage-10000.md`  
**Target:** Nuxel `v0.8.1-beta` lineage; Galaxy S10+ `SM-G975F` / `beyond2lte`  
**Mission:** freeze and measure the current known-good graphics system before implementing NEO.

## Execute this mission

Read `full-pwnage-10000.md` completely and follow it as the authoritative Phase 0 specification. This is an execution task, not a request to produce another plan. Work in the current checked-out Nuxel repository, inspect the live phone over WLAN SSH, collect evidence, create the baseline artifacts and run the safe tests.

Start with:

```bash
cd ~/x/nuxel
git rev-parse --show-toplevel
git rev-parse HEAD
git status --short
KEY="$HOME/.ssh/wicked_wqn_id_rsa"
test -r "$KEY"
./scripts/s10plus-debug-pack/nuxel-live-ssh.sh \
  --transport wlan --host 192.168.178.167 \
  --user root --key "$KEY" --status
```

If the helper syntax differs, inspect it and use its supported form. Direct fallback connection is `ssh -i ~/.ssh/wicked_wqn_id_rsa root@192.168.178.167`. Keep SSH host-key checking enabled. Do not expose key contents.

## Critical guardrails

- **Phase 0 is read-only with respect to active graphics.** Do not activate NEO, change the display bridge, switch frame rate, restart Phoc/presenter, change the kernel or deploy a candidate.
- The existing Phoc/Mali GLES + `nuxel-wl-fb` + `/dev/fb0` path is the tested working fallback. Preserve it permanently, record its installed binary and service hashes, and do not overwrite it.
- Do not enable DRM/KMS, DMA-BUF presentation or the previous crashing wlroots/Mesa canary.
- Do not rewrite the NEON scaler, SHM buffer reuse, partial-row blits, FBIOPAN commit, idle backoff or screen-off/wake logic.
- Inspect and document the actual notification stack and design the required physical YES/NO confirmation UI. Do not activate a candidate or ask for a canary confirmation in Phase 0.

## Required output

Create `docs/nexus-neo/phase-0/` with the baseline, source map, live capability JSON, service/panel ownership map, performance measurements, fallback integrity proof, confirmation design, issues and timestamped sanitized evidence. Run the applicable non-invasive tests and record exact commands, exit codes and limitations.

Use the current source as truth; verify historical audit claims against the live device. If SSH or a workload blocks physical evidence, report it honestly and continue all host-side work. Do not claim live validation you did not perform.

## Finish line

Phase 0 is complete only when the actual renderer-to-panel path, active panel owner, current binary and recovery method, GPU/DRM/SHM/DMA-BUF capability states, frame timing baseline and notification-confirmation design are documented and reproducible, with no active graphics change.

Read and execute `full-pwnage-10000.md` now. Finish with a Phase 0 go/no-go report for Phase 1.
