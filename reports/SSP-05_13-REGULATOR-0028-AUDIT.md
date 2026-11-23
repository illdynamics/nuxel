# SSP-05_13 — Regulator 0028 (`regulator_force_enable`) Correctness Audit

**Date:** 2026-11-23
**Agent:** DeepSeek-V4-Pro-Thinking
**Scope:** `drivers/regulator/core.c` (0028), plus its two call sites
(`set_mcu_power` and `nuxel_ssp_bringup_hw`).

## 1. What 0028 adds

```c
int regulator_force_enable(struct regulator *regulator)
{
        struct regulator_dev *rdev = regulator->rdev;
        int ret;

        mutex_lock(&rdev->mutex);
        ret = _regulator_do_enable(rdev);
        mutex_unlock(&rdev->mutex);

        if (rdev->supply)
                while (rdev->open_count--)
                        regulator_enable(rdev->supply);

        return ret;
}
```

## 2. Invariant review (verdict per check)

| # | Check | Result | Detail |
|---|---|---|---|
| 1 | Ownership | OK (scoped) | `regulator->rdev` is owned per-handle; no new global owner. |
| 2 | Locking | PARTIAL | `_regulator_do_enable()` does **not** assert the lock (unlike `_regulator_enable()` which does `lockdep_assert_held_once`), and 0028 re-takes/uses `rdev->mutex` correctly for the enable, but the trailing `while (open_count--)` runs *outside* any lock. |
| 3 | Reference-count consistency | **DEFECT** | The trailing loop **decrements `rdev->open_count` to 0** and calls `regulator_enable(rdev->supply)` once per prior open. `open_count` is a "number of consumers holding this regulator" counter; consuming it is semantically wrong and desynchronises it from reality. |
| 4 | `always_on` interaction | ACCEPTABLE for the narrow goal | The whole point is to bypass `always_on`; however it does **not** clear `regulator->always_on`, so a *subsequent* `regulator_is_enabled()` still returns 1 and `regulator_disable()` still no-ops. |
| 5 | Parent (`supply`) behavior | **DEFECT** | Upstream `regulator_enable()` recurses the parent *before* enabling this regulator, and `_regulator_do_enable()` does **not** touch the supply. 0028 instead enables the parent in a post-hoc, count-consuming loop. This diverges from upstream ordering and count semantics. |
| 6 | Enable/disable balance | **ASYMMETRIC** | `regulator_force_disable()` resets `regulator->uA_load = 0`; `regulator_force_enable()` does **not** restore any load. More importantly `force_disable` does not decrement `use_count`, and `force_enable` does not increment it — the pair is "balanced" only in the physical rail sense, not in the reference-count sense. |
| 7 | Error handling | PARTIAL | If `_regulator_do_enable()` fails, the function still runs the `while(open_count--)` tail and returns the (negative) error — but `open_count` has already been consumed. |
| 8 | Unrelated consumers | **Regression risk** | Because it bypasses `always_on` and mutates `open_count`, any other consumer holding a handle to the same `rdev` sees a desynchronised `open_count` and a rail that may have been force-enabled without a matching use-count. |
| 9 | Limited to MCU path | PARTIAL | The *symbol* is called only from `ssp_sysfs.c`/`ssp_bbd.c`, but it is exported `EXPORT_SYMBOL_GPL` and lives in the shared core, so it is globally reachable — broadening the blast radius of the defects above. |

## 3. The single most serious defect

`while (rdev->open_count--) regulator_enable(rdev->supply);`

copies the *disable* tail from `regulator_force_disable()`, but for *enable* it
is wrong on two counts:

1. It **destroys** `open_count` (drains it to zero), which corrupts the
   framework's consumer-count invariant and can later trigger the
   `WARN_ON(rdev->open_count)` teardown path (`core.c:4215`).
2. It enables the **parent** regulator `open_count` times, even though the
   parent was never correspondingly disabled by `force_disable` (which
   disabled it `open_count` times too — so pre-existing open_count consumers
   were already "paired").  For a single regulator with no `supply` (the common
   LDO21M case), this loop is a no-op and the *primary* damage is only the
   `open_count` drain.

For `vdd_mcu_1p8` (LDO21M, no parent supply, `always_on`), the *observable*
symmetric cycle worked on hardware, but the framework invariant
(`open_count` == number of live consumer handles) is now violated.

## 4. Narrowly-scoped correction (prepared, NOT yet applied)

The correct symmetric enable for the *narrow recovery goal* is to mirror
`regulator_force_disable()` exactly, guarded to the same path, and to **not**
touch `open_count`:

```c
int regulator_force_enable(struct regulator *regulator)
{
        struct regulator_dev *rdev = regulator->rdev;
        int ret;

        mutex_lock(&rdev->mutex);
        ret = _regulator_do_enable(rdev);
        mutex_unlock(&rdev->mutex);

        return ret;
}
```

Rationale:
- `_regulator_do_enable()` already performs `ena_gpio_ctrl`/`ops->enable` and
  the ramp delay; it is the same physical primitive `_regulator_enable()` uses.
- It must **not** recurse into or re-count parents (that is `_regulator_enable`/
  `regulator_enable`'s job and depends on `use_count` tracking).
- It must **not** consume `open_count`.

An alternative, *lower-risk* correction is to avoid the core change entirely and
restore the rail in `set_mcu_power`/`nuxel_ssp_bringup_hw` by calling
`regulator_force_disable()` followed by the pre-existing
`_regulator_do_enable`-equivalent via a **balanced disable+enable of the
parent handle** — but since the immediate need is symmetric re-enable after
force_disable, the minimal 3-line core fix above is sufficient and least
invasive.

## 5. Conclusion

The 0028 core change **does not fully preserve the regulator framework's
invariants**: `open_count` is corrupted and notifier symmetry is broken.  A
`echo 0/1 > mcu_power` success is **not** proof the core change is universally
safe.  The correction in §4 is prepared and offline-reviewable but, per the
mission safety directive, must **not** be deployed without a full BOOT
preflight + rollback + separate flash authorization.
