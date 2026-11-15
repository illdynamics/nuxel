# Host-side SHA-1 probe built with the SAME cross toolchain as the kernel.
# It reproduces drivers/nfc/s3fwrn5/firmware.c:s3fwrn5_fw_download() exactly
# (crypto_shash "sha1" == sha1-ce once the kernel registers it at boot) and
# reports the first unreadable byte so a boot-crashing firmware image is
# rejected on the workstation instead of on the phone.
CROSS ?= aarch64-linux-gnu-
CC    := $(CROSS)gcc
CFLAGS ?= -O2 -Wall -Wextra -static

all: nuxel-nfc-hash-probe

nuxel-nfc-hash-probe: nuxel-nfc-hash-probe.c
	$(CC) $(CFLAGS) -o $@ $<

clean:
	rm -f nuxel-nfc-hash-probe

.PHONY: all clean
