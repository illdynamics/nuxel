// Root & Sudo — the honest privilege model of this device.
//
// This module exists to stop the app from ever claiming more than the kernel can
// deliver.  It (a) parses the REAL sudoers state, (b) describes the privilege
// mechanism that actually exists on Linux 4.14 (DAC + capabilities + seccomp +
// systemd unit sandbox, and NOT Landlock/AppArmor/SELinux), and (c) audits every
// claim against a list of forbidden absolute statements.  Root compromise is
// explicitly out of scope: the app states plainly that root-owned devices cannot
// be made unbypassable by this build.
(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.PrivilegeModel = factory();
}(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  var ATTACKER_CLASSES = {
    app: 'unprivileged application (sandboxed PWA or native app)',
    user: 'unprivileged local user with a shell',
    sudoUser: 'local user holding a sudoers entry',
    root: 'root / already-privileged process',
    physical: 'attacker with physical access to the device',
    network: 'remote attacker on the network'
  };

  var CLAIM_STATUS = ['enforced', 'partial', 'not-enforced', 'out-of-scope'];

  // Absolute phrases this app must never use.  auditClaims() enforces it and the
  // offline test suite fails if any shipped UI string contains one.
  var FORBIDDEN_ABSOLUTES = [
    'unbypassable', 'un-bypassable', 'impossible to bypass', 'cannot be bypassed',
    'fully secure', '100% secure', 'guaranteed secure', 'hack-proof', 'unhackable',
    'root cannot be compromised', 'cannot be rooted'
  ];

  /* ---------------- sudoers ---------------- */
  function parseSudoers(text) {
    var out = { defaults: [], userSpecs: [], includeDirs: [], aliases: {},
                nopasswd: [], wildcards: [], comments: 0, lines: 0 };
    (String(text || '')).split('\n').forEach(function (raw) {
      out.lines++;
      var line = raw.trim();
      if (!line) return;
      if (line.charAt(0) === '#') {
        out.comments++;
        if (/^#include(dir)?\s+/i.test(line)) out.includeDirs.push(line.replace(/^#include(dir)?\s+/i, '').trim());
        return;
      }
      if (/^Defaults\b/i.test(line)) { out.defaults.push(line); return; }
      var alias = /^(User_Alias|Host_Alias|Runas_Alias|Cmnd_Alias)\s+([A-Za-z0-9_]+)\s*=\s*(.+)$/.exec(line);
      if (alias) {
        (out.aliases[alias[1]] = out.aliases[alias[1]] || {})[alias[2]] = alias[3];
        return;
      }
      var m = /^([^\s]+)\s+([^\s=]+)\s*=\s*(\(([^)]*)\))?\s*(.+)$/.exec(line);
      if (!m) { return; }
      var spec = { user: m[1], hosts: m[2], runas: m[4] || 'root (default)', commands: m[5],
                   nopasswd: /NOPASSWD\s*:/.test(m[5]), passwd: !/NOPASSWD\s*:/.test(m[5]) };
      if (/^\s*ALL\s*$/.test(spec.commands.replace(/NOPASSWD\s*:/, ''))) spec.allCommands = true;
      out.userSpecs.push(spec);
      if (spec.nopasswd) out.nopasswd.push(spec);
      if (/\bALL\b/.test(spec.commands)) out.wildcards.push(spec);
    });
    return out;
  }

  function parseGroupMembers(groupText, group) {
    var members = [];
    (String(groupText || '')).split('\n').forEach(function (line) {
      var p = line.split(':');
      if (p.length >= 4 && p[0] === group) {
        p[3].split(',').forEach(function (u) { if (u.trim()) members.push(u.trim()); });
      }
    });
    return members;
  }

  /* ---------------- mechanism ---------------- */
  function mechanism(env) {
    env = env || {};
    var lsmText = String(env.lsm || '');
    var kernel = String(env.kernelRelease || '');
    var majorMinor = /^(\d+)\.(\d+)/.exec(kernel);
    var mm = majorMinor ? Number(majorMinor[1]) * 100 + Number(majorMinor[2]) : 0;
    return {
      kernelRelease: kernel || 'unknown',
      dac: { enabled: true,
             detail: 'POSIX mode bits and ownership — the primary confinement on this kernel.' },
      capabilities: { enabled: true,
                      detail: 'Fine-grained root privileges are split into capabilities; a process holds only ' +
                              'the CapEff mask it was given.' },
      seccomp: { enabled: env.seccomp === true,
                 detail: env.seccomp === true ? 'seccomp filters are installed by systemd (mode 2).'
                                              : 'seccomp availability was not read from this device.' },
      systemdSandbox: { enabled: env.systemdSandbox !== false,
                        detail: 'Units use NoNewPrivileges=, ProtectSystem=, ProtectHome= and ' +
                                'CapabilityBoundingSet= — these are per-unit policy, not a kernel MAC.' },
      landlock: { enabled: /landlock/.test(lsmText),
                  detail: /landlock/.test(lsmText) ? 'Landlock is active.' :
                          'Landlock does not exist in Linux 4.14 (it arrived in 5.13), so no Landlock claim is made.' },
      apparmor: { enabled: /apparmor/.test(lsmText), detail: 'AppArmor ' + (/apparmor/.test(lsmText) ? 'is active.' : 'is not active on this kernel.') },
      selinux: { enabled: /selinux/.test(lsmText), detail: 'SELinux ' + (/selinux/.test(lsmText) ? 'is active.' : 'is not active on this kernel.') },
      yama: { enabled: /yama/.test(lsmText), detail: 'Yama restricts ptrace scope when configured.' },
      lsmRaw: lsmText || 'not reported',
      macEnabled: /landlock|apparmor|selinux|smack/.test(lsmText)
    };
  }

  /* ---------------- privileged operations ---------------- */
  var PRIVILEGED_OPS = [
    { op: 'Set the system clock / RTC', needs: 'CAP_SYS_TIME', via: 'systemd-timesyncd (root) or a sudoers entry',
      note: 'Timesync is done by a root service; the app never sets the clock itself.' },
    { op: 'Manage nftables firewall rules', needs: 'CAP_NET_ADMIN', via: 'nuxel-firewall (root unit)',
      note: 'The UI only views rules; applying them is a signed root service action.' },
    { op: 'Attach a USB gadget configuration', needs: 'CAP_SYS_ADMIN', via: 'the live console init stage',
      note: 'The console gadget is created by the early boot stage before privileges are dropped.' },
    { op: 'Open the framebuffer / DRM master', needs: 'group access or CAP_SYS_ADMIN', via: 'the single display owner (nuxel-wl-fb)',
      note: 'Exactly one process owns the panel; opening /dev/fb0 anywhere else has knocked the AMOLED out before.' },
    { op: 'Write a raw block device', needs: 'CAP_SYS_RAWIO + device permissions', via: 'never — the beta mission forbids all direct writes',
      note: 'No Nuxel component writes to raw partitions; recovery/download mode entries are offline-tested only.' },
    { op: 'Install a package', needs: 'a verified NuxTore signature + a registry write', via: 'NuxTore with the local staging catalog',
      note: 'No remote install path and no unsigned auto-install.' },
    { op: 'Change another app\u2019s data directory', needs: 'CAP_DAC_OVERRIDE or root', via: 'denied by DAC; per-app data dirs are 0700',
      note: 'Each PWA runs with its own WebKitGTK data directory.' }
  ];

  /* ---------------- claims ---------------- */
  function enforcementClaims(mech) {
    mech = mech || mechanism({});
    return [
      { id: 'app-isolation',
        claim: 'An unprivileged app cannot read another app\u2019s stored data.',
        status: 'enforced', attackerClass: 'app',
        evidence: 'Per-app WebKitGTK data directories under /var/app/<id>/data with mode 0700; DAC + a separate ' +
                  'uid means a normal app has no read path into another app\u2019s storage.',
        limitation: 'A kernel bug or an explicit root action can defeat DAC; this is not MAC.' },
      { id: 'no-raw-io',
        claim: 'An unprivileged app cannot write to a raw block device or partition.',
        status: 'enforced', attackerClass: 'app',
        evidence: 'No app process holds CAP_SYS_RAWIO and the device nodes are root-owned; the beta mission ' +
                  'forbids all direct writes and no component implements one.',
        limitation: 'Root, or a device node with permissive group ownership, would change this.' },
      { id: 'no-net-admin',
        claim: 'An unprivileged app cannot reconfigure the network or open raw sockets.',
        status: 'enforced', attackerClass: 'app',
        evidence: 'Firewall rules are applied by a root unit; an unprivileged app has no CAP_NET_ADMIN and ' +
                  'no CAP_NET_RAW in its CapEff mask.',
        limitation: 'Traffic is not anonymised: this says nothing about where traffic goes.' },
      { id: 'service-sandbox',
        claim: 'Sandboxed system services cannot trivially escalate to root.',
        status: 'partial', attackerClass: 'user',
        evidence: 'Units run with NoNewPrivileges=, CapabilityBoundingSet=, ProtectSystem=strict and ' +
                  'ProtectHome=read-only; seccomp mode 2 filters are applied.',
        limitation: 'These are per-unit policies, not a kernel MAC. A unit that is wrong, or a kernel ' +
                    'vulnerability, can still lead to escalation — so the claim is partial.' },
      { id: 'mac',
        claim: 'Mandatory access control confines every process.',
        status: 'not-enforced', attackerClass: 'user',
        evidence: 'The running kernel reports LSM modules "' + mech.lsmRaw + '" — capability and (at most) yama. ' +
                  'Landlock is a 5.13 feature and does not exist in 4.14; no SELinux or AppArmor policy is loaded.',
        limitation: 'Do not treat this device as MAC-confined. Confinement is DAC + capabilities + seccomp + ' +
                    'unit policy.' },
      { id: 'root',
        claim: 'An account that can run arbitrary commands as root owns the device.',
        status: 'out-of-scope', attackerClass: 'root',
        evidence: 'Root has CAP_SYS_ADMIN and the full 4.14 bounding set; a process that reaches it can load ' +
                  'modules, read every file and write every device. No component in this build claims otherwise.',
        limitation: 'Root compromise is explicitly out of scope for every claim Nuxel makes. This build does ' +
                    'NOT claim unbypassable root protection, and the UI refuses to say it does.' },
      { id: 'physical',
        claim: 'Protection against physical access (recovery mode, download mode, direct storage access).',
        status: 'out-of-scope', attackerClass: 'physical',
        evidence: 'The boot chain contains Samsung recovery and download modes that Nuxel does not control. ' +
                  'Nuxel implements power-menu entries for them but never triggers them.',
        limitation: 'No anti-tamper claim is made for a device in an attacker\u2019s hands.' },
      { id: 'remote',
        claim: 'Remote confidentiality of application traffic.',
        status: 'not-enforced', attackerClass: 'network',
        evidence: 'No VPN or Tor service is enabled by default on this image.',
        limitation: 'A running tunnel service would still not prove every flow is inside it; that needs a ' +
                    'syscall/flow-level proof, which this build does not claim.' }
    ];
  }

  // A phrase is only a violation when it is used AFFIRMATIVELY.  "This build does
  // NOT claim unbypassable root protection" must pass the audit: the disclaimers
  // are the honest statements, only the boast is forbidden.
  function isNegatedAt(low, idx) {
    var pre = low.slice(Math.max(0, idx - 48), idx);
    return /(\bnot\b|\bno\b|\bnever\b|cannot|n't|doesn't|don't|refuses? to)\s*[^.;]{0,40}$/.test(pre);
  }

  function auditClaims(texts) {
    var violations = [];
    (texts || []).forEach(function (t) {
      var low = String(t || '').toLowerCase();
      FORBIDDEN_ABSOLUTES.forEach(function (bad) {
        var idx = low.indexOf(bad);
        while (idx !== -1) {
          if (!isNegatedAt(low, idx)) {
            violations.push({ text: String(t).slice(Math.max(0, idx - 40), idx + bad.length + 20),
                              phrase: bad, at: idx });
          }
          idx = low.indexOf(bad, idx + bad.length);
        }
      });
    });
    return violations;
  }

  function sudoSummary(parsed) {
    var allCommands = parsed.userSpecs.filter(function (s) { return s.allCommands; });
    return {
      ruleCount: parsed.userSpecs.length,
      passwordless: parsed.nopasswd.length,
      fullSudoAccounts: allCommands.map(function (s) { return s.user; }),
      groupsWithFullSudo: parsed.wildcards.filter(function (s) { return /^%/.test(s.user); })
        .map(function (s) { return s.user; }),
      includeDirs: parsed.includeDirs,
      defaults: parsed.defaults,
      dangerous: parsed.nopasswd.filter(function (s) { return /\bALL\b/.test(s.commands); }).length
    };
  }

  return {
    ATTACKER_CLASSES: ATTACKER_CLASSES,
    CLAIM_STATUS: CLAIM_STATUS,
    FORBIDDEN_ABSOLUTES: FORBIDDEN_ABSOLUTES,
    PRIVILEGED_OPS: PRIVILEGED_OPS,
    parseSudoers: parseSudoers,
    parseGroupMembers: parseGroupMembers,
    mechanism: mechanism,
    enforcementClaims: enforcementClaims,
    auditClaims: auditClaims,
    sudoSummary: sudoSummary
  };
}));
