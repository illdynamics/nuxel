#!/usr/bin/env python3
"""NUXEL-105200 regression checks (static, offline).

Covers the three fixes made after the phone was left in TWRP with no working
serial/SSH console:
  * the firewall unit can no longer block or fail the boot graph;
  * the console guard covers the prerouting hook and the verifier proves it;
  * the Wi-Fi LAN allowlist is self-healing;
  * Settings has a button-driven, two-draw pattern setup wizard (no pattern or
    PIN field visible until the owner starts it).

These are source contracts only; the live proof is recorded in the mission
report after the device run.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
fails = 0


def check(name, cond, detail=""):
    global fails
    print(("PASS " if cond else "FAIL ") + name + ("" if cond or not detail else "  " + detail))
    if not cond:
        fails += 1


def read(rel):
    return (ROOT / rel).read_text()


# ---- firewall unit: bounded, cannot fail the boot --------------------------
unit = read("configs/nftables/systemd/nuxel-firewall.service")
check("firewall unit is bounded (TimeoutStartSec)", "TimeoutStartSec=" in unit)
check("firewall checks run under timeout", "timeout " in unit)
check("firewall failure/warning steps are soft", "[Unit]" in unit and "SuccessExitStatus=0" in unit)
check("firewall keeps no start-limit give-up", "StartLimitIntervalSec=0" in unit)
check("firewall never uses an unbounded bare check", "ExecStartPre=-/usr/bin/nuxel-firewall.sh check" not in unit)

# ---- console guard --------------------------------------------------------
guard = read("configs/nftables/nuxel-console-guard.nft")
check("guard has a prerouting chain", "chain prerouting_guard" in guard)
check("guard prerouting runs before nuxel_raw", "priority -300" in guard)
check("guard accepts SSH at every hook", guard.count("tcp dport { 22, 2022 } accept") >= 2)
fw = read("tools/s10plus/a33/nuxel-firewall.sh")
check("console-verify proves the prerouting guard",
      "type filter hook prerouting priority -300" in fw)
check("console-verify repairs an empty ruleset with the accept-only guard",
      "accept-only recovery plane" in fw)
check("apply reloads the guard before rolling back", "accept-only console guard reloaded before rollback" in fw)

# ---- LAN allowlist self-healing -------------------------------------------
helper = ROOT / "configs/nuxel/security/ssh/systemd/nuxel-ssh-lan-allow.sh"
check("LAN allowlist helper exists and is executable", helper.is_file() and (helper.stat().st_mode & 0o111) != 0)
h = helper.read_text()
check("helper writes the owner LAN CIDR", "root@192.168.178.0/24" in h)
check("helper is idempotent (verifies before exit)", "grep -Eq" in h)
dropin = read("configs/nuxel/security/ssh/systemd/sshd.service.d-nuxel-lan-allow.conf")
check("sshd drop-in runs the helper before sshd starts",
      "ExecStartPre=-/usr/lib/nuxel/nuxel-ssh-lan-allow" in dropin)
apply36000 = read("services/nuxel-s10/bin/nuxel-apply-pwnage36000.sh")
check("36000 bootstrap installs the helper + drop-in",
      "nuxel-ssh-lan-allow" in apply36000 and "sshd.service.d" in apply36000)

# ---- initramfs console self-heals the UDC --------------------------------
init = read("boot/initramfs/init.sh")
check("initramfs unbinds foreign gadgets before the console",
      "LIVE_CONSOLE unbound foreign gadget" in init)
check("initramfs proves ttyGS0 exists", "LIVE_CONSOLE_TTY_READY" in init)

# ---- pattern setup wizard -------------------------------------------------
html = read("pwa/nuxel-apps/settings/index.html")
js = read("pwa/nuxel-apps/settings/pwange45000-settings.js")
css = read("pwa/nuxel-apps/settings/settings.css")
card = re.search(r'<div class="card" id="sec-pattern-card">(.*?)</div>\s*</div>', html, re.S)
check("pattern card has a setup button", 'id="sec-pattern-setup"' in html and "Set up pattern lock" in html)
start = html.index('<div class="pattern-setup" id="sec-pattern-wizard" hidden>')
end = html.index('</div>', html.index('id="sec-pattern-wizard-status"', start))
wizard = html[start:end]
check("wizard body is hidden until started", 'hidden>' in wizard[:80])
check("matrix lives inside the hidden wizard", 'id="sec-pattern-editor"' in wizard)
check("fallback PIN lives inside the hidden wizard", 'id="sec-pattern-pin"' in wizard)
check("wizard has two steps + cancel",
      all(x in js for x in ("Step 1 of 2", "Step 2 of 2", "sec-pattern-cancel")))
check("wizard stores only after two identical draws",
      "wirePatternEditor._first !== first" in js and "pattern_confirm: first" in js)
check("pattern preset opens the wizard instead of activating",
      "openPatternSetup();" in js and "params.secret = first; params.secret_confirm = first;" not in js)
check("layout adapts to landscape", "@media (orientation: landscape)" in css)
check("status exposes whether a pattern exists", '"pattern_set":' in read("services/nuxel-bridge/src/security_provider.py"))

print("\n%d failed" % fails)
sys.exit(1 if fails else 0)
