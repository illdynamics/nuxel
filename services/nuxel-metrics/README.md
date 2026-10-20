# Nuxel Home system monitor

`nuxel-metricsd` is a socket-activated, loopback-only (`127.0.0.1:8624`) C
endpoint. It takes no periodic samples: each `GET /metrics` reads the kernel
files once and it exits after 30 seconds without a request.

It exposes CPU usage from successive aggregate `/proc/stat` deltas (including
`iowait` in idle). A cold, socket-activated instance takes one short in-request
delta, so the first Home poll is already a real percentage. Memory uses
`MemTotal` and `MemAvailable`. GPU use comes from the Mali
`/sys/devices/platform/18500000.mali/utilization` node with
`/sys/kernel/gpu/gpu_busy` as a fallback. VRAM (`gpu_memory_kib`) is the sum of
the Mali per-process allocation table in `/sys/kernel/gpu/gpu_memory`; because
the S10+ GPU shares system RAM, `gpu_memory_total_kib` is `MemTotal`. If a source
is absent or malformed, its JSON value is `null` and the corresponding status is
`unavailable`.

Run `nuxel-metricsd --json` for a one-shot diagnostic snapshot (it takes the
same short CPU delta as the first request). Home cache-busts every sample and
the endpoint accepts `GET /metrics?t=...` plus its CORS `OPTIONS` preflight. The
endpoint has no network listener beyond loopback. The browser poller runs only
while Home is foregrounded and the monitor preference is enabled.
