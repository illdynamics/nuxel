# Nuxel Galaxy S10+ camera recovery — V2 host kit

**What this kit can and cannot do:** It contains a recovered-firmware hash audit, a read-only host audit program, an opt-in/hash-pinned reference downloader, original offline tests and a detailed continuation prompt. It does **not** contain proprietary Samsung binary firmware, nor a completed camera driver, nor a live-handset fix. It never writes to the phone.

## Recommended install

Extract this folder directly under your actual, up-to-date working repository (`~/x/nuxel/NUXEL_CAMERA_RECOVERY_V2/`). **Do not overwrite** or replace the project with the partially readable uploaded `nuxel-feat-cam.zip`. Your current checkout and the camera worktree (`/tmp/nuxel-camera-endgame-audit`, if it still exists) are the authoritative source.

Run:

```sh
cd ~/x/nuxel
python3 -S -m unittest discover -s NUXEL_CAMERA_RECOVERY_V2 -p 'test_camera_recovery.py' -v

python3 -S NUXEL_CAMERA_RECOVERY_V2/camera_firmware_audit.py \
    --manifest firmware/s10plus/manifest.yml \
    --root firmware/s10plus/blobs/device-vendor-firmware \
    --report /tmp/nuxel-camera-blob-compare.json
```

After the agent identifies the **matching original stock Android `vendor` directory** from the user's already downloaded `G975FXXS9DTK9` AP package, add another `--root /ABSOLUTE/PATH/TO/EXTRACTED/vendor` to compare all candidates. A candidate is **NOT approved for deployment** merely because it matches a manifest.

The downloader makes zero network requests unless `--download` is specified:

```sh
python3 -S NUXEL_CAMERA_RECOVERY_V2/fetch_pinned_camera_reference.py \
    --manifest firmware/s10plus/manifest.yml \
    --dest "$HOME/.local/share/nuxel-camera-reference"
```

Once you have inspected the output and source, adding `--download` downloads only the eight camera blobs from a pinned public Linux4 revision into that **host-only** directory, validating SHA-256 before placing each file. If hashes differ, files are refused. The tool's network fetching has not been tested against live GitHub; it was tested with simulated responses.

For agent continuation, give the full document:
`NUXEL_CAMERA_RECOVERY_V2/02_AGENT_CAMERA_CONTINUE_UNTIL_VERIFIED.md`

## Where the required firmware most likely already exists

Previous SSP work extracted a matching owner-held Samsung AP build:
`AP_G975FXXS9DTK9_CL20034833_QB35905779_REV01_user_low_ship_meta_OS10.tar.md5`

Inspect the owner-held stock package and previous temporary images under local `~/x/nuxel` and owner-only directories. The exact paths may have changed. **Use this stock firmware first; do not download another generic firmware archive before checking.**

Public references, each a **comparison source only**:
- https://github.com/Linux4/proprietary_vendor_samsung
- https://github.com/Evolution-X-Devices/vendor_samsung_beyond2lte/blob/bka/beyond2lte-vendor.mk
- https://libcamera.org/faq.html
- https://docs.libcamera.org/master/guides/pipeline-handler.html

## Audit scope caveat

The uploaded ZIP lacks a central directory. The archived camera firmware and manifest were read from independently CRC-checked local ZIP members, but **not every source file in the archive** could be verified. The two latest camera-worktree commits and the live `CAMERA-FIRST-REAL-FRAME.md` report were provided by the user's pasted tool output, rather than validated directly from this incomplete ZIP.

## Package contents

- `01_DEEP_CAMERA_AUDIT.md`: firmware SHA comparison and bounded camera status
- `ARCHIVE_CAMERA_SHA256_AUDIT.json`: machine-readable independently computed hashes
- `camera_firmware_audit.py`: inspect local candidate roots; flag missing/mismatched/duplicate firmware
- `fetch_pinned_camera_reference.py`: optional host-only, SHA-pinned reference download
- `test_camera_recovery.py`: 10 offline behavioral tests
- `02_AGENT_CAMERA_CONTINUE_UNTIL_VERIFIED.md`: engineering agent mission

Do not install all 8 blobs blindly. Identify the loader's **actual requested file and failure condition** first. No device writes or camera initialization were done during this kit's creation.
