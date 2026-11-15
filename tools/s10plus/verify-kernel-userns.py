#!/usr/bin/env python3
"""Fail-closed user-namespace gate for the combined S10+ kernel (PWNAGE-SSP).

Measured history this gate exists to prevent from recurring:

* The live kernel advertised CONFIG_USER_NS=y in /proc/config.gz while
  kernel/user_namespace.c had been edited to `ret = -EPERM;` before the upstream
  current_chrooted() check.  create_user_ns() therefore failed for *every*
  caller and Flatpak/bubblewrap could never work.  The claim (config flag) was
  true; the behaviour was not.
* The same edit deleted the CONFIG_LOD_SEC uid gate and turned a vendor
  "block unprivileged userns" policy into "allow everything".

The gate checks three independent things and fails closed:

1. CONFIG_USER_NS=y in the built .config (with NAMESPACES/PID_NS/NET_NS/
   UTS_NS/IPC_NS/SECCOMP/SECCOMP_FILTER/CGROUPS that bubblewrap needs).
2. Source shape: create_user_ns() still contains the upstream
   `if (current_chrooted())` check and no unconditional `ret = -EPERM;`
   immediately preceding it.
3. The opt-in knobs exist in source: kernel.unprivileged_userns_clone registered
   in kernel/sysctl.c and user.max_user_namespaces retained in kernel/ucount.c.

Usage: verify-kernel-userns.py --src kernel/s10plus/.build/src --config OUT/.config
Exit: 0 pass, 1 gate failure, 2 unusable inputs.
"""
from __future__ import annotations

import argparse
import json
import re
import sys

REQUIRED = (
    "CONFIG_MULTIUSER", "CONFIG_NAMESPACES", "CONFIG_USER_NS", "CONFIG_UTS_NS",
    "CONFIG_IPC_NS", "CONFIG_PID_NS", "CONFIG_NET_NS", "CONFIG_SECCOMP",
    "CONFIG_SECCOMP_FILTER", "CONFIG_CGROUPS",
)
REQUIRED_NFT = (
    "CONFIG_NF_TABLES", "CONFIG_NF_TABLES_INET", "CONFIG_NF_TABLES_IPV4",
    "CONFIG_NFT_CT", "CONFIG_NFT_NAT", "CONFIG_NFT_MASQ", "CONFIG_NFT_REJECT",
    "CONFIG_NFT_COMPAT",
)


def read_config(path):
    out = {}
    with open(path, "r", errors="replace") as f:
        for line in f:
            line = line.strip()
            m = re.match(r"^(CONFIG_\w+)=(.*)$", line)
            if m:
                out[m.group(1)] = m.group(2)
                continue
            m = re.match(r"^# (CONFIG_\w+) is not set$", line)
            if m:
                out[m.group(1)] = "n"
    return out


def check_source(src):
    path = f"{src}/kernel/user_namespace.c"
    text = open(path, "r", errors="replace").read()
    failures = []
    if "int create_user_ns(struct cred *new)" not in text:
        failures.append("create_user_ns() not found in kernel/user_namespace.c")
        return failures, {}
    body = text[text.index("int create_user_ns(struct cred *new)"):]
    body = body[: body.find("\n}\n") + 3]
    # 1. the upstream chroot policy check must be intact (called from
    #    create_user_ns()); its inside-the-namespace refinement lives in
    #    fs/namespace.c and must not simply return false.
    if "current_chrooted()" not in body:
        failures.append("upstream current_chrooted() check is missing from create_user_ns()")
    # 2. no unconditional EPERM return before it
    pre = body.split("if (current_chrooted())", 1)[0]
    if re.search(r"^\s*ret\s*=\s*-EPERM;\s*$", pre, re.M):
        failures.append("create_user_ns() contains an unconditional `ret = -EPERM;` "
                        "before current_chrooted()")
    # 3. opt-in knobs
    sysctl = open(f"{src}/kernel/sysctl.c", "r", errors="replace").read()
    if "unprivileged_userns_clone" not in sysctl:
        failures.append("kernel.unprivileged_userns_clone is not registered in kernel/sysctl.c")
    ucount = open(f"{src}/kernel/ucount.c", "r", errors="replace").read()
    if "max_user_namespaces" not in ucount:
        failures.append("user.max_user_namespaces is missing from kernel/ucount.c")
    # 4. Nuxel's PID1 chroots into the Fedora root: current_chrooted() must
    #    accept a chroot that is reachable inside the mount namespace, or
    #    every unprivileged create_user_ns() fails with ENOSPC (measured on
    #    boot #43/#47).  The refinement must not be a blanket "return false".
    ns = open(f"{src}/fs/namespace.c", "r", errors="replace").read()
    i = ns.find("bool current_chrooted(void)")
    if i < 0:
        failures.append("current_chrooted() not found in fs/namespace.c")
    else:
        fn = ns[i: ns.find("\n}\n", i) + 3]
        if "is_path_reachable" not in fn:
            failures.append("current_chrooted() lacks the Nuxel reachable-chroot "
                            "refinement (unprivileged userns would ENOSPC)")
    facts = {
        "user_namespace_sha256": __import__("hashlib").sha256(text.encode()).hexdigest(),
        "has_chroot_check": "if (current_chrooted())" in body,
        "has_unconditional_eperm": bool(re.search(r"^\s*ret\s*=\s*-EPERM;\s*$", pre, re.M)),
        "has_clone_sysctl": "unprivileged_userns_clone" in sysctl,
        "has_max_user_namespaces": "max_user_namespaces" in ucount,
        "has_reachable_chroot_refinement": (
            "is_path_reachable" in open(f"{src}/fs/namespace.c", errors="replace").read()),
    }
    return failures, facts


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--config", required=True)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    try:
        cfg = read_config(a.config)
        failures, facts = check_source(a.src)
    except OSError as e:
        print(f"userns gate: unusable input: {e}", file=sys.stderr)
        return 2
    for k in REQUIRED:
        if cfg.get(k) != "y":
            failures.append(f"{k} is {cfg.get(k, 'missing')}, expected y")
    for k in REQUIRED_NFT:
        if cfg.get(k) != "y":
            failures.append(f"{k} is {cfg.get(k, 'missing')}, expected y (per-app firewalling)")
    result = {"status": "PASS" if not failures else "FAIL", "failures": failures, **facts}
    if a.json:
        print(json.dumps(result, indent=2))
    elif failures:
        for f in failures:
            print(f"userns gate: FAIL: {f}", file=sys.stderr)
    else:
        print("userns gate: PASS — USER_NS + namespace set + nftables are built in, "
              "create_user_ns() keeps the upstream chroot check (with the "
              "reachable-chroot refinement Nuxel's PID1 requires), and the "
              "unprivileged_userns_clone / user.max_user_namespaces knobs exist")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
