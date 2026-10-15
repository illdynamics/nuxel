# A26 evidence

| File | What it is |
|---|---|
| `nuxel-home-1440x3040-preview.png` | 4x-averaged preview of `ui-small.ppm`, captured on 2026-10-15 through the **running** UI's own FIFO (`echo "screenshot /var/lib/nuxel/ui-small.ppm" > /run/nuxel-ui.cmd`) and pulled to the Mac with `nuxel-live.sh --pull`. Source was P6 720x1520 (half of the 1440x3040 panel), remote and local SHA-256 both `7a83b03c4d34546572ca3c690f3ce2acee2a898a6dc41e1c5c1756ff0fc19eed`. |

A framebuffer capture is not proof of what the glass shows; it is proof that the
application committed those pixels (`PAN_RC=0`, `decon-0 UNBLANK`).
