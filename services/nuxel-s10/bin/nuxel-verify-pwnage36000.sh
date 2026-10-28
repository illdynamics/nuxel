#!/bin/sh
# Read-only PWN36000 verification.  Avoids aplay/amixer: opening the MADERA
# mixer can block in rpm_resume on this kernel.
set -u
ok=0; bad=0
chk() { if eval "$2" >/dev/null 2>&1; then echo "OK   $1"; ok=$((ok+1)); else echo "FAIL $1"; bad=$((bad+1)); fi; }

echo "== kernel / Bluetooth =="
zcat /proc/config.gz 2>/dev/null | grep -q '^CONFIG_BT_HCIUART=y$' && echo "OK   CONFIG_BT_HCIUART=y" || { echo "FAIL CONFIG_BT_HCIUART"; bad=$((bad+1)); }
hciconfig 2>/dev/null | grep -q 'UP RUNNING' && echo "OK   hci0 UP RUNNING" || { echo "FAIL hci0"; bad=$((bad+1)); }
systemctl is-active --quiet bluetooth && echo "OK   bluetooth active" || { echo "FAIL bluetooth"; bad=$((bad+1)); }

echo "== Wi-Fi =="
ip -4 -brief addr show wlan0 2>/dev/null | grep -q 'UP' && echo "OK   wlan0 up: $(ip -4 -brief addr show wlan0 | awk '{print $3}')" || { echo "FAIL wlan0"; bad=$((bad+1)); }
systemctl is-enabled --quiet nuxel-wifi && echo "OK   nuxel-wifi enabled" || { echo "FAIL nuxel-wifi enabled"; bad=$((bad+1)); }

echo "== Audio =="
pgrep -x pipewire >/dev/null && echo "OK   pipewire running" || { echo "FAIL pipewire"; bad=$((bad+1)); }
pgrep -x pipewire-pulse >/dev/null && echo "OK   pipewire-pulse running" || echo "WARN pipewire-pulse not running"
pgrep -x wireplumber >/dev/null && echo "OK   wireplumber running" || { echo "FAIL wireplumber"; bad=$((bad+1)); }
echo "     $(cat /run/nuxel-audio-route.state 2>/dev/null || echo 'route state unavailable')"
echo "     $(grep -c '^ *[0-9]' /proc/asound/cards 2>/dev/null || echo 0) ALSA card(s)"

echo "== Location =="
systemctl is-active --quiet geoclue && echo "OK   geoclue active" || { echo "FAIL geoclue"; bad=$((bad+1)); }
grep -q '^\[wifi\]' /etc/geoclue/geoclue.conf 2>/dev/null && echo "OK   geoclue Wi-Fi source configured" || echo "WARN geoclue config"
echo "     $(/usr/local/bin/nuxel-gps-status 2>/dev/null | tr '\n' ' ')"

echo "== Preload cinema =="
if [ -f /run/nuxel/preload-cinema.receipt ]; then
    grep -q '"verdict": "PLAYED"' /run/nuxel/preload-cinema.receipt && echo "OK   preload receipt PLAYED" || echo "WARN preload verdict: $(grep -o '"verdict": *"[^"]*"' /run/nuxel/preload-cinema.receipt | head -1)"
else
    echo "FAIL preload receipt missing"; bad=$((bad+1))
fi
[ -e /etc/systemd/system/multi-user.target.wants/nuxel-preload-cinema.service ] && { echo "FAIL preload systemd unit still enabled"; bad=$((bad+1)); } || echo "OK   preload systemd unit disabled"
[ -f /run/nuxel-preload-session.owner ] && echo "OK   session owns preload overlay" || echo "WARN session owner marker missing"

echo "== udev / charger / ssh =="
for r in 90-nuxel-s10.rules 90-nuxel-audio.rules 90-nuxel-bluetooth.rules 99-bluetooth.rules; do
    [ -e "/etc/udev/rules.d/$r" ] && { echo "FAIL udev rule present: $r"; bad=$((bad+1)); } || echo "OK   udev rule absent: $r"
done
systemctl is-enabled --quiet nuxel-charger-mode-recovery && echo "OK   charger-mode recovery enabled" || { echo "FAIL charger-mode recovery"; bad=$((bad+1)); }
[ -s /root/.ssh/authorized_keys ] && echo "OK   root authorized_keys present" || echo "WARN root authorized_keys missing"
grep -qF "$(cat /usr/lib/nuxel/stage36000/ssh/wicked_wqn_id_rsa.pub 2>/dev/null)" /home/nuxel/.ssh/authorized_keys 2>/dev/null && echo "OK   wicked_wqn key authorized for nuxel" || echo "WARN nuxel key check"

echo "== zsh =="
command -v zsh >/dev/null && echo "OK   zsh: $(zsh --version)" || { echo "FAIL zsh missing"; bad=$((bad+1)); }
[ -r /usr/lib/nuxel/zsh/nuxel.zsh ] && echo "OK   nuxel zsh runtime" || { echo "FAIL nuxel zsh runtime"; bad=$((bad+1)); }
command -v nuxel-theme >/dev/null && echo "OK   nuxel-theme: $(nuxel-theme 2>/dev/null | head -1)" || { echo "FAIL nuxel-theme"; bad=$((bad+1)); }
grep -q '# >>> nuxel-zsh >>>' /etc/zshrc 2>/dev/null && echo "OK   /etc/zshrc sources nuxel.zsh" || { echo "FAIL /etc/zshrc block"; bad=$((bad+1)); }

echo "== stuck I/O =="
n=$(ps -eo state= | grep -c '^D' || true)
echo "     D-state tasks: $n (vendor ABox/rpm_resume tasks may remain until reboot)"
echo
echo "PWN36000 verification: $ok OK, $bad FAIL"
[ "$bad" -eq 0 ]
