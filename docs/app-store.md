<!-- Nuxel v0.3.1-alpha -->
# Nuxel App Distribution Model

> **Philosophy:** F-Droid principles + Flathub mechanics + GrapheneOS paranoia
> + Linux-native guts — no accounts required, no tracking, no surveillance.

---

## 1. Core Principles

Nuxel's app distribution model is designed to avoid the Linux anti-pattern of
users curling random install scripts from the internet. Every app distributed
for Nuxel must meet strict security, privacy, and transparency requirements.

### 1.1 Ten Commandments of Nuxel Distribution

| # | Principle | Rationale |
|---|-----------|-----------|
| 1 | **Signed packages only** | Every package must carry a signature from a known maintainer or the Nuxel signing key. Unsigned packages are rejected at install time. |
| 2 | **Permission manifests required** | Every app declares exactly what capabilities it needs. Users see the manifest before install, and permission changes are highlighted on update. |
| 3 | **Source links mandatory** | Every package must link to a publicly available source repository. No binary-only packages except when source availability is impossible (and even then, the burden of proof is on the publisher). |
| 4 | **Reproducible build metadata** | Where possible, packages should include build metadata that allows third parties to verify that the binary matches the source. |
| 5 | **Update history visible** | Users can see every published version, its changelog, who signed it, and what permissions changed. |
| 6 | **Maintainer identity tracked** | Every update is attributed to a verified maintainer identity. Anonymous uploads are not permitted for production packages. |
| 7 | **Vulnerability status tracked** | Each package shows whether any known vulnerabilities exist and whether they are patched. |
| 8 | **No account required for free apps** | Users can browse, install, and update free apps without creating an account, logging in, or providing any personal information. |
| 9 | **Permissions shown before install** | The permission manifest is displayed on the app detail page, before the user clicks "Install". |
| 10 | **Easy uninstall with full data wipe** | A single action removes the app, its data directory, its permissions, its desktop entries, cgroup, and network rules. See `nuxel-uninstall-helper.sh`. |

---

## 2. Package Format

### 2.1 Manifest (`nuxel.json`)

Every Nuxel package includes a signed manifest at `<app-id>/nuxel.json`:

```json
{
  "app_id": "org.nuxel.Calendar",
  "version": "1.2.0",
  "release_date": "2026-05-01",
  "maintainer": {
    "name": "Nuxel Core Team",
    "key_fingerprint": "A1B2...C3D4"
  },
  "source": "https://git.nuxel.org/apps/calendar",
  "homepage": "https://nuxel.org/apps/calendar",
  "license": "GPL-3.0-or-later",
  "description": "A full-featured calendar application for Nuxel OS.",
  "categories": ["Utility", "Calendar"],
  "permissions": {
    "calendar": {
      "required": true,
      "description": "Access your calendar to read and manage events",
      "risk": "medium"
    },
    "notifications": {
      "required": true,
      "description": "Send event reminders",
      "risk": "low"
    }
  },
  "sandbox": {
    "network": false,
    "home_dir": false,
    "devices": [],
    "session_bus": ["org.freedesktop.DBus"],
    "system_bus": ["org.nuxel.Portal"]
  },
  "signed_with": "nuxel-org-2026",
  "signature": "base64-encoded-signature..."
}
```

### 2.2 Package types

| Type | Format | When used |
|------|--------|-----------|
| **Nuxel native** | `.nuxel` (tar.xz + manifest + signature) | System apps, native GTK apps |
| **Flatpak wrapper** | `.flatpak` | Apps that run inside Flatpak sandbox |
| **PWA manifest** | `.pwa.json` | Progressive Web App (web app wrapper) |

### 2.3 Structure of a `.nuxel` package

```
org.nuxel.Calendar-1.2.0.nuxel/
├── nuxel.json              # Signed manifest
├── bin/
│   └── nuxel-calendar      # Main binary
├── lib/
│   └── libcalendar.so      # Shared libraries (if any)
├── share/
│   ├── applications/
│   │   └── org.nuxel.Calendar.desktop
│   ├── icons/
│   │   └── hicolor/
│   │       ├── 48x48/apps/org.nuxel.Calendar.png
│   │       ├── 128x128/apps/org.nuxel.Calendar.png
│   │       └── scalable/apps/org.nuxel.Calendar.svg
│   ├── glib-2.0/schemas/
│   │   └── org.nuxel.Calendar.gschema.xml
│   └── dbus-1/services/
│       └── org.nuxel.Calendar.service
└── data/
    └── default-config.json  # Initial config template
```

---

## 3. Repository Structure

### 3.1 Repository metadata

The Nuxel app repository is served from a root URL containing:

