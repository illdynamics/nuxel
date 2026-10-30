# P5 nav icons + P8 lockscreen USB connection-mode

## P5 Bottom navigation icons
- Source of truth: tools/s10plus/a45/gen-navdock-art.py + nuxel-navdock.c.
- Art pipeline already correct: PIL LANCZOS contain at 48px, premultiplied
  ARGB8888, centered on transparent canvas; navdock blits with nearest-neighbor
  integer scaling at buffer scale (crisp pixel art, no clipping/distortion).
- Assets present on device at /usr/share/nuxel/assets/button-{left,middle,right}.png
  and /usr/share/nuxel/nuxel-home/assets/branding/ (byte-identical to repo).
- Screenshot captured (720x1520) for owner review:
  docs/beta-finalization/live/evidence/pwnage-39000/screen-20261030T1306.png
- No visual claim made beyond source/assets; a human screenshot review is the
  honest confirmation step.

## P8 Lockscreen USB connection-mode
- Deployed missing assets to /usr/share/nuxel/assets/ (HTTP 200 verified):
  nuxel-connection-mode.png (1809724 bytes)
  nuxel-file-transfer.png (911221 bytes)
- Deployed missing safe helper /usr/lib/nuxel/nuxel-usb-mode.sh (repo:
  services/nuxel-s10/bin/nuxel-usb-mode.sh). Backend usb_mode.py already
  reports helper truth and never claims activation without it.
- Normal Charging verified: helper rc=0, state mode=charging active=false.
- File Transfer: helper honestly returns unsupported (no MTP responder
  umtprd/mtp-server/jmtpfs present; kernel configfs has no MTP function), so
  the UI must show failure rather than a fake file-transfer icon.
  => BLOCKED for genuine file transfer on this 4.14.253 image; NO raw USB
     mass storage was used (safety rule honoured).
