"""Raw transport abstraction for /dev/sec-nfc and deterministic mocks."""

from __future__ import annotations

import errno
import fcntl
import os
import select
import time

from . import abi


class TransportError(RuntimeError):
    def __init__(self, message, code="TRANSPORT_ERROR"):
        super().__init__(message)
        self.code = code


class SecNfcTransport:
    """Exclusive owner of the Samsung misc character device."""

    def __init__(self, path=None, clock=time.monotonic):
        self.path = path or abi.DEVICE_PATH
        self.fd = -1
        self.clock = clock
        self.mode = abi.MODE_OFF
        self._closed = True

    def open(self, mode=abi.MODE_FIRMWARE):
        if self.fd >= 0:
            return
        try:
            self.fd = os.open(self.path, os.O_RDWR | os.O_CLOEXEC)
        except OSError as exc:
            raise TransportError("open %s failed: %s" % (self.path, exc),
                                 abi.errno_name(exc)) from exc
        self._closed = False
        try:
            self.set_mode(mode)
        except Exception:
            self.close()
            raise

    def set_mode(self, mode):
        if mode not in (abi.MODE_OFF, abi.MODE_FIRMWARE):
            raise TransportError("refusing unverified NFC mode %r" % (mode,),
                                 "UNSAFE_MODE")
        try:
            fcntl.ioctl(self.fd, abi.SEC_NFC_SET_MODE, int(mode))
        except OSError as exc:
            raise TransportError("SEC_NFC_SET_MODE(%d) failed: %s" % (mode, exc),
                                 abi.errno_name(exc)) from exc
        self.mode = mode

    def write(self, data):
        if self.fd < 0:
            raise TransportError("device is not open", "NOT_OPEN")
        if not data or len(data) > abi.SEC_NFC_MSG_MAX_SIZE:
            raise TransportError("invalid transfer length %d" % len(data),
                                 "INVALID_LENGTH")
        view = memoryview(data)
        while view:
            try:
                n = os.write(self.fd, view)
            except OSError as exc:
                if exc.errno == errno.EINTR:
                    continue
                if exc.errno == errno.EAGAIN:
                    self.poll(0.5)
                    continue
                raise TransportError("write failed: %s" % exc,
                                     abi.errno_name(exc)) from exc
            if n <= 0:
                raise TransportError("short write (%d)" % n, "SHORT_WRITE")
            view = view[n:]

    def poll(self, timeout_s):
        if self.fd < 0:
            raise TransportError("device is not open", "NOT_OPEN")
        p = select.poll()
        p.register(self.fd, select.POLLIN)
        return bool(p.poll(max(0, int(timeout_s * 1000))))

    def read_exact(self, count):
        if self.fd < 0:
            raise TransportError("device is not open", "NOT_OPEN")
        if count < 0 or count > abi.SEC_NFC_MSG_MAX_SIZE:
            raise TransportError("invalid read length %d" % count, "INVALID_LENGTH")
        if count == 0:
            return b""
        deadline = self.clock() + 2.0
        chunks = []
        while sum(len(c) for c in chunks) < count:
            try:
                chunk = os.read(self.fd, count - sum(len(c) for c in chunks))
            except OSError as exc:
                if exc.errno == errno.EINTR:
                    continue
                if exc.errno in (errno.EAGAIN, errno.EWOULDBLOCK):
                    if self.clock() >= deadline:
                        raise TransportError("read timeout", "TIMEOUT") from exc
                    self.poll(0.1)
                    continue
                raise TransportError("read failed: %s" % exc,
                                     abi.errno_name(exc)) from exc
            if not chunk:
                raise TransportError("short read", "SHORT_READ")
            chunks.append(chunk)
        return b"".join(chunks)

    def close(self):
        if self.fd >= 0:
            try:
                self.set_mode(abi.MODE_OFF)
            except Exception:
                pass
            try:
                os.close(self.fd)
            finally:
                self.fd = -1
                self._closed = True
                self.mode = abi.MODE_OFF

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, *exc):
        self.close()


class MockTransport:
    """Deterministic transport used only by tests (never a hardware claim)."""

    def __init__(self, frames=None, clock=time.monotonic):
        self.frames = list(frames or [])
        self.writes = []
        self.mode = abi.MODE_OFF
        self.fd = -1
        self.open_count = 0
        self.close_count = 0
        self.fail_next = None
        self.clock = clock

    def open(self, mode=abi.MODE_FIRMWARE):
        self.open_count += 1
        self.mode = mode
        if self.fail_next == "open":
            self.fail_next = None
            raise TransportError("mock EBUSY", "BUSY")
        self.fd = 3

    def set_mode(self, mode):
        self.mode = mode

    def write(self, data):
        if self.fail_next == "write":
            self.fail_next = None
            raise TransportError("mock write failure", "IO_ERROR")
        self.writes.append(bytes(data))

    def poll(self, timeout_s):
        return bool(self.frames)

    def read_exact(self, count):
        out = bytearray()
        while len(out) < count:
            if not self.frames:
                raise TransportError("mock read timeout", "TIMEOUT")
            frame = self.frames[0]
            if not frame:
                self.frames.pop(0)
                continue
            need = count - len(out)
            out.extend(frame[:need])
            rest = frame[need:]
            if rest:
                self.frames[0] = rest
            else:
                self.frames.pop(0)
        return bytes(out)

    def close(self):
        self.close_count += 1
        self.fd = -1
        self.mode = abi.MODE_OFF