```
repository/
├── index.json              # Full index of all available apps
├── index.sig               # Ed25519 signature of index.json
├── apps/
│   ├── org.nuxel.Calendar/
│   │   ├── index.json      # Version history for this app
│   │   ├── icon.png
│   │   ├── screenshot-1.png
│   │   ├── screenshot-2.png
│   │   └── versions/
│   │       ├── 1.0.0.nuxel
│   │       ├── 1.1.0.nuxel
│   │       └── 1.2.0.nuxel
│   └── org.nuxel.Mail/
│       └── ...
├── sources/
│   └── <checksum>.tar.gz   # Cached source tarballs for reproducibility
└── keys/
    ├── maintainers/
    │   ├── A1B2...C3D4.asc  # Maintainer public keys
    │   └── ...
    └── repository.asc       # Repository signing key
```

### 3.2 Repository index format (`index.json`)

```json
{
  "repository": {
    "name": "Nuxel Official Repository",
    "url": "https://repo.nuxel.org/",
    "maintainer": "Nuxel Core Team",
    "key_fingerprint": "E5F6...G7H8",
    "last_updated": "2026-05-10T14:00:00Z",
    "app_count": 28
  },
  "apps": [
    {
      "app_id": "org.nuxel.Calendar",
      "name": "Calendar",
      "summary": "Full-featured calendar with event management",
      "icon": "https://repo.nuxel.org/apps/org.nuxel.Calendar/icon.png",
      "current_version": "1.2.0",
      "license": "GPL-3.0-or-later",
      "maintainer": "Nuxel Core Team",
      "categories": ["Utility", "Calendar"],
      "source": "https://git.nuxel.org/apps/calendar",
      "permission_count": 2,
      "has_update": false,
      "installed": false
    }
  ]
}
```

### 3.3 App index format (`apps/<app-id>/index.json`)

```json
{
  "app_id": "org.nuxel.Calendar",
  "name": "Calendar",
  "summary": "Full-featured calendar with event management",
  "description": "A complete calendar app supporting events, reminders, ...",
  "homepage": "https://nuxel.org/apps/calendar",
  "icon": "icon.png",
  "screenshots": ["screenshot-1.png", "screenshot-2.png"],
  "categories": ["Utility", "Calendar"],
  "license": "GPL-3.0-or-later",
  "source": "https://git.nuxel.org/apps/calendar",
  "donate": "https://nuxel.org/donate",
  "maintainer": {
    "name": "Nuxel Core Team",
    "email": "core@nuxel.org",
    "key_fingerprint": "A1B2...C3D4"
  },
  "versions": [
    {
      "version": "1.2.0",
      "release_date": "2026-05-01",
      "size_bytes": 2456789,
      "checksum": "sha256:abc123...",
      "signature": "base64...",
      "changelog": "Added event reminders. Fixed timezone bug. Updated permissions.",
      "permissions": {
        "calendar": {"required": true, "description": "Access calendar", "risk": "medium"},
        "notifications": {"required": true, "description": "Send reminders", "risk": "low"}
      },
      "vulnerabilities": [
        {"id": "CVE-2026-0123", "status": "fixed", "patched_in": "1.2.0"}
      ]
    },
    {
      "version": "1.1.0",
      "release_date": "2026-04-15",
      "size_bytes": 2400000,
      "checksum": "sha256:def456...",
      "signature": "base64...",
      "changelog": "Added weekly view. Fixed crash on January 1.",
      "permissions": {
        "calendar": {"required": true, "description": "Access calendar", "risk": "medium"},
        "notifications": {"required": true, "description": "Send reminders", "risk": "low"}
      },
      "vulnerabilities": []
    }
  ]
}
```

---

## 4. Permission Diff on Update

When an app updates, the client performs a **permission diff** between the old
and new manifests. The diff is shown to the user before the update proceeds:

```
Update available: Calendar 1.1.0 → 1.2.0

Permission changes:
  + network                NEW — Access the internet
  - phone_status           REMOVED

  ⚠  This update adds 1 new permission. Review carefully.
```

If a permission is downgraded or removed, the update proceeds silently.
If a permission is added or upgraded (e.g., low→medium→high risk), the user
must explicitly approve.

If the app's signing key changes, the update is blocked and the user is
notified.

---

## 5. Security Model

### 5.1 Signing hierarchy

```
Nuxel Root CA (offline, hardware token)
├── Repository signing key (online)
│   └── App version signatures
├── Maintainer signing key
│   └── App version signatures
└── Emergency rollback key (offline, geographically separate)
```

- Every package is signed by at least the repository key.
- Optionally co-signed by the maintainer's personal key.
- Root CA is kept offline and only used for key rotation.
- Emergency rollback key allows revoking compromised repository keys.

### 5.2 Verification chain

```
1. Fetch repository index          → Verify index.sig against repository public key
2. Fetch app index                 → Verify signature in app index
3. Download package                → Verify package signature
4. Verify package checksum         → SHA-256 match
5. Verify maintainer key           → Cross-reference with maintainer fingerprint in package
```

