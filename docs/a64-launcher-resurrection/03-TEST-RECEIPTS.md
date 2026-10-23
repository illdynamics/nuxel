# 03 — Test receipts

All commands ran over the framed, SHA-256-verified USB console.

```
# pre-fix
sha256sum /usr/share/nuxel/nuxel-home/css/launcher.css
  -> e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855  (0 bytes)
curl -s -o /dev/null -w 'CSS=%{http_code} %{size_download}\n' \
  http://127.0.0.1:8000/pwa/nuxel-home/css/launcher.css
  -> CSS=200 0

# apply (push_bytes: stage -> decode -> sha256 readback -> atomic mv)
PUSH {'path': '/usr/share/nuxel/nuxel-home/css/launcher.css',
      'bytes': 12764, 'decoded_sha256': '9d56a005af3bf09e0c31d1869b7c34f071b285676a3cd7184371dd1de18573e3'}
sha256sum /usr/share/nuxel/nuxel-home/css/launcher.css
  -> 9d56a005af3bf09e0c31d1869b7c34f071b285676a3cd7184371dd1de18573e3
curl .../css/launcher.css -> CSS=200 12764

# hot reload (host FIFO), no service/Phoc restart
printf 'screen-on\n' > /run/nuxel-wl-fb.cmd
printf 'action reload-launcher\n' > /run/nuxel-pwa-host.cmd

# post-reload state receipts
NUXEL_HOME_READY uri=http://127.0.0.1:8000/pwa/nuxel-home/index.html?boot=os&v=...
STATUSBAR_OVERLAP_CHECK cells=2 overlaps=none
EVT wallpaper ... decoded=1 natural=941x1672 w=360 h=760 dpr=2
LOCKS[a45.1] gesture=unlock-request ... state=UNLOCKING locked=1 visible=1
EVT unlock reason=host
LOCKS[a45.1] hide ... state=UNLOCKED locked=0 visible=0
EVT unlock:complete gen=1 locked=0 visible=0

# app launch receipts (launcher registry)
LAUNCH app_id=org.nuxel.SnekByte via launcher registry
EVT app:launch id=org.nuxel.SnekByte name=SnekByte
EVT app:lifecycle id=org.nuxel.SnekByte state=ACTIVE
```

No failing tests were skipped to produce a PASS; the only two `JS-warn` lines are
the pre-existing initial `[Bridge] not connected, using mock fallback` race and
the reload-time repeat, both of which recover once the native bridge attaches.
