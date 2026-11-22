# PROMPT 05 — FIRST REAL REAR SAK2L4 PHYSICAL FRAME (BOUNDED HARDWARE TEST)

**Entry:** 04 successfully booted Nuxel with camera driver and correct selected DT; required raw V4L2 nodes exist; system baseline healthy. **Do not use the old private vendor FIMC-IS2 STREAMON tools.**

1. Discover *native* V4L2/Media Controller graph with actual CSIS, sensor and video node identities, and prove exclusive driver ownership. Record `media-ctl -p`, `v4l2-ctl --all --list-formats-ext` where supported, sensor I2C identity, regulator/clock/PM state, DMA buffer allocation capabilities and relevant dmesg.
2. Select rear main 2L4 only. Configure a real supported low-risk sensor mode (source report identified **2016x1512@30** nominal; verify native driver supports it), RAW10 Bayer/CSI media bus formats and valid lane geometry. Start with **bounded 1–3 frames** and a strict timeout. Never improvise simultaneous test-pattern and physical-source paths; fail closed on missing media entities.
3. Allocate/queue V4L2 buffer(s), turn the native pipeline on in correct order, then **dequeue completed buffers**. Record `sequence`, timestamp, `bytesused`, pixel format/packing/stride, buffer lengths and DMA completion. On timeout, IRQ storm, DMA fault or warning, perform safe stream-off/power cleanup and stop this test; collect logs. Do not repeat crash loops autonomously.
4. Capture at least two **physically distinct real scenes**, e.g. darkened lens vs illuminated different background, with two different completed frames, validating sane statistics/content and visible scene differences. Save raw file(s) with correct metadata. Check integrity and prove no synthetic/cached/stale buffers. A queued buffer or JPEG created from static data is FAIL.
5. Check subsequent open/close cycles and return to normal low-power state. Verify Nuxel still healthy and active DT unchanged. If new kernel/DT fix truly required, **go back through PROMPT 02–04** and fresh validation; do not live-patch or flash from here.
6. Once genuinely captured, set `FIRST_FRAME_VERIFIED=PASS` and attach output SHA-256, logs, capture program command, raw frame metadata and a read-only preview conversion. Only then begin color-processing/ISP integration.

**Deliver:** `reports/camera-05-first-physical-frame.md`, raw captures (private if appropriate), metadata and kernel traces. **EXIT GATE:** real DQBUF with changing pixels and healthy Nuxel. Else report exact hardware blocking stage, not an optimistic completion percentage.

---
