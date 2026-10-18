# Known limitations

- The full physical navigation and keyboard sequence still needs owner proof.
- This session could not open the enumerated CDC-ACM device due to host sandboxing.
- The S10+ uses Samsung Linux 4.14.253 and DECON framebuffer, not DRM/KMS.
- Modem, GNSS, camera, NFC, Bluetooth and unrelated hardware retain their
  existing documented verdicts; v0.5.2 does not claim to complete them.
- No image was flashed in this work.
- Commit/tag/push/release are pending because this session cannot write `.git`
  and its GitHub CLI token is invalid.
