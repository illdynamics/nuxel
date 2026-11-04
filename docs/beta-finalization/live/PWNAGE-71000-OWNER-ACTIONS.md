# PWNAGE-71000 — owner actions: flash, verify, first decode, rollback

**Status:** prepared, not executed. The phone is still on the old kernel and has no MFC firmware; `/dev/video6` has never been opened by this work.

## Artifacts

- New boot image (host): `/x/nuxel/evidence/pwnage-61000/71000/pwnage71000-boot.img`
  - size 48,596,992
  - SHA-256 `0a888ae709582e5072f9ae979e9d9f6468c72adf7d8850fbb0aad43991f6535a`
- Phone copy: `/root/pwnage71000/pwnage71000-boot.img` (same hash)
- Original BOOT backup (host): `/x/nuxel/evidence/pwnage-61000/71000/live-boot-before.img`
  - size 57,671,680
  - SHA-256 `2cbc5085d871d043baea6e64aec6c94df60adae18b86fa8696ad942f46b748fc`
- Phone backup: `/root/pwnage71000/live-boot-before.img` (same hash)
- Firmware: `/x/nuxel/firmware/s10plus/blobs/vendor-firmware/mfc_fw.bin` — 685,832 bytes, SHA-256 `f3802d34524f5919c16505c03b4cbfe184963f98787feed6232b643bda68b55f`
- Userspace: `/x/nuxel/evidence/pwnage-61000/71000/nuxel-mfc-userspace.tar.gz` — SHA-256 `409916dc572407b80aca282d0378b04a889c3293190dad5214e9dbb70c0593f0`

## 1. Recovery prerequisites (do first)

- Charge above 50%.
- Confirm the existing TWRP (Vol Up + Bixby + Power) or Download Mode path works.
- Keep a second SSH session open and a USB data cable available.
- Copy the original BOOT backup to the host/TWRP-accessible storage and verify its hash before writing anything.
- Do not touch EFS, modem, recovery, dtbo, param, persistent, keystorage, carrier, misc or any other partition.

## 2. Flash BOOT (TWRP recommended)

```sh
adb devices
adb push /x/nuxel/evidence/pwnage-61000/71000/pwnage71000-boot.img /tmp/
adb shell 'sha256sum /tmp/pwnage71000-boot.img'
# expect 0a888ae709582e5072f9ae979e9d9f6468c72adf7d8850fbb0aad43991f6535a
adb shell 'dd if=/tmp/pwnage71000-boot.img of=/dev/block/by-name/boot bs=1M conv=fsync; sync'
adb shell 'sha256sum /dev/block/by-name/boot'
# must match 0a888ae7...
adb reboot
```

Do not interrupt the write. If the readback hash does not match, immediately restore the backup in section 6.

Alternative: Download Mode + heimdall, flash **only BOOT**, read back and compare.  
Live Wi-Fi SSH `dd` to `/dev/sda14` is technically possible but only with explicit owner risk acceptance and a proven recovery path; it is not the recommended path.

## 3. Verify the patched kernel and fail-closed missing-firmware state

After the phone returns to SSH:

```sh
uname -a
uname -v   # expect #9 SMP PREEMPT Tue Nov 3 01:36:01 CET 2026
cat /proc/sys/kernel/random/boot_id
systemctl is-active nuxel-wayland nuxel-wl-fb nuxel-bridge
test ! -e /lib/firmware/mfc_fw.bin && echo FIRMWARE_ABSENT_EXPECTED
dmesg -T | grep -i -E 'mfc|firmware' | tail -40
```

Do **not** open `/dev/video6` yet. Confirm the diagnostic reports the read-only inventory/status and `safe_open_allowed=false`:

```sh
/usr/lib/nuxel/nuxel-mfc-diag --inventory --json || true
/usr/lib/nuxel/nuxel-mfc-diag --status --json || true
```

If the phone does not return after a bounded wait, restore the backup in section 6 via TWRP/Download Mode. Do not blind-reboot repeatedly.

## 4. Install firmware and userspace (only after the patched kernel is running)

