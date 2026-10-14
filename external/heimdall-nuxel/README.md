# heimdall-nuxel — instrumented Heimdall v2.2.2 for Nuxel S10+ bring-up

This is **not** a new flasher. It is a small, auditable set of patches on top of
the exact upstream Heimdall v2.2.2 tree used for the S10+ bring-up, plus the
build/test tooling and the Nuxel flash wrapper.

The upstream project cannot tell you *why* an S10+ session fails to close: it
prints `Failed to receive session end confirmation!` for a timeout, a USB
disconnect, a malformed reply and a rejected command alike, and returns a bare
`1`. That is not enough evidence to repair anything, and it invites the worst
possible response — reflashing an unverified device in a loop.

## Provenance

| Item | Value |
|---|---|
| Upstream | `https://git.sr.ht/~grimler/Heimdall` (mirror: `https://github.com/JingMatrix/Heimdall`) |
| Version | tag `v2.2.2` |
| Commit | `d9554e7fa30a00abed7f0ac86b10e63c2c3b8e20` |
| Copyright | Benjamin Dobell / Glass Echidna; Henrik Grimler (2021-2024) |
| Licence | MIT (unchanged) |

`fetch-upstream.sh` refuses to build if the checked-out commit does not match
the pinned hash, so a build can never silently drift onto different source.

The binary this repo's guides previously used (`/opt/homebrew/bin/heimdall`,
`v2.2.2`) is byte-for-byte very close to a build of this source (144648 vs
144552 bytes) and behaves identically, so the analysis below applies to it.

## What the patches add

| Patch | Change |
|---|---|
| `0001` | `NuxelSession.{h,cpp}`: a libusb-free state machine for the Odin EndSession/reboot handshake with precise failure classification. Unit-testable. |
| `0002` | `BridgeManager`: `EndSessionEx()`, raw transfers that surface libusb error codes, bounded configurable timeouts, hex packet tracing, and a Download-Mode presence probe. Upstream `EndSession()` is untouched. |
| `0003` | `FlashAction`: `NUXEL_*` machine-readable result lines, a distinct exit code per failure class, and a post-session "did the phone actually leave Download Mode?" check. |
| `0004` | Identifies the build: `heimdall version` prints `v2.2.2-nuxel`. |
| `0005` | **Write gate**: refuses to write to any device unless `NUXEL_ALLOW_DEVICE_WRITE=1`. |

Nothing else is modified. `git diff v2.2.2` after applying the patches is the
complete change set.

## Failure classes

`NuxelSession` distinguishes, and the tests assert, all of these:

| Result token | Meaning | libusb evidence |
|---|---|---|
| `ok_acknowledged` | 8-byte `0x67` reply received | — |
| `ok_delayed_ack` | as above, but only after ≥1 retry | first read `-7` |
| `timeout` | no acknowledgement within the bounded timeout | all reads `-7` |
| `usb_disconnect` | device left / endpoint stalled mid-session | `-4`, `-9`, `-1` |
| `malformed_packet` | reply was not a well-formed 8-byte control response | short/long read |
| `rejected_command` | well-formed reply, wrong response type | type ≠ `0x67` |
| `usb_transport_error` | any other libusb error | other |
| `reboot_timeout` / `reboot_disconnect` | reboot step not positively acknowledged | — |
| `still_in_download_mode` | handshake acked, phone never left Download Mode | presence probe |

A missing acknowledgement is **never** success. A disconnected device during the
reboot request is reported as `reboot_disconnect` (unconfirmed), never as a
successful reboot.

## Exit codes (`heimdall flash`)

| Code | Meaning |
|---:|---|
| 0 | session acked and (if reboot requested) phone left Download Mode |
| 1 | generic failure |
| 10 | no Download-Mode device |
| 11 | connection/initialise failed |
| 12 | begin-session failed |
| 13 | end-session packet could not be sent |
| 14 | end-session acknowledgement timeout |
| 15 | USB disconnect during end-session |
| 16 | malformed reply |
| 17 | unexpected/rejected response type |
| 18 | other USB transport error |
| 19 | reboot acknowledgement timeout |
| 20 | device disconnected during reboot (unconfirmed) |
| 21 | still in Download Mode after reboot request |
| 22 | a flash step (total-bytes / PIT / partition upload) failed |
| 23 | internal error |
| 24 | write refused: `NUXEL_ALLOW_DEVICE_WRITE` not set |

## Build

### macOS (Apple Silicon or Intel)

```bash
brew install cmake libusb pkgconf
cd /path/to/nuxel
external/heimdall-nuxel/scripts/build-and-test.sh
# binary: build/heimdall-nuxel/out/heimdall-nuxel
build/heimdall-nuxel/out/heimdall-nuxel version    # -> v2.2.2-nuxel
```

Verified in this repo on `arm64-apple-darwin24.6.0`, Apple clang 17, libusb
1.0.30, CMake 4.4.4.

### Fedora 43 (aarch64 or x86_64)

```bash
sudo dnf install -y gcc-c++ cmake make pkgconf-pkg-config libusb1-devel git
cd /path/to/nuxel
external/heimdall-nuxel/scripts/build-and-test.sh
build/heimdall-nuxel/out/heimdall-nuxel version    # -> v2.2.2-nuxel
```

For non-root USB access on Fedora, add a udev rule (`build-fedora43.sh` prints
one):

```bash
sudo tee /etc/udev/rules.d/60-heimdall.rules >/dev/null <<'RULE'
SUBSYSTEM=="usb", ATTR{idVendor}=="04e8", TAG+="uaccess"
RULE
sudo udevadm control --reload-rules && sudo udevadm trigger
```

### Tests only (no device, no libusb, no root)

```bash
external/heimdall-nuxel/scripts/fetch-upstream.sh
external/heimdall-nuxel/scripts/apply-patches.sh
external/heimdall-nuxel/scripts/run-tests.sh
```

`run-tests.sh` builds the tests twice (plain and with ASan/UBSan) and runs 53
assertions covering every scripted outcome. Logs land in
`build/heimdall-nuxel/logs/`.

## Using it

Always go through the wrapper, which performs the PIT/capacity/board-revision
preflight, asks for explicit confirmation, sets `NUXEL_ALLOW_DEVICE_WRITE=1`
only afterwards, and maps the result to a verdict:

```bash
bash boot/s10plus/flash-heimdall.sh --device s10plus \
  --pit-text docs/s10plus-device-pit-2026-10-14.txt \
  --board-rev 26 --image-overlay "BEYOND2LTE EUR OPEN 26" \
  --verified-block-bytes 4096 \
  --boot  build/out/s10plus/nuxel-beyond2lte-boot-merged-fixed.img \
  --rootfs build/out/s10plus/nuxel-beyond2lte-rootfs-diagnostic-fixed.img
```

Never invoke the binary directly for flashing. By design it will refuse unless
`NUXEL_ALLOW_DEVICE_WRITE=1` is set, precisely to prevent an accidental write to
a phone that the operator did not know was attached.
