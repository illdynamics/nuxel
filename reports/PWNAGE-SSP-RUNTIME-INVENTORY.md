# PWNAGE-SSP — Runtime inventory (`./sensors/`)

Source: `sensors/acquired/` (operator-provided extraction pack from this handset).

| File | Bytes | Format / ABI | Verdict |
|---|---:|---|---|
| `vendor-bin-hw-lhd` | 318 024 | ELF64 aarch64, interpreter `/system/bin/linker64`, stripped | **not runnable under glibc** |
| `vendor-lib64-sensors.sensorhub.so` | 212 192 | Bionic shared object | not loadable (needs Android libc) |
| `vendor-lib64-hw-sensors.exynos9820.so` | 15 336 | Bionic HAL | not loadable |
| `vendor-etc-sensor-lhd.conf` | 1 264 | text config | read; paths match the live kernel nodes |

## `lhd` dependency closure (measured with `objdump -p`)

```
NEEDED liblog.so libutils.so libz.so libhardware_legacy.so libc++.so libc.so libm.so libdl.so
```

Missing on Nuxel: all eight.  `lhd` is also a daemon (not a one-shot patch loader):
it binds a TCP port (`PortName=tcp:127.0.0.1:300`), speaks RPC, expects the Android
sensor HAL, and needs the Bionic loader.  Running it would mean shipping a
complete Android userspace, which the handoff forbids as a first-line approach.

## Kernel-side runtime actually used

| Component | Location | State |
|---|---|---|
| SSP/BBD driver | `drivers/sensorhub/brcm` (+ `bbdpl/`) | built in, bring-up patched |
| Hub patch image | `bbdpl/r_os/bbd_patch_file_beyond.h` (R tree) | embedded, served on `/dev/bbd_patch` |
| Native peer | `services/nuxel-orientation/nuxel_ssp_bridge.py` | deployed, relays real frames |
| Orientation owner | `services/nuxel-orientation/nuxel-orientationd` | live; Auto truthfully blocked |

## What is still missing for a live sensor

The patch-download RPC (`IrpcPatch`/download-start sequence in `lhd`) is not present
in the kernel (`bbd_rpc_lh.c` implements RX only) and not reproducible from the
GPL sources.  Without it the hub never leaves "SSI idle-high" state, so
`raw_data` cannot become non-zero.  This is recorded as **FAIL**, not worked around.
