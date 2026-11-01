# PWNAGE-51000 — kernel flash approval manifest

**Device:** Samsung Galaxy S10+ SM-G975F, `beyond2lte` (verified from TWRP props)
**Transport:** TWRP ADB, serial `R58M75KDB2X`
**Target partition:** `/dev/block/by-name/boot` -> `/dev/block/sda14` (verified symlink)
**Partition size:** 57,671,680 bytes
**Image:** `docs/beta-finalization/live/evidence/pwnage-51000/kernel/boot14.userns.padded.img`
**Image SHA-256:** `574c239c910152fcf8321a132df9c567c8ce63da787fb2f7f0a8300a10b2fa59`
**Kernel release:** `4.14.253-gf7194c1d15ed-dirty`
**Config delta:** `CONFIG_USER_NS=y` only (proved by extracting IKCONFIG from the final Image)
**Expected boot:** ≤ 3 minutes to Nuxel lockscreen/Home; Wi-Fi SSH `root@192.168.178.167`

## Pre-flash state

- Live boot SHA-256: `97f78f5da871ef5df55113814096c9fb0c1de2671b04e11c7edd77630a6bc7da`
- Off-device rollback: `twrp/sda14.current.img`, SHA `97f78f5d…`
- On-device rollback: `/root/pwnage51000/sda14.known-good.img`, SHA `7f3f4454…`
  (same kernel payload as live; only the partition tail padding differs)

## Flash (single attempt)

```sh
adb -s R58M75KDB2X push boot14.userns.padded.img /tmp/
adb -s R58M75KDB2X shell 'dd if=/tmp/boot14.userns.padded.img of=/dev/block/by-name/boot bs=1M; sync'
adb -s R58M75KDB2X shell 'sha256sum /dev/block/sda14'   # expect 574c239c…
adb -s R58M75KDB2X reboot
```

## Pass criteria

Nuxel lockscreen/Home, Phoc kbase context, `/dev/fb0` 1440×3040, DECON frames,
touch, Wi-Fi/SSH and `nuxel-*` services. Then:
`unshare -Ur true`, `bwrap --unshare-user ...`, `/proc/sys/user/max_user_namespaces`.

## Fail / rollback

If bootloop, black screen, no SSH after 3–4 minutes, or lost display/touch/network:
re-enter TWRP and restore the verified boot image:

```sh
adb -s R58M75KDB2X push twrp/sda14.current.img /tmp/
adb -s R58M75KDB2X shell 'dd if=/tmp/sda14.current.img of=/dev/block/by-name/boot bs=1M; sync'
adb -s R58M75KDB2X shell 'sha256sum /dev/block/sda14'   # expect 97f78f5d…
adb -s R58M75KDB2X reboot
```

Do not retry another kernel in the same recovery session.
