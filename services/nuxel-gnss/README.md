# Experimental native BBD/GNSS helpers (S10+ BCM47752)

The transport module implements source-backed TL framing, CRC and RPC parsing.
It does not establish firmware-operation acknowledgements or initialize the hub.
The matched Samsung `lhd` and runtime have been recovered for isolated analysis.

`nuxel_lhd.py --session` now refuses with `INITIALIZATION_PROTOCOL_UNVERIFIED`
before acquiring power, opening devices or writing controls. The old session
incorrectly sent `ESW:READY` after only reading the patch; that path is removed.
The CLI exits 2, which the existing optional systemd unit accepts without a
restart loop. These repository changes have not been deployed to the handset.

Components:

- `src/nuxel_bbd_tl.py`: framing, strict decoding and separate ACK/NACK metadata.
- `src/nuxel_control.py`: kernel control constants and patch-file parser.
- `src/nuxel_lhd.py`: gated session entry point and experimental low-level helpers.
- `tests/`: offline parser, kernel sample, protocol gate and socketpair tests.

Firmware-file identity is not proof of a loaded or running application. The
older BCM4773-labelled inventory and historical GPS reports do not establish
the BCM47752 initialization contract. Physical GNSS fixes, motion samples and
hardware rotation remain unverified by this module.

See [current protocol review](../../reports/SSP-PROTOCOL-CONTRACT-2026-11-17.md)
and [offline framework](../../tools/s10plus/ssp-runtime/README.md).
