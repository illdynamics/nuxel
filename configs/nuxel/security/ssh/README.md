# Nuxel Tri-Link SSH policy (NUXEL-26000)

These files are host-side sources for the phone's key-only SSH console. They are
applied by the transactional deploy tool, not by hand:

```bash
sudo -n -u wicked -g dialout -- python3 tools/beta/live/nuxel-live-deploy.py \
  --manifest tools/beta/live/nuxel-ssh-provision-manifest.json \
  --name tri-link-ssh-apply --dev /dev/ttyACM0 --apply --timeout 30 \
  --lock-wait 30 --reconnect-timeout 180
```

| File | Target on the phone | Purpose |
|---|---|---|
| `50-nuxel-a74-recovery.conf` | `/etc/ssh/sshd_config.d/50-nuxel-a74-recovery.conf` | preserves the existing root key, removes the previous unrestricted `AllowUsers root` |
| `60-nuxel-tri-link.conf` | `/etc/ssh/sshd_config.d/60-nuxel-tri-link.conf` | key-only auth, CIDR-restricted `AllowUsers`, bounded auth timeouts, no forwarding/tunnels |
| `authorized_keys.nuxel` | `/home/nuxel/.ssh/authorized_keys` | public key for the dedicated `nuxel` owner console |
| `known_hosts` | host only | pinned Ed25519 host key under `HostKeyAlias nuxel-s10plus` |
| `known_hosts.fingerprint` | host only | the fingerprint an operator can compare |

The private key is **not** in the repository. The working host key is
`~/.ssh/nuxel-tri-link_ed25519` (mode 0600). To generate a replacement:

```bash
python3 tools/beta/live/nuxel-live-ssh.py --init-key
# put the printed public key in authorized_keys.nuxel, deploy, then:
python3 tools/beta/live/nuxel-live-ssh.py --transport wlan --host PHONE_IP --trust-host-key
```

`--trust-host-key` is the only way a new host key is pinned; it prints the
fingerprint first and refuses to overwrite an existing different key. Ordinary
connections always use `StrictHostKeyChecking=yes`, `UserKnownHostsFile` set to
the pinned file and `HostKeyAlias=nuxel-s10plus`.

Password, keyboard-interactive and blank-password login are disabled. Root key
login remains available only from the local WLAN (`10.20.30.0/24`), the reserved
USB subnet (`10.15.19.0/24`) and loopback. The live image has no nft/iptables
binary, so the CIDR restriction is enforced by `sshd` itself; do not replace it
with a wildcard `AllowUsers` entry and do not port-forward 22 from the Internet.
