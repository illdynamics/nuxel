#!/usr/bin/env python3
"""Focused regression coverage for the 0029 regulator-core correction.

0029 removes the open_count-draining / parent-supply-recursing tail that 0028
erroneously copied from regulator_force_disable() into regulator_force_enable().
This test proves the corrected source cannot regress to the defective form:
  * regulator_force_enable() must NOT mutate rdev->open_count.
  * regulator_force_enable() must NOT recurse into rdev->supply.
  * regulator_force_enable() must still physically enable via _regulator_do_enable().
  * The symbol must remain declared in include/linux/regulator/consumer.h.
  * Both call sites (set_mcu_power case 1, nuxel_ssp_bringup_hw) must use it.

This is a read-only source invariant test; it never builds or flashes anything.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path


def function_body(src: str, name: str) -> str:
    """Return the body between 'name(...)' and the next top-level closing brace."""
    idx = src.find(name)
    if idx < 0:
        return ""
    open_brace = src.find("{", idx)
    if open_brace < 0:
        return ""
    # find matching close brace
    depth = 0
    for i in range(open_brace, len(src)):
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                return src[open_brace : i + 1]
    return ""


def main(argv=None) -> int:
    root = Path(__file__).resolve().parents[3]  # repo root
    core = root / "kernel" / "s10plus" / ".build" / "src" / "drivers" / "regulator" / "core.c"
    # The build tree may be symlinked or named differently; resolve the real source.
    candidates = [
        root / "kernel" / "s10plus" / ".build" / "src" / "drivers" / "regulator" / "core.c",
        Path("/Volumes/kernelbuild/src/drivers/regulator/core.c"),
    ]
    core = next((c for c in candidates if c.exists()), None)
    failures = []

    if core is None:
        print("SKIP: regulator core.c not found in any candidate path")
        return 0

    src = core.read_text(errors="replace")
    body = function_body(src, "int regulator_force_enable")

    checks = []
    # 1. not mutate open_count
    checks.append(("no open_count-- drain", "open_count--" not in body))
    # 2. no parent supply recursion
    checks.append(("no rdev->supply recursion", "rdev->supply" not in body))
    # 3. no 'while (rdev->open_count' loop
    checks.append(("no while(open_count--) loop", "while" not in body))
    # 4. still physically enables
    checks.append(("calls _regulator_do_enable", "_regulator_do_enable(rdev)" in body))
    # 5. symbol present at all
    checks.append(("symbol defined", "int regulator_force_enable" in src))
    checks.append(("EXPORT_SYMBOL_GPL", "EXPORT_SYMBOL_GPL(regulator_force_enable)" in src))

    for label, ok in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {label}")
        if not ok:
            failures.append(label)

    # consumer.h declaration
    consumer = next((c for c in [
        root / "kernel" / "s10plus" / ".build" / "src" / "include" / "linux" / "regulator" / "consumer.h",
        Path("/Volumes/kernelbuild/src/include/linux/regulator/consumer.h"),
    ] if c.exists()), None)
    if consumer is not None:
        ch = consumer.read_text(errors="replace")
        ok = "int regulator_force_enable(struct regulator *regulator);" in ch
        print(f"  [{'PASS' if ok else 'FAIL'}] consumer.h declaration")
        if not ok:
            failures.append("consumer.h declaration")
    else:
        print("  [WARN] consumer.h not found; skipping declaration check")

    # call sites
    for label, path, needle in [
        ("ssp_sysfs.c set_mcu_power uses force_enable",
         "drivers/sensorhub/brcm/ssp_sysfs.c",
         "regulator_force_enable(data->regulator_vdd_mcu_1p8)"),
        ("ssp_bbd.c bring-up uses force_disable+force_enable",
         "drivers/sensorhub/brcm/ssp_bbd.c",
         "regulator_force_enable(data->regulator_vdd_mcu_1p8)"),
    ]:
        f = next((c for c in [
            root / "kernel" / "s10plus" / ".build" / "src" / path,
            Path(f"/Volumes/kernelbuild/src/{path}"),
        ] if c.exists()), None)
        if f is not None:
            ok = needle in f.read_text(errors="replace")
            print(f"  [{'PASS' if ok else 'FAIL'}] {label}")
            if not ok:
                failures.append(label)
        else:
            print(f"  [WARN] {path} not found; skipping")

    if failures:
        print(f"\nFAIL: {len(failures)} regulator-0029 invariant(s) violated: {failures}")
        return 1
    print("\nPASS: regulator_force_enable() 0029 correction invariants hold")
    return 0


if __name__ == "__main__":
    sys.exit(main())
