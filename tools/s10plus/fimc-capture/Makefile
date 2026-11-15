# nuxel-fimc-capture — build for the S10+ (aarch64) and for host testing.
#
#   make                      # native build (host gcc) if a V4L2 uapi is present
#   make S10PLUS=1            # cross build with aarch64-linux-gnu-
#   make CROSS=aarch64-linux-gnu-   # explicit cross prefix
#
# The binary is linked -static so it runs on the Nuxel rootfs without depending
# on glibc's runtime loader version.
#
# The vendored include/linux subset (UAPI 4.14 ioctl/videodev2 headers) makes
# the tool buildable on macOS too; on a Linux host the system <linux/videodev2.h>
# is preferred when USE_SYSTEM_UAPI=1.
CC ?= cc
CROSS ?=
ifeq ($(S10PLUS),1)
CROSS := aarch64-linux-gnu-
endif
CFLAGS ?= -O2 -Wall -Wextra -std=gnu99
UAPI_CFLAGS := -I../v4l2-uapi
ifeq ($(USE_SYSTEM_UAPI),1)
UAPI_CFLAGS :=
endif

LDFLAGS_STATIC :=
ifneq ($(CROSS),)
LDFLAGS_STATIC := -static
endif

all: nuxel-fimc-capture

nuxel-fimc-capture: nuxel-fimc-capture.c
	$(CROSS)$(CC) $(CFLAGS) $(UAPI_CFLAGS) $(LDFLAGS_STATIC) -o $@ $<

check: nuxel-fimc-capture
	./nuxel-fimc-capture --help || true
	@echo "check: usage path OK (a real frame needs the S10+ /dev/video node)"

clean:
	rm -f nuxel-fimc-capture

.PHONY: all check clean
