"""Nuxel orientation policy service (A49).

One authoritative policy service for the seven user-selectable orientation
modes. The selected user policy (`mode`) is kept distinct from the current
effective orientation (`effective_degrees`). Pure policy/state-machine logic
lives in :mod:`nuxel_orientation.policy` (no I/O), sensor decoding in
:mod:`nuxel_orientation.sensors`, and the compositor apply/revert path in
:mod:`nuxel_orientation.apply`.

Everything that requires the physical handset (gravity readings, the exact
mount matrix, the compositor transform + touch calibration) is honestly marked
``unverified`` until an owner physically proves it. Nothing here flashes,
writes partitions, or reboots.
"""

__version__ = "0.1.0"
__all__ = ["policy", "sensors", "apply"]
