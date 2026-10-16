#!/usr/bin/env node
// DevMgmt offline parser tests.        node pwa/nuxel-apps/devmgmt/tests/test-parsers.js
//
// Pins the exact interpretation of real /proc and /sys text against the bundled
// S10+ snapshot, so a change in the UI can never silently change what the tool
// claims the hardware is.
'use strict';
const fs = require('fs');
const path = require('path');
const P = require(path.join(__dirname, '..', 'js', 'devmgmt-parsers.js'));

let pass = 0, fail = 0;
function check(name, cond, detail) {
  if (cond) { pass++; console.log('  PASS ' + name); }
  else { fail++; console.log('  FAIL ' + name + (detail !== undefined ? '  — ' + detail : '')); }
}
function near(a, b, eps) { return Math.abs(a - b) < (eps || 0.05); }

const snap = JSON.parse(fs.readFileSync(
  path.join(__dirname, '..', '..', '_shared', 'samples', 'sys-snapshot.json'), 'utf8'));
const f = snap.files;

check('snapshot is explicitly labelled as a non-live sample',
      snap.kind === 'sample-snapshot' && /NOT a live read/.test(snap.warning));

const cpu = P.parseCpuinfo(f['/proc/cpuinfo']);
check('cpuinfo: 8 logical processors found', cpu.processorCount === 8, cpu.processorCount);
check('cpuinfo: Exynos 9820 hardware string preserved', cpu.hardware === 'Samsung EXYNOS9820', cpu.hardware);
check('cpuinfo: distinct CPU parts counted (4x d05 = A55)', cpu.cpuParts['0xd05'] === 4, JSON.stringify(cpu.cpuParts));
check('cpuinfo: two A75-class cores (d0a)', cpu.cpuParts['0xd0a'] === 2);
check('cpuinfo: two M4-class cores (d0b) — 4x A55 + 2x A75 + 2x M4', cpu.cpuParts['0xd0b'] === 2, JSON.stringify(cpu.cpuParts));

const mem = P.parseMeminfo(f['/proc/meminfo']);
check('meminfo: MemTotal parsed to bytes', mem.totalBytes === 5662310 * 1024, mem.totalBytes);
check('meminfo: MemAvailable parsed', mem.availableBytes === 1923412 * 1024);
check('meminfo: swap reported as zero, not omitted', mem.swapTotalBytes === 0);

const st = P.parseKernelStatus(f['/proc/self/status']);
check('status: unprivileged app process has an empty effective capability set', st.capEff.length === 0);
check('status: NoNewPrivs is read and true', st.noNewPrivs === true);
check('status: seccomp filter mode reported', st.seccomp === '2' && st.seccompFilters === '1');

const root = P.parseKernelStatus(f['/proc/1/status']);
check('status: PID 1 (systemd) bounding set decodes to full 4.14 set',
      root.capBnd.indexOf('CAP_SYS_ADMIN') !== -1 && root.capBnd.indexOf('CAP_BPF') !== -1,
      root.capBnd.length + ' caps');
check('status: capability decode follows the 4.14 numbering (CAP_CHECKPOINT_RESTORE = 40)',
      root.capBnd.indexOf('CAP_CHECKPOINT_RESTORE') !== -1 && P.CAPS.length === 41);

const lsm = P.parseLsm(f['/sys/kernel/security/lsm']);
check('lsm: 4.14 reports capability,yama — no Landlock, no AppArmor, no SELinux',
      lsm.capabilityOnly && !lsm.landlock && !lsm.apparmor && !lsm.selinux, lsm.raw);

const inputs = P.parseInputDevices(f['/proc/bus/input/devices']);
const touch = inputs.filter(d => /touch/i.test(d.name || ''));
check('input: sec_touchscreen discovered', touch.length === 1 && touch[0].name === 'sec_touchscreen');
check('input: event node is read from the handler list, never hard-coded',
      touch[0].eventNode === 'event3', touch[0].eventNode);

const ps = P.parsePowerSupply({ battery: { capacity: '78', status: 'Discharging\n',
  voltage_now: '3981000', current_now: '412000', temp: '318' } });
check('power: capacity 78% and discharging', ps.battery.capacityPercent === 78 && ps.battery.status === 'Discharging');
check('power: voltage/current converted from micro-units', near(ps.battery.voltageV, 3.981, 0.001) &&
      near(ps.battery.currentA, 0.412, 0.001));
check('power: battery thermal zone converted from tenths of a degree', near(ps.battery.celsius, 31.8, 0.001));

const th = P.parseThermal({ 'cpu0-thermal': '48200', 'battery-thermal': '31800' });
check('thermal: millidegrees converted to celsius', near(th[0].celsius, 48.2, 0.001));

const mounts = P.parseMounts(f['/proc/self/mountinfo']);
const rootMnt = mounts.filter(m => m.mountPoint === '/')[0];
check('mounts: / is ext4 on mmcblk0p23', rootMnt && rootMnt.fstype === 'ext4' &&
      /mmcblk0p23/.test(rootMnt.source), rootMnt && rootMnt.source);
const sysMnt = mounts.filter(m => m.mountPoint === '/sys')[0];
check('mounts: /sys is mounted read-only', sysMnt && sysMnt.options.indexOf('ro') !== -1);

const blocks = P.parseBlockDevices({ mmcblk0: { size: '122142720', name: 'S0J9K8\n' },
                                     mmcblk1: { size: '62521344', name: 'SL32G\n' } });
check('block: internal UFS/LPDDR size derived from 512-byte sectors',
      near(blocks[0].gib, 58.24, 0.01), blocks[0].gib);
check('block: devices sorted largest first (internal before microSD)',
      blocks[0].device === 'mmcblk0' && blocks[1].device === 'mmcblk1');

const drm = P.parseDrm({ 'card0-DSI-1': { status: 'connected\n', enabled: 'enabled\n', modes: '1440x3040\n' } });
check('drm: panel connector reports 1440x3040 and is enabled',
      drm[0].mode === '1440x3040' && drm[0].enabled === 'enabled');

const sum = P.summarise({ '/proc/cpuinfo': { ok: true, text: f['/proc/cpuinfo'] },
                          '/proc/meminfo': { ok: true, text: f['/proc/meminfo'] },
                          '/proc/version': { ok: true, text: f['/proc/version'] },
                          '/proc/self/status': { ok: true, text: f['/proc/self/status'] },
                          '/etc/os-release': { ok: true, text: f['/etc/os-release'] },
                          '/sys/kernel/security/lsm': { ok: true, text: f['/sys/kernel/security/lsm'] },
                          '/proc/bus/input/devices': { ok: true, text: f['/proc/bus/input/devices'] },
                          '/proc/self/mountinfo': { ok: true, text: f['/proc/self/mountinfo'] } });
check('summarise: kernel release 4.14.253 reported verbatim', sum.kernel === '4.14.253-g2b2e5a0a1b2c', sum.kernel);
check('summarise: OS name read from /etc/os-release', /^Nuxel Beta/.test(sum.osRelease || ''), sum.osRelease);
check('summarise: touchscreen brings its event node through to the summary',
      sum.touchDevices[0].eventNode === 'event3');
check('summarise: no capability is claimed for an unprivileged process',
      Array.isArray(sum.capabilities) && sum.capabilities.length === 0);

console.log('\n' + pass + ' passed, ' + fail + ' failed');
process.exit(fail ? 1 : 0);
