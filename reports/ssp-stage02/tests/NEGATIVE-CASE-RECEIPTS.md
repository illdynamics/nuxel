# SSP Stage 02 — Negative-Case Test Receipts

Offline host tests.  They do not touch the device.  They assert the structural
behaviour the prompt requires and mirror the corrected kernel code paths.

## `test_ssp_patch_negative_cases.py` (purely-logic mirror)

Result: **8/8 PASS**

| # | Case | Expected | Observed |
|---|------|----------|----------|
| 1 | truncated F1 record | hard-fail (TRUNCATED) | PASS |
| 2 | F1 with len<4 | MALFORMED | PASS |
| 3 | valid F0 record | OTHER (valid, not dispatched) | PASS |
| 4 | BlobLength != decoded | reject | PASS (`declared 5 != decoded 4`) |
| 5 | BlobLength == decoded | accept | PASS (`deadbeef`) |
| 6 | odd hex digits | reject | PASS (`odd hex`) |
| 7 | blob > DL_MAX_BLOB | refuse before allocation | PASS (would allocate 524310 > cap) |
| 8 | text `Crc` value | not an IEEE CRC32 / not a hex PatchAddress | PASS (documented separation) |

Run:  `cd reports/ssp-stage02/tests && python3 test_ssp_patch_negative_cases.py`

## `test_ssp_lock_deadlock_static.py` (scans the applied source)

Result: **PASS**

- `pending_mutex` locked exactly once on the failure path (no self-deadlock).
- `pending_mutex` unlock == lock (balanced).
- `clean_msg(msg)` runs after both `pending_mutex` and `comm_mutex` are released.
- `comm_mutex` is released on the failure path.

Run:  `cd reports/ssp-stage02/tests && python3 test_ssp_lock_deadlock_static.py`

## Compile receipt (cross)

```
aarch64-unknown-linux-gnu-gcc (GCC 15.2.0)
...
drivers/sensorhub/brcm/ssp_bbd.o      -> built, 0 warnings
drivers/sensorhub/brcm/ssp_dev.o      -> built
drivers/sensorhub/brcm/ssp_sysfs.o    -> built
drivers/sensorhub/brcm/ssp_i2c.o      -> built
drivers/sensorhub/brcm/bbdpl/bbd.o    -> built
drivers/sensorhub/brcm/bbdpl/bcm_gps_spi.o -> built (pre-existing vendor warnings only)
drivers/sensorhub/brcm/factory/gyro_lsm6dsl.o -> built
```

Only pre-existing vendor warnings remain (unused `flags` in `bcm_gps_spi.c`, a
`-Wformat` in unrelated logs); all are downgraded to non-fatal by the existing
`-Wno-error` KCFLAGS in `kernel/s10plus/build-kernel.sh`.
