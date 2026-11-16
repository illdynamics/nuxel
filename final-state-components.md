# Nuxel component state — Galaxy S10+ (`beyond2lte`)

Date: 2026-11-16. This is a consolidated state report from the repository's
latest hardware reports and the live phone at `10.11.12.99`. “Proved” means
observed in the device evidence; it does not mean that a driver node alone is
being treated as a working feature.

## Summary

| Component | Current state | First failing stage | What is actually proved |
|---|---|---|---|
| NFC | `BLOCKED_KERNEL` / hardware-clock dependent | NFC core/NCI runtime; the latest S3NRN82 path also reports a 0 Hz reference clock | I2C controller, `/dev/sec-nfc`, firmware blob and daemon are present; no verified tag read |
| Fingerprint | `BLOCKED_SECURE_PROVIDER` | TEE/trusted application | QBT2000 driver and device nodes exist; enrollment/authentication is correctly refused; PIN fallback works |
| Auto-rotation sensors | `BLOCKED_VENDOR_RUNTIME` | SSP sensor-hub runtime | LSM6DSO/SSP are enumerated and manual rotation modes work; live samples remain zero and auto-rotation is unverified |
| Mobile networking | `NOT_SUPPORTED_ON_DEVICE` / `BLOCKED_FIRMWARE` | Shannon CP host transport + ModemManager/native plugin | `umts_*` nodes exist, but no supported modem, SIM registration, bearer, data, SMS, voice or IMS path is available |
| Camera | `BLOCKED_FIRMWARE` | FIMC-IS sensor/ISP firmware and setfiles | Five sensor modules and V4L2 nodes bind; no media graph or verified real frame exists |

## NFC

The S10+ exposes the Samsung `sec-nfc` transport at `/dev/sec-nfc` and the
controller is present on I2C bus `7-0027`. The pinned S3NRN82 firmware is
present and hash-verified, and `nuxel-nfcd` runs fail-closed with NFC off.
The kernel NFC class/netlink path has not produced a usable device in the
current fallback state. Earlier bring-up proved bootloader framing, but the
NFC reference clock reported 0 Hz and NCI `CORE_RESET` did not complete. No
physical tag read, NDEF exchange, payment capability or protocol success is
claimed. The safe next step is a controlled kernel/clock experiment or a
documented vendor-transport implementation; NFC must remain off by default.

## Fingerprint scanner

The QCOM/Samsung QBT2000 ultrasonic sensor is detected through
`/dev/qbt2000_fd`, `/dev/qbt2000_ipc` and `/sys/class/fingerprint/fingerprint`.
The downstream driver is alive, but no verified TEE-backed trusted application
or secure template provider is available. Nuxel therefore reports
`BLOCKED_SECURE_PROVIDER`, refuses enrollment and authentication, and retains
PIN/password fallback. A userspace matcher or fabricated `fprintd` backend
would violate the security boundary.

## Auto-rotation sensors

The LSM6DSO accelerometer/gyro and Broadcom SSP sensor hub enumerate, and the
orientation policy supports seven modes plus manual/locked rotation. The SSP
MCU is not ready/streaming: accelerometer samples are `0,0,0`, enable remains
off after attempted activation, and kernel logs report `ssp_down == true`.
Thus the UI/orientation policy is not the blocker; auto-rotation and physical
tilt acceptance remain unverified. The required work is the vendor BBD/SSP
power, patch, handshake, sample decoding, timestamps and mount calibration.

## Mobile networking

The integrated Samsung Shannon LTE modem is visible only through opaque
`umts_*` vendor character nodes. ModemManager finds no modem and there is no
Shannon plugin or native CP bearer implementation. No SIM detection,
registration, cellular data netdev, SMS, voice or IMS/VoLTE path is proved.
This is independent of the working Wi-Fi and USB local network. The safe
roadmap is a documented Shannon transport/plugin, beginning with SIM and LTE
data; raw AT/QMI/MBIM assumptions and EFS/IMEI writes are not appropriate.

## Camera

Five sensor modules bind and many `exynos-fimc-is-*` V4L2 nodes exist, but the
expected sensor setfiles, Exynos ISP firmware and board calibration are absent.
No usable media/subdevice graph or integrated real-scene frame has been
verified. Standard V4L2 capture operations previously returned unsupported
errors consistent with a private downstream ioctl ABI. The camera is therefore
`BLOCKED_FIRMWARE`, not “working because a node exists”. Completing it needs
owner-authorized firmware/setfiles/calibration and a dedicated FIMC-IS
pipeline handler, followed by physical rear/front/repeated-frame tests.

## Scope and confidence

The report is intentionally conservative: it records runtime evidence and the
first failing stage, not inferred success. NFC, fingerprint, auto-rotation,
mobile networking and camera have no verified end-to-end acceptance test in
the current state. The detailed source reports remain in `reports/`.
