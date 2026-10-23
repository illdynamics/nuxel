# 🐧 NUXEL A64 — Penguin Launcher Resurrection

Surgical UI/launcher regression repair for the Galaxy S10+ (SM-G975F) after the
A63 12KMAXIMUM partial deploy.

**Precise root cause:** the deployed launcher stylesheet
`/usr/share/nuxel/nuxel-home/css/launcher.css` was a **0-byte empty file**
(SHA-256 `e3b0c442…`) while the served `index.html` still linked it. With no
grid/dock/icon sizing rules the Home screen collapsed to a one-column wall of
full-size icons, the system-monitor rendered as raw GPU/VRAM/MEM text, and the
bottom dock painted as an oversized dark circle. The A63 runtime deploy
(`a63-launcher-runtime-apply`) had already replaced `index.html`, `manifest.json`
and `sw.js` but failed at `launcher.css` and aborted, leaving a mixed bundle.

**Fix (minimal):** restored the known-good `launcher.css` bytes
(`9d56a005…`, 12764 bytes) on-device and hot-reloaded the WebKit launcher via the
host control FIFO. No kernel/partition flashing, no reboot, no service removal.

Evidence: `evidence/after-home-fixed.png` (on-device framebuffer capture) and the
state receipts quoted in `01`–`04` below.
