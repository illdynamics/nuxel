# Procedure — NuXtore and Flatpak on the handset (honest state first)

## The state today

* **flatpak is not installed** on the handset. The device baseline is 410 RPM
  packages and `flatpak` is not among them; `images/s10plus/packages-manifest.json`
  does not request it (its 11 groups cover base/dbus/python/graphics/session/
  webkit/network/connectors/audio/security/power).
* NuXtore is therefore in the state the mission calls honest:
  `IMPLEMENTED_NOT_DEPLOYED` for the in-repository application
  (`pwa/nuxel-apps/nuxtore/` — catalogue browser, ed25519 verification, staged
  bundles) and `BLOCKED_EXTERNAL_RESOURCE` for anything that needs the Flatpak
  runtime. It is **not** `VERIFIED_ON_S10PLUS`, and no capture may claim it is.
* The Flatpak manifests (`pwa/flatpak/org.nuxel.{Home,Calendar,Mail,Platform}.json`,
  `nuxel-launcher.sh`) are repository artefacts for that path; they are named in
  `non_deployable[]` with the `BLOCKED_EXTERNAL_RESOURCE` state and this file as
  their procedure.

## 1. What is already deployable without Flatpak

The NuXtore **PWA** is part of the `pwa-app-suite` group: its `index.html`,
`manifest.json`, `sw.js`, `js/` (catalogue, crypto), `css/`, icons, the catalogue
schemas and the beta development key are staged to the launcher docroot and served
by `nuxel-web`. Reaching the catalogue UI *through the launcher* is a
`DEPLOYED_UNVERIFIED` claim at best until the surface is observed on the glass.

The catalogue **tooling** (`pwa/nuxel-apps/nuxtore/tools/nuxtore-{stage,verify}.py`,
`nuxtore_common.py`, `ed25519_ref.py`) needs a host/device python3 with the
repository's own verifier; it is deliberately not staged onto the phone in this
revision (`INSTALL_PROCEDURE_REQUIRED`) because a signing tool on the device is a
key-handling surface and the mission forbids writing key material.

## 2. Installing Flatpak through the normal package path

Only if the owner wants it, and only with the normal Fedora path — never by
copying a binary in by hand:

```sh
# 1. prove the repository is reachable at all; if not, stop and report
#    BLOCKED_EXTERNAL_RESOURCE rather than guessing
curl -sS -o /dev/null -w '%{http_code}\n' https://dl.fedoraproject.org/pub/fedora/linux/updates/43/Everything/aarch64/repodata/repomd.xml

# 2. install the runtime (KERNEL EXCLUDED: this mission never installs a kernel)
dnf --exclude=kernel,kernel-core,kernel-modules,kernel-modules-extra,kernel-devel \
    install flatpak

# 3. record the transaction so it can be undone
dnf history list | head -3
rpm -qa --qf '%{NAME}\n' | sort > /var/tmp/nuxel-rpmqa-after-flatpak.txt

# 4. the Flatpak remote needs the network too; a remote that cannot be added is
#    the next external-resource block, not a retry loop
flatpak --version
flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
```

Verdicts after step 2: `DEPLOYED_UNVERIFIED` for the package, and the Flatpak
application path stays `BLOCKED_EXTERNAL_RESOURCE` until a network-backed remote
actually serves the runtime. On the 4.14 kernel there is a further, real
limitation to state rather than hide: Flatpak's bubblewrap sandbox depends on
kernel features (user namespaces, mount namespaces) that must be *proven* on this
kernel before any claim is made — `flatpak run` failing is the honest result, and
it is reported as `NOT_SUPPORTED_ON_DEVICE` only with that failure captured.

## 3. Rollback

```sh
dnf history undo <id>          # the transaction id captured in step 3
rpm -q flatpak                 # must report "not installed" again
```

No Flatpak application data is created by this procedure on the device (no
application is installed), so the rollback needs no per-app cleanup. Nothing here
touches a partition, a bootloader, the kernel or the console.
