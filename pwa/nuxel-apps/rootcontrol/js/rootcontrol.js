// Root & Sudo — show the real privilege mechanism, claim nothing more.
(function () {
  'use strict';
  var PM = window.PrivilegeModel;
  var S = window.NuxelSysInfo;
  var el = function (id) { return document.getElementById(id); };
  function esc(s) {
    return String(s === null || s === undefined ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }
  function chip(status) { return '<span class="chip ' + status + '">' + esc(status.replace(/-/g, ' ')) + '</span>'; }

  var PATHS = ['/etc/sudoers', '/etc/sudoers.d/50-nuxel-installer', '/etc/group',
               '/sys/kernel/security/lsm', '/proc/version', '/proc/1/status',
               '/proc/self/status', '/usr/lib/systemd/system/nuxel-settings.service'];

  function render(res) {
    var t = function (p) { return res[p] && res[p].ok ? res[p].text : ''; };
    var src = S.sourceLabel(res);
    var live = /live/.test(src);
    el('source-badge').textContent = 'state: ' + src;
    el('source-badge').className = 'badge ' + (live ? 'live' : 'sample');
    var note = el('source-note');
    if (!live) {
      note.className = 'note show';
      note.innerHTML = '<b>Snapshot state, not a live read.</b> The Nuxel host is not reachable, so the sudoers ' +
        'and kernel state below come from the bundled snapshot. Every row is still labelled with its source, ' +
        'and nothing here changes any privilege.';
    } else { note.className = 'note'; }

    var full = PM.parseSudoers(t('/etc/sudoers'));
    var dropin = PM.parseSudoers(t('/etc/sudoers.d/50-nuxel-installer'));
    var combined = PM.parseSudoers(t('/etc/sudoers') + '\n' + t('/etc/sudoers.d/50-nuxel-installer'));
    var summary = PM.sudoSummary(combined);
    var wheel = PM.parseGroupMembers(t('/etc/group'), 'wheel');
    var kernelRel = (/Linux version (\S+)/.exec(t('/proc/version')) || [])[1] || 'not reported';
    var mech = PM.mechanism({ kernelRelease: kernelRel, lsm: t('/sys/kernel/security/lsm').trim(),
                              seccomp: /Seccomp:\s*2/.test(t('/proc/1/status')) });
    var claims = PM.enforcementClaims(mech);

    // ---- overview ----
    el('tab-overview').innerHTML =
      '<div class="card"><h3>In one paragraph</h3><p class="hint">' +
      'Privilege on this device is ordinary Linux: POSIX file permissions and ownership, the capability ' +
      'split, seccomp filters installed by systemd, and per-unit sandbox directives such as ' +
      '<code>NoNewPrivileges=</code> and <code>CapabilityBoundingSet=</code>. There is <b>no</b> kernel ' +
      'mandatory-access-control policy in force: this kernel reports LSM modules “' + esc(mech.lsmRaw) + '”. ' +
      'Whoever reaches root owns the phone, and Nuxel does not pretend otherwise.</p></div>' +
      '<div class="card"><h3>Real sudoers state</h3>' +
      '<table><thead><tr><th>Rule</th><th>Runs as</th><th>Commands</th><th>Password</th></tr></thead><tbody>' +
      combined.userSpecs.map(function (s) {
        return '<tr><td>' + esc(s.user) + '</td><td>' + esc(s.runas) + '</td><td>' + esc(s.commands) +
          '</td><td>' + (s.nopasswd ? 'not required (NOPASSWD)' : 'required') + '</td></tr>';
      }).join('') + '</tbody></table>' +
      '<p class="hint">Full-sudo accounts: <b>' + esc(summary.fullSudoAccounts.join(', ') || 'none') + '</b>. ' +
      'Passwordless rules: <b>' + summary.passwordless + '</b>' +
      (summary.passwordless ? ' (the installer drop-in, limited to staging and rollback commands)' : '') + '. ' +
      'wheel members: <b>' + esc(wheel.join(', ') || 'none') + '</b>.</p></div>' +
      '<div class="card"><h3>This app\u2019s own privileges</h3><pre class="log">' +
      esc(['uid: ' + ((/Uid:\s*(\S+)/.exec(t('/proc/self/status')) || [])[1] || 'not reported'),
           'effective capabilities: ' + (PM.mechanism ? '' : '') +
             ((/CapEff:\s*([0-9a-f]+)/i.exec(t('/proc/self/status')) || [])[1] === '0000000000000000'
               ? 'none (unprivileged)' : ((/CapEff:\s*([0-9a-f]+)/i.exec(t('/proc/self/status')) || [])[1] || 'not reported')),
           'NoNewPrivs: ' + (((/NoNewPrivs:\s*(\d+)/.exec(t('/proc/self/status')) || [])[1] === '1') ? 'yes' : 'no'),
           'seccomp: ' + (((/Seccomp:\s*(\d+)/.exec(t('/proc/self/status')) || [])[1] === '2') ? 'mode 2 (filter)' : 'none')].join('\n')) +
      '</pre></div>' +
      '<div class="card"><h3>Privileged operations and what they really need</h3>' +
      '<table><thead><tr><th>Operation</th><th>Mechanism</th><th>How Nuxel does it</th></tr></thead><tbody>' +
      PM.PRIVILEGED_OPS.map(function (o) {
        return '<tr><td>' + esc(o.op) + '<div class="hint">' + esc(o.note) + '</div></td><td>' +
          esc(o.needs) + '</td><td>' + esc(o.via) + '</td></tr>';
      }).join('') + '</tbody></table></div>' +
      '<div class="card"><h3>Manual inspection</h3><p class="hint">This app never runs commands. If you want to see ' +
      'the live rules yourself, open the Terminal and run <code>sudo -l</code>, <code>ls -l /etc/sudoers.d</code> ' +
      'or <code>cat /proc/1/status</code>.</p><div class="row">' +
      '<button id="open-terminal">Open Terminal</button></div></div>';

    // ---- sudoers ----
    el('tab-sudoers').innerHTML =
      '<div class="card"><h3>/etc/sudoers (verbatim)</h3><pre class="log">' + esc(t('/etc/sudoers')) + '</pre></div>' +
      '<div class="card"><h3>/etc/sudoers.d/50-nuxel-installer (verbatim)</h3><pre class="log">' +
      esc(t('/etc/sudoers.d/50-nuxel-installer')) + '</pre></div>' +
      '<div class="card"><h3>Parsed summary</h3>' +
      '<ul class="reqs">' +
      '<li>Defaults: ' + esc(full.defaults.join(' | ') || 'none') + '</li>' +
      '<li>Include directives: ' + esc(full.includeDirs.join(', ') || 'none') + '</li>' +
      '<li>Full-sudo (ALL) rules: ' + esc(summary.fullSudoAccounts.join(', ') || 'none') + '</li>' +
      '<li>Groups with full sudo: ' + esc(summary.groupsWithFullSudo.join(', ') || 'none') + '</li>' +
      '<li>Passwordless rules: ' + summary.passwordless + ' — the only one is limited to ' +
        esc(dropin.userSpecs[0] ? dropin.userSpecs[0].commands : 'n/a') + '</li>' +
      '<li>Dangerous passwordless ALL rules: ' + summary.dangerous + '</li>' +
      '</ul></div>' +
      '<div class="card"><h3>Membership</h3><pre class="log">' + esc(t('/etc/group')) + '</pre></div>';

    // ---- mechanism ----
    var rows = [['DAC (ownership + mode bits)', mech.dac], ['Capabilities', mech.capabilities],
                ['seccomp filters', mech.seccomp], ['systemd unit sandbox', mech.systemdSandbox],
                ['Landlock', mech.landlock], ['AppArmor', mech.apparmor], ['SELinux', mech.selinux],
                ['Yama ptrace scope', mech.yama]];
    el('tab-mechanism').innerHTML =
      '<div class="card"><h3>What is actually enforcing on this kernel</h3>' +
      '<table><thead><tr><th>Mechanism</th><th>State</th><th>Detail</th></tr></thead><tbody>' +
      rows.map(function (r) {
        return '<tr><td>' + esc(r[0]) + '</td><td>' + (r[1].enabled ? '<span class="chip on">active</span>'
          : '<span class="chip off">not active</span>') + '</td><td>' + esc(r[1].detail) + '</td></tr>';
      }).join('') + '</tbody></table>' +
      '<p class="hint">Kernel release: <b>' + esc(kernelRel) + '</b> · LSM line: <b>' + esc(mech.lsmRaw) +
      '</b> — read from /sys/kernel/security/lsm, not assumed.</p></div>' +
      '<div class="card"><h3>Example unit sandbox (nuxel-settings.service)</h3><pre class="log">' +
      esc(t('/usr/lib/systemd/system/nuxel-settings.service')) + '</pre>' +
      '<p class="hint">CapabilityBoundingSet= (empty) means the service cannot regain any capability even if it ' +
      'is compromised. That is per-unit policy, not a kernel MAC.</p></div>';

    // ---- claims ----
    el('tab-claims').innerHTML =
      '<div class="card"><h3>Enforcement claims, by attacker class</h3>' +
      '<p class="hint">Each claim names who it is about, what enforces it, and where it stops being true. ' +
      'A passing unit test never upgrades any of these to “verified on hardware”.</p>' +
      '<table><thead><tr><th>Claim</th><th>Status</th><th>Attacker</th></tr></thead><tbody>' +
      claims.map(function (c) {
        return '<tr><td>' + esc(c.claim) + '</td><td>' + chip(c.status) + '</td><td>' +
          esc(PM.ATTACKER_CLASSES[c.attackerClass]) + '</td></tr>';
      }).join('') + '</tbody></table></div>' +
      claims.map(function (c) {
        return '<div class="card"><h3>' + chip(c.status) + ' ' + esc(c.claim) + '</h3>' +
          '<p class="hint"><b>Enforced by:</b> ' + esc(c.evidence) + '</p>' +
          '<p class="hint"><b>Limitation:</b> ' + esc(c.limitation) + '</p>' +
          '<p class="hint"><b>Attacker class:</b> ' + esc(PM.ATTACKER_CLASSES[c.attackerClass]) + '</p></div>';
      }).join('');

    // ---- limits ----
    var violations = PM.auditClaims(claims.map(function (c) { return c.claim + ' ' + c.evidence + ' ' + c.limitation; }));
    el('tab-limits').innerHTML =
      '<div class="card"><h3>What this build does NOT claim</h3><ul class="reqs">' +
      '<li><b>No unbypassable root protection.</b> Root compromise is out of scope for every claim Nuxel ' +
      'makes. If an attacker has root — or a kernel exploit — the device is theirs.</li>' +
      '<li><b>No kernel MAC.</b> Linux 4.14 has no Landlock, and this image loads neither SELinux nor AppArmor ' +
      'policy. Confinement is DAC + capabilities + seccomp + unit policy.</li>' +
      '<li><b>No anonymity claim.</b> VPN/Tor are not enabled by default, and a running service would not by ' +
      'itself prove that every flow is inside it.</li>' +
      '<li><b>No anti-tamper claim for physical access.</b> Recovery and download modes belong to the boot ' +
      'chain Nuxel does not control; Nuxel implements entries for them and never triggers them.</li>' +
      '<li><b>No claim that a unit sandbox is a security boundary.</b> It is defence in depth and is labelled ' +
      'partial for exactly that reason.</li>' +
      '</ul></div>' +
      '<div class="card"><h3>Wording audit</h3><p class="hint">This app refuses to display absolute security ' +
      'words. The audit runs over every claim and privileged-operation note that ships in the UI; the offline ' +
      'test suite fails if a forbidden phrase appears affirmatively.</p>' +
      '<p class="hint">Forbidden phrases checked: <code>' + esc(PM.FORBIDDEN_ABSOLUTES.join('</code>, <code>')) +
      '</code></p><p class="hint">Violations found in the shipped text: <b>' + violations.length + '</b></p></div>' +
      '<div class="card"><h3>Deliberate limitations carried into the beta report</h3><ul class="reqs">' +
      '<li>Root-owned devices cannot be protected from their owner by the operating system.</li>' +
      '<li>“Enforced” above means enforced against the named attacker class with DAC and capabilities, not ' +
      'against a kernel vulnerability.</li>' +
      '<li>No time, no human observation and no hardware interaction is fabricated anywhere in this app.</li>' +
      '</ul></div>';

    el('sb-source').textContent = 'state source: ' + src;
    el('sb-kernel').textContent = 'kernel: ' + kernelRel;
    el('sb-mac').textContent = 'MAC: ' + (mech.macEnabled ? 'present' : 'absent (' + mech.lsmRaw + ')');
    var ot = document.getElementById('open-terminal');
    if (ot) ot.addEventListener('click', function () {
      var b = window.NuxelBridge;
      if (b && typeof b.call === 'function') b.call('apps', 'launch', { app_id: 'org.nuxel.Terminal' });
      else if (window.parent && window.parent.appRegistry) window.parent.appRegistry.launchApp('org.nuxel.Terminal');
    });
  }

  async function refresh() {
    el('source-badge').textContent = 'state: reading…';
    var res = await S.readMany(PATHS);
    window.__rootcontrolLastRead = { at: new Date().toISOString(), result: res };
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
    if (f) {
      var closedByLauncher = false;
      try {
        if (window.parent !== window && window.parent.NuxelLauncherClose) {
          window.parent.NuxelLauncherClose();
          closedByLauncher = true;
        }
      } catch (e) { /* cross-origin parent: fall through */ }
      if (!closedByLauncher && f.parentNode) f.parentNode.removeChild(f);
    }
    else if (f && f.parentNode) f.parentNode.removeChild(f);
  });
  refresh();
})();
