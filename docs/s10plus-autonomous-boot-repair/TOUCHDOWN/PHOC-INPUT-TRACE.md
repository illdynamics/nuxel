# PHOC INPUT TRACE — A34

## Current compositor

After the A34 service restart:

* `phoc --no-xwayland -C /etc/nuxel/phoc-phone.ini -E /usr/lib/nuxel/nuxel-session.sh`
* headless output `HEADLESS-1`, configured `720x1520`, scale 2 → 360×760 CSS px
* Wayland socket `/run/nuxel-wayland/wayland-0`
* `nuxel-pwa-host` is a child of phoc and owns the WebKit view.

## Input forwarding

Phoc holds `/dev/input/event2` and `/dev/input/event4`. The physical tap at
10:13:01Z was observed by WebKit as **both** `pointerdown` and `touchstart`, with
the same coordinates. Phoc therefore forwarded the contact as a Wayland touch
event (and WebKitGTK synthesised the compatibility pointer event).

`WAYLAND_DEBUG=1` was not enabled for this capture because it requires a phoc
restart and produces a very large log. The DOM evidence is the decisive
observation: a compositor that did not forward touch could not produce
`wl_touch`-derived `touchstart` in the client.

## Focus / surface

At the time of the tap the active surface was the launcher document
(`w=360 h=760 dpr=2 splash=absent`). The tap hit `DIV#app-icon` for Mail. There
was no invisible splash: `document.getElementById('boot-splash')` was absent
at t+1s, t+4s and t+9s.

## Verdict

T5 **PASS** for the correlated physical tap. No second compositor, no duplicate
framebuffer owner, no launcher rewrite.
