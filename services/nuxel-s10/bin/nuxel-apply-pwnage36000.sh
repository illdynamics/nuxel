#!/bin/sh
# Nuxel S10+ PWN36000 staged apply.
#
#   --files-only   install files, keys, udev cleanup and preload ownership
#                  (called synchronously from nuxel-device-permissions.service,
#                  which is ordered Before=nuxel-wayland.service)
#   --services     package install + service enable/restart/verification
#                  (called from a transient unit after the early phase)
#   --all          both (manual/recovery use)
#
# Fail-open: every step logs and continues.  This script never touches the boot
# partition, the kernel, /dev/fb0, or the SSH daemon configuration.
set -u
umask 022
STAGE=${NUXEL_STAGE:-/usr/lib/nuxel/stage36000}
MODE=${1:---all}
LOG=${NUXEL_APPLY_LOG:-/var/lib/nuxel/apply-pwnage36000.log}
BACKUP=${NUXEL_ROLLBACK_DIR:-/var/lib/nuxel/rollback-pwnage36000-$(date +%Y%m%dT%H%M%S)}

mkdir -p /var/lib/nuxel 2>/dev/null || true
say() { printf '%s %s\n' "$(date -u +%FT%TZ 2>/dev/null || date)" "$*" >>"$LOG" 2>/dev/null || true; }
backup() {
    [ -e "$1" ] || return 0
    rel=${1#/}
    mkdir -p "$BACKUP/$(dirname "$rel")" 2>/dev/null || true
    cp -a "$1" "$BACKUP/$rel" 2>/dev/null || true
}
inst() {
    src=$1 dst=$2 mode=${3:-0644}
    if [ ! -f "$src" ]; then say "missing-stage $src"; return 1; fi
    [ -e "$dst" ] && backup "$dst"
    mkdir -p "$(dirname "$dst")" 2>/dev/null || true
    # Atomic replace: do not truncate a script that may be executing (e.g.
    # nuxel-wifi-up.sh during the early boot window).
    tmp="${dst}.nuxel-new.$$"
    cp -f "$src" "$tmp" 2>/dev/null || { say "copy-failed $src -> $dst"; rm -f "$tmp" 2>/dev/null || true; return 1; }
    chmod "$mode" "$tmp" 2>/dev/null || true
    mv -f "$tmp" "$dst" 2>/dev/null || { cp -f "$tmp" "$dst" 2>/dev/null; rm -f "$tmp" 2>/dev/null || true; }
    say "installed $dst"
    return 0
}
remove_file() {
    [ -e "$1" ] || return 0
    backup "$1"
    rm -f "$1" 2>/dev/null || true
    say "removed $1"
}
run() {
    desc=$1; shift
    if command -v timeout >/dev/null 2>&1; then
        timeout 45 "$@" >>"$LOG" 2>&1
    else
        "$@" >>"$LOG" 2>&1
    fi
    rc=$?
    say "$desc rc=$rc"
    return $rc
}

install_ssh_keys() {
    keyfile=$STAGE/ssh/wicked_wqn_id_rsa.pub
    [ -f "$keyfile" ] || { say "ssh-key: staged key missing"; return 0; }
    key=$(tr -d '\r\n' <"$keyfile" 2>/dev/null)
    [ -n "$key" ] || return 0
    for home in /home/nuxel /root; do
        [ -d "$home" ] || continue
        mkdir -p "$home/.ssh" 2>/dev/null || true
        chmod 700 "$home/.ssh" 2>/dev/null || true
        touch "$home/.ssh/authorized_keys" 2>/dev/null || true
        if ! grep -Fq "$key" "$home/.ssh/authorized_keys" 2>/dev/null; then
            printf '%s\n' "$key" >>"$home/.ssh/authorized_keys" 2>/dev/null || true
            say "ssh-key: appended to $home/.ssh/authorized_keys"
        else
            say "ssh-key: already present in $home/.ssh/authorized_keys"
        fi
        chmod 600 "$home/.ssh/authorized_keys" 2>/dev/null || true
        if [ "$home" = /home/nuxel ]; then
            chown -R nuxel:nuxel "$home/.ssh" 2>/dev/null || true
        fi
    done
}

install_zsh_files() {
    z=$STAGE/nuxel-zsh
    [ -d "$z" ] || { say "zsh: stage missing"; return 0; }
    mkdir -p /usr/lib/nuxel/zsh /etc/nuxel /usr/local/bin /etc/profile.d 2>/dev/null || true
    inst "$z/nuxel.zsh" /usr/lib/nuxel/zsh/nuxel.zsh 0644 || true
    inst "$z/nuxel-theme" /usr/lib/nuxel/zsh/nuxel-theme 0755 || true
    inst "$z/nuxel-theme" /usr/local/bin/nuxel-theme 0755 || true
    inst "$z/nuxel-banner" /usr/lib/nuxel/zsh/nuxel-banner 0644 || true
    inst "$z/nuxel-banner.sh" /etc/profile.d/nuxel-banner.sh 0755 || true
    if [ ! -e /etc/nuxel/zsh.conf ]; then
        inst "$z/nuxel-zsh.conf" /etc/nuxel/zsh.conf 0644 || true
    fi
    if [ ! -e /etc/nuxel/banner ]; then
        inst "$z/nuxel-banner" /etc/nuxel/banner 0644 || true
    fi
    if [ -f /etc/zshrc ] && grep -Fq '# >>> nuxel-zsh >>>' /etc/zshrc 2>/dev/null; then
        say "zsh: /etc/zshrc already sources nuxel.zsh"
    else
        [ -f /etc/zshrc ] && backup /etc/zshrc
        {
            printf '\n# >>> nuxel-zsh >>>\n'
            printf '[ -r /usr/lib/nuxel/zsh/nuxel.zsh ] && source /usr/lib/nuxel/zsh/nuxel.zsh\n'
            printf '# <<< nuxel-zsh <<<\n'
        } >>/etc/zshrc 2>/dev/null || true
        say "zsh: appended source block to /etc/zshrc"
    fi
}

install_preload() {
    # Session/controller live in /usr/lib/nuxel; the PWA files are root-owned.
    [ -f "$STAGE/session/nuxel-session.sh" ] && inst "$STAGE/session/nuxel-session.sh" /usr/lib/nuxel/nuxel-session.sh 0755 || true
    [ -f "$STAGE/nuxel-preload-cinema/nuxel-preload-cinema" ] && inst "$STAGE/nuxel-preload-cinema/nuxel-preload-cinema" /usr/lib/nuxel/nuxel-preload-cinema 0755 || true
    [ -f "$STAGE/nuxel-preload-cinema/nuxel-preload-cinema.service" ] && inst "$STAGE/nuxel-preload-cinema/nuxel-preload-cinema.service" /etc/systemd/system/nuxel-preload-cinema.service 0644 || true
    for f in index.html css/style.css js/app.js sw.js; do
        [ -f "$STAGE/pwa/$f" ] && inst "$STAGE/pwa/$f" "/usr/share/nuxel/pwa/nuxel-home/$f" 0644 || true
    done
    # The early session controller owns the one-shot video.  The systemd unit
    # raced it and could write the .done marker before the launcher existed.
    remove_file /etc/systemd/system/multi-user.target.wants/nuxel-preload-cinema.service
    remove_file /etc/systemd/system/sockets.target.wants/nuxel-preload-cinema.service
    remove_file /usr/share/nuxel/pwa/nuxel-home/preload-status.json
    remove_file /usr/share/nuxel/nuxel-home/preload-status.json
    say "preload: session owns the boot overlay; systemd unit disabled"
}

files_only() {
    say "== files-only begin (stage=$STAGE) =="
    install_ssh_keys
    install_zsh_files
    install_preload

    # nuxel-s10 binaries.  The real permissions script is installed under a
    # distinct name because the live path is the early wrapper.
    for f in nuxel-audio-route.sh nuxel-wifi-up.sh nuxel-charger-mode-recovery.sh; do
        [ -f "$STAGE/nuxel-s10/bin/$f" ] && inst "$STAGE/nuxel-s10/bin/$f" "/usr/lib/nuxel/$f" 0755 || true
    done
    [ -f "$STAGE/nuxel-s10/bin/nuxel-device-permissions.sh" ] && \
        inst "$STAGE/nuxel-s10/bin/nuxel-device-permissions.sh" /usr/lib/nuxel/nuxel-device-permissions.sh.real-36000 0755 || true
    # Do not overwrite the wrapper while it is executing this script.  It is
    # installed once during deployment; the staged copy is kept for rollback.
    if ! grep -q "Early boot wrapper" /usr/lib/nuxel/nuxel-device-permissions.sh 2>/dev/null; then
        [ -f "$STAGE/nuxel-s10/bin/nuxel-device-permissions-early-wrapper.sh" ] && \
            inst "$STAGE/nuxel-s10/bin/nuxel-device-permissions-early-wrapper.sh" /usr/lib/nuxel/nuxel-device-permissions.sh 0755 || true
    fi
    [ -f "$STAGE/nuxel-s10/bin/nuxel-audio-status" ] && inst "$STAGE/nuxel-s10/bin/nuxel-audio-status" /usr/local/bin/nuxel-audio-status 0755 || true
    [ -f "$STAGE/nuxel-s10/bin/nuxel-gps-status" ] && inst "$STAGE/nuxel-s10/bin/nuxel-gps-status" /usr/local/bin/nuxel-gps-status 0755 || true
    [ -f "$STAGE/nuxel-s10/bin/nuxel-verify-pwnage36000.sh" ] && \
        inst "$STAGE/nuxel-s10/bin/nuxel-verify-pwnage36000.sh" /usr/local/bin/nuxel-verify-pwnage36000 0755 || true
    for f in "$STAGE"/nuxel-s10/systemd/*.service; do
        [ -f "$f" ] && inst "$f" "/etc/systemd/system/$(basename "$f")" 0644 || true
    done
    [ -f "$STAGE/nuxel-s10/wireplumber/99-nuxel-s10.conf" ] && \
        inst "$STAGE/nuxel-s10/wireplumber/99-nuxel-s10.conf" /etc/wireplumber/wireplumber.conf.d/99-nuxel-s10.conf 0644 || true
    [ -f "$STAGE/nuxel-s10/pipewire/99-nuxel-s10.conf" ] && \
        inst "$STAGE/nuxel-s10/pipewire/99-nuxel-s10.conf" /etc/pipewire/pipewire.conf.d/99-nuxel-s10.conf 0644 || true
    [ -f "$STAGE/nuxel-s10/alsa/99-nuxel-s10-default.conf" ] && \
        inst "$STAGE/nuxel-s10/alsa/99-nuxel-s10-default.conf" /etc/alsa/conf.d/99-nuxel-s10-default.conf 0644 || true
    # The old workaround pointed at RDMA0, which never advances.  Remove it.
    remove_file /etc/alsa/conf.d/99-nuxel-s10-workaround.conf
    [ -f "$STAGE/nuxel-s10/geoclue/geoclue.conf" ] && \
        inst "$STAGE/nuxel-s10/geoclue/geoclue.conf" /etc/geoclue/geoclue.conf 0644 || true
    [ -f "$STAGE/nuxel-s10/dbus/99-geoclue-nuxel.conf" ] && \
        inst "$STAGE/nuxel-s10/dbus/99-geoclue-nuxel.conf" /etc/dbus-1/system.d/99-geoclue-nuxel.conf 0644 || true

    # udevd is masked on this kernel.  Remove the rules that never ran.
    for r in 90-nuxel-s10.rules 90-nuxel-audio.rules 90-nuxel-bluetooth.rules 99-bluetooth.rules; do
        remove_file "/etc/udev/rules.d/$r"
    done
    # Apply the new permission policy immediately on the first boot too.
    [ -x /usr/lib/nuxel/nuxel-device-permissions.sh.real-36000 ] && \
        /usr/lib/nuxel/nuxel-device-permissions.sh.real-36000 >>"$LOG" 2>&1 || true
    say "== files-only done (rollback=$BACKUP) =="
    printf '{"ok":true,"mode":"files-only","rollback":"%s","finished_at":"%s"}\n' \
        "$BACKUP" "$(date -u +%FT%TZ 2>/dev/null || date)" > /var/lib/nuxel/pwnage36000-files.json 2>/dev/null || true
}

services() {
    say "== services begin =="
    if ! command -v zsh >/dev/null 2>&1; then
        say "zsh: installing package"
        if command -v dnf >/dev/null 2>&1; then
            timeout 240 dnf install -y zsh >>"$LOG" 2>&1; say "dnf install zsh rc=$?"
        elif command -v apt-get >/dev/null 2>&1; then
            timeout 240 apt-get install -y zsh >>"$LOG" 2>&1; say "apt-get install zsh rc=$?"
        fi
    fi
    if [ -x "$STAGE/nuxel-zsh/install-nuxel-zsh.sh" ] && command -v zsh >/dev/null 2>&1; then
        run "nuxel-zsh installer" sh "$STAGE/nuxel-zsh/install-nuxel-zsh.sh" --root / --no-package || true
    fi

    run "daemon-reload" systemctl daemon-reload
    run "disable preload unit" systemctl disable nuxel-preload-cinema.service
    run "enable services" systemctl enable bluetooth.service nuxel-bluetooth.service geoclue.service \
        nuxel-wifi.service nuxel-device-permissions.service nuxel-audio-route.service \
        nuxel-charger-mode-recovery.service
    run "rfkill bluetooth" rfkill unblock bluetooth
    run "rfkill wifi" rfkill unblock wifi
    run "restart bluetooth bring-up" systemctl restart nuxel-bluetooth.service
    run "restart bluetooth" systemctl restart bluetooth.service
    run "restart geoclue" systemctl restart geoclue.service
    run "restart wifi" systemctl restart nuxel-wifi.service
    run "start audio route" systemctl start nuxel-audio-route.service
    run "wifi radio" nmcli radio wifi on
    # Make every stored profile autoconnect again after the unit restart.
    nmcli -t -f NAME,TYPE connection show 2>/dev/null | while IFS=: read -r name type; do
        [ "$type" = wifi ] || continue
        nmcli connection modify "$name" connection.autoconnect yes connection.autoconnect-retries 0 >/dev/null 2>&1 || true
    done
    if ! nmcli -t -f DEVICE,STATE device 2>/dev/null | grep -q '^wlan0:connected'; then
        name=$(nmcli -t -f NAME,TYPE,AUTOCONNECT connection show 2>/dev/null | awk -F: '$2=="wifi" && $3=="yes" {print $1; exit}')
        [ -n "${name:-}" ] && run "wifi connect $name" timeout 45 nmcli connection up "$name" || true
    fi
    say "bluetooth: $(hciconfig 2>&1 | head -2 | tr '\n' ' ')"
    say "wifi: $(ip -4 -brief addr show wlan0 2>/dev/null | awk '{print $3}')"
    say "audio: $(nuxel-audio-status 2>&1 | tr '\n' ' ')"
    say "gps: $(nuxel-gps-status 2>&1 | tr '\n' ' ')"
    say "== services done =="
    printf '{"ok":true,"mode":"services","finished_at":"%s"}\n' \
        "$(date -u +%FT%TZ 2>/dev/null || date)" > /var/lib/nuxel/pwnage36000-services.json 2>/dev/null || true
}

case $MODE in
    --files-only) files_only ;;
    --services) services ;;
    --all) files_only; services ;;
    *) echo "usage: $0 [--files-only|--services|--all]" >&2; exit 2 ;;
esac
exit 0
