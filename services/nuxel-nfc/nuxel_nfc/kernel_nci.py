"""Kernel NCI client for the S10+ S3NRN82 controller.

The production path is /dev/nfc0 from s3fwrn5_i2c.  Userspace never touches
I2C directly: the kernel NCI core owns CORE_RESET/CORE_INIT and RF discovery,
and this module speaks the standard Linux NFC netlink + AF_NFC raw-socket ABI
(linux/nfc.h).  It has no third-party dependency: CPython's socket/select
modules and the kernel UAPI constants are sufficient.

Important 4.14 limitation: this downstream kernel never emits a userspace
multicast notification when a poll target appears, and there is no netlink
target lookup.  The only reliable activation path is an AF_NFC raw socket
connect() with the target index discovered by the ``nfc`` command-line tool.
This module therefore never invents a target from an IRQ or a poll ACK.
"""

from __future__ import annotations

import os
import select
import socket
import struct
import time

from . import abi

NETLINK_GENERIC = 16
GENL_ID_CTRL = 0x10
GENL_CMD_GETFAMILY = 3
GENL_ATTR_FAMILY_ID = 1
GENL_ATTR_FAMILY_NAME = 2

NLM_F_REQUEST = 0x01
NLM_F_ACK = 0x04
NLM_F_DUMP = 0x300

NFC_GENL_NAME = "nfc"
NFC_GENL_VERSION = 1

# enum nfc_commands in the 4.14 UAPI (NFC_CMD_UNSPEC is zero).
NFC_CMD_GET_DEVICE = 1
NFC_CMD_DEV_UP = 2
NFC_CMD_DEV_DOWN = 3
NFC_CMD_DEP_LINK_UP = 4
NFC_CMD_DEP_LINK_DOWN = 5
NFC_CMD_START_POLL = 6
NFC_CMD_STOP_POLL = 7
NFC_CMD_GET_TARGET = 8

# enum nfc_attrs in the 4.14 UAPI (verified against include/uapi/linux/nfc.h).
NFC_ATTR_DEVICE_INDEX = 1
NFC_ATTR_DEVICE_NAME = 2
NFC_ATTR_PROTOCOLS = 3
NFC_ATTR_TARGET_INDEX = 4
NFC_ATTR_TARGET_SENS_RES = 5
NFC_ATTR_TARGET_SEL_RES = 6
NFC_ATTR_TARGET_NFCID1 = 7
NFC_ATTR_TARGET_SENSB_RES = 8
NFC_ATTR_TARGET_SENSF_RES = 9
NFC_ATTR_IM_PROTOCOLS = 13
NFC_ATTR_TM_PROTOCOLS = 14

NFC_PROTO_JEWEL = 1
NFC_PROTO_MIFARE = 2
NFC_PROTO_FELICA = 3
NFC_PROTO_ISO14443 = 4
NFC_PROTO_NFC_DEP = 5
NFC_PROTO_ISO14443_B = 6

NFC_PROTO_JEWEL_MASK = 1 << NFC_PROTO_JEWEL
NFC_PROTO_MIFARE_MASK = 1 << NFC_PROTO_MIFARE
NFC_PROTO_FELICA_MASK = 1 << NFC_PROTO_FELICA
NFC_PROTO_ISO14443_MASK = 1 << NFC_PROTO_ISO14443
NFC_PROTO_NFC_DEP_MASK = 1 << NFC_PROTO_NFC_DEP
NFC_PROTO_ISO14443_B_MASK = 1 << NFC_PROTO_ISO14443_B

# Read-only discovery; target mode is always zero.  This daemon is never a
# card, never a payment device and never enables a secure element.
POLL_PROTOCOLS = (NFC_PROTO_JEWEL_MASK | NFC_PROTO_MIFARE_MASK |
                  NFC_PROTO_FELICA_MASK | NFC_PROTO_ISO14443_MASK |
                  NFC_PROTO_NFC_DEP_MASK | NFC_PROTO_ISO14443_B_MASK)

