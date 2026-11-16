# Firmware and redistribution note

Samsung's `lhd` executable, sensor HAL libraries and any proprietary sensor-hub patch payload are vendor firmware/software. A public vendor-blobs repository or an indexed raw URL does not itself grant a redistribution licence. This pack therefore does not re-host those proprietary binaries. It supplies an owner-side, read-only extractor so the exact files can be recovered from the owner's own matching handset/stock image for local analysis and use subject to the applicable licence.

Do not download or package a random device's `SensorHub.patch` and assume it fits BCM47752. In particular, a BCM47765/Pixel payload is not proven compatible with this Samsung BCM47752 implementation.
