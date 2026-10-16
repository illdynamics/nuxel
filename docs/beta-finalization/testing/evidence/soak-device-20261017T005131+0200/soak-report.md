# Soak / performance report

- **generated:** 2026-10-17T00:51:31+0200
- **mode:** device
- **verdict:** BLOCKED_EXTERNAL_RESOURCE
- **terminal state:** BLOCKED_EXTERNAL_RESOURCE
- **samples:** 0

## Blocked

the live S10+ USB console is not reachable from this execution environment (see docs/beta-finalization/preflight/ENVIRONMENT.md section 6); retry with the handset booted into Nuxel and the live console enumerated

## Criteria

- `S0-no-resource` **FAIL** — the live S10+ USB console is not reachable from this execution environment (see docs/beta-finalization/preflight/ENVIRONMENT.md section 6); retry with the handset booted into Nuxel and the live console enumerated

## Statistics

```
```

## Load-average note

load1 on the S10+ is dominated by Samsung vendor kernel threads (TrustZone/RPMB/REE time), per the A31 finding; it is recorded but never gated.

_A passing soak proves stability over the sampled window. It never proves that untested hardware works._
