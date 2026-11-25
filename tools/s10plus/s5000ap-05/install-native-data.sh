#!/bin/bash
# Install the physically recovered S5000AP data runtime, without resetting CP.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
[[ $(id -u) -eq 0 ]] || { echo 'requires root' >&2; exit 1; }
rpm -q systemd-resolved tayga >/dev/null
[[ -x /usr/libexec/nuxel/nuxel-radiod && -d /sys/class/net/rmnet0 ]]
backup=$(mktemp -d /var/lib/nuxel/native-data-install.XXXXXX)
gcc -O2 -Wall -Wextra -Werror -shared -fPIC "$here/src/socket_compat.c" -o "$backup/socket-compat.so"
paths=(/usr/libexec/nuxel/nuxel-cellular-link /usr/libexec/nuxel/cellular_link.py
       /usr/libexec/nuxel/cellular_clat.py /etc/systemd/system/nuxel-cellular-clat.service
       /etc/systemd/system/nuxel-cellular-compat.service
       /etc/systemd/system/nuxel-cellular-lock.service
       /usr/lib/nuxel/libnuxel-resolved-socket.so
       /etc/systemd/system/systemd-resolved.service.d/60-nuxel-socket.conf
       /etc/systemd/system/nuxel-radiod.service.d/30-native-data.conf
       /etc/systemd/resolved.conf.d/60-nuxel-kernel.conf
       /etc/NetworkManager/conf.d/60-nuxel-resolved.conf /etc/resolv.conf)
printf '%s\n' "${paths[@]}" > "$backup/paths.list"
for file in "${paths[@]}"; do
    if [[ -e "$file" || -L "$file" ]]; then
        mkdir -p "$backup$(dirname "$file")"
        cp -a "$file" "$backup$file"
    fi
done
cat > "$backup/rollback.sh" <<'ROLLBACK'
#!/bin/bash
set -euo pipefail
backup=$(cd "$(dirname "$0")" && pwd)
while IFS= read -r path; do
    rm -f "$path"
    if [[ -e "$backup$path" || -L "$backup$path" ]]; then cp -a "$backup$path" "$path"; fi
done < "$backup/paths.list"
systemctl daemon-reload
systemctl restart systemd-resolved
nmcli general reload conf,dns-full
ROLLBACK
chmod 0700 "$backup/rollback.sh"
trap '"$backup/rollback.sh"' ERR
install -m 0755 "$here/scripts/cellular_link.py" /usr/libexec/nuxel/nuxel-cellular-link
install -m 0644 "$here/scripts/cellular_link.py" /usr/libexec/nuxel/cellular_link.py
install -m 0644 "$here/scripts/cellular_clat.py" /usr/libexec/nuxel/cellular_clat.py
install -m 0644 "$here/nuxel-cellular-compat.service" /etc/systemd/system/nuxel-cellular-compat.service
install -m 0644 "$here/nuxel-cellular-clat.service" /etc/systemd/system/nuxel-cellular-clat.service
install -m 0644 "$here/nuxel-cellular-lock.service" /etc/systemd/system/nuxel-cellular-lock.service
install -m 0755 "$backup/socket-compat.so" /usr/lib/nuxel/libnuxel-resolved-socket.so
mkdir -p /etc/systemd/system/systemd-resolved.service.d
cat > /etc/systemd/system/systemd-resolved.service.d/60-nuxel-socket.conf <<'CONF'
[Service]
# Translate an unsupported index binding into an equivalent name binding.
Environment=LD_PRELOAD=/usr/lib/nuxel/libnuxel-resolved-socket.so
CONF
mkdir -p /etc/systemd/system/nuxel-radiod.service.d /etc/systemd/resolved.conf.d /etc/NetworkManager/conf.d
cat > /etc/systemd/system/nuxel-radiod.service.d/30-native-data.conf <<'CONF'
[Unit]
Requires=systemd-resolved.service
After=systemd-resolved.service
[Service]
# Recovered historical tuple. Attach selector and preferred mode changed
# together during recovery; their individual causal effects are not isolated.
Environment=NUXEL_ATTACH_FLAG=1
Environment=NUXEL_PROTO=ipv4
Environment=NUXEL_NETWORK_MODE=lte
Environment=NUXEL_REATTACH_IA=0
CONF
cat > /etc/systemd/resolved.conf.d/60-nuxel-kernel.conf <<'CONF'
[Resolve]
# The service-scoped compatibility library preserves interface binding.
DNSStubListener=yes
LLMNR=no
MulticastDNS=no
CONF
cat > /etc/NetworkManager/conf.d/60-nuxel-resolved.conf <<'CONF'
[main]
dns=systemd-resolved
rc-manager=symlink
CONF
systemctl daemon-reload
systemctl enable --now systemd-resolved
systemctl restart systemd-resolved
nmcli general reload conf,dns-full
ln -sfn /run/systemd/resolve/stub-resolv.conf /etc/resolv.conf
trap - ERR
echo "Installed. Rollback: $backup/rollback.sh"
echo 'Restart nuxel-radiod explicitly after checking management connectivity.'
