# PWNAGE-60000 evidence index

All data was collected from the physical S10+ (`root@10.20.30.16`) unless a
file explicitly says it is a synthetic/offline test.

| Directory | Contents |
|---|---|
| `baseline/` | pre-change identity, GPU libraries/FDs, WebKit software state, probes |
| `live/` | post-deploy, fallback, cold-boot, API and final status captures |
| `bench/final/` | final 3 × 60 s matched A/B (idle + Settings scroll), raw JSON and `SUMMARY.json` |
| `bench/final-invalid-screenoff/` | discarded run where panel blanking stopped the bridge; retained to show what was rejected |
| `webkit/` | WebKitGTK 2.54.1 source files, `drmMainDevice` analysis and live libdrm probe |
| `mfc/` | MFC DT/driver/firmware evidence and exact blocker |
| `typec/` | read-only USB-C/DP Alt Mode diagnostics |
| `cast/` | read-only P2P/capture/encoder capability diagnostics |
| `deploy/` | deploy logs, rollback proof, installed hashes |
| `tests/` | targeted pytest result |

## Reproduction commands

```sh
# host tests
python3 -m pytest -q tests/pwnage52000 tests/pwnage50000 tests/pwnage53000 tests/pwnage60000

# live status
ssh -i ~/.ssh/wicked_wqn_id_rsa root@10.20.30.16 \
  '/usr/lib/nuxel/nuxel-gpu-status --deep --json'

# match A/B (takes ~15 min; restores GPU at the end)
tools/s10plus/a67/run-pwnage60000-final-ab.sh root@10.20.30.16

# deploy / rollback
tools/s10plus/a67/deploy-pwnage60000.sh root@10.20.30.16
tools/s10plus/a67/rollback-pwnage60000.sh root@10.20.30.16 [backup]
```

## Measurement caveats

- CPU is userspace ticks for the measured UI processes normalized to one core.
  It is not whole-device CPU and not FPS/battery.
- The 11 Samsung TrustZone/secure-monitor kthreads in D state inflate load
  average; load average is not used as a CPU metric.
- The Settings scroll workload is a synthetic bounded wheel stream, not touch.
- `nuxel-wl-fb` still CPU-copies/scales; zero-copy scanout is false.
