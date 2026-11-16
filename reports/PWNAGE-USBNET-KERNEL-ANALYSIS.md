# PWNAGE-USBNET — Kernel Analysis: Samsung NCM teardown lifetime

**Target:** Samsung Galaxy S10+ `SM-G975F` (`beyond2lte`, Exynos 9820),
Samsung-derived Linux 4.14.253.
**Pinned source:** `https://github.com/Linux4/android_kernel_samsung_exynos9820`
commit `f7194c1d15eded1c2a1a4dc63825b26103435cc0` (verified with
`git -C kernel/s10plus/.build/src rev-parse HEAD`).
**Original crash evidence:** `docs/beta-finalization/live/evidence/n26000-usb-ncm-panic/`.
**Patch:** `kernel/s10plus/patches/0011-nuxel-usb-ncm-lifecycle.patch`
(sha256 `95d8a3e7fde4e6145bc87ae6c284fa094d6d55c4e9aebd6f7d3c041e03e84b78`),
`.required` sidecar present.

**Result:** root cause proven from the pinned source; a durable patch exists
(applies to the *pristine* pinned `f_ncm.c`, not just a pre-edited tree);
`f_ncm.o` compiles with the CI toolchain and carries the marker in `.rodata`.
**Physical teardown soak on the handset: NOT TESTED** — the phone was not
reachable over Wi-Fi, USB or ADB during this run (see
`PWNAGE-USBNET-TEST-RESULTS.md` §1).

---

## 1. What the previous run actually left behind

The earlier *report* described a refcounted lifecycle fix, but the artifact did
not match it:

* `kernel/s10plus/.build/src/drivers/usb/gadget/function/f_ncm.c` was the
  **pristine** pinned file plus a 10-line partial edit (unused statics), i.e.
  the "fix" was **not** in the tree that built the recorded boot image.
* The patch named in the manifest (`0011-nuxel-usb-ncm-lifecycle.patch`) was
  **not in `kernel/s10plus/patches/`** at all; two stale copies sat in
  `/tmp/patches-quarantine/` and an evidence SHA256SUMS file still referenced a
  hash for a file that was gone.
* The two `test_usbnet_lifecycle_gate.py` tests that read that patch failed
  (`FileNotFoundError`) and were never run to completion.

That is exactly the "source patch is a distinct milestone from a built image"
trap in `full-pwnage-usbnet.md` §0.1. The patch below was written from the
pinned source and is tested for real.

## 2. Reproduction that matters

Under `CONFIG_USB_ANDROID_SAMSUNG_COMPOSITE=y` (verified in the resolved
`.config`) the vendor `f_ncm.c` adds one **global** misc device (`usb_ncm`,
"MirrorLink") and one global work item. The recorded pstore stack was:

```text
misc_deregister+0x48/0xc8
ncm_free_inst+0x38/0x60
usb_put_function_instance+0x20/0x40
ncm_attr_release+0xc/0x20
config_item_put.part.0+0x70/0xa0
configfs_rmdir+0x20c/0x338
```

i.e. `rmdir functions/ncm.*` → configfs releases the instance →
`ncm_free_inst()` → `ncm_function_cleanup()` → `misc_deregister()`.

## 3. The actual defects (from the pinned source)

| # | Defect | Where |
|---|---|---|
| 1 | Singleton registered from `ncm_alloc()`, which runs **again on every bind**; deregistered once per *instance*. Unbalanced. | `ncm_alloc()`, `ncm_free_inst()` |
| 2 | `misc_register()` failure logged and ignored; `ncm_function_init()` returns 0 regardless. | `ncm_function_init()` |
| 3 | A second instance could `misc_deregister()` the device the first still owns. | `ncm_function_init/cleanup` |
| 4 | `ncm_function_cleanup()` did `kfree(_ncm_dev); _ncm_dev = NULL;` with **no** `cancel_work_sync()`, while `set_ncm_ready()` (vendor control requests) does `schedule_work(&_ncm_dev->work)`. | `set_ncm_ready()`, `ncm_work()`, `cleanup` |
| 5 | `ncm_work()` dereferences `mirrorlink_device.this_device->kobj` unconditionally. Between `misc_deregister()` and the next `misc_register()` `this_device` is `NULL` → NULL deref in `kobject_uevent_env()`; after the `kfree` it is a use-after-free. | `ncm_work()` |
| 6 | `ncm_work()` and the teardown could run concurrently with no lock. | all of the above |

The old "idempotent deregister" boolean (retired patch) addressed only (2):
it could not see (1), (3), (4), (5) or (6).

## 4. The fix (ownership model)

The misc device + work item are **one singleton owned by the set of live NCM
function instances**.

```
mirrorlink_lock  spinlock   guards mirrorlink_users, mirrorlink_refs,
                            mirrorlink_active, _ncm_dev, ncm_connect
mirrorlink_txn   mutex      serialises register vs deregister (both sleep)
mirrorlink_users count      instances that took a reference from init
mirrorlink_refs  count      ncm_alloc()/ncm_free() callers that may still
                            reach the per-instance work
mirrorlink_active bool      singleton registered (true) / being torn down
```

* `ncm_function_init()` — first user only: allocate, `INIT_WORK`,
  `misc_register()`, create `nuxel_fix`; on failure free, drop the count and
  return the error, which `ncm_alloc()` now propagates as `ERR_PTR(status)`
  after undoing `refcnt++`/`kfree(ncm)`. Later instances only take a count.
* `ncm_function_cleanup()` — last user only: clear `mirrorlink_active` and
  `_ncm_dev` under the lock, **wait for `mirrorlink_refs` to drain**, then
  `cancel_work_sync(&dev->work)`, `device_remove_file(nuxel_fix)`, exactly one
  `misc_deregister()`, `kfree(dev)`. Extra calls return immediately.