### 5.3 Reproducible builds

Where possible, Nuxel encourages reproducible builds. The repository may
include:

- **Build manifest**: Docker image hash, build command, environment variables.
- **Source archive**: A `.tar.gz` of the exact source used for the build.
- **Build log**: Anonymized build log for transparency.
- **Attestations**: Independent rebuild attestations from third parties.

The build metadata is displayed in the app detail view under "Reproducibility":

```
Reproducibility: Verified by 2 independent builders
  Builder 1: hash matches (2026-05-01)
  Builder 2: hash matches (2026-05-01)
```

---

## 6. User Experience

### 6.1 Browsing apps

- No user account required
- Browse by category, search, or view recommended apps
- Each app shows: name, icon, description, permission summary, license, maintainer, version history
- Permission manifest displayed prominently — before install, not after

### 6.2 Installation flow

```
1. Browse/search → Select app → View app detail page
2. Review permission manifest
3. Check vulnerability status
4. Click "Install"
5. Package downloaded, verified, signed, extracted
6. Desktop entry installed, icon cache updated
7. App appears in Phosh app grid
```

### 6.3 Update flow

```
1. Background check: repository index vs. installed versions
2. If update available: fetch new manifest, compute permission diff
3. If permission added: show diff, request approval
4. If permission unchanged or reduced: update silently
5. Download, verify, install new version
```

### 6.4 Uninstall flow

```
1. Select app → Click "Uninstall"
2. Confirmation dialog with list of what will be removed
3. Run nuxel-uninstall-helper.sh <app-id>
4. App, data, permissions, desktop entries, cgroup, nftables rules all removed
5. "Uninstall complete" with verification result
```

---

## 7. Privacy-Respecting Paid Apps (Future)

The current distribution model is entirely free and account-free. A future path
for paid apps will be designed with privacy as a requirement:

- No tracking of which free apps users install or browse
- For paid apps: anonymous purchase tokens (not user accounts)
- No phone-home telemetry
- Purchases use privacy-preserving payment methods (e.g., Stripe without
  storing customer data, or cryptocurrency)
- Maintainers receive payment without seeing user identities
- Users can verify that paid app downloads match published checksums

---

## 8. Comparison with Existing Models

| Feature | Nuxel | F-Droid | Flathub | Google Play | Apple App Store |
|---------|-------|---------|---------|-------------|-----------------|
| No account required | ✅ | ✅ | ✅ | ❌ | ❌ |
| Permission manifest per app | ✅ | ✅ | ✅ | ✅ | ✅ |
| Permission diff on update | ✅ | ❌ | ❌ | ❌ | ❌ |
| Full source links | ✅ | ✅ | ❌ | ❌ | ❌ |
| Reproducible build metadata | ✅ | ✅ | ❌ | ❌ | ❌ |
| Vulnerability tracking | ✅ | ❌ | ❌ | ❌ | ❌ |
| Signed packages | ✅ | ✅ | ✅ | ✅ | ✅ |
| Maintainer identity tracked | ✅ | ✅ | ❌ | ❌ | ❌ |
| No telemetry | ✅ | ✅ | ❌ | ❌ | ❌ |
| Uninstall with data wipe | ✅ | ❌ | ✅ | ❌ | ❌ |
| Network isolation per app | ✅ | ❌ | ❌ | ❌ | ❌ |
| No tracking SDK requirement | ✅ | ✅ | ❌ | ❌ | ❌ |

---

## 9. Relationship to the Design Document

This distribution model maps directly to **Section 7 (App Distribution)** of the
Nuxel design document (`nuxel-linux-phone-design.md`):

> *"Nuxel needs an app store/repository model that avoids the Linux anti-pattern
> of users curling random install scripts."*

The model implements the design document's requirements:

- ✅ Signed packages and signed metadata
- ✅ Permission manifests
- ✅ Source links and reproducible build metadata where possible
- ✅ Update history and maintainer identity
- ✅ Vulnerability status
- ✅ No account required for free apps
- ✅ Privacy-respecting paid app path (future)
- ✅ Permission changes visible on update
- ✅ Easy uninstall and full data wipe

---

## 10. References

- F-Droid Repository Specification: <https://f-droid.org/en/docs/Repository_Specification/>
- Flatpak Sandbox Permissions: <https://docs.flatpak.org/en/latest/sandbox-permissions.html>
- GrapheneOS Approach to App Isolation: <https://grapheneos.org/features>
- Debian Reproducible Builds: <https://reproducible-builds.org/>
- Signify (package signing): <https://github.com/aperezdc/signify>
- The Update Framework (TUF): <https://theupdateframework.io/>
- Nuxel Design Document: `nuxel-linux-phone-design.md`
- Nuxel Uninstall Helper: `shell/nuxel-shell/nuxel-uninstall-helper.sh`
