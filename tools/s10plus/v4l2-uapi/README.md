# Vendored V4L2 UAPI subset (for host builds)

macOS ships no `<linux/videodev2.h>`. Two host tools include it:

- `tools/s10plus/fimc-capture/nuxel-fimc-capture.c` (FIMC-IS capture client)
- `tools/s10plus/a61/nuxel-mfc-decode.c` (MFC decode helper; tests build it)

This directory is a vendored subset of the Linux **4.14** UAPI headers
(the version of the pinned S10+ kernel), so host builds use the same ioctl
numbers and struct layouts as the device:

| file | origin |
|---|---|
| `linux/videodev2.h`, `linux/v4l2-common.h`, `linux/v4l2-controls.h` | torvalds/linux v4.14 `include/uapi/linux/` |
| `asm-generic/ioctl.h` | torvalds/linux v4.14 `include/uapi/asm-generic/ioctl.h` |
| `linux/compiler.h`, `linux/types.h`, `linux/ioctl.h`, `asm/ioctl.h`, `asm/types.h` | minimal userspace shims (macOS has no kernel headers); `_IOC` values match the UAPI exactly |

On a Linux host the tool's `<linux/ioctl.h>` forwards to the system header
(`#include_next`). Keep these files in sync with the pinned kernel when the
kernel version changes; they carry no executable code.
