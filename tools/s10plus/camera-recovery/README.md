# Host-only stock camera preparation

Run `python3 prepare.py --source OWNER_EXTRACTED_DIRECTORY --destination NEW_HOST_DIRECTORY`.
The nine pinned inputs are eight camera binaries and stock `build.prop`, all
independently reproduced from the owner-held DTK9 AP. Output includes a
transaction proposal, **blocked** until the executable DDK ABI is resolved.
It does not install anything or establish physical camera success.

`firmware/s10plus/camera-stock-DTK9.json` records this separate stock provenance;
`firmware/s10plus/manifest.yml` remains the unchanged Linux4 public reference.
Never combine revisions. Proprietary binaries stay outside Git.

Public reference verification:

```
NUXEL_DEVICE=s10plus bash firmware/s10plus/verify-firmware.sh --camera-root HOST_DIRECTORY
```

That command requires all eight files to match the public pin, including
optional entries, and rejects missing/duplicate paths. It deliberately rejects
the stock DTK9 set. Use `prepare.py` for stock verification. Neither command is
an ABI test. See `reports/CAMERA-RECOVERY-2026-11-17.md` for remaining gates.
