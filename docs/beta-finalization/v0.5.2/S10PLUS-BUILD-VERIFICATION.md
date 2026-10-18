# S10+ build verification

The rootfs builder compiles the A34 display bridge, host, button manager,
libinput shim, and snapshot tool from checkout sources inside Fedora aarch64.
The rootfs verifier compares packaged launcher, Terminal, registry, bridge, and
keyboard files byte-for-byte with the checkout. BOOT remains the known A25 raw
Image/embedded-initramfs design; no kernel or phone partition was changed.
