# SSP Golden-Frame Corpus (offline)

`build_golden_frames.py` generates byte-exact SSI/TL/RPC wire frames (normal
and faulty) derived from the vendor kernel decoder `bbd_rpc_lh.c` and
`bcm_gps_regs.c`, hashing each with SHA-256, and optionally replays them through
the existing native decoder `nuxel_bbd_download --replay-stdin`.

These are **OFFLINE** synthetic frames. Nothing here is a hardware capture and
no frame proves firmware acceptance. A later on-device capture can be compared
to a frame's SHA-256 byte-for-byte without trusting this tool's interpretation.

Run:

    python3 build_golden_frames.py --out out \
        --decoder ../ssp-native/build/nuxel_bbd_download

Outputs: `out/<name>.bin` + `out/manifest.json` (+ `out/replay.json` with
`--decoder`).

Key non-obvious results (also recorded in replay.json):
- `faulty_missing_detail_bit` / `faulty_stale_ack` decode as *valid packets*
  at the framing layer (rc=0) — this is exactly correct: an ACK/NACK flag that
  is structurally parseable is a *transport* event, not an RPC completion.
- `faulty_surplus_payload`, `faulty_truncated_rpc`, `faulty_wrong_crc`,
  `faulty_unfinished_frame` are rejected (rc=2).
- `idle_0xff_not_protocol` yields 0 packets: SPI `0xFF` idle is never a reply.
