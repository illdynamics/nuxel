# A55 Pwnage 4000 — Final Status

## Gate summary (honest, evidence-backed)
| Gate | Result |
|---|---|
| WIFI-L2 / WIFI-IP | **PASS_INTEGRATION** (association, IP, route, DNS, HTTPS 200) |
| WIFI-PERSIST (cold boot) | NOT_TESTED (owner-approved reboot required) |
| NUXEL-BROWSER (google.nl top-level WebKitGTK) | **PASS_INTEGRATION** (finished load + real WebProcess + rendered frame) |
| NUXEL-BROWSER (OSK typing/scroll/back-fwd by hand) | NOT_TESTED (owner hands-on) |
| ROT-MENU | PASS_INTEGRATION (7 modes, no undefined, persistence) |
| ROT-FORCED | PARTIAL (policy correct; wlr-randr transform backend absent) |
| ROT-AUTO | BLOCKED_HARDWARE (no IIO gravity source) |
| STATUS | PASS_INTEGRATION (collision detector: 0 overlaps) |
| BATTERY | PASS_INTEGRATION (numeric percent, full-vs-charging correct) |
| CAMERA-NUXEL | PASS_INTEGRATION (A54 app + media store live) |
| CAMERA-NATIVE (Snapshot) | BLOCKED_EXTERNAL_RESOURCE (no package manager) |
| CAMERA-FRAMES | BLOCKED_HARDWARE (FIMC-IS ENOTTY) |
| FIREFOX / CHROMIUM / CHROME / LADYBIRD | BLOCKED_EXTERNAL_RESOURCE (no dnf/flatpak; no toolchain) |
| GUI-APP-REGISTRY | PARTIAL (native browser desktop entry staged; Home tap-through NOT_TESTED) |
| RECOVERY | PASS (USB console + all units healthy after hot reload) |

## Changed paths (this cycle)
- `shell/nuxel-browser-native/nuxel_browser_native.py` (new, deployed + verified)
- `shell/nuxel-browser-native/org.nuxel.BrowserNative.desktop` (new, deployed)
- `shell/nuxel-browser-native/README.md`
- `docs/a55-pwnage-4000/*` (evidence)

## Rollback
- Browser: `rm /usr/lib/nuxel/nuxel-browser-native/nuxel_browser_native.py` +
  `/usr/share/nuxel/applications/org.nuxel.BrowserNative.desktop`; the iframe
  PWA remains untouched. No service restart required (native app is launch-on-demand).

## Non-negotiable honesty
No hardware camera frames, no functioning Ladybird, and no physical-touch PASS
are claimed. Firefox/Chromium/Chrome/Snapshot installs are blocked by the absent
on-device package manager, not by silent omission.
