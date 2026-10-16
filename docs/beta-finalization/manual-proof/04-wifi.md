# Area 4 — Wi-Fi association and data path (S10+ / beyond2lte)

**Status: NEEDS_OWNER_TEST** (repository side: OFFLINE_TESTED).
Owner action required? **Yes** — an association cannot be observed without the
phone, a real access point and (for the PSK) the owner's credential.

**Device truth used by this document.** The Samsung Galaxy S10+ (SM-G975F,
Exynos 9820) carries a Murata/Broadcom **BCM4375-class** Wi-Fi module behind the
Samsung SDIO/PCIe glue. `docs/wifi-bcm4390-status.md` documents the Google Pixel
10 Pro XL **BCM4390** and therefore does **not** apply to this device; none of its
blob names, driver quirks or conclusions are carried over. The S10+ radio state
is unknown until the owner runs this test.

---

## 1. Feature

Wi-Fi bring-up on the S10+ radio: NetworkManager policy
(`configs/networkmanager/10-nuxel-s10plus-wifi.conf`), supplicant parameters
(`configs/networkmanager/wpa_supplicant-s10plus.conf`), a credential-free
connection template
(`configs/networkmanager/nuxel-s10plus-wifi.nmconnection.example`), the
evidence-only diagnostic `tools/s10plus/a33/nuxel-wifi-diag.sh` (also published
as `nuxelctl wifi …`), and the manual association test below.

## 2. Why this matters

Network, time sync (area 5), the browser, NuxTore and every "online" claim in the
beta depend on a working radio. Equally important: the repository must not claim
Wi-Fi works because files exist. The diagnostic therefore reports only what the
live kernel, firmware directory and NetworkManager actually show, and the
terminal verdict for the radio stays `NEEDS_OWNER_TEST` until an association with
a real IPv4 address is observed **on the handset**.

## 3. Preparation

1. Handset powered on, booted into Nuxel, screen unlocked.
2. A 2.4 GHz or 5 GHz access point in range whose **WPA2-PSK** credential the
   owner knows. (Enterprise/WPA3-SAE is out of scope for this test.)
3. Console/SSH access to the handset (USB serial console or the on-device
   terminal app) so `nuxelctl wifi` can be run.
4. Run the zero-cost evidence snapshot first — it decides whether the radio is
   even reachable from Linux before any credential is typed:

   ```sh
   nuxelctl wifi status            # human report + verdict
   nuxelctl wifi status --json     # machine-readable, for the bridge/apps
   nuxelctl wifi firmware          # blob inventory for this radio class
   ```

   If the verdict is `BLOCKED_DRIVER` or `BLOCKED_FIRMWARE`, **stop**: this test
   cannot pass, and the correct next action is the bring-up work described in
   `docs/beta-finalization/system/` (offline, no flashing), not a retry loop.

## 4. Exact action

1. Snapshot the evidence, keeping the output:
   `nuxelctl wifi report > /tmp/wifi-before.txt` (also appended to
   `/var/log/nuxel/wifi-diag.log`).
2. Scan and confirm the AP is visible:
   `nuxelctl wifi scan`  → the SSID must appear with the expected security.
3. Associate, typing the PSK when prompted (the PSK is never written by the
   tool and never stored in the repository):
   `nuxelctl wifi connect "<SSID>"`
4. Re-run the status check and confirm the associated state:
   `nuxelctl wifi status`  → verdict line `ASSOCIATED`.
5. Prove the data path, not just the link:
   `ip -4 addr show dev wlan0` (or the reported ifname) shows an IPv4 address,
   then `getent hosts fedoraproject.org` resolves, then open the Nuxel browser
   and load one page.
6. Leave the radio connected for 10 minutes and re-run `nuxelctl wifi status`
   once more — a link that drops while idle is a different (power-save) failure
   and must be reported as such, not as "Wi-Fi works".
7. Save the evidence: `nuxelctl wifi report` (post-run) plus
   `journalctl -b -u NetworkManager --no-pager | tail -100`.

## 5. Expected result

* `nuxelctl wifi scan` lists the AP with a plausible signal level.
* `nuxelctl wifi connect "<SSID>"` returns success and `nuxelctl wifi status`
  prints `ASSOCIATED` with a non-empty IPv4 address.
* `getent hosts fedoraproject.org` returns an address, and one page loads in the
  browser.
* After 10 idle minutes the link is still associated.

## 6. Failure symptoms (and what each one means)

| Symptom | Meaning |
|---|---|
| Verdict `BLOCKED_DRIVER` — no wireless netdev, no matching module | The Wi-Fi driver/firmware pair is not bound. Kernel-side work (offline), not a user error. |
| Verdict `BLOCKED_FIRMWARE` — netdev or driver present, no candidate blob | Vendor firmware has not been installed into `/lib/firmware`. Deploy the blob (repository-only step), never by flashing a partition. |
| Verdict `BLOCKED_EXTERNAL_RESOURCE` — no `wpa_supplicant` | Nothing on the image can associate; a package-completion issue. |
| Scan sees the AP, connect fails with `Secrets were required` | Wrong PSK or key management (WPA3/802.1X) — retry with WPA2-PSK, no code change. |
| Connects, no IPv4 address | DHCP failure — capture `journalctl -b -u NetworkManager` and the DHCP client log. |
| Connects, drops after minutes | Firmware/power-save problem; capture `dmesg | grep -i -E 'bcmdhd|brcmfmac|wlan'` before touching any config. |
| Scan returns an empty list | Not automatically a failure: regulatory domain, AP band or an idle radio can all explain it. Report as unproven, never as PASS. |

