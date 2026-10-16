#!/usr/bin/env python3
"""pwa-geometry-harness.py — measure the UTM launcher's DOM inside WebKitGTK.

Runs INSIDE the UTM guest (Phosh Wayland session, python3-gi + WebKit2 4.1),
loads http://127.0.0.1:8000/pwa/nuxel-home/index.html and prints, as JSON, the
COMPUTED geometry/style of the launcher's own elements:

  * #app-list   : display, grid-template-columns, row/column gap, item count, order
  * .app-icon   : rect, colour, background, font-size, border-radius, glyph text
  * #dock       : height, background, gap, docked order, dock icon rect
  * #status-bar : height, background, padding
  * body        : background-color and background-image (the wallpaper reference)

This is a numeric comparison basis for the S10+ port — no screenshots, no image
interpretation.  Used by tools/s10plus/a28/verify-utm-consistency.sh.
"""
import json
import os
import sys
import time

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('WebKit2', '4.1')
from gi.repository import Gtk, WebKit2, GLib

PWA_URL = os.environ.get('PWA_URL', 'http://127.0.0.1:8000/pwa/nuxel-home/index.html')

CHECK_JS = r"""
(() => {
  const out = {};
  const cs = el => el ? getComputedStyle(el) : null;
  const rect = el => { const b = el.getBoundingClientRect();
    return {x: +b.x.toFixed(2), y: +b.y.toFixed(2), w: +b.width.toFixed(2), h: +b.height.toFixed(2)}; };
  out.window = {w: window.innerWidth, h: window.innerHeight};
  out.registryCount = (typeof NUXEL_APPS !== 'undefined') ? Object.keys(NUXEL_APPS).length : null;
  out.order = (typeof appRegistry !== 'undefined') ? appRegistry.getAllApps().map(a => a.name) : null;
  out.dockOrder = (typeof appRegistry !== 'undefined') ? appRegistry.getDockedApps().map(a => a.name) : null;
  out.apps = {};
  document.querySelectorAll('.app-item').forEach(el => {
    const icon = el.querySelector('.app-icon');
    const label = el.querySelector('.app-label');
    const c = cs(icon);
    out.apps[el.dataset.appId] = {
      glyph: icon ? icon.textContent.trim() : null,
      name: label ? label.textContent.trim() : null,
      color: c ? c.color : null,
      background: c ? c.backgroundColor : null,
      fontSize: c ? c.fontSize : null,
      radius: c ? c.borderTopLeftRadius : null,
      rect: icon ? rect(icon) : null,
      labelFontSize: label ? cs(label).fontSize : null,
      docked: !!el.closest('#dock-items'),
    };
  });
  const grid = document.querySelector('#app-list');
  const gc = cs(grid);
  const items = [...document.querySelectorAll('#app-list .app-item')];
  out.grid = {display: gc.display, columns: gc.gridTemplateColumns, rowGap: gc.rowGap,
              columnGap: gc.columnGap, padding: gc.padding, itemCount: items.length,
              items: items.map(el => el.dataset.appId),
              rect: rect(grid)};
  const dock = document.querySelector('#dock');
  const dc = cs(dock);
  out.dock = {count: document.querySelectorAll('#dock-items .app-item').length,
              height: rect(dock).h, background: dc.backgroundColor,
              borderTopWidth: dc.borderTopWidth, gap: cs(document.querySelector('.dock-items')).gap,
              y: rect(dock).y,
              items: [...document.querySelectorAll('#dock-items .app-item')].map(el => el.dataset.appId)};
  const bar = document.querySelector('#status-bar');
  const bc = cs(bar);
  out.statusBar = {height: rect(bar).h, background: bc.backgroundColor, padding: bc.padding,
                   fontSize: bc.fontSize};
  const title = document.querySelector('.app-grid-title');
  out.title = {fontSize: cs(title).fontSize, text: title.textContent.trim(),
               backgroundImage: cs(title).backgroundImage};
  const body = cs(document.body);
  out.body = {backgroundColor: body.backgroundColor, backgroundImage: body.backgroundImage,
              backgroundSize: body.backgroundSize};
  window.__pwa_result = JSON.stringify(out);
  window.__pwa_done = true;
  return true;
})(); true;
"""

state = {'result': None, 'loaded': False, 'err': None}


def js(webview, script):
    holder = {}
    loop = GLib.MainLoop()

    def cb(view, res, _ud=None):
        try:
            jres = view.run_javascript_finish(res)
            v = jres.get_js_value()
            holder['val'] = v.to_string() if v else None
        except Exception as e:                                  # noqa: BLE001
            holder['err'] = str(e)
        loop.quit()

    webview.run_javascript(script, None, cb)
    GLib.timeout_add(8000, lambda: (loop.quit(), False)[1])
    loop.run()
    return holder


def main():
    win = Gtk.Window(title='nuxel-launcher-geometry')
    win.set_default_size(440, 940)
    webview = WebKit2.WebView()
    settings = webview.get_settings()
    settings.set_enable_developer_extras(True)
    win.add(webview)
    win.show_all()
    webview.connect('load-changed',
                    lambda w, ev: state.__setitem__('loaded', ev == WebKit2.LoadEvent.FINISHED))
    webview.load_uri(PWA_URL)

    deadline = time.time() + int(os.environ.get('PWA_TIMEOUT_SEC', '90'))
    injected = False
    while time.time() < deadline:
        while Gtk.events_pending():
            Gtk.main_iteration_do(False)
        time.sleep(0.4)
        if state['loaded'] and not injected:
            js(webview, CHECK_JS)
            injected = True
        if injected:
            h = js(webview, 'window.__pwa_done === true ? "DONE" : "PENDING"')
            if h.get('val') == 'DONE':
                break
    res = js(webview, 'window.__pwa_result || "null"')
    state['result'] = res.get('val')
    state['err'] = res.get('err')
    print(json.dumps({'pwa_url': PWA_URL, 'geometry': json.loads(state['result'])
                      if state['result'] and state['result'] != 'null' else None,
                      'eval_error': state['err']}, indent=2, default=str))
    Gtk.main_quit()
    sys.exit(0 if state['result'] and state['result'] != 'null' else 3)


if __name__ == '__main__':
    GLib.timeout_add(500, main)
    Gtk.main()
