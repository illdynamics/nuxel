// DevMgmt — read-only device and peripheral inspection.
//
// Reads the real paths through the shared sysinfo client, parses them with
// devmgmt-parsers.js and renders them with an explicit source label.  There is
// no write path: every call is `system.read` with mode "read-only", and refusals
// are shown as refusals instead of being hidden.
(function () {
  'use strict';
  var P = window.DevMgmtParsers;
  var S = window.NuxelSysInfo;
  var el = function (id) { return document.getElementById(id); };
  function esc(s) {
    return String(s === null || s === undefined ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }
  function bytes(n) {
    if (n === null || n === undefined) return 'not reported';
    var u = ['B', 'KiB', 'MiB', 'GiB', 'TiB'], i = 0;
    while (n >= 1024 && i < u.length - 1) { n /= 1024; i++; }
    return (i ? n.toFixed(1) : n) + ' ' + u[i];
  }
  function kv(pairs) {
    return '<dl class="kv">' + pairs.map(function (p) {
      return '<dt>' + esc(p[0]) + '</dt><dd>' + (p[2] ? p[1] : esc(p[1])) + '</dd>';
    }).join('') + '</dl>';
  }

  var PATHS = [
    '/proc/version', '/proc/cpuinfo', '/proc/meminfo', '/proc/loadavg', '/proc/uptime',
    '/proc/cmdline', '/proc/asound/cards', '/proc/bus/input/devices', '/proc/self/status',
    '/proc/self/mountinfo', '/proc/sys/kernel/osrelease', '/proc/sys/kernel/randomize_va_space',
    '/etc/os-release', '/sys/kernel/security/lsm',
    '/sys/class/thermal/thermal_zone0/type', '/sys/class/thermal/thermal_zone0/temp',
    '/sys/class/thermal/thermal_zone1/type', '/sys/class/thermal/thermal_zone1/temp',
    '/sys/class/thermal/thermal_zone2/type', '/sys/class/thermal/thermal_zone2/temp',
    '/sys/class/power_supply/battery/capacity', '/sys/class/power_supply/battery/status',
    '/sys/class/power_supply/battery/voltage_now', '/sys/class/power_supply/battery/current_now',
    '/sys/class/power_supply/battery/temp', '/sys/class/power_supply/charger/online',
    '/sys/class/power_supply/usb/online',
    '/sys/class/drm/card0-DSI-1/status', '/sys/class/drm/card0-DSI-1/modes',
    '/sys/class/drm/card0-DSI-1/enabled',
    '/sys/class/graphics/fb0/virtual_size', '/sys/class/graphics/fb0/bits_per_pixel',
    '/sys/class/net/wlan0/address', '/sys/class/net/wlan0/operstate',
    '/sys/class/block/mmcblk0/size', '/sys/class/block/mmcblk0/device/name',
    '/sys/class/block/mmcblk1/size', '/sys/class/block/mmcblk1/device/name',
    '/sys/bus/usb/devices/1-1/product', '/sys/bus/usb/devices/1-1/idVendor',
    '/sys/bus/usb/devices/1-1/idProduct'
  ];

  function render(res) {
    var t = function (p) { return res[p] && res[p].ok ? res[p].text : null; };
    var src = S.sourceLabel(res);
    var badge = el('source-badge');
    var live = /live/.test(src);
    badge.textContent = 'source: ' + src;
    badge.className = 'badge ' + (live ? 'live' : 'sample');
    var note = el('source-note');
    if (!live) {
      var snap = null;
      Object.keys(res).forEach(function (k) { if (res[k].snapshot && !snap) snap = res[k].snapshot; });
      note.className = 'note show';
      note.innerHTML = '<b>Sample snapshot, not a live read.</b> ' +
        esc(snap ? snap.warning : 'The Nuxel bridge/host is not reachable, so this page is showing the bundled offline snapshot.') +
        (snap ? ' Snapshot captured ' + esc(snap.captured) + ' for ' + esc(snap.device) + '.' : '');
    } else {
      note.className = 'note';
    }

    // ---- device ----
    var cpu = P.parseCpuinfo(t('/proc/cpuinfo'));
    var mem = P.parseMeminfo(t('/proc/meminfo'));
    var st = P.parseKernelStatus(t('/proc/self/status'));
    var kern = /Linux version (\S+)/.exec(t('/proc/version') || '');
    var osrel = (t('/etc/os-release') || '').split('\n')
      .filter(function (l) { return /^PRETTY_NAME=/.test(l); })
      .map(function (l) { return l.split('=')[1].replace(/"/g, ''); })[0];
    var parts = Object.keys(cpu.cpuParts).map(function (k) { return cpu.cpuParts[k] + 'x ' + k; }).join(', ');
    el('tab-device').innerHTML =
      '<div class="card"><h3>Kernel &amp; OS</h3>' +
      kv([['kernel release', kern ? kern[1] : 'not reported'],
          ['os release', osrel || 'not reported'],
          ['kernel osrelease', (t('/proc/sys/kernel/randomize_va_space') ? t('/proc/sys/kernel/osrelease') || '' : '').trim() || 'not reported'],
          ['ASLR', (t('/proc/sys/kernel/randomize_va_space') || 'not reported').trim()],
          ['cmdline', (t('/proc/cmdline') || 'not reported').trim()],
          ['uptime', ((t('/proc/uptime') || '').split(' ')[0] || 'not reported') + ' s'],
          ['load average', (t('/proc/loadavg') || 'not reported').trim()]]) +
      '<p class="hint">The ~12 load average on this device is produced by the Samsung vendor kernel threads ' +
      '(TrustZone/RPMB), not by the Nuxel userspace — recorded in the A31 notes.</p></div>' +
      '<div class="card"><h3>SoC</h3>' +
      kv([['hardware', cpu.hardware || 'not reported'],
          ['logical cpus', cpu.processorCount],
          ['cpu parts', parts || 'not reported'],
          ['asimd/neon features', cpu.features.join(' ') || 'not reported']]) + '</div>' +
      '<div class="card"><h3>Memory</h3>' +
      kv([['MemTotal', bytes(mem.totalBytes)], ['MemFree', bytes(mem.freeBytes)],
          ['MemAvailable', bytes(mem.availableBytes)], ['Cached', bytes(mem.cachedBytes)],
          ['SwapTotal', mem.swapTotalBytes === 0 ? '0 (no swap configured)' : bytes(mem.swapTotalBytes)]]) +
      '</div>' +
      '<div class="card"><h3>Security state of this app process</h3>' +
      kv([['uid', st.uid || 'not reported'],
          ['effective capabilities', st.capEff && st.capEff.length ? st.capEff.join(', ') : 'none (unprivileged)'],
          ['bounding set', (st.capBnd || []).length + ' capabilities'],
          ['NoNewPrivs', String(st.noNewPrivs)],
          ['seccomp mode', st.seccomp === '2' ? '2 (filter)' : String(st.seccomp || 'not reported')],
          ['seccomp filters', String(st.seccompFilters || '0')],
          ['LSM modules', (P.parseLsm(t('/sys/kernel/security/lsm')).raw) || 'none reported']]) +
      '<p class="hint">This is what the running process can actually do — not a marketing claim. ' +
      'Linux 4.14 on this SoC has no Landlock and no AppArmor; the enforcement is DAC plus capabilities ' +
      'plus seccomp plus the systemd unit sandbox.</p></div>';

    // ---- display ----
    var drm = P.parseDrm({ 'card0-DSI-1': { status: t('/sys/class/drm/card0-DSI-1/status'),
                                            modes: t('/sys/class/drm/card0-DSI-1/modes'),
                                            enabled: t('/sys/class/drm/card0-DSI-1/enabled') } })[0];
    el('tab-display').innerHTML =
      '<div class="card"><h3>Panel connector</h3>' +
      kv([['connector', drm.connector], ['status', drm.status || 'not reported'],
          ['enabled', drm.enabled || 'not reported'], ['mode', drm.mode || 'not reported']]) + '</div>' +
      '<div class="card"><h3>Framebuffer</h3>' +
      kv([['virtual size', (t('/sys/class/graphics/fb0/virtual_size') || 'not reported').trim()],
          ['bits per pixel', (t('/sys/class/graphics/fb0/bits_per_pixel') || 'not reported').trim()]]) +
      '<p class="hint">DevMgmt never opens /dev/fb0. Closing a framebuffer fd runs decon_release and powers ' +
      'the AMOLED down (measured A21/A24), so display state is read from sysfs only.</p></div>';

    // ---- input ----
    var inputs = P.parseInputDevices(t('/proc/bus/input/devices'));
    var touch = inputs.filter(function (d) { return /touch/i.test(d.name || ''); });
    el('tab-input').innerHTML =
      '<div class="card"><h3>Touchscreen</h3>' +
      (touch.length ? touch.map(function (d) {
        return kv([['name', d.name], ['bus', d.bus], ['vendor:product', d.vendor + ':' + d.product],
                   ['phys', d.phys], ['sysfs', d.sysfs], ['event node', d.eventNode || 'no event handler']]);
      }).join('<hr>') : '<p class="hint">No touch device reported. If the panel is up but the touchscreen is ' +
        'missing from /proc/bus/input/devices, the sec_ts driver did not probe — see the touchscreen pipeline trace.</p>') +
      '<p class="hint">The event node is read from the device itself. Nothing in Nuxel hard-codes ' +
      '<code>event3</code>: the node differs between boot paths (charger mode claimed a different one), which is ' +
      'exactly why the launcher resolves it from sysfs and the libinput path.</p></div>' +
      '<div class="card"><h3>All input devices (' + inputs.length + ')</h3>' +
      '<ul class="reqs">' + inputs.map(function (d) {
        return '<li>' + esc(d.name || d.sysfs) + ' — ' + esc(d.handlers.join(',') || 'no handler') + '</li>';
      }).join('') + '</ul></div>';

    // ---- power ----
    var ps = P.parsePowerSupply({
      battery: { capacity: t('/sys/class/power_supply/battery/capacity'),
                 status: t('/sys/class/power_supply/battery/status'),
                 voltage_now: t('/sys/class/power_supply/battery/voltage_now'),
                 current_now: t('/sys/class/power_supply/battery/current_now'),
                 temp: t('/sys/class/power_supply/battery/temp') },
      charger: { online: t('/sys/class/power_supply/charger/online') },
      usb: { online: t('/sys/class/power_supply/usb/online') } });
    var th = P.parseThermal({
      'cpu0-thermal': (t('/sys/class/thermal/thermal_zone0/temp') || '').trim(),
      'gpu-thermal': (t('/sys/class/thermal/thermal_zone1/temp') || '').trim(),
      'battery-thermal': (t('/sys/class/thermal/thermal_zone2/temp') || '').trim() });
    el('tab-power').innerHTML =
      '<div class="card"><h3>Battery</h3>' +
      kv([['capacity', ps.battery.capacityPercent === null ? 'not reported' : ps.battery.capacityPercent + ' %'],
          ['status', ps.battery.status || 'not reported'],
          ['voltage', ps.battery.voltageV === null ? 'not reported' : ps.battery.voltageV.toFixed(3) + ' V'],
          ['current', ps.battery.currentA === null ? 'not reported' : ps.battery.currentA.toFixed(3) + ' A'],
          ['temperature', ps.battery.celsius === null ? 'not reported' : ps.battery.celsius.toFixed(1) + ' °C'],
          ['charger online', String(ps.charger ? ps.charger.online : 'not reported')],
          ['usb online', String(ps.usb ? ps.usb.online : 'not reported')]]) +
      '<p class="hint">The historical "charger mode" finding: when the phone boots with a cable attached, the ' +
      'boot path could differ. DevMgmt only reports what the power supply class says right now.</p></div>' +
      '<div class="card"><h3>Thermal zones</h3>' +
      (th.length ? '<ul class="reqs">' + th.map(function (z) {
        return '<li>' + esc(z.zone) + ' — ' + (z.celsius === null ? 'not reported' : z.celsius.toFixed(1) + ' °C') + '</li>';
      }).join('') + '</ul>' : '<p class="hint">No thermal zones reported.</p>') + '</div>';

    // ---- storage ----
    var blocks = P.parseBlockDevices({
      mmcblk0: { size: t('/sys/class/block/mmcblk0/size'), name: t('/sys/class/block/mmcblk0/device/name') },
      mmcblk1: { size: t('/sys/class/block/mmcblk1/size'), name: t('/sys/class/block/mmcblk1/device/name') } });
    var mounts = P.parseMounts(t('/proc/self/mountinfo'));
    el('tab-storage').innerHTML =
      '<div class="card"><h3>Block devices</h3>' +
      (blocks.filter(function (b) { return b.sectors !== null; }).length
        ? '<ul class="reqs">' + blocks.map(function (b) {
            return '<li>' + esc(b.device) + ' — ' + (b.gib === null ? 'size unreadable' : b.gib.toFixed(2) + ' GiB') +
              (b.model ? ' · ' + esc(b.model) : '') + '</li>';
          }).join('') + '</ul>'
        : '<p class="hint">No block device sizes reported.</p>') +
      '<p class="hint">mmcblk0 is the internal UFS, mmcblk1 the microSD slot when a card is present. ' +
      'DevMgmt never opens these devices; sizes come from the sysfs <code>size</code> attribute.</p></div>' +
      '<div class="card"><h3>Mounts</h3>' +
      (mounts.length ? '<ul class="reqs">' + mounts.slice(0, 14).map(function (m) {
        return '<li>' + esc(m.mountPoint) + ' — ' + esc(m.fstype || '?') + ' from ' + esc(m.source || '?') +
          (m.options.indexOf('ro') !== -1 ? ' (read-only)' : '') + '</li>';
      }).join('') + '</ul>' : '<p class="hint">mountinfo not readable.</p>') + '</div>' +
      '<div class="card"><h3>Wi-Fi &amp; audio devices</h3>' +
      kv([['wlan0 address', (t('/sys/class/net/wlan0/address') || 'not reported').trim()],
          ['wlan0 operstate', (t('/sys/class/net/wlan0/operstate') || 'not reported').trim()],
          ['ALSA cards', (t('/proc/asound/cards') || 'not reported').trim().split('\n')[0]]]) +
      '<p class="hint">Murata/BCM4375-class Wi-Fi on this board. A registered driver would not be proof of a ' +
      'working link — the Wi-Fi diagnostic is the tool that decides that.</p></div>';

    // ---- usb ----
    el('tab-raw').querySelector('.card').insertAdjacentHTML('afterbegin',
      '<div class="raw" id="usb-block"><h4>/sys/bus/usb/devices/1-1 (live console gadget)</h4><pre>' +
      esc(['product: ' + (t('/sys/bus/usb/devices/1-1/product') || 'not reported'),
           'idVendor: ' + (t('/sys/bus/usb/devices/1-1/idVendor') || 'not reported'),
           'idProduct: ' + (t('/sys/bus/usb/devices/1-1/idProduct') || 'not reported')].join('\n')) +
      '</pre></div>');

    // raw
    var raw = el('raw-lines');
    raw.innerHTML = PATHS.map(function (p) {
      var r = res[p] || {};
      var body = r.ok ? r.text : ('[' + r.source + '] ' + (r.error || 'unavailable'));
      return '<h4>' + esc(p) + ' <span class="badge ' + (r.source === 'live' ? 'live' : 'sample') + '">' +
        esc(r.source) + '</span></h4><pre>' + esc(String(body).slice(0, 2000)) + '</pre>';
    }).join('');

    el('sb-paths').textContent = 'paths: ' + PATHS.length + ' read (' + src + ')';
    el('sb-time').textContent = 'read at ' + new Date().toISOString();
  }

  async function refresh() {
    el('source-badge').textContent = 'source: reading…';
    var res = await S.readMany(PATHS);
    window.__devmgmtLastRead = { at: new Date().toISOString(), result: res };
    render(res);
  }

  document.querySelectorAll('.tab').forEach(function (t) {
    t.addEventListener('click', function () {
      document.querySelectorAll('.tab').forEach(function (x) { x.classList.remove('active'); });
      document.querySelectorAll('.panel').forEach(function (x) { x.classList.remove('active'); });
      t.classList.add('active');
      el('tab-' + t.dataset.tab).classList.add('active');
    });
  });
  el('refresh').addEventListener('click', refresh);
  el('close').addEventListener('click', function () {
    var f = window.frameElement;
    if (f && window.parent !== window && window.parent.NuxelLauncherClose) window.parent.NuxelLauncherClose();
    else if (f && f.parentNode) f.parentNode.removeChild(f);
  });
  el('open-rootcontrol').addEventListener('click', function () {
    var b = window.NuxelBridge;
    if (b && typeof b.call === 'function') b.call('apps', 'launch', { app_id: 'org.nuxel.RootControl' });
    else if (window.parent && window.parent.appRegistry) window.parent.appRegistry.launchApp('org.nuxel.RootControl');
  });

  refresh();
})();