## 7. Diagnostic command / log path

* `nuxelctl wifi status | firmware | scan | report` —
  `tools/s10plus/a33/nuxel-wifi-diag.sh`
* Evidence log: `/var/log/nuxel/wifi-diag.log`
* Kernel side: `dmesg | grep -i -E 'bcmdhd|brcmfmac|dhd|4375|sdio|wlan'`
* NetworkManager: `journalctl -b -u NetworkManager --no-pager | tail -100`
* Offline regression suite: `python3 tools/s10plus/a33/tests/test-wifi-diag.py`
  (five fixtures: no radio / no firmware / no supplicant / no association /
  associated) and `nuxel-wifi-diag.sh selftest`.

## 8. PASS / FAIL

* **PASS** — steps 2–7 all hold, and both the pre- and post-run evidence logs
  plus the NetworkManager journal excerpt are attached to the report.
* **FAIL** — any of: no `ASSOCIATED` verdict, no IPv4 address, no DNS
  resolution, no page load, or the link drops while idle. Record the exact
  verdict string from `nuxelctl wifi status`; the verdict names the layer, and a
  verdict is what the repair cycle needs — not a screenshot.

## 9. Reconnection across a normal reboot (acceptance, not optional)

Wi-Fi is not accepted on the strength of one successful association: it has to
come back **by itself** after an ordinary reboot. This is the evidence pair
`nuxelctl wifi mark` / `nuxelctl wifi compare` (state records live in
`/var/lib/nuxel/wifi/`, written by `tools/s10plus/a33/nuxel-wifi-diag.sh`).

1. While connected, run `nuxelctl wifi mark`. This records ifname, state, SSID,
   BSSID, IPv4, gateway and the kernel `boot_id`.
2. Perform **one** ordinary reboot (userspace; never a bootloader/recovery mode —
   this mission performs no flashing).
3. Re-run `nuxelctl wifi compare`. It writes the post-reboot record and prints
   one verdict word:

| Verdict | Meaning |
|---|---|
| `PASS` | the same SSID is associated again with an IPv4 address (a different BSSID with the same SSID is reported as a roam and still PASSes) |
| `FAIL` | the radio is not associated after the reboot, re-associated to a different network, or has no IPv4 address |
| `REFUSED` | the boot id did not change — no reboot happened, so the pair proves nothing |
| `INVALID` | the pre-reboot mark was taken while not associated; re-mark while connected |
| `NO_MARKS` | one of the two records is missing |

To judge two existing records without touching live state (what the offline test
does): `nuxelctl wifi compare before.json after.json`.

## 10. No silent cellular fallback

The mission requires that Wi-Fi work is not propped up by mobile data, and that
the repository never implies a working cellular fallback on a device whose
Shannon LTE modem has no upstream ModemManager plugin (briq-08i).

* **Policy audit:** `nuxelctl wifi fallback` scans the NetworkManager profile
  directory for `type=gsm` / `type=cdma` profiles with `autoconnect=true` and
  prints `CELLULAR_FALLBACK=present` (a finding for the owner) or
  `CELLULAR_FALLBACK=absent`. Presence is **not** proof that the modem can
  associate; absence is proof only that no profile on this image can bring one
  up automatically.
* **Behavioural test (owner):** while associated, power the access point off,
  wait 30 s, then run:
  `ip -4 route show default` and `nuxelctl wifi status`.
  Expected: the wlan default route disappears and **no** `wwan*`/`rmnet*`
  default route appears. A mobile-data default route appearing here is a FAIL of
  this area even if a page still loads.

## 11. Native Network Settings feature set (bg-06d append point)

The owner-facing pages are rendered by the Settings app (briq-06d); the facts
they may display come from the read contract in
`configs/networkmanager/nuxel-network-settings.spec.json` (bg-03 owns it). Print
it with `nuxelctl wifi settings-spec`. It covers: radio on/off and rfkill,
available networks (SSID, signal, security, band, channel, BSSID), connect and
disconnect, per-network settings, DNS/resolver, advanced routing, the regulatory
domain and channel occupancy (only when the driver reports survey data — the page
must say "not reported by this driver" otherwise; only regulatory-compliant
controls are offered), reconnection/reboot persistence and the
no-cellular-fallback audit. Nothing in that list may be displayed before its
`read_api` command has produced it, and no SSID/PSK is ever written by Nuxel.

## Current automatic evidence (repository, this build group)

* `tools/s10plus/a33/nuxel-wifi-diag.sh selftest` → 5/5 fixtures PASS
  (`tools/s10plus/a33/tests/fixtures-p3/wifi-*`: no radio / no firmware / no
  supplicant / no association / associated). The "no supplicant" fixture is a
  regression guard: it fails if the tool borrows the *host's* supplicant when it
  is pointed at a faked root.
* `python3 tools/s10plus/a33/tests/test-wifi-diag.py` → all checks PASS
  (verdict logic, NM/wpa config syntax, no-credential check, no-flashing
  invariant, this fragment's field completeness, the mark/compare reconnection
  judgement incl. REFUSED, the no-cellular-fallback audit, host-tool leakage,
  and the bg-06d settings spec).
* Verdict for the live radio: **unknown / not claimed** — default state
  `BLOCKED_FIRMWARE` in
  `configs/nuxel/capabilities/connectivity-time-audio-buttons.json` until an
  association is observed on the handset.
* Owner test registered as `NEEDS_OWNER_TEST` in area 4 of
  `docs/beta-finalization/BETA-MANUAL-PROOF-CHECKLIST.md` (report group).
