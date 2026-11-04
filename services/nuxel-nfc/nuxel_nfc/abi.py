"""Exact userspace ABI for the pinned Samsung ``sec_nfc`` misc driver.

The numbers are derived from the pinned kernel header and are asserted against
that header by ``tests/pwnage65000/test_nfc_abi.py``.  No ioctl is re-typed by
hand: ``_IOC`` below implements the Linux generic encoding used by
``include/uapi/asm-generic/ioctl.h``.
"""

from __future__ import annotations

import os

SEC_NFC_DRIVER_NAME = "sec-nfc"
SEC_NFC_MAX_BUFFER_SIZE = 512
SEC_NFC_MSG_MAX_SIZE = 256 + 4

SEC_NFC_MAGIC = ord("S")

_IOC_NRBITS = 8
_IOC_TYPEBITS = 8
_IOC_SIZEBITS = 14
_IOC_DIRBITS = 2
_IOC_NRSHIFT = 0
_IOC_TYPESHIFT = _IOC_NRSHIFT + _IOC_NRBITS
_IOC_SIZESHIFT = _IOC_TYPESHIFT + _IOC_TYPEBITS
_IOC_DIRSHIFT = _IOC_SIZESHIFT + _IOC_SIZEBITS
_IOC_NONE = 0
_IOC_WRITE = 1
_IOC_READ = 2


def _ioc(direction: int, typ: int, nr: int, size: int) -> int:
    return ((direction << _IOC_DIRSHIFT) | (typ << _IOC_TYPESHIFT) |
            (nr << _IOC_NRSHIFT) | (size << _IOC_SIZESHIFT))


def _iow(typ: int, nr: int, size: int) -> int:
    return _ioc(_IOC_WRITE, typ, nr, size)


def _io(typ: int, nr: int) -> int:
    return _ioc(_IOC_NONE, typ, nr, 0)


# enum sec_nfc_mode
MODE_OFF = 0
MODE_FIRMWARE = 1
MODE_BOOTLOADER = 2
MODE_COUNT = 3

# enum sec_nfc_power / firmpin / wake
POWER_ON = 0
POWER_OFF = 1
FIRMWARE_PIN_OFF = 0
FIRMWARE_PIN_ON = 1
WAKE_SLEEP = 0
WAKE_UP = 1

# The header uses _IOW(..., unsigned int); the size is therefore 4.
SEC_NFC_GET_MODE = _iow(SEC_NFC_MAGIC, 0, 4)
SEC_NFC_SET_MODE = _iow(SEC_NFC_MAGIC, 1, 4)
SEC_NFC_SLEEP = _iow(SEC_NFC_MAGIC, 2, 4)
SEC_NFC_WAKEUP = _iow(SEC_NFC_MAGIC, 3, 4)
SEC_NFC_SET_NPT_MODE = _iow(SEC_NFC_MAGIC, 4, 4)
SEC_NFC_DEBUG = _io(SEC_NFC_MAGIC, 99)

DEVICE_PATH = os.environ.get("NUXEL_NFC_DEVICE", "/dev/sec-nfc")
SOCKET_PATH = os.environ.get("NUXEL_NFC_SOCKET", "/run/nuxel/nfc/nfc.sock")
STATE_PATH = os.environ.get("NUXEL_NFC_STATE", "/run/nuxel/nfc/state.json")
LAST_TAG_PATH = os.environ.get("NUXEL_NFC_LAST_TAG", "/run/nuxel/nfc/last-tag.json")
FIRMWARE_PATH = "/lib/firmware/nfc/sec_s3nrn82_firmware.bin"
FIRMWARE_SHA256 = "d315cd8bf47d90b7537aa978cb52299b7f2a56e8748588fb980b83ee823c0bfb"
FIRMWARE_SIZE = 151852
CONTROLLER_I2C = "/sys/bus/i2c/devices/7-0027"
SEC_NFC_CLASS = "/sys/class/sec_nfc"
GENERIC_NFC_CLASS = "/sys/class/nfc"

# This is a published NCI 1.0/2.0 controller family mapping.  It is deliberately
# *not* advertised as verified hardware support until a physical tag read is
# recorded by the owner.
PROTOCOL_NAME = "NCI 1.0/2.0 over Samsung sec-nfc misc transport"
PROTOCOL_VERIFIED = False

ERROR_MAP = {
    16: "BUSY",              # EBUSY: another process owns /dev/sec-nfc
    19: "DEVICE_MISSING",    # ENODEV
    5: "IO_ERROR",           # EIO
    22: "INVALID_ARGUMENT",  # EINVAL
    11: "WOULD_BLOCK",       # EAGAIN
    4: "INTERRUPTED",        # EINTR
}


def errno_name(exc: BaseException) -> str:
    num = getattr(exc, "errno", None)
    if num in ERROR_MAP:
        return ERROR_MAP[num]
    return type(exc).__name__.upper()
