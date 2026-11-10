# PWNAGE-11000 — NEXUS + NEO Phase 1 Kickstarter

**Execution prompt**  
**Authoritative specification:** `full-pwnage-11000.md`  
**Prerequisite:** Phase 0 baseline and fallback-integrity proof  
**Mission:** implement NEO's observe-only contracts, telemetry and the mandatory physical confirmation mechanism.

## Execute now

Read `full-pwnage-11000.md` completely, along with the Phase 0 reports and NEXUS/NEO engineering specification. Work in the current Nuxel checkout, revalidate the live S10+, implement the Phase 1 code/tests, deploy only the observer canary and prove it does not change the graphics output.

Use the known phone connection:

```bash
cd ~/x/nuxel
KEY="$HOME/.ssh/wicked_wqn_id_rsa"
test -r "$KEY"
./scripts/s10plus-debug-pack/nuxel-live-ssh.sh \
  --transport wlan --host 192.168.178.167 \
  --user root --key "$KEY" --status
```

Inspect the helper's actual CLI if needed; direct fallback is `ssh -i ~/.ssh/wicked_wqn_id_rsa root@192.168.178.167`. Keep strict host-key verification.

## Absolutely preserve

The known-good Phoc/Mali GLES + A67 `nuxel-wl-fb` + fbdev display engine remains installed, default and recoverable. Do not replace its binary/service or change its panel ownership. No `copy_with_damage`, DMA-BUF, KMS, direct scanout, FPS or kernel work in Phase 1. NEO is observe-only.

## Mandatory confirmation agreement

Before any NEO runtime activation on the phone, display the on-device question: **“NEO graphics test: Can you see the Nuxel display working correctly?”** with **YES** and **NO**. The owner must physically press YES within 30 seconds. NO, timeout, candidate crash or missing visible prompt means failure and immediate rollback to legacy. Fix the root cause and retry with a materially changed candidate when safe. Never accept SSH/log/mock YES as the live confirmation. Implement and test the independent supervisor/timer in this phase so Phase 2 can rely on it.

## Required finish line

Create NEO capability contracts, bounded telemetry, read-only status/probe/dump tools, confirmation UI/supervisor, tests, release hashes and Phase 1 evidence under `docs/nexus-neo/phase-1/`. Verify observer overhead and compare output against legacy. Keep NEO disabled by default after the test; do not promote it to the graphics path.

If the phone or notification mechanism is unavailable, finish host-side work, leave legacy active and report physical verification as blocked. Do not invent evidence.

Read and execute `full-pwnage-11000.md` now. Finish with an explicit Phase 2 go/no-go report.
