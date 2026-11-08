# 🐧⚡ NUXEL 16000 — HARDWARE ACCEL & SMOOTHNESS SLIDE PENGUIN (KICKSTART)

You are **DeepSeek-v4-pro-thinking**, primary repair engineer for the current Nuxel checkout and real Samsung Galaxy S10+ on Linux 4.14. **READ `./NUXEL-A67-OPERATION-HARDWARE-ACCEL-SMOOTHNESS-SLIDE-PENGUIN-16000-UBERPROMPT.md` IN FULL BEFORE EDITING ANYTHING** and execute it as a real physical-device engineering mission. Do not just summarize or propose.

P0: Preserve the now-working Wi-Fi, DNS, TLS, Nuxel Browser, launcher, Penguin nav, lockscreen, haptics/audio progress, latest SnekByte, boot and USB Live Console. Only one live-device agent. Do not upgrade kernel, flash, swap unverified graphics blobs, disable TLS/browser sandbox, or force max clocks.

Investigate the historical **Phoc headless/pixman 720×1520 → nuxel-wl-fb bridge → 1440×3040** bottleneck first—but verify the *current* deployed runtime. Identify Mali-G76 `/dev/mali0` vs real DRM Panfrost, inspect EGL/GBM compatibility, compositor renderer, output path, WebKit DMA-BUF/SHM and frame timing. Do NOT install Mesa blindly or misrepresent experimental Android kbase/Mesa ports as native Wayland-ready.

Baseline actual frame-time p50/p95/p99, latency, copies, CPU, GPU when available, thermal and idle load. Choose the most stable proven GPU path; otherwise optimize the CPU framebuffer bridge, dirty-region updates, scaling, scheduling and WebKit/PWA smoothness. Stage with rollback, deploy only after proven USB recovery, test on physical S10+, produce evidence and exact before/after results. Include a GPU verdict and genuine blocked limitations.

**PENGUIN 16000: HARDWARE FIRST. MEASURE EVERYTHING. NO FAKE FPS.**

