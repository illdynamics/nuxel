#!/usr/bin/env python3
"""Offline Nuxel kernel .config presence scanner. Makes no phone changes."""
import argparse
import gzip
import pathlib

RELEVANT = {
    "Storage/init": ["CONFIG_BLK_DEV", "CONFIG_SCSI", "CONFIG_SCSI_UFSHCD", "CONFIG_SCSI_UFSHCD_PLATFORM",
                     "CONFIG_DEVTMPFS", "CONFIG_DEVTMPFS_MOUNT", "CONFIG_EXT4_FS", "CONFIG_BLK_DEV_INITRD",
                     "CONFIG_RD_GZIP", "CONFIG_BINFMT_ELF", "CONFIG_TMPFS", "CONFIG_CGROUPS"],
    "Previous-boot logs": ["CONFIG_PRINTK", "CONFIG_KMSG_DUMP", "CONFIG_PSTORE", "CONFIG_PSTORE_CONSOLE",
                           "CONFIG_PSTORE_RAM", "CONFIG_RAMOOPS", "CONFIG_MAGIC_SYSRQ"],
    "Phone display": ["CONFIG_DRM", "CONFIG_FB", "CONFIG_DRM_PANEL", "CONFIG_DRM_EXYNOS",
                      "CONFIG_DRM_MIPI_DSI", "CONFIG_INPUT_EVDEV", "CONFIG_TOUCHSCREEN"],
    "Possible USB diagnostics": ["CONFIG_USB_GADGET", "CONFIG_USB_CONFIGFS", "CONFIG_USB_CONFIGFS_ACM",
                                 "CONFIG_USB_CONFIGFS_RNDIS", "CONFIG_USB_F_ACM"],
}

def audit(path):
    raw = path.read_bytes()
    if path.suffix == '.gz' or raw[:2] == b'\x1f\x8b':
        raw = gzip.decompress(raw)
    text = raw.decode('utf-8', 'replace')
    values = {}
    for line in text.splitlines():
        if line.startswith('CONFIG_') and '=' in line:
            k, v = line.split('=', 1)
            values[k] = v
        elif line.startswith('# CONFIG_') and line.endswith(' is not set'):
            values[line[2:].split(' is not set')[0]] = 'n'
    print('Nuxel Exynos S10+ kernel config audit (offline, not a running-kernel measurement)')
    print('Config:', path)
    print('NOTE: Some drivers use different vendor-specific Kconfig names; missing names may be harmless.')
    for section, names in RELEVANT.items():
        print('\n==', section, '==')
        for name in names:
            print(f'{name:40} {values.get(name, "NOT LISTED")}')
    print('\nDo not assume that CONFIG_PSTORE=y guarantees a persistent log after a reboot.')

def main():
    a = argparse.ArgumentParser(description=__doc__)
    a.add_argument('config', type=pathlib.Path)
    opts = a.parse_args()
    audit(opts.config)

if __name__ == '__main__':
    main()