AF_NFC = 39
# Kernel rawsock_create() rejects anything but SOCK_RAW/SEQPACKET for PF_NFC.
# The data protocol selector is NFC_SOCKPROTO_RAW = 0 in linux/nfc.h.
NFC_SOCKTYPE = socket.SOCK_SEQPACKET
NFC_SOCKPROTO_RAW = 0
NFC_HEADER_SIZE = 1
# struct sockaddr_nfc: sa_family_t + 2 bytes padding, then three __u32.
SOCKADDR_NFC = "=H2xIII"
SOCKADDR_NFC_LEN = struct.calcsize(SOCKADDR_NFC)

# NFC protocol ID -> the raw protocol that must be selected in sockaddr_nfc.
# The mask returned by GET_TARGET is a bitfield; AF_NFC connect() takes the
# single protocol value (2 = MIFARE for Type 2/Ultralight).
_SINGLE_PROTOCOLS = (NFC_PROTO_MIFARE, NFC_PROTO_ISO14443, NFC_PROTO_JEWEL,
                     NFC_PROTO_FELICA, NFC_PROTO_NFC_DEP, NFC_PROTO_ISO14443_B)


def protocol_from_mask(mask):
    """Pick the raw protocol for a GET_TARGET protocols bitfield."""
    mask = int(mask or 0)
    if mask & NFC_PROTO_MIFARE_MASK:
        return NFC_PROTO_MIFARE
    for proto in _SINGLE_PROTOCOLS:
        if mask & (1 << proto):
            return proto
    raise KernelNciError("unsupported NFC protocol mask 0x%x" % mask,
                         "NFC_BAD_PROTOCOL")


class KernelNciError(RuntimeError):
    def __init__(self, message, code="NCI_ERROR"):
        super().__init__(message)
        self.code = code


def _align4(n):
    return (n + 3) & ~3


def _attr(kind, payload):
    n = len(payload)
    pad = _align4(4 + n) - (4 + n)
    return struct.pack("=HH", 4 + n, kind) + payload + b"\x00" * pad


def _u32(value):
    return struct.pack("=I", int(value))


def _parse_attrs(blob):
    out = []
    pos = 0
    while pos + 4 <= len(blob):
        alen, atype = struct.unpack_from("=HH", blob, pos)
        if alen < 4 or pos + alen > len(blob):
            break
        out.append((atype, blob[pos + 4:pos + alen]))
        pos += _align4(alen)
    return out


def _parse_genl(data):
    if len(data) < 16:
        raise KernelNciError("short netlink message", "ENETLINK")
    mlen, mtype, flags, seq, pid = struct.unpack_from("=IHHII", data, 0)
    if mlen < 16 or mlen > len(data):
        raise KernelNciError("invalid netlink message length", "ENETLINK")
    body = data[16:mlen]
    if len(body) < 4:
        raise KernelNciError("short generic-netlink header", "ENETLINK")
    cmd, version, _res = struct.unpack_from("=BBH", body, 0)
    return {"type": mtype, "flags": flags, "seq": seq, "pid": pid,
            "cmd": cmd, "version": version, "attrs": _parse_attrs(body[4:])}


def _send(sock, msg_type, cmd, version, attrs=b"", flags=NLM_F_REQUEST, seq=1):
    body = struct.pack("=BBH", cmd, version, 0) + attrs
    sock.send(struct.pack("=IHHII", 16 + len(body), msg_type, flags, seq, 0) +
              body)


def _recv(sock, timeout_s):
    msgs = []
    end = time.monotonic() + max(0.0, float(timeout_s))
    while True:
        left = end - time.monotonic()
        if left <= 0:
            break
        ready, _, _ = select.select([sock], [], [], left)
        if not ready:
            break
        try:
            data = sock.recv(65536)
        except ConnectionRefusedError:
            # AF_NETLINK reports rejected requests as ECONNREFUSED on
            # recv; the synchronous caller handles the empty result.
            break
        if not data:
            break
        off = 0
        while off + 16 <= len(data):
            mlen, mtype = struct.unpack_from("=IH", data, off)
            if mlen < 16 or off + mlen > len(data):
                break
            if mtype != 2:  # NLMSG_ERROR; ACK is error == 0
                try:
                    msgs.append(_parse_genl(data[off:off + mlen]))
                except KernelNciError:
                    pass
            off += _align4(mlen)
        if msgs:
            break
    return msgs


