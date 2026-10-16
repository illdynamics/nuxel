# configs/libinput/ — libinput configuration for the S10+

| File | Installed to | Device |
|---|---|---|
| `nuxel-s10plus-touch.conf` | `/etc/libinput/local-overrides/99-nuxel-s10plus-touch.conf` | Galaxy S10+ SM-G975F (beyond2lte) |

**This directory used to be a symlink** to `configs/google-pixel-10-pro-xl/libinput/`.
That would have installed a Google Pixel ("mustang") touch InputClass on the S10+.
Hardware configuration that does not match the device must not be applied to it, so
the symlink was replaced by this real directory. The Pixel configuration is
untouched and still lives at
`configs/google-pixel-10-pro-xl/libinput/nuxel-mustang-touch.conf`.

Rules for anything added here:

* match the device by **name + capability** (`MatchName=sec_touchscreen`,
  `MatchIsTouchscreen=yes`) — never by a node number;
* ship **no invented calibration values**; an unset transform is better than a
  guessed one, and the identity is only written down because the panel and the
  framebuffer share orientation (measured);
* keep the X11 form (`configs/s10plus/libinput/99-nuxel-beyond2lte-touch.conf`)
  separate — it is only for an X session, which this device does not run.

See `docs/beta-finalization/touch/PIPELINE-TRACE.md` (layer 3/4) for how the node
is selected and how a wrong selection would be detected.
