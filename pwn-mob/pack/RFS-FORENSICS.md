# RFS evidence and security analysis

## Real 25-byte sample (provided by user)

```
19 00 00 00 0b 01 0f 00 00 00 44 45 4c 45 54 45 5f 41 4c 4c 5f 56 49 53 00
```

| Byte range | Observed bytes | Confirmable interpretation | Confidence |
|---|---|---|---|
| 0..3 | `19 00 00 00` | LE32 25 == total observed packet length | HIGH for this packet, not universal |
| 4 | `0b` | Observed type/op-class *candidate* | VALUE certain, semantics unknown |
| 5 | `01` | Observed byte | VALUE certain, semantics unknown |
| 6..7 | `0f 00` | LE16 15 | VALUE certain, meaning not proven |
| 8..9 | `00 00` | Two zero bytes | Observed, unknown purpose |
| 10..24 | ASCII `DELETE_ALL_VIS\0` | 14 chars + NUL | Text certain, meaning unknown |

**Use cautious language:** The string is *consistent with* a destructive filesystem operation. It is not independently verified to be an opcode, path, or instruction. A safe parser classifies it as potentially destructive and never performs a filesystem action based solely on its presence.

## The repeated `2040`-byte reads

RFS-probe output included 2040-byte reads containing unrelated-looking binary or all-0xff runs. This might mean transport chunking, unread queued traffic, mixed channels, or retry conditions; the length alone doesn't establish any of those. A userspace `read()` size is not automatically an on-wire application-message size. Inspect pinned `io_device` routing, `link_device_shmem` RX and `skb` dequeue code rather than deriving a protocol from arbitrary binary.

Potential questions to resolve in a safe code audit:

- Does `read()` of `/dev/umts_rfs0` return already stripped SIPC link headers, or raw link-layer frames?
- Is `read()` boundary one `skb` or a stream fragment? What is the maximum readable per call?
- Can `read()` from `umts_ipc0` and `umts_rfs0` be opened concurrently? Does the kernel require both endpoints for SHMEM IPC READY?
- Does the driver mark radio `ONLINE` independent of RFS service response?
- Are the 2040-byte reads RFS endpoint reads or a trace labeling/dispatch bug?
- Were the 2040-byte reads unique consecutive content? Do hashes differ?

## Protecting modem data

The Replicant historical RFS findings show why filesystem operations from the CP require strict AP-side boundaries. They do not prove the same vulnerability exists on S5000AP. Never map arbitrary CP-provided paths directly into the host filesystem. Current Nuxel policy's rejection of protected/NV paths is a deliberately preserved owner decision; do not override to make initialization succeed.

To make RFS progress, first document the semantic contract (which operations, on what object, how replies are encoded, and security requirements). If the modem demands privileged NV/EFS access, ask for explicit separate authorization; do not promise that denying it has no functional consequence.

## Safe acceptance threshold

- Verified read-only framing and traffic provenance: achievable now from reported evidence.
- Correct and safe RFS command handling: not proven.
- Necessary and sufficient RFS behavior for telephony: unknown.
- Correct bidirectional response: not proven.

All unknown fields remain unknown in `data/telephony-command-matrix.csv` until matched to evidence.
