# nuxel-modem Stage-05 — RFS + SIPC5 + native radio daemon groundwork

SPDX-License-Identifier: GPL-2.0-only (code) / CC-BY-SA-4.0 (docs)

This directory contains the SAFE, fully host-testable portion of Stage-05. It
does NOT claim any live CP protocol success and does NOT fabricate radio state.

## Components

| File | Purpose | Safe-by-default |
|---|---|---|
| `src/sipc5_fmt.h/.c` | SIPC5 link-header + SIPC FORMAT message parser (clean-room from pinned kernel `sipc5.h`/`modem_prj.h`) | parse-only, no writes |
| `src/rfs_policy.h/.c` | FAIL-CLOSED RFS path/access validator (allowlist, traversal/symlink/hardlink/device/protected-prefix rejection) | deny-all default |
| `tests/test_sipc5_fmt.c` | 27 unit assertions incl. ABI sizes, truncation, overflow, bad-start | — |
| `tests/test_rfs_policy.c` | 18 unit assertions incl. traversal, symlink, hardlink, protected prefixes, write-downgrade | — |
| `tests/fuzz_driver.c` + `tests/fuzz_sipc5.py` | mutational fuzzer (memory/time capped) + ASan/UBSan gate | no writes, never prints payload |
| `dbus/nl.nuxel.Radio1.xml` | versioned D-Bus API contract (v1) | read-only defaults, auth for writes |
| `dbus/nl.nuxel.radiod.policy`, `.conf` | polkit + bus policy | default-deny |
| `ARCHITECTURE-DECISION.md` | Sub-job C decision matrix | — |

## Build & test

```sh
./build.sh          # builds + runs unit + fuzz + ASan gates
./build.sh clean
```

## Truth contract

`nuxel-radiod` "ONLINE" means **daemon alive**, never modem/cellular available.
All modem-derived fields are populated only from a real modem source; otherwise
they are absent/reported `supported=false`. The closed Samsung RIL/RFS message
vocabulary is `UNKNOWN` and is NOT fabricated.