```sh
scp /x/nuxel/firmware/s10plus/blobs/vendor-firmware/mfc_fw.bin root@10.20.30.16:/lib/firmware/mfc_fw.bin
ssh root@10.20.30.16 'sha256sum /lib/firmware/mfc_fw.bin; stat -c %s /lib/firmware/mfc_fw.bin; od -An -tx4 -N4 /lib/firmware/mfc_fw.bin'
# expect f3802d34..., 685832, ea000077
scp /x/nuxel/evidence/pwnage-61000/71000/nuxel-mfc-userspace.tar.gz root@10.20.30.16:/tmp/
ssh root@10.20.30.16 'tar -xzf /tmp/nuxel-mfc-userspace.tar.gz -C / && chmod 0755 /usr/lib/nuxel/nuxel-mfc-diag /usr/lib/nuxel/nuxel-mfc-play /usr/lib/nuxel/nuxel-mfc-safety-receipt.py /usr/lib/nuxel/nuxel-mfc-image-verify.sh /usr/lib/nuxel/nuxel-mfc-decode && chmod 0644 /usr/share/nuxel/mfc-status.schema.json'
ssh root@10.20.30.16 '/usr/lib/nuxel/nuxel-mfc-diag --inventory --json; /usr/lib/nuxel/nuxel-mfc-diag --status --json'
```

## 5. Safety receipt, first open, decode

Only with explicit owner approval at the time of the action:

```sh
ssh root@10.20.30.16 '/usr/lib/nuxel/nuxel-mfc-safety-receipt.py   --out /etc/nuxel/mfc/safety-receipt.json   --decoder-node /dev/video6   --firmware /lib/firmware/mfc_fw.bin   --owner-approve --approved-by "<owner>"   --kernel-patch-applied --firmware-installed   --missing-firmware-test PASS'
ssh root@10.20.30.16 'dmesg -T > /tmp/mfc-before.log'
ssh root@10.20.30.16 '/usr/lib/nuxel/nuxel-mfc-diag --device /dev/video6   --allow-hardware-open --receipt /etc/nuxel/mfc/safety-receipt.json   --query-only --json 2>&1 | tee /tmp/mfc-query-1.json'
ssh root@10.20.30.16 'dmesg -T > /tmp/mfc-after.log'
```

If the first open does not return promptly, **stop**. Do not launch a second opener; do not assume `timeout`/`kill -9` releases an uninterruptible `D` task. Keep the guard active.

Only after a prompt first open, repeat 5/20/100 open-query-close cycles and run a real 720p30 H.264 decode with objective frame count, dimensions, checksum and software comparison. A successful compile or firmware hash is not decode proof.

## 6. Rollback

Restore the original BOOT image via TWRP/Download Mode:

```sh
adb push /x/nuxel/evidence/pwnage-61000/71000/live-boot-before.img /tmp/
adb shell 'sha256sum /tmp/live-boot-before.img'
# expect 2cbc5085d871d043baea6e64aec6c94df60adae18b86fa8696ad942f46b748fc
adb shell 'dd if=/tmp/live-boot-before.img of=/dev/block/by-name/boot bs=1M conv=fsync; sync'
adb shell 'sha256sum /dev/block/by-name/boot'
# must match 2cbc5085...
adb reboot
```

Firmware rollback (only the MFC blob):

```sh
ssh root@10.20.30.16 'rm -f /lib/firmware/mfc_fw.bin'
```

Userspace rollback:

```sh
ssh root@10.20.30.16 '/usr/lib/nuxel/rollback-pwnage61000.sh --rootfs / --receipt --firmware --userspace --restore-guard'
```

Keep the guard and software-only playback unless a full decode proof and owner review justify a narrow, reversible transition.

## 7. Hard safety rules

- Write only BOOT. Never write EFS/modem/recovery/dtbo/param/persistent/keystorage/carrier/misc or any other partition.
- Do not install the firmware before the patched kernel is running.
- Do not open any `/dev/video*` node before the safety receipt exists and the exact allow-list identity is confirmed.
- Never scan/probe every video node; never auto-retry a hung open.
- No `reboot -f`, SysRq, forced power-cycle or bootloader changes.
- Do not claim physical MFC success without real decoded frames and an objective software comparison.
