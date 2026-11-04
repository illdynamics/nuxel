# NFC report — PWNAGE 65000

## Final status: `IMPLEMENTED — HARDWARE VERIFICATION REQUIRED`

The native controller service is deployed and running; NFC is **OFF by default**
and no tag read is claimed.

## Live evidence

```
nuxel-nfcd.service: active (running), enabled
socket: /run/nuxel/nfc/nfc.sock (0600, root)
controller_present: true
device_open: false
enabled: false
state: OFF
mode: off
firmware.path: /lib/firmware/nfc/sec_s3nrn82_firmware.bin
firmware.size: 151852
firmware_file_verified: true
firmware.sha256: d315cd8b…c0bfb
protocol_adapter_ready: true
protocol_verified: false
transport: /dev/sec-nfc (10:107, 0600, root)
payment_supported: false
tag_writes_supported: false
```

`nuxel-nfc selftest`: **PASS** (ABI, NCI framing, NDEF parser; no hardware
opened). The bridge's `nfc_provider` talks only to the local Unix socket and
never opens `/dev/sec-nfc`. Quick Settings and Settings expose status, toggle
and a bounded tag test; no payment/eSE/HCE claims are made.

## Tests

- `tests/pwnage65000`: **17 passed**
- `tools/s10plus/a33/tests/hw-subsystems/test-nfc-diag.py`: **all checks PASS**

## Owner action

With a known NDEF tag, run `nuxel-nfc scan --timeout 10` (or the Settings
“Test tag read”) and compare the UID/text with the physical tag. The controller
stays OFF until explicitly enabled. A tag detection is the only physical proof.
