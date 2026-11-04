# Final matched A/B — S10+ (PWNAGE-60000)

Date: 2026-11-03 (Europe/Amsterdam), live phone `root@10.20.30.16`.

Method:
- Same kernel, image, brightness, Wi-Fi and thermal start window.
- 3 x 60 s per case; `bench-pwnage60000.py` samples `/proc/<pid>/stat` once
  per second and normalizes CPU ticks to one core.
- Cases:
  - `idle`: normal Home, screen kept on via the documented
    `/run/nuxel-wl-fb.cmd` `screen-on` control (identical for both profiles).
  - `settings-scroll`: a second `nuxel-pwa-host` loads
    `/pwa/nuxel-apps/settings/index.html` under the *same* verified profile;
    `nuxel-scroll-workload` sends bounded wheel events through
    `zwlr_virtual_pointer_manager_v1` (50 events/s, alternating direction).
- `software-safe` sets the compositor fallback marker (pixman) and the WebKit
  software environment.  `gpu-rendered-shm-presented` removes the marker,
  restarts the session, and the measured WebKit process is asserted to have
  `NUXEL_GRAPHICS_PROFILE_ACTIVE=gpu-rendered-shm-presented`,
  `WEBKIT_DISABLE_COMPOSITING_MODE=0`, `libgallium_dri.so` mapped and
  `/dev/mali0` open.
- The final raw JSON is under `final-bench/`; `SUMMARY.json` has medians and
  per-run CPU.  No FPS or frame-time claim is made: the bridge reports only
  per-phase capture/compare/blit/pan averages.

Results (median, % of one core):

| Case | software-safe | GPU-SHM | Delta |
|---|---:|---:|---:|
| idle Home | 11.05 | 5.10 | -53.8% (GPU lower) |
| Settings scroll | 22.80 | 23.83 | +4.5% (GPU slightly higher) |

Interpretation:
- At idle the GPU path is clearly cheaper.  Phoc drops from a median 3.41
  to 1.16 and WebKit from 3.01 to 1.65.
- Under Settings scroll the totals are close and the GPU path is 4.5% higher:
  Phoc falls from 8.35 to 3.29, but WebKitWebProcess rises from ~4.0 to ~13.8
  because GPU compositing keeps a real accelerated compositor busy.  This is
  not a CPU win for that specific workload; it is reported as PARTIAL.
- Frame production: idle software 186–306 captures/60 s vs GPU 94–132;
  Settings scroll software 344–383 vs GPU 257–303.  The GPU path captures
  fewer frames for the same input, consistent with damage-driven compositor
  updates in this trace.  No p50/p95 frame-time claim is made.

Renderers/transport observed in the GPU runs: `Mali-G76 MC12 (Panfrost)`,
WebKit transport `shm`; the final panel remains the CPU framebuffer bridge.
