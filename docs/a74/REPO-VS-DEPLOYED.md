# NUXEL A74 / 23000 — Repo vs deployed

## Deployed artifacts

| file | role | owner process | reload |
|---|---|---|---|
| `/usr/lib/nuxel/nuxel-bridge/system_indicators.py` | indicator truth (Python) | `nuxel-http-bridge` (python3 PID 6464→restarted) | restart `nuxel-http-bridge.service` |
| `/usr/lib/nuxel/nuxel-pwa-host` | lockscreen native host indicator truth (C) | `nuxel-wayland` → `phoc -E nuxel-session.sh` (PID 9556) | restart `nuxel-wayland.service` |
| `/usr/lib/nuxel/a74-logger.sh` | bounded detach evidence logger | detached `sh` (PID 10287) | none (no-op until killed) |
| `/usr/lib/nuxel/a73-logger.sh` | **superseded stub** (refuses to run the unsafe sampler) | not running | none |

## sha256 — repo source vs deployed bytes
| repo path | repo sha256 | deployed path | deployed sha256 | match |
|---|---|---|---|---|
| `services/nuxel-bridge/src/system_indicators.py` | `d68c36318f4525263eca19c1f428d2ecc70fdfa86a6a663fb786a246db6b4a5a` | `/usr/lib/nuxel/nuxel-bridge/system_indicators.py` | `d68c3631…` | ✅ |
| `tools/s10plus/a45/nuxel-pwa-host.c` | `4860e52c66c88b5e9158beaef930b748de695aafa69b7c7bf840537973e2db02` | `/var/tmp/nuxel-pwa-host.c.a74` (staged source) | `4860e52c…` | ✅ |
| — (compiled binary) | — | `/usr/lib/nuxel/nuxel-pwa-host` | `07f6458141835df357f79780b855a1955e27cfaee26e2c340fe09670d245f2d7` | built from staged source |
| `docs/a74/a74-logger.sh` | `9c4cdfd9e559b1acd1100d6712ed4ff9dc592e635c4cdd9c1aad1fe7f3367dd2` | `/usr/lib/nuxel/a74-logger.sh` | `9c4cdfd9…` | ✅ |

## Backup hashes (rollback sources)
- `/var/lib/nuxel/a74-backup/bridge/system_indicators.py.pre-a74` = `93b2d3d0…bcf67c` (pre-A74)
- `/var/lib/nuxel/a74-backup/bin/nuxel-pwa-host.pre-a74` = `cff15529…36d33e3` (pre-A74)
