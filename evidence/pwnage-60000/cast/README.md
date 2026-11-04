# Wireless casting — PWNAGE-60000

Read-only diagnostic result on the live S10+:

```
p2p: iw-p2p
wpa_p2p: (empty)
capture: grim,pipewire
encoders: openh264enc,av1enc,vp8enc,vp9enc
gnome_network_displays: absent
wifi interfaces include wlan0, wlan1, p2p0
verdict: MIRACAST_CANDIDATE
moving_picture_verified: false
```

Interpretation:

- The Wi-Fi driver exposes a P2P device and a `p2p0` interface.  This is a
  capability, not a Miracast session.
- H.264 (`openh264enc`) and other software encoders exist.
- `grim` and PipeWire are installed, but no real capture→encode→RTP→receiver
  pipeline has been implemented or proven on Phoc.
- There is no `gnome-network-displays` drop-in and no receiver test.
- Therefore no Cast UI control is exposed.  Miracast remains `CANDIDATE`;
  LAN/WebRTC screen share is `CANDIDATE`/not implemented.
- Lockscreen redaction, explicit start/stop, authentication and privacy gates
  are not implemented because the transport does not exist yet.

The owner test is `docs/A49/OWNER-TEST-CAST.md`; it requires a real receiver and
must be performed by the owner.  Do not label this as Chromecast or Miracast
until moving pixels are proven end-to-end.
