# PWNAGE-12000 — NEXUS + NEO Phase 2 Kickstarter

**Execution prompt**  
**Authoritative specification:** `full-pwnage-12000.md`  
**Prerequisites:** Phase 0 baseline and Phase 1 observer/confirmation framework accepted  
**Mission:** implement damage-driven capture in the existing A67 fbdev presenter as a reversible NEO canary.

## Execute this mission

Read `full-pwnage-12000.md` completely, along with the NEXUS/NEO specification and Phase 0/1 evidence. Work in the current Nuxel checkout. Re-verify the live S10+, current panel owner, deployed legacy presenter hash and rollback path before making any changes.

Connect using the established authenticated WLAN route:

```bash
cd ~/x/nuxel
KEY="$HOME/.ssh/wicked_wqn_id_rsa"
test -r "$KEY"
./scripts/s10plus-debug-pack/nuxel-live-ssh.sh \
  --transport wlan --host 192.168.178.167 \
  --user root --key "$KEY" --status
```

Inspect the helper CLI if necessary. Direct fallback is `ssh -i ~/.ssh/wicked_wqn_id_rsa root@192.168.178.167`. Never weaken host-key checking.

## Implementation focus

Use the screencopy protocol already in the repository: v3 manager/frame interfaces with `copy_with_damage` and `damage` since v2. The current A67 presenter still calls ordinary `copy()` and its damage callback ignores rectangle coordinates before full-row comparison. Add a damage-aware path that validates and unions protocol rectangles, preserves the first/wake full repaint, remains responsive to the display-control FD while the protocol waits for damage, and retains a full-copy fallback.

Preserve the cached SHM buffers, previous-frame correctness, NEON scaler, partial-row updates, required `FBIOPAN_DISPLAY`, single panel owner, 20 FPS active cap, 8/3/1 idle backoff, display-off stop and wake/backlight ordering. Do not modify DMA-BUF, KMS, WebKit, GPU renderer, kernel or frame-rate policy.

## Mandatory confirmation and rollback

The existing current graphics engine must remain installed and recoverable. Build the NEO damage candidate separately; never overwrite the only legacy binary or let two processes own the panel.

For every physical canary activation, show the on-phone question: **“NEO graphics test: Can you see the Nuxel display working correctly?”** with **YES** and **NO**. The owner must physically press YES within 30 seconds for that unique run. NO, timeout, missing/hidden prompt, candidate crash or failed display means immediate rollback to the exact legacy presenter. Diagnose, implement a material fix and retry with a new run ID when safe. Never accept SSH/log/mock confirmation. A prior YES never approves a later binary or run.

## Finish line

Implement `legacy-full-copy` as the unchanged default and `neo-copy-with-damage` as an opt-in candidate. Add shadow full-frame validation, host tests, physical scenario tests, metrics and rollback drills. Keep legacy permanently available. Keep the 20 FPS policy fixed so the damage-path result is isolated. Only report a performance gain if repeated measurements prove a reduction in actual workload without visual, touch, wake, thermal or power regression.

If Phase 0/1 prerequisites, physical access, notification confirmation or fallback integrity are missing, do host-side work only and leave the phone on legacy. Do not bypass a gate.

Read and execute `full-pwnage-12000.md` now. Finish with a measured Phase 2 report and go/no-go for subsequent NEO work.