def _bind(sock):
    """Bind once so ACKs are delivered to this socket's portid.

    An unbound netlink socket is implicitly bound on send(), but the kernel
    also subscribes it to the first multicast group of the family (nfc's group
    0 is "targets found").  Binding with groups=0 keeps discovery events out of
    the synchronous ACK/dump reads.
    """
    sock.bind((0, 0))


def _family_id(sock, timeout_s=2.0):
    _bind(sock)
    _send(sock, GENL_ID_CTRL, GENL_CMD_GETFAMILY, 1,
          _attr(GENL_ATTR_FAMILY_NAME, NFC_GENL_NAME.encode() + b"\x00"))
    for msg in _recv(sock, timeout_s):
        for kind, val in msg["attrs"]:
            if kind == GENL_ATTR_FAMILY_ID and len(val) >= 2:
                return struct.unpack("=H", val[:2])[0]
    raise KernelNciError("NFC generic-netlink family is unavailable",
                         "NFC_GENL_UNAVAILABLE")


class KernelNci:
    """Kernel NCI device state with explicit, verifiable netlink operations."""

    def __init__(self, device=abi.KERNEL_NCI_DEVICE, clock=time.monotonic):
        self.device = device
        self.clock = clock
        self.fd = -1
        self.dev_idx = None
        self.dev_name = None
        self.protocols = 0
        self.polling = False
        self.target_idx = None
        self.target_protocol = None
        self.target_uid = None
        self.activation_params = b""

    @staticmethod
    def present(device=abi.KERNEL_NCI_DEVICE):
        """Is a kernel NCI device registered?

        NUXEL: net/nfc exposes nfcN through /sys/class/nfc, but this kernel's
        NFC class registers no character device, so "nfc0" (the name the ABI
        here historically used) does not exist.  The device is present iff
        /sys/class/nfc/nfcN exists; the generic-netlink nfc family is the
        userspace entry point.  Keep accepting a real device path too.
        """
        if device and os.path.exists(device):
            return True
        return KernelNci.sysfs_device() is not None

    @staticmethod
    def sysfs_device():
        try:
            names = sorted(n for n in os.listdir(abi.NFC_SYSFS_CLASS)
                           if n.startswith("nfc"))
        except OSError:
            return None
        for name in names:
            if os.path.isdir(os.path.join(abi.NFC_SYSFS_CLASS, name)):
                return name
        return None

    def _ensure_fd(self):
        """Bind the generic-netlink "nfc" family.

        There is no character device to open: nfc0 is a netlink device.  The
        socket is created here once (AF_NETLINK/NETLINK_GENERIC) and the
        device index is discovered by refresh(); callers that only need
        presence must use present().
        """
        if self.fd >= 0:
            return
        self.fd = 0  # sentinel: "opened", no file descriptor to manage

    def open(self):
        """Open the NCI node and verify the kernel exposes a device."""
        self._ensure_fd()
        self.refresh()
        return self

    def close(self):
        if self.polling:
            try:
                self.stop_poll()
            except Exception:
                pass
        if self.fd >= 0:
            self.fd = -1
        self.target_idx = None

    # -- device discovery --------------------------------------------------
    def refresh(self):
        self._ensure_fd()
        sock = socket.socket(socket.AF_NETLINK, socket.SOCK_RAW, NETLINK_GENERIC)
        try:
            fam = _family_id(sock)
            dump = socket.socket(socket.AF_NETLINK, socket.SOCK_RAW,
                                 NETLINK_GENERIC)
            try:
                _bind(dump)
                _send(dump, fam, NFC_CMD_GET_DEVICE, NFC_GENL_VERSION,
                      flags=NLM_F_REQUEST | NLM_F_DUMP)
                for msg in _recv(dump, 2.0):
                    for kind, val in msg["attrs"]:
                        if kind == NFC_ATTR_DEVICE_INDEX and len(val) >= 4:
                            self.dev_idx = struct.unpack("=I", val[:4])[0]
                        elif kind == NFC_ATTR_DEVICE_NAME:
                            self.dev_name = val.rstrip(b"\x00").decode(
                                "ascii", "replace")
                        elif kind == NFC_ATTR_PROTOCOLS and len(val) >= 4:
                            self.protocols = struct.unpack("=I", val[:4])[0]
            finally:
                dump.close()
        except OSError as exc:
            raise KernelNciError("generic netlink unavailable: %s" % exc,
                                 "ENETLINK") from exc
        finally:
            sock.close()
        if self.dev_idx is None:
            raise KernelNciError("kernel NCI has no registered device",
                                 "NFC_DEVICE_MISSING")
        sysdev = self.sysfs_device()
        if sysdev and not self.dev_name:
            self.dev_name = sysdev
        return {"device_index": self.dev_idx, "device_name": self.dev_name,
                "protocols": self.protocols}

    def _command(self, cmd, seq, extra=b"", flags=NLM_F_REQUEST | NLM_F_ACK,
                 timeout_s=2.0):
        sock = socket.socket(socket.AF_NETLINK, socket.SOCK_RAW, NETLINK_GENERIC)
        try:
            fam = _family_id(sock)
            _send(sock, fam, cmd, NFC_GENL_VERSION,
                  _attr(NFC_ATTR_DEVICE_INDEX, _u32(self.dev_idx)) + extra,
                  flags, seq=seq)
            return _recv(sock, timeout_s)
        finally:
            sock.close()

    def _device_command(self, cmd, seq):
        return self._command(cmd, seq)

    def start_poll(self, timeout_s=10.0):
        if self.dev_idx is None:
            self.refresh()
        # nci_dev_up() runs CORE_RESET/CORE_INIT (and s3fwrn5's firmware
        # post_setup) through the kernel.  A fresh DEV_UP failure here is a
        # real controller initialisation failure, not a "no tag" result.
        try:
            up = self._device_command(NFC_CMD_DEV_UP, 2)
        except OSError as exc:
            raise KernelNciError("NFC DEV_UP failed: %s" % exc,
                                 "NFC_DEV_UP_FAILED") from exc
        if not up:
            raise KernelNciError("NFC DEV_UP was not acknowledged",
                                 "NFC_DEV_UP_FAILED")
        try:
            msgs = self._command(
                NFC_CMD_START_POLL, 3,
                _attr(NFC_ATTR_IM_PROTOCOLS, _u32(POLL_PROTOCOLS)) +
                _attr(NFC_ATTR_TM_PROTOCOLS, _u32(0)),
                timeout_s=min(2.0, max(0.1, float(timeout_s))))
            if msgs:
                # START_POLL returns an ACK on success, or the NCI status as
                # the first netlink payload byte.  Never convert a negative
                # status into "polling".
                for msg in msgs:
                    for kind, val in msg["attrs"]:
                        if val and val[0] not in (0x00,):
                            raise KernelNciError(
                                "START_POLL rejected (status 0x%02x)" % val[0],
                                "NFC_POLL_REJECTED")
            else:
                raise KernelNciError("START_POLL was not acknowledged "
                                     "(no target is claimed without activation)",
                                     "NFC_POLL_NO_ACK")
        except OSError as exc:
            raise KernelNciError("START_POLL failed: %s" % exc,
                                 "NFC_POLL_FAILED") from exc
        self.polling = True
        return {"device_index": self.dev_idx, "device_name": self.dev_name,
                "protocols": POLL_PROTOCOLS, "polling": True}

    def targets(self, timeout_s=2.0):
        """Dump kernel targets found by the current poll (NFC_CMD_GET_TARGET).

        The 4.14 kernel implements this command as a dumpit, so it returns
        one message per target even though there is no event-only API.
        """
        if self.dev_idx is None:
            raise KernelNciError("NFC device is not initialised",
                                 "NFC_DEVICE_MISSING")
        found = []
        msgs = []
        # NFC_CMD_GET_TARGET is 8 in the pinned 4.14.253 UAPI and is a dump.
        try:
            msgs = self._command(NFC_CMD_GET_TARGET, 4,
                                 flags=NLM_F_REQUEST | NLM_F_DUMP,
                                 timeout_s=timeout_s)
        except OSError as exc:
            raise KernelNciError("GET_TARGET dump failed: %s" % exc,
                                 "NFC_TARGET_DUMP_FAILED") from exc
        # The generic-netlink layer emits a zero-length NLMSG_DONE marker for
        # a GET_TARGET dump with no targets; _recv() ignores non-genl types, so
        # an empty list is the only honest "no target" result.
        for msg in msgs:
            target = {}
            for kind, val in msg["attrs"]:
                if kind == NFC_ATTR_TARGET_INDEX and len(val) >= 4:
                    target["target_index"] = struct.unpack("=I", val[:4])[0]
                elif kind == NFC_ATTR_PROTOCOLS and len(val) >= 4:
                    target["protocols"] = struct.unpack("=I", val[:4])[0]
                elif kind == NFC_ATTR_TARGET_NFCID1:
                    target["uid"] = val.hex(":").upper()
                elif kind == NFC_ATTR_TARGET_SENS_RES and len(val) >= 2:
                    target["sens_res"] = struct.unpack("=H", val[:2])[0]
                elif kind == NFC_ATTR_TARGET_SEL_RES:
                    target["sel_res"] = (val + b"\x00")[0]
            if "target_index" in target:
                found.append(target)
        return found

    def stop_poll(self):
        self.polling = False
        if self.fd < 0 or self.dev_idx is None:
            return
        self._command(NFC_CMD_STOP_POLL, 5, timeout_s=1.0)
        self._command(NFC_CMD_DEV_DOWN, 6, timeout_s=2.0)

    # -- target I/O --------------------------------------------------------
    def set_target(self, target_idx, protocol=NFC_PROTO_ISO14443, uid=None):
        if not isinstance(target_idx, int) or target_idx < 0:
            raise KernelNciError("target index must be a non-negative integer",
                                 "NFC_BAD_TARGET")
        if protocol not in _SINGLE_PROTOCOLS:
            raise KernelNciError("unsupported NFC protocol %r" % (protocol,),
                                 "NFC_BAD_PROTOCOL")
        self.target_idx = target_idx
        self.target_protocol = protocol
        self.target_uid = uid

    def transceive(self, data, timeout_s=1.5):
        """Activate the selected target and exchange one APDU/frame."""
        if self.target_idx is None:
            raise KernelNciError("no activated target", "NFC_NOT_ACTIVATED")
        if not data or len(data) > 1024:
            raise KernelNciError("invalid transceive length", "INVALID_LENGTH")
        try:
            sock = socket.socket(AF_NFC, NFC_SOCKTYPE, NFC_SOCKPROTO_RAW)
        except OSError as exc:
            raise KernelNciError("AF_NFC raw socket failed: %s" % exc,
                                 "NFC_SOCKET_FAILED") from exc
        try:
            sock.settimeout(timeout_s)
            saddr = struct.pack(SOCKADDR_NFC, AF_NFC, int(self.dev_idx),
                                int(self.target_idx), int(self.target_protocol))
            sock.connect(saddr)
            # rawsock_add_header() prepends one byte to every RX datagram.
            # SOCK_SEQPACKET preserves that record boundary, so send the frame
            # exactly as the NFC Forum command bytes and strip one byte here.
            sock.sendall(bytes(data))
            out = sock.recv(4096)
        except (OSError, socket.timeout) as exc:
            code = "NFC_TIMEOUT" if isinstance(exc, socket.timeout) else \
                   abi.errno_name(exc)
            raise KernelNciError("NFC transceive failed: %s" % exc, code) from exc
        finally:
            sock.close()
        if out is None or len(out) < NFC_HEADER_SIZE:
            raise KernelNciError("empty NFC response", "NFC_SHORT_READ")
        return out[NFC_HEADER_SIZE:]
