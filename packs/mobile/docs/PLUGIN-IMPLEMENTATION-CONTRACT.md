# Samsung Shannon ModemManager plugin — implementation contract

## Rule: build the backend before the plugin

A ModemManager plugin identifies a supported port/device, creates a modem object and provides vendor-specific behavior by subclassing the generic modem implementation. It does not invent the missing CP boot protocol or SIPC command dictionary. The upstream ModemManager documentation describes this plugin model and the asynchronous per-interface operations; use the exact source/API version that the Nuxel image actually packages.

The required ordering is:

1. CP reaches a known online state using a G975F-verified bootstrap.
2. SIPC/RFS backend can query actual SIM state and registration.
3. It can create and tear down a real PDP context on an actual rmnet device.
4. Only then implement/enable the ModemManager plugin and map the tested backend operations to standard ModemManager interfaces.

## Device matching

- Match only Samsung SM-G975F / `beyond2lte` / Exynos 9820 / the verified S5000AP kernel transport.
- Match from stable sysfs parent/compatible data and the actual expected device nodes. Do not claim any generic Samsung, arbitrary tty, QMI, MBIM, or Pixel device.
- Never send AT probes to `/dev/umts_ipc*`, `/dev/umts_rfs0`, `/dev/umts_boot0`, or arbitrary `/dev/tty*`.
- Never treat a placeholder filename, empty file, or test fixture as a loadable plugin.

## Capability honesty

- Export 3GPP registration only when the backend returns a real decoded registration response.
- Export signal quality/access technology only from actual CP indications/responses.
- Export SIM only when real SIM state is decoded. Never include IMSI/ICCID/IMEI in ordinary logs, status bar, third-party API responses or diagnostics.
- Export SMS only after the real send acknowledgement and receive indication path is tested.
- Export a bearer only after PDP activation returns a real context and the assigned rmnet path/IP configuration is verified.
- Export Voice only if real call control exists and the call state machine/audio routing are implemented. A generic modem object is not evidence of a call-capable modem.
- Do not provide a fake AT port, fake `+CSQ`, static registration response, dummy APN, or fake success callback.

## Interface mapping to prove

| Shannon backend result | ModemManager surface | Acceptance evidence |
|---|---|---|
| CP/transport alive | modem state | exact `MODEM_STATUS` plus CP heartbeat/ready indication |
| SIM state | SIM object | inserted SIM state from decoded SIM protocol; no identifier leak |
| PLMN registration | 3GPP interface | real network registration state/operator code |
| signal | signal interface | live quality and access technology from CP |
| PDP context | bearer | active context, correct rmnet netdev, assigned addresses and DNS |
| SMS | Messaging interface | send ack + receive indication, real test message |
| voice call | Voice interface | real call state transitions and audio path; separate approval/test |
| SIM phonebook | SIM phonebook API if supported | read/list and carefully confirmed write without overwriting entries |

## Build and integration

- Record exact ModemManager package/source version and ABI before starting.
- Use the packaged ModemManager source tree's in-tree plugin patterns and private headers when required; do not code to `main` and deploy against an older binary.
- Use Meson/autotools and compiler flags from the same package build. Confirm target architecture `aarch64` and runtime shared-library dependencies.
- Add a plugin self-test which checks the built file is a non-empty ELF for AArch64, resolves its dependencies, is discovered by ModemManager, and is actually loaded by the running daemon.
- Add a device-match negative test: generic tty, unrelated Samsung node, missing `umts_ipc*`, or absent `nuxel-radiod` must not create a modem.
- Add transport-loss tests: CP crash, node disappearance, timeout, radio reset, SIM removal, and NetworkManager disconnect must all clear stale state and drop the bearer without stale green status icons.
- Plugin must fail closed and report a clear unsupported/error state until all underlying APIs it exposes are working.

## Permissions

No application receives direct access to `/dev/umts_*` or `org.freedesktop.ModemManager1` by default. Core apps call a Nuxel permission-mediated service/portal. The ModemManager service and the narrowly scoped radio backend are privileged system services. See the full prompt for the capability matrix and Permission Manager integration.
