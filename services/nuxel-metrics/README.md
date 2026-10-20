# Nuxel Home system monitor

`nuxel-metricsd` is a socket-activated, loopback-only (`127.0.0.1:8624`) C
endpoint. It takes no periodic samples: each `GET /metrics` reads the kernel
files once and it exits after 30 seconds without a request.

It exposes CPU usage from successive aggregate `/proc/stat` deltas (including
`iowait` in idle), memory use from `MemTotal` and `MemAvailable`, and GPU use
only when the live Mali driver exposes
`/sys/devices/platform/18500000.mali/utilization`. If that interface is absent
or malformed, `gpu_percent` is `null` and `gpu_status` is `unavailable`.

This endpoint has no network listener beyond loopback and accepts only
`GET /metrics`. The browser poller runs only while Home is foregrounded and the
monitor preference is enabled.
