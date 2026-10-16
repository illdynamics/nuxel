// DevMgmt parsers — pure functions over real /proc and /sys text.
//
// Every value DevMgmt shows comes from one of these parsers, so the offline test
// suite can pin the exact parsing behaviour (tests/test-parsers.js) and the UI
// cannot invent hardware state: if a parser cannot find a field, the UI shows
// "not reported" instead of a guess.
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.DevMgmtParsers = factory();
}(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  // Linux capability names for the 4.14 capability set (CAP_LAST_CAP = 40).
  var CAPS = ['CHOWN', 'DAC_OVERRIDE', 'DAC_READ_SEARCH', 'FOWNER', 'FSETID', 'KILL', 'SETGID',
    'SETUID', 'SETPCAP', 'LINUX_IMMUTABLE', 'NET_BIND_SERVICE', 'NET_BROADCAST', 'NET_ADMIN',
    'NET_RAW', 'IPC_LOCK', 'IPC_OWNER', 'SYS_MODULE', 'SYS_RAWIO', 'SYS_CHROOT', 'SYS_PTRACE',
    'SYS_PACCT', 'SYS_ADMIN', 'SYS_BOOT', 'SYS_NICE', 'SYS_RESOURCE', 'SYS_TIME', 'SYS_TTY_CONFIG',
    'MKNOD', 'LEASE', 'AUDIT_WRITE', 'AUDIT_CONTROL', 'SETFCAP', 'MAC_OVERRIDE', 'MAC_ADMIN',
    'SYSLOG', 'WAKE_ALARM', 'BLOCK_SUSPEND', 'AUDIT_READ', 'PERFMON', 'BPF', 'CHECKPOINT_RESTORE'];

  function parseMeminfo(text) {
    var out = {};
    (text || '').split('\n').forEach(function (line) {
      var m = /^([A-Za-z_()0-9]+):\s+(\d+)(?:\s+kB)?/.exec(line);
      if (m) out[m[1]] = Number(m[2]);
    });
    var kb = function (name) { return out[name] === undefined ? null : out[name] * 1024; };
    return {
      totalBytes: kb('MemTotal'), freeBytes: kb('MemFree'), availableBytes: kb('MemAvailable'),
      cachedBytes: kb('Cached'), buffersBytes: kb('Buffers'), swapTotalBytes: kb('SwapTotal'),
      raw: out
    };
  }

  function parseCpuinfo(text) {
    var procs = 0, parts = {}, hardware = null, features = null, implementations = {};
    (text || '').split(/\n\n+/).forEach(function (block) {
      if (!/processor/.test(block)) return;
      procs++;
      var p = /CPU part\s*:\s*(\S+)/.exec(block);
      if (p) parts[p[1]] = (parts[p[1]] || 0) + 1;
      var f = /Features\s*:\s*(.+)/.exec(block);
      if (f && !features) features = f[1].trim().split(/\s+/);
      var i = /CPU implementer\s*:\s*(\S+)/.exec(block);
      if (i) implementations[i[1]] = (implementations[i[1]] || 0) + 1;
    });
    var hw = /Hardware\s*:\s*(.+)/.exec(text || '');
    if (hw) hardware = hw[1].trim();
    return { processorCount: procs, cpuParts: parts, features: features || [],
             implementations: implementations, hardware: hardware };
  }

  function parseThermal(entries) {
    // entries: {"cpu0-thermal": "48200", ...} already keyed by type by the caller
    return Object.keys(entries || {}).map(function (type) {
      var milli = Number(String(entries[type]).trim());
      return { zone: type, milliC: isNaN(milli) ? null : milli,
               celsius: isNaN(milli) ? null : milli / 1000 };
    });
  }

  function parsePowerSupply(readings) {
    // readings: { battery: {capacity, status, voltage_now, current_now, temp}, ... }
    var out = {};
    Object.keys(readings || {}).forEach(function (name) {
      var r = readings[name] || {};
      out[name] = {
        online: r.online === undefined ? null : (String(r.online).trim() === '1'),
        capacityPercent: r.capacity === undefined ? null : Number(String(r.capacity).trim()),
        status: r.status ? String(r.status).trim() : null,
        voltageV: r.voltage_now === undefined ? null : Number(r.voltage_now) / 1e6,
        currentA: r.current_now === undefined ? null : Number(r.current_now) / 1e6,
        celsius: r.temp === undefined ? null : Number(r.temp) / 10
      };
    });
    return out;
  }

  function parseInputDevices(text) {
    var devices = [], cur = null;
    (text || '').split('\n').forEach(function (line) {
      var m = /^I:\s+Bus=(\S+)\s+Vendor=(\S+)\s+Product=(\S+)\s+Version=(\S+)/.exec(line);
      if (m) { cur = { bus: m[1], vendor: m[2], product: m[3], version: m[4], name: null,
                       phys: null, sysfs: null, handlers: [] }; devices.push(cur); return; }
      if (!cur) return;
      var n = /^N:\s+Name="(.*)"$/.exec(line); if (n) { cur.name = n[1]; return; }
      var p = /^P:\s+Phys=(\S+)/.exec(line); if (p) { cur.phys = p[1]; return; }
      var s = /^S:\s+Sysfs=(\S+)/.exec(line); if (s) { cur.sysfs = s[1]; return; }
      var h = /^H:\s+Handlers=(\S+)/.exec(line); if (h) { cur.handlers = h[1].split(','); return; }
    });
    devices.forEach(function (d) { d.eventNode = d.handlers.filter(function (x) { return /^event\d+$/.test(x); })[0] || null; });
    return devices;
  }

  function parseLsm(text) {
    var raw = String(text || '').trim();
    return { raw: raw, modules: raw ? raw.split(',') : [],
             landlock: /landlock/.test(raw), apparmor: /apparmor/.test(raw),
             selinux: /selinux/.test(raw), yama: /yama/.test(raw),
             capabilityOnly: raw === 'capability' || raw === 'capability,yama' };
  }

  function parseKernelStatus(text) {
    var get = function (re) { var m = re.exec(text || ''); return m ? m[1].trim() : null; };
    var capHex = get(/CapEff:\s*([0-9a-f]+)/i);
    var bndHex = get(/CapBnd:\s*([0-9a-f]+)/i);
    return {
      uid: get(/Uid:\s*(\S+)/), name: get(/Name:\s*(\S+)/),
      capEffHex: capHex, capBndHex: bndHex,
      capEff: capHex ? decodeCaps(capHex) : null,
      capBnd: bndHex ? decodeCaps(bndHex) : null,
      noNewPrivs: get(/NoNewPrivs:\s*(\d+)/) === '1',
      seccomp: get(/Seccomp:\s*(\d+)/), seccompFilters: get(/Seccomp_filters:\s*(\d+)/)
    };
  }

  function decodeCaps(hex) {
    var value = BigInt('0x' + String(hex).replace(/^0x/i, '') || '0x0');
    var out = [];
    CAPS.forEach(function (name, i) { if ((value >> BigInt(i)) & 1n) out.push('CAP_' + name); });
    return out;
  }

  function parseMounts(text) {
    return (text || '').split('\n').filter(Boolean).map(function (line) {
      var parts = line.split(' ');
      var sep = parts.indexOf('-');
      return { mountPoint: parts[4], source: sep >= 0 ? parts[sep + 2] : null,
               fstype: sep >= 0 ? parts[sep + 1] : null,
               options: (parts[5] || '').split(',') };
    });
  }

  function parseDrm(statuses) {
    // statuses: {"card0-DSI-1": {status, enabled, modes}}
    return Object.keys(statuses || {}).map(function (conn) {
      var d = statuses[conn] || {};
      var mode = d.modes ? String(d.modes).trim().split('\n')[0] : null;
      return { connector: conn, status: d.status ? String(d.status).trim() : null,
               enabled: d.enabled ? String(d.enabled).trim() : null, mode: mode };
    });
  }

  function parseBlockDevices(entries) {
    // entries: {"mmcblk0": {size, name}, ...}
    return Object.keys(entries || {}).map(function (dev) {
      var e = entries[dev] || {};
      var sectors = Number(e.size);
      return { device: dev, model: e.name ? String(e.name).trim() : null,
               sectors: isNaN(sectors) ? null : sectors,
               bytes: isNaN(sectors) ? null : sectors * 512,
               gib: isNaN(sectors) ? null : (sectors * 512) / (1024 * 1024 * 1024) };
    }).sort(function (a, b) { return (b.bytes || 0) - (a.bytes || 0); });
  }

  function summarise(res) {
    res = res || {};
    var text = function (p) { return (res[p] && res[p].ok) ? res[p].text : null; };
    var cpu = parseCpuinfo(text('/proc/cpuinfo'));
    var mem = parseMeminfo(text('/proc/meminfo'));
    var kst = parseKernelStatus(text('/proc/self/status'));
    var lsm = parseLsm(text('/sys/kernel/security/lsm'));
    var inputs = parseInputDevices(text('/proc/bus/input/devices'));
    var touch = inputs.filter(function (d) { return /touch/i.test(d.name || ''); });
    var kern = /Linux version (\S+)/.exec(text('/proc/version') || '');
    return {
      kernel: kern ? kern[1] : null,
      osRelease: (text('/etc/os-release') || '').split('\n')
        .filter(function (l) { return /^PRETTY_NAME=/.test(l); })
        .map(function (l) { return l.split('=')[1].replace(/"/g, ''); })[0] || null,
      soc: cpu.hardware, cores: cpu.processorCount, cpuParts: cpu.cpuParts,
      features: cpu.features.slice(0, 12),
      memory: mem, capabilities: kst.capEff, capabilityBoundingSet: kst.capBnd,
      noNewPrivs: kst.noNewPrivs, seccomp: kst.seccomp,
      lsm: lsm, inputDevices: inputs, touchDevices: touch,
      mounts: parseMounts(text('/proc/self/mountinfo')),
      thermal: parseThermal(res.__thermalTypes || {}),
      asoundCards: text('/proc/asound/cards')
    };
  }

  return {
    CAPS: CAPS,
    parseMeminfo: parseMeminfo, parseCpuinfo: parseCpuinfo, parseThermal: parseThermal,
    parsePowerSupply: parsePowerSupply, parseInputDevices: parseInputDevices,
    parseLsm: parseLsm, parseKernelStatus: parseKernelStatus, decodeCaps: decodeCaps,
    parseMounts: parseMounts, parseDrm: parseDrm, parseBlockDevices: parseBlockDevices,
    summarise: summarise
  };
}));
