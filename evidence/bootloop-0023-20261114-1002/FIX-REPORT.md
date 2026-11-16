# S10+ bootloop after "0023 fix" flash — root cause & resolution (2026-11-14)

## Symptom
After flashing `work/bootloop-fix/boot-fixed-0023.img` and rebooting, the phone
returned to TWRP. The bootloader ring showed repeated `Starting kernel...`
lines with NO `Linux version 4.14.253 ...` line ever following them — the
kernel never executed a single instruction.

## Root cause
The 0023 kernel was packed with a **gzipped** kernel payload
(`1f8b0800...`, 16,404,690 bytes, inner ARM64 Image 45,848,584 bytes).

Every boot image that has ever booted on this device — `boot-current.img` (#95),
`boot-k65-verified`, `boot-pre-*`, `boot-nfc-custom-fw-*` — stores the kernel as
a **raw ARM64 `Image`** (magic `00..6c14`, ~45.7 MB). The S10+ S-Boot chainload
path does not decompress a gzip kernel in the boot image, so the label was
rejected instantly and S-Boot reset the SoC. That is the "returned to TWRP"
behaviour: not an NFC panic, not a userspace crash.

(The 0023 NFC crash fix itself is present and correct: `sha1-generic` and
"NFC bring-up disabled" strings are in the image. It never got to run.)

## Resolution
Repacked with the **raw** Image:
- donor: `work/bootloop-fix/boot-current.img` (same cmdline/addrs, `dt_size=1`)
- kernel: `work/bootloop-fix/fix2/Image-raw` (uncompressed from the gzip)
- **no appended DTB** — the donor has `dt_size=1`; appending the 9.5 MB DTB
  produced a 57.8 MB image that exceeds the 57,671,680-byte boot partition and
  got truncated (dd wrote 55/56 MB — must not repeat).

Output: `work/bootloop-fix/boot-fixed-0023-raw2.img` (48,277,505 bytes,
kernel magic `00c06c14`, ramdisk byte-identical, cmdline identical).

Flashed to `/dev/block/by-name/boot` (sda14), readback verified byte-identical.
Boot succeeded on the first attempt (~35 s), kernel `#3` 4.14.253.

## Verification
- SSH root@192.168.178.167 via `~wicked/.ssh/wicked_wqn_id_rsa`: OK
- WiFi wlan0 192.168.178.167/24: OK
- `systemctl --failed`: none; nuxel-bridge/wayland/NetworkManager active
- Full reboot re-tested: booted again, same results.

## PIN 3838
`3838` is accepted by the deployed `_trivial_pin` (only the in-repo Nov 13 copy
rejected repeats). The device was in `pattern` (9 dots) mode with a *different*
main verifier, and `3838` existed only as the **fingerprint fallback**, so the
keypad never offered a PIN and `set_pin` failed with
`current_credential_required`.

Fixed by writing a fresh authoritative PIN credential as root (scrypt
n=2^14,r=8,p=1, dklen=32, 16-byte salts), backing up the old doc to
`lock.json.bak-pin3838-*`, mode=`pin`, secret_kind=`pin`, fallback kept = 3838.
Bridge restarted. RPC verified:
  status -> mode: pin
  unlock {"secret":"3838"} -> success:true, via:"pin"
  unlock {"secret":"1234"} -> rejected
Persistent across reboot.
