# IPC Capture / Parsing Truth Contract

This pack does not collect any new live traffic. Do not add aggressive raw packet capture to Nuxel while CP is online.

## FMT observed event (user report)

```
19 00 00 00 13 05 03 0f 00 0d 0a 41 53 54 5f 50 4f 57 45 52 4f 4e 0d 0a 00
```

- Total record size: 25 bytes.
- First 2 bytes: LE16=25, consistent with the user's corrected inner FMT total-length behavior.
- Bytes 4..6: `13 05 03`, decoded by the user's Stage 05 `radiod` as `main=0x13 sub=0x05 type=0x03`.
- User-reported decoded notification: `AST_POWERON`. No further telephony semantics proven.
- This is **inner FMT framing**, not the 4-byte/variable SIPC5 *link-layer* header documented in the external kernel header. Kernel userspace reads may strip the outer header; verify locally.

## RFS observed event (user report)

```
19 00 00 00 0b 01 0f 00 00 00 44 45 4c 45 54 45 5f 41 4c 4c 5f 56 49 53 00
```

- First four bytes match LE32 total length 25 for this record.
- Contains `DELETE_ALL_VIS\0`. The name and command bytes do not establish a safe response.
- FMT parser must not be applied to this RFS inner payload just because both happen to have the number 25.

## Privacy-safe evidence design

For each **authorized** recorded packet, preserve separately:

- Sanitized timestamp, boot ID reference (not full user IDs).
- Kernel CP state at time of receipt.
- Endpoint/channel and direction.
- Number of bytes returned by read(), parsed inner/outer lengths, structural pass/fail.
- A local-only SHA-256 of redacted payload, or a stable keyed digest when cross-session correlation is justified; do not publish hashes of sensitive low-entropy identifiers.
- Protocol fields only if explicitly reviewed as non-sensitive. Do not log SIM identifiers, UICC APDUs, phone numbers, credentials, SMS/call content, NV blobs or proprietary buffers.

## One key warning

`mmcli -L` returning no modems is **expected** when the generic ModemManager backends don't recognize `/dev/umts_*` as a supported modem. It does not prove CP is OFFLINE or that `nuxel-radiod` is broken. The Stage 06 integration needs a defined adapter or independent native control plane; never equate daemon lifetime with cellular status.
