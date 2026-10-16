# nuxel-phone-data — one data layer for the three core phone apps

`nuxel-dialer`, `nuxel-contacts` and `nuxel-messages` are one application family
on the S10+; before this module they each carried an ad-hoc model (a contacts
file that was never flushed, conversations that lived only in RAM, three
different phone-number rules). This directory is the single model they share.

## What lives here

| File | Purpose |
|---|---|
| `nuxel-phone-data.h` | the public model + API, with the honesty contract in the header comment |
| `nuxel-phone-data.c` | storage, number normalisation, vCard, JSON store, capability labels (plain C11, no glib, no json-glib) |
| `nuxel-phone-data-test.c` | 74 offline checks (see below) |
| `run-tests.sh` | builds and runs the checks with `cc`, no device and no display needed |

## Data model (schema_version 1)

```
store    = { contacts[], calls[], messages[] }
contact  = { id, name, phone, email, avatar_color, updated_at }
call     = { id, number, name, direction(in|out|missed), state, started_at, duration_s }
message  = { id, peer, body, direction(in|out), state(stored|sent|queued|no-modem), at }
```

* Phone numbers are normalised once (`nuxel_phone_normalize_number`) and compared
  with `nuxel_phone_number_match`, so `+31 6 1234 5678`, `0031612345678` and
  `0612345678` resolve to the same contact.
* The store is written **atomically**: `<path>.tmp` + `rename()`, so a crash or a
  power cut during a save cannot destroy the address book. The test suite checks
  that no `.tmp` file is left behind and that a corrupt store is reported
  *without* losing the previous file.
* `nuxel_phone_export_vcard` / `nuxel_phone_import_vcard` are the user-facing
  import/export path (vCard 3.0, `FN`/`TEL`/`EMAIL`); the test suite feeds the
  importer garbage to prove it cannot crash on malformed input.

## The honesty contract

`NuxelPhoneCapabilities` is filled **only** from a real probe (ModemManager over
GDBus). `nuxel_phone_capability_label()` turns it into the sentence the UI shows,
and it can never invent a working modem:

* `modem_present == -1` (never probed) → "Modem status unknown";
* `modem_present == 0` → the UI says there is no modem, so there are no calls and
  no SMS — it does **not** pretend to dial;
* a SIP/mock transport is a *labelled mock*, never presented as a carrier.

The S10+ carries a Samsung Shannon LTE modem with no upstream ModemManager
plugin, so on the real device this layer is expected to report "no modem" until
that work lands. A message the transport could not send is stored with
`state = "queued"` and shown as *not sent*; `state = "sent"` is written only when
a transport confirmed the send.

## Running the tests

```sh
shell/nuxel-shell/nuxel-phone-data/run-tests.sh     # cc + the test binary, no meson
meson test -C build nuxel-phone-data                # when the shell tree is configured
```

Expected: `74 checks, 0 failure(s)`.

## Consumers

* `shell/nuxel-shell/meson.build` compiles `nuxel-phone-data.c` into all three
  apps and builds this test binary.
* `tools/s10plus/a33/tests/test-phone-apps.py` re-runs the suite and additionally
  checks that each app only calls symbols this header declares, and that the
  honest capability strings are actually wired into the UI.
