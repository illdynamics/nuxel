# PWNAGE-49000 evidence

| File | Meaning |
|---|---|
| `offline-tests.log` | Source/headless test run for chrome, navigation, lock reconciliation, Authenticator and regressions. |
| `browser-layout.txt` | Computed CSS + sampled pixels proving the proper DOM bar paints above the lockscreen and that Home has one bar. |
| `lockscreen-dom-topbar.png` | 360x760 headless capture; boot splash/preload cover hidden, lockscreen active. |
| `home-single-topbar.png` | 360x760 headless capture; Home desktop, one DOM bar. |
| `sha256-changed-files.txt` | Hashes of every source file changed by this pass. |
| `authenticator-qr-decode.txt` | Bundled jsQR decoded a generated test otpauth URI in headless Chrome. |
| `physical-access.txt` | Why no physical/device evidence could be collected. |

These are **not** physical S10+ proof. The handset was unreachable; NFC,
fingerprint, MTP enumeration, haptic feel and real app-launch tests remain
`PHYSICAL_BLOCKED` until run on the device.
