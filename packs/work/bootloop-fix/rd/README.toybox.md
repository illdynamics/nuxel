# toybox — static aarch64 shell/coreutils for the Nuxel initramfs

`bin/toybox` is the statically-linked **aarch64** toybox ELF that the Nuxel
initramfs uses for PID 1 and the early userland. It provides `sh`, `mount`,
`switch_root`, `modprobe`, `mknod`, `dd`, `cp`, `mv`, `rm`, `ls`, `ps`, etc.
— making the initramfs genuinely bootable with no other userspace dependency.

## Provenance

* Source project: **Toybox** (https://landley.net/toybox/) — 0BSD licence.
* Binary source: official toybox binary distribution
  `https://landley.net/toybox/bin/toybox-aarch64`.
* SHA-256: `223b5ff5929371225d0bc62fb3b99a148692295fb6f85ad86bb924f689a55ea4`
* Format: ELF 64-bit LSB executable, ARM aarch64, statically linked, stripped.

## Refresh / re-fetch

```sh
curl -fsSL https://landley.net/toybox/bin/toybox-aarch64 \
  -o images/initramfs/bin/toybox
chmod +x images/initramfs/bin/toybox
```

If the network is unavailable, the vendored binary is used as-is; if you would
prefer a busybox build, drop a static busybox at `images/initramfs/bin/busybox`
and the initramfs `/init` will prefer toybox then busybox.
