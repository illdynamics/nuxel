from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_exact_source_patch_is_present_and_required():
    patch = (ROOT / 'kernel/s10plus/patches/0006-sec-ts-lpm-bind.patch').read_text()
    assert 'drivers/input/touchscreen/sec_ts/y771/sec_ts.c' in patch
    assert '-ENODEV' in patch
    assert (ROOT / 'kernel/s10plus/patches/0006-sec-ts-lpm-bind.patch.required').exists()


def test_patch_does_not_clear_lpcharge_or_change_power_policy():
    patch = (ROOT / 'kernel/s10plus/patches/0006-sec-ts-lpm-bind.patch').read_text()
    changed = '\n'.join(l for l in patch.splitlines() if l.startswith('+') and not l.startswith('+++'))
    assert 'lpcharge = 0' not in changed
    assert 'charging' not in changed.lower()
    assert 'sysfs' not in changed.lower()
    assert 'regulator' not in changed.lower()


def test_fallback_has_owner_locks_uptime_charging_and_cooldown():
    sh = (ROOT / 'services/nuxel-s10/bin/nuxel-charger-mode-recovery.sh').read_text()
    for needle in ('/run/nuxel-owner-test.lock', 'uptime', 'status" != "Charging"', '900'):
        assert needle in sh, needle
    assert 'ONESHOT_FILE' in sh


def test_twrp_absent_is_recorded_not_claimed():
    audit = (ROOT / 'docs/beta-finalization/live/PWNAGE-52000-LPM-AUDIT.md').read_text()
    assert 'TWRP was not visible' in audit
    assert 'BLOCKED_OWNER/TWRP' in audit


def test_rootfs_builder_installs_and_enables_bootmode_guard():
    b = (ROOT / 'images/s10plus/build-phone-rootfs-inside-fedora.sh').read_text()
    assert 'nuxel-bootmode-guard.py' in b
    assert 'nuxel-bootmode-guard.service' in b
    assert 'multi-user.target.wants/nuxel-bootmode-guard.service' in b
