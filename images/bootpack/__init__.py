"""Nuxel boot image packaging helpers.

This package builds a *genuinely bootable* boot artifact for the Nuxel phone
OS and is invoked by images/build.sh.

Because the AOSP ``mkbootimg`` / Google ABL (bootloader) blobs are NOT
available in this build environment, this packager does NOT fabricate an
Android Boot Image header.  Instead, by default it produces the closest
genuinely bootable artifact for a generic ARM64 machine (vm) — a Linux
``newc`` cpio initramfs (gzip) that UTM/QEMU boots with ``-kernel`` +
``-initrd``.  When a real ``mkbootimg`` (or avbtool-derived tool) and a
mustang device tree are made available, build.sh switches to emitting the true
Android Boot Header v4 image via boot/mkbootimg.py (correct on-disk layout,
no fake bytes).
"""
