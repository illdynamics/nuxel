# Hardware-denied SSP runtime trial

Build the diagnostic helpers from source on a host with the AArch64 GNU
toolchain (tested with GCC 15.2.0):

```sh
make -C tools/s10plus/ssp-runtime OUT=/tmp/nuxel-ssp-helpers all check
```

The probe is static and has no ELF interpreter. The logging shim is freestanding,
has no DT_NEEDED entries, and resolves only `vsnprintf` and `write` from the
reviewed Android runtime. It does not substitute GPIO, Binder, properties or HALs.

Before staging a daemon trial, recover and review the **matching** Samsung
runtime and vendor hashes as required by the recovery mission. A dependency
closure or an Android 10 Halium image alone does not establish that match.
Keep proprietary files owner-local and outside Git.

In the host staging root, install the newly built probe at `isolation-probe`,
the shim at `system/lib64/libssp-log-stderr.so`, and create empty `proc`, `dev`,
`tmp`, `data`, `logs` directories. Generate the hardware-denied configuration
and a manifest covering **every regular file except the manifest itself**.
Symlinks, special files, missing hashes and unlisted files are refused. Retain
previous manifests/results separately; never overwrite evidence.

Transfer the reviewed root to a temporary directory on the phone. Run
`run_isolated.py --root ROOT --output NEW_RESULT_DIR --probe` first. Inspect
`stdout.log`, `syscalls.log`, and `result.json`: UID/GID 65534, zero effective
capabilities, NoNewPrivs, read-only runtime and denied hardware paths are
required. Only then, with the matched runtime reviewed, run a separate bounded
trial without `--probe`. No hardware mode exists.

A probe-only test can use the static probe plus the original `lhd` as a
read-only file fixture, with no Android linker/libraries. This tests isolation
only; it cannot execute `lhd` and says nothing about its ABI compatibility or
the sensor hub. The November 16, 2026 recovery report records such a live test.

No firmware upload, reset, power operation, or boot flash is authorized by
these commands. The native downloader's `--download` refusal remains in place.

For the matched Samsung Android 10 tree, `--stock-namespaces` uses only
`/vendor/lib64` in `LD_LIBRARY_PATH` and preloads the diagnostic shim from
`vendor/lib64/libssp-log-stderr.so`. Stage the unmodified stock
`system/etc/ld.config.29.txt` also as `system/etc/ld.config.txt`, together with
the referenced VNDK-29 variants and canonical runtime APEX files. This makes
the stock namespace policy select the VNDK dependencies; the broad static
resolver alone cannot do that. The flag requires the config in the integrity
manifest. Probe and daemon trials retain identical hardware restrictions.
Private `/tmp/nv` and `/tmp/log` directories support the vendor lock/log paths.
