# PWNAGE-52000 — deployment, verification and rollback

## Target / transport

- `root@192.168.178.167` over Wi-Fi SSH.
- Key: `~/.ssh/wicked_wqn_id_rsa` (never printed or copied).
- Host key verified against the existing `known_hosts` entry.
- No TWRP/adb target was present (`adb devices -l` empty), so no BOOT write was
  attempted.

## Backups (on phone)

`/root/pwnage-52000/backup-<UTC>/` contains:

- previous `pwa/nuxel-home`, `pwa/nuxel-apps`, `pwa/nuxel-common`;
- previous `/usr/lib/nuxel/nuxel-bridge`;
- previous `nuxel-metricsd`, `nuxel-navdock`, `nuxel-pwa-host`;
- previous bridge/metrics/charger-recovery units and charger-recovery script;
- previous display/privacy/security configs when present.

## Deployed deltas

| Path | What |
|---|---|
| `/usr/share/nuxel/pwa/nuxel-home/*` | responsive Home, lock privacy, status icons, QS row, GPU labels |
| `/usr/share/nuxel/pwa/nuxel-apps/*` | responsive PWAs, Settings graphics/icons cards |
| `/usr/share/nuxel/pwa/nuxel-common/statusbar-icons.js`, `responsive.css` | shared contracts |
| `/usr/lib/nuxel/nuxel-bridge/{api,bridge,privacy_provider,security_provider}.py` | graphics/privacy/biometric providers |
| `/usr/lib/nuxel/nuxel-metricsd` | kbase `used_pages` + shared-RAM metrics |
| `/usr/lib/nuxel/nuxel-navdock` | fail-closed native dock lock state |
| `/usr/lib/nuxel/nuxel-pwa-host` | real lock-state path, deferred dock restore |
| `/etc/nuxel/display/statusbar-icons.json` | per-icon preference document |
| `/etc/nuxel/privacy/{camera,microphone}.json` | privacy policy documents |
| `/etc/nuxel/security/biometric-unlock.json` | fingerprint-auth policy |
| `/etc/systemd/system/nuxel-metrics.service`, `nuxel-http-bridge.service`, `nuxel-charger-mode-recovery.service` | sandbox/path/recovery gates |
| `/usr/lib/nuxel/nuxel-charger-mode-recovery.sh` | gated one-shot LPM fallback |

## Verification commands

```sh
ssh -i ~/.ssh/wicked_wqn_id_rsa root@192.168.178.167
uname -a
tr ' ' '\n' < /proc/cmdline | grep -E 'androidboot.mode|charging_mode'
grep -c 'Name="sec_touchscreen"' /proc/bus/input/devices
systemctl is-active nuxel-wayland nuxel-wl-fb nuxel-http-bridge nuxel-bridge nuxel-web
curl -s "http://127.0.0.1:8624/metrics?t=$(date +%s)"
curl -s -X POST http://127.0.0.1:8080/api/v1/rpc \
  -H 'Content-Type: application/json' \
  -d '{"app_id":"nuxel-settings","namespace":"graphics","verb":"status","params":{}}'
tail -8 /run/nuxel-navdock.state
cat /run/nuxel/security/lock-state.json
```

## Rollback

1. **PWA/CSS/JS only**: restore the backed-up `pwa/nuxel-home`,
   `pwa/nuxel-apps`, `pwa/nuxel-common` trees and restart the host or reboot.
   Bump/restore `sw.js` cache version if a stale service worker is suspected.
2. **Bridge**: restore `/usr/lib/nuxel/nuxel-bridge` from the backup and
   `systemctl restart nuxel-http-bridge nuxel-bridge`.
3. **Metrics**: restore `/usr/lib/nuxel/nuxel-metricsd` and the old unit, then
   `systemctl daemon-reload; systemctl restart nuxel-metrics.socket`.
4. **Native dock/host**: restore the two binaries and reboot. Do not restart
   `nuxel-wayland` just to roll back CSS.
5. **Privacy configs**: restore the backed-up JSON files; no radio state is
   changed by these files.
6. **LPM fallback**: restore the previous charger-recovery script/unit, or
   `systemctl disable --now nuxel-charger-mode-recovery.service`.
7. **Kernel/BOOT**: not deployed. The prepared patch is in
   `kernel/s10plus/patches/0006-sec-ts-lpm-bind.patch`. If a future flash is
   authorised, use the TWRP gate and the off-device verified BOOT backup; restore
   that image immediately on any boot/touch/display failure.

## Notes

- Phoc and `nuxel-wl-fb` were not restarted to refresh PWA files. A final normal
  reboot (requested by the owner) proved a clean userspace start.
- The device is left locked after verification; native dock is hidden while
  locked by design.