* `ncm_free_inst()` — drops its ref after `kfree(opts)` (before cleanup, so a
  module unload blocked in `ncm_function_shutdown()` cannot deadlock).
* `ncm_work()` / `set_ncm_ready()` — re-check `mirrorlink_active && _ncm_dev`
  under `mirrorlink_lock` before scheduling or touching the misc device.
* `nuxel_ncm_mod_exit()` — wraps the macro-generated `ncm_mod_exit()` so module
  exit releases the singleton even with no function instance left
  (`ncm_function_shutdown()` forces one final cleanup).

### Invariants enforced

| Invariant | Mechanism |
|---|---|
| one successful `misc_register()` ⇔ exactly one `misc_deregister()` | count to 1 + `mirrorlink_txn` |
| failed registration never deregistered | register failure returns before `mirrorlink_active = true` |
| partial setup unwinds only what it acquired | `kfree(dev)` + count rollback |
| no work/callback touches freed state | `mirrorlink_active` checked under lock + `cancel_work_sync()` |
| no in-flight caller can be freed underneath | `mirrorlink_refs` barrier (waits after removing work source) |
| second instance cannot deregister the shared device | refcounted owner |
| configfs op fails cleanly | `ERR_PTR(status)` from `ncm_alloc()` |
| module unload releases the singleton | `nuxel_ncm_mod_exit()` |

## 5. Marker and the userspace gate

The patch exposes the fix in two ways:

* `const char nuxel_ncm_lifecycle_marker[] = "nuxel-ncm-lifecycle-fix-v2";`
  (`EXPORT_SYMBOL_GPL`) — always present in the image, so build/CI tooling can
  prove a kernel carries the fix with `nm`/`strings` without creating a gadget.
* `/sys/class/misc/usb_ncm/nuxel_fix` → `nuxel-ncm-lifecycle-fix-v2` on the
  live misc device.

Userspace (`tools/beta/live/nuxel-usb-net.py`,
`services/nuxel-s10/bin/nuxel-usb-mode.sh`,
`services/nuxel-bridge/src/tri_link_status.py`) requires the marker before it
will create an NCM function. The **running build**, not the `4.14.253` string,
is the verdict; there is no override flag.

## 6. Mode selection

| Mode | Status | Why |
|---|---|---|
| ACM | **always** | recovery console; present in every composition |
| CDC-NCM | primary (gated on marker) | native `AppleUSBDeviceNCM` on macOS 15; the only physically targeted data plane |
| RNDIS | not enabled | no native macOS driver; its teardown path is not proof of safety; would need a third-party driver/SIP change (refused) |
| ECM / ECM-subset / EEM | not enabled | no measured host requirement; macOS has no ECM network driver |

`services/nuxel-bridge/src/usb_tethering.py` accepts only `ncm` and returns
`UNSUPPORTED_FUNCTION` for the others instead of silently substituting.

RNDIS source audit note for a later batch: `f_rndis.c` uses `gether_cleanup()`
in `rndis_free_inst()` and has no mirrorlink singleton, so it does **not**
share this panic path — but "different path" is not "validated". A physical
teardown + ACM soak on a Linux/Windows host would be required before enabling
it, and it still would not be the macOS path.

## 7. Configuration (actual build inputs)

`kernel/s10plus/configs/nuxel-drm-kbase.fragment` (the active fragment) already
has `CONFIG_USB_F_NCM=y`, `CONFIG_USB_CONFIGFS_NCM=y`,
`CONFIG_USB_ANDROID_SAMSUNG_COMPOSITE=y` (defconfig), nf_tables + conntrack +
`CONFIG_NFT_MASQ_IPV4=y` for the tether provider. No new symbol is required by
this patch. The `.config` used for the build check had all of them resolved.

## 8. Verification actually performed

| Check | Result |
|---|---|
| Patch applies to **pristine** pinned `f_ncm.c` (`git apply --check` in a scratch index) | **PASS** |
| Applied source compiles: `drivers/usb/gadget/function/f_ncm.o` with `aarch64-linux-gnu-gcc`, no `f_ncm.c` warnings | **PASS** |
| Object contains marker in read-only data (`nm`: `R nuxel_ncm_lifecycle_marker`) | **PASS** |
| Tests pin the invariants (refcounts, lock order, single deregister, drain before free, `ERR_PTR`, module exit) | **PASS** |
| Full combined kernel image rebuilt from *this* patch in this run | **NOT COMPLETED** — the shared `kernel/s10plus/.build/src` is mid-series for the NFC agent (required `0007` conflicts), and a scratch full build cannot embed the firmware set outside the wrapper; the mandatory `f_ncm.o` gate above is the artifact proof. See `PWNAGE-USBNET-REFLASH-MANIFEST.md` §5. |
| Physical create/bind/unbind/remove ×10, pstore clean, ACM preserved | **NOT TESTED** (no device) |

## 9. Post-review correction (2026-11-14, final pass)

The first draft of this patch used `device_is_registered(mirrorlink_device.this_device)`
after a teardown (a NULL-deref risk) and had `ncm_function_shutdown()` clear
`mirrorlink_users` before calling cleanup (a leak on module unload). Both were
found by re-reading/compiling the patch and are fixed in the shipped file:
the shutdown path now forces the count to 1 and lets cleanup do the teardown,
and the attribute is only removed when the owning `dev` was live.
A one-step typed owner action (`usb-net enable-for-host`) and a one-command
Mac acceptance script were also added after review.
