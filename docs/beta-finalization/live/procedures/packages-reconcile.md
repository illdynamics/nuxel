# Procedure — reconciling `images/s10plus/packages-manifest.json` against the handset

**Data.** `images/s10plus/packages-manifest.json` (schema `nuxel.packages-manifest/1`)
is the **resolved** Fedora 43 aarch64 set for this image: 11 groups, 50 resolved
packages, `verdict = "resolved"`, `pin_mismatches = []`, every NEVRA attributable
to a specific `repomd.xml` + `primary.xml` payload whose sha256 is recorded under
`source.metadata_provenance[]`.
**Build-time verifier.** `tools/s10plus/a33/verify-packages.py` (installed to
`/usr/local/bin/verify-packages.py` by the `packages-reconcile` group) and the
offline suite `tools/s10plus/a33/tests/test-packages-manifest.py`.
**Device baseline.** 410 installed packages (`rpm -qa | wc -l`), captured in the
live baseline bundle.

The deploy plan stages the **data and the verifier** only. It never runs a package
transaction: a `dnf` transaction needs a repository (network) or a local cache,
changes hundreds of files at once, and its rollback is a different mechanism from
the plan's per-file `.nuxel-rollback`. That is why the group's terminal state for
the transaction is `INSTALL_PROCEDURE_REQUIRED`, not `DEPLOYED_*`.

## 1. Read the device state first (read-only)

```sh
rpm -qa --qf '%{NAME}\n' | sort > /var/tmp/nuxel-rpmqa-before.txt
wc -l < /var/tmp/nuxel-rpmqa-before.txt                 # expect the 410 baseline
rpm -q systemd                                           # must be systemd-258.11-1.fc43.aarch64
cat /etc/nuxel/phone-runtime-status                      # device identity of this boot
```

The **systemd NEVRA is load-bearing**: the carried kernel-4.14 patch
(`libsystemd-shared`, `protected_compat_items[0]`) exists only for
`systemd-258.11-1.fc43`, so a "helpful" upgrade silently drops the
`posix_spawn`/`PidRef` fix and every unit start returns `ENOSYS`. Treat the pin as
a gate, not a preference.

## 2. Find the verified-missing packages (no transaction yet)

```sh
/usr/local/bin/verify-packages.py --manifest /usr/lib/nuxel/packages-manifest.json \
    --report /var/tmp/nuxel-packages-report.json
python3 -c "import json;d=json.load(open('/var/tmp/nuxel-packages-report.json'));\
print(d.get('verdict'));print(d.get('resolved_count'))"
```

* `verdict=resolved` with the recorded provenance ⇒ the manifest is trustworthy.
* No metadata source available (no cache, no network) ⇒ the verifier answers
  `BLOCKED_EXTERNAL_RESOURCE`. That is the honest verdict: **do not invent
  versions**, and do not install anything from a manifest you could not resolve.

Only packages the report names as missing *and* that an installed consumer needs
may be installed. The KERNEL is excluded unconditionally:

```sh
# the exclusion is part of the command, not a convention
dnf --exclude=kernel,kernel-core,kernel-modules,kernel-modules-extra,kernel-devel \
    install <package>=<NEVRA-from-the-manifest>
```

Never `--skip-broken`, never `--skip-unavailable`, never `--nogpgcheck`: those
flags would turn "this package does not exist" into a silent success, which is the
failure mode `images/s10plus/build-phone-rootfs-fedora.sh` was written to abort on.

## 3. Record the transaction so it can be undone

```sh
dnf history list | head -3                       # capture the transaction id
dnf history info <id>                            # the exact set that changed
rpm -qa --qf '%{NAME}\n' | sort > /var/tmp/nuxel-rpmqa-after.txt
diff /var/tmp/nuxel-rpmqa-before.txt /var/tmp/nuxel-rpmqa-after.txt
```

Rollback of a dnf transaction is `dnf history undo <id>`, executed on the device
with the output captured; it is **not** covered by the per-file rollback route of
`tools/beta/live/deploy-manifest.json`, and that difference is stated in the
group's `rollback` text so nobody assumes the plan will undo a package change.

## 4. Verdicts

| Situation | Verdict |
|---|---|
| Nothing missing, baseline intact | `VERIFIED_ON_S10PLUS` **only** if a fresh on-device `rpm -qa` capture from this session is committed as evidence; otherwise `OFFLINE_TESTED` |
| Packages installed and their consumers observed | `DEPLOYED_UNVERIFIED` until the consumer is seen working |
| Repository/cache unreachable | `BLOCKED_EXTERNAL_RESOURCE` (never a fabricated list) |
| flatpak specifically | `BLOCKED_EXTERNAL_RESOURCE` today (see [nuxtore-and-flatpak.md](nuxtore-and-flatpak.md)) |

A package listed in the manifest is **not** proof that a capability works: the
device may be missing a kernel driver, a firmware blob, or a config the userspace
package never installs. A missing userspace package is equally not proof that a
kernel driver is missing.
