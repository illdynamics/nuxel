"""No hardware: regression for fabricated READY and internal-RPC confusion."""
import socket
import sys
import time
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import nuxel_lhd as lhd
import nuxel_bbd_tl as tl


def test_session_refuses_before_any_device_or_power_access():
    daemon = lhd.LhdDaemon()
    for name in ('present', 'load_firmware', 'open_transport', 'write_control',
                 'handshake', 'cleanup', 'ioctl_get_hw_rev'):
        setattr(daemon, name, Mock(side_effect=AssertionError('hardware access')))
    daemon.power = Mock()
    result = daemon.run_session()
    assert result['blocker'] == 'INITIALIZATION_PROTOCOL_UNVERIFIED'
    assert result['success'] is False and result['fix'] is None
    assert result['power'] is None and result['transport'] is None
    assert daemon.power.mock_calls == []


def test_rx_ignores_internal_and_truncated_rpc_then_recovers():
    daemon = lhd.LhdDaemon()
    left, right = socket.socketpair()
    try:
        daemon.tfd = left.fileno()
        valid = tl.build_rpc_packet(1, b'abc')
        right.sendall(tl.build_frame(0, valid, tl.FLAG_INTERNAL_PACKET,
                                    {tl.FLAG_INTERNAL_PACKET: 0}) +
                      tl.build_frame(1, b'\x01\x05\x00') +
                      tl.build_frame(2, valid))
        right.shutdown(socket.SHUT_WR)
        callback = Mock()
        assert daemon.rx_poll(time.monotonic() + 1, callback) == [
            {'rpc_id': 1, 'data': b'abc'}]
        callback.assert_called_once_with(1, b'abc')
    finally:
        left.close()
        right.close()
