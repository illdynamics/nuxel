# kernel-patches/ — offline proposals only

These files are **proposals**. Nothing here is compiled, flashed, loaded or
deployed on the SM-G975F. They exist so a kernel/DTB change that userspace cannot
express is *reviewable*, and so the item can be closed honestly as
`BLOCKED_KERNEL / BOOT_UPDATE_REQUIRED` instead of being faked in userspace.

| File | Item | Verdict |
|---|---|---|
| `sec_ts-lpm-initcall-deferred-bind.patch` | charger/LPM boot removes `sec_ts` for the whole boot | BLOCKED_KERNEL / BOOT_UPDATE_REQUIRED / NOT_DEPLOYED |

The userspace mitigation that *is* implemented (no flashing, no kernel change) is
`tools/s10plus/a33/nuxel-bootmode-guard.py`; its reasoning and the non-executed
future flashing procedure are in
`docs/beta-finalization/touch/CHARGER-MODE-ROOTCAUSE.md`.

Hard rules for this directory:

* no patch here may be applied to the phone as part of beta finalization;
* the deferred-bind idea must not be described anywhere as "fixed on device";
* any future deployment needs an explicit owner authorisation, a BOOT-only write
  with full-partition readback, and a retained rollback image.
