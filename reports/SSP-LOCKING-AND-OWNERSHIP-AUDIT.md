# SSP — LOCKING AND OWNERSHIP AUDIT (Stage 02)

**Date:** 2026-11-22
**Object files audited:** `drivers/sensorhub/brcm/ssp_bbd.c`, `ssp_i2c.c`,
`bbdpl/bbd.c`, `bbdpl/bcm_gps_spi.c`, plus the downloader added by 0027.

## 1. `bbd_do_transfer()` — the primary lock defect

### Original (buggy) failure path

```c
mutex_lock(&data->pending_mutex);            /* entry: +1 */
if (!send_ok) {
    ...
    mutex_unlock(&data->comm_mutex);
    mutex_lock(&data->pending_mutex);        /* DEADLOCK: already held */
    if (!use_no_irq && ...) list_del(&msg->list);
    mutex_unlock(&data->pending_mutex);
    clean_msg(msg);                          /* kfree(msg) */
    mutex_unlock(&data->pending_mutex);      /* unbalanced */
    return -1;
}
```

`data->pending_mutex` is `struct mutex pending_mutex;` (raw, non-recursive) in
`struct ssp_data`.  Re-locking a held raw mutex blocks forever.  This is triggered
by *any* failed frame (size > `MAX_SSP_PACKET_SIZE`, or `bbd_send_packet()<=0`,
or the native-peer `nuxel_bbd_peer_send()<=0`).

### Corrected failure path

```c
mutex_lock(&data->pending_mutex);            /* entry: +1 */
if (!send_ok) {
    ...
    if (msg != NULL) {
        msg->done = NULL;
        msg->dead_hook = NULL;
        if (!use_no_irq && msg->list.next != NULL &&
            msg->list.next != LIST_POISON1)
            list_del(&msg->list);            /* under the held lock */
    }
    mutex_unlock(&data->pending_mutex);      /* -1 (balanced) */
    mutex_unlock(&data->comm_mutex);         /* -1 (balanced) */
    if (msg != NULL)
        clean_msg(msg);                      /* free AFTER both unlocks */
    return -1;
}
```

- Lock order: `comm_mutex` → `pending_mutex` (acquire), reverse (release), matching
  the rest of the function.
- `clean_msg()` = `kfree(msg)` in `ssp_i2c.c`; it is now called only after the msg
  is removed from the pending list and both mutexes are released, so no
  use-after-free and no free-while-locked.
- `msg->list.next != NULL` correctly skips `list_del` for `use_no_irq` (length-0)
  messages that were never `list_add_tail`'d (all `ssp_msg` are `kzalloc`'d, so
  `list.next` starts NULL).

**Verification:** `tests/test_ssp_lock_deadlock_static.py` (PASS: 1 lock / 1
unlock balanced, `clean_msg` after both unlocks).

## 2. `clean_msg` / freed-pointer ownership

`clean_msg(struct ssp_msg *msg)` frees `msg->buffer` (if `free_buffer`) then
`kfree(msg)`.  Audited call sites in `ssp_bbd.c`:

- `bbd_do_transfer` ssp_down early-return: `clean_msg` under `comm_mutex` before
  any pending-list add — safe (msg never listed).
- `bbd_do_transfer` failure path: fixed per above.
- `callback_bbd_on_packet` paths: `clean_msg` after `list_del` under
  `pending_mutex` — safe (msg removed before free).
- `initialize_mcu`/`ssp_spi_sync` timeout paths: `clean_msg` after list removal
  under `pending_mutex` — safe.

No double-free and no free-then-read was found in the corrected tree.

## 3. Downloader ownership (0027)

- **Single transport owner:** the kernel downloader (`nuxel_ssp_dl_download`) is
  the ONE authoritative kernel download path.  It must not run concurrently with
  `nuxel_bbd_flash` / `nuxel-ssp-bridge` / `lhd`.  Android `lhd` remains
  offline-only reference.
- **ACL correlation state** is per-`struct dl_sess` (stack-local), not global, so
  no cross-session staleness.  `op_seq`/`op_rel_seq` snapshots are committed before
  send and cleared on completion/timeout/error.
- **Allocation:** `dl_decode_blob` uses `kvmalloc`/`kvfree` with a `DL_MAX_BLOB`
  (512 KiB) bound; every `kvmalloc` has a matching `kvfree` on all paths
  (including the `BlobLength`-mismatch and odd-hex early returns).

## 4. Regulator `regulator_force_disable` (0025)

- Only reachable via the explicit `echo 0 > mcu_power` sysfs write (`set_mcu_power`
  `case 0`) and the single bring-up recovery (`nuxel_ssp_bringup_hw` in 0027).
  Not callable from any periodic/service/auto-retry loop.
- **Shared-consumer risk:** vdd_mcu_1p8 may be shared with GNSS; a force-disable
  drops every consumer reference.  The code comments this and always restores via
  `regulator_enable()` (`case 1`) as part of the same bounded operation.
- **No unbounded loop:** a single force-disable + `msleep(120)` + enable + bounded
  retry; failure returns a distinct negative error, never an automatic retry storm.

## 5. Residual (deferred, honest)

- Vendor `bcm477x_rpc_get_version()` has an inverted poll loop (`do {…}
  while (delta > 1000)` runs once and returns 0 unconditionally).  It is NOT used
  as a sync authority; 0027's phase-1 polls for a real GetVersion reply.
- Exact frame/CRC/sequence/ACK vendor parity and `rpc_id` transport-vs-operational
  semantics remain Stage 03.

**Summary:** the double-lock, double-unlock, iterator/ownership, `comm_mutex`
order, and allocation defects identified in the original 0027 are corrected and
statically verified.
