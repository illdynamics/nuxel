# USB-C / DisplayPort Alt Mode and HDMI — PWNAGE-60000

Read-only diagnostic result on the live S10+:

```
verdict: TYPEC_ENUMERATED_NO_DP
typec_ports: /sys/class/typec/port0
dp_altmodes: []
drm_connectors: []
drm_connected: []
modules: []
visible_output_verified: false
```

Interpretation:

- A generic Type-C port exists and reports dual role.
- No DisplayPort alt-mode directory is exposed.
- No DRM connector exists (`/sys/class/drm` has only `version`; `/dev/dri` is
  absent).  This is the same ABI boundary that blocks WebKit DMA-BUF.
- This does **not** prove the silicon cannot do DP Alt Mode.  It proves the
  current Nuxel kernel/DT does not expose a usable DP/HDMI output path.
- No mux, PMIC, PHY, regulator or Type-C role was written.

Safe next step is an owner-supervised adapter test with an alternate recovery
path (Wi-Fi SSH is currently available) and pre-captured `dmesg -w` logs.  The
acceptance stages are in `docs/A49/OWNER-TEST-EXTERNAL-DISPLAY.md`.  HDMI is
`NEEDS OWNER TEST` / `NOT YET SUPPORTED`, not a working feature.
