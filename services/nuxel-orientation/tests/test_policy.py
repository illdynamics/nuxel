"""Offline tests for the seven-mode orientation policy state machine."""

import pytest

from nuxel_orientation.policy import (
    ALL_ORIENTATIONS, MODE_ORDER, SEVEN_MODES, Orientator, PolicyError,
    allowed_orientations, choose_initial_orientation, is_auto,
    mode_from_document, normalize_mode, validate_mode,
)


def test_seven_modes_exactly():
    assert len(SEVEN_MODES) == 7
    assert len(MODE_ORDER) == 7
    assert set(SEVEN_MODES) == set(MODE_ORDER)
    assert set(MODE_ORDER) == {
        "portrait", "reverse-portrait", "landscape", "reverse-landscape",
        "auto", "auto-portrait", "auto-landscape",
    }


def test_fixed_modes_have_single_allowed():
    assert allowed_orientations("portrait") == (0,)
    assert allowed_orientations("reverse-portrait") == (180,)
    assert allowed_orientations("landscape") == (90,)
    assert allowed_orientations("reverse-landscape") == (270,)


def test_auto_modes_have_multiple_allowed():
    assert allowed_orientations("auto") == (0, 90, 180, 270)
    assert allowed_orientations("auto-portrait") == (0, 180)
    assert allowed_orientations("auto-landscape") == (90, 270)


def test_is_auto():
    assert not is_auto("portrait")
    assert not is_auto("landscape")
    assert is_auto("auto")
    assert is_auto("auto-portrait")
    assert is_auto("auto-landscape")


def test_validate_mode_rejects_garbage():
    with pytest.raises(PolicyError):
        validate_mode("six")
    with pytest.raises(PolicyError):
        validate_mode("AUTO")
    with pytest.raises(PolicyError):
        validate_mode(None)


def test_validate_mode_accepts_all_seven():
    for m in MODE_ORDER:
        assert validate_mode(m) == m

def test_validate_mode_migrates_legacy_underscore_keys():
    # A49-A53 persisted underscore keys migrate to the A54 hyphenated keys.
    assert validate_mode("auto_portrait") == "auto-portrait"
    assert validate_mode("auto_landscape") == "auto-landscape"
    assert validate_mode("reverse_portrait") == "reverse-portrait"
    assert validate_mode("reverse_landscape") == "reverse-landscape"


def test_mode_from_document_defaults_to_portrait():
    assert mode_from_document({}) == "portrait"
    assert mode_from_document({"mode": "garbage"}) == "portrait"
    assert mode_from_document({"mode": "auto"}) == "auto"


def test_choose_initial_fixed():
    assert choose_initial_orientation("landscape", 0, 0) == 90
    assert choose_initial_orientation("reverse-portrait", 0, 0) == 180


def test_choose_initial_auto_prefers_last_permitted():
    # last=0 is legal in auto_portrait
    assert choose_initial_orientation("auto-portrait", 0, 180) == 0
    # last=90 is NOT legal in auto_portrait; sensor 180 is -> 180
    assert choose_initial_orientation("auto-portrait", 90, 180) == 180
    # neither legal -> first allowed
    assert choose_initial_orientation("auto-landscape", 0, 0) == 90


def test_never_outside_allowed_set_on_switch():
    for m in MODE_ORDER:
        for last in ALL_ORIENTATIONS:
            for sensor in ALL_ORIENTATIONS:
                o = choose_initial_orientation(m, last, sensor)
                assert o in allowed_orientations(m)


def test_normalize_mode_corrects_stale_effective():
    mode, effective, last = normalize_mode(
        {"mode": "auto-portrait", "effective_orientation": 90})
    assert mode == "auto-portrait"
    assert effective in (0, 180)
    # landscape effective corrected to 90
    mode, effective, _ = normalize_mode({"mode": "landscape", "effective_orientation": 0})
    assert effective == 90


def test_classify_good_poses():
    o = Orientator("auto")
    assert o.classify((0, -9.8, 0)) == (0, "good")
    assert o.classify((0, 9.8, 0)) == (180, "good")
    assert o.classify((9.8, 0, 0)) == (90, "good")
    assert o.classify((-9.8, 0, 0)) == (270, "good")


def test_classify_flat_and_weak():
    o = Orientator("auto")
    # gravity mostly along z -> flat
    assert o.classify((1.0, -1.0, 9.8))[1] == "flat"
    # tiny vector -> weak
    assert o.classify((0.1, 0.1, 0.1))[1] == "weak"


def test_fixed_mode_never_rotates_from_sensor():
    o = Orientator("landscape")
    assert o.current == 90
    assert o.update((0, -9.8, 0), 0.0) is None
    assert o.update((9.8, 0, 0), 1.0) is None
    assert o.current == 90


def test_hysteresis_requires_sustained_candidate():
    o = Orientator("auto")
    now = 0.0
    # one sample of landscape (90) is not enough
    assert o.update((9.8, 0, 0), now) is None
    assert o.current == 0
    # keep feeding below the hysteresis window
    for step in range(3):
        now += 0.1
        assert o.update((9.8, 0, 0), now) is None
    # cross the 450 ms window
    now += 0.6
    assert o.update((9.8, 0, 0), now) == 90
    assert o.current == 90


def test_flat_preserves_last_good():
    o = Orientator("auto")
    o.current = 90
    assert o.update((0.1, 0.1, 9.8), 0.0) is None
    assert o.current == 90


def test_auto_portrait_never_rotates_to_landscape():
    o = Orientator("auto-portrait")
    # landscape candidate (90) is disallowed; feed it a long time
    now = 0.0
    for _ in range(30):
        now += 0.1
        assert o.update((9.8, 0, 0), now) is None
        assert o.current in (0, 180)
    # portrait->reverse portrait is allowed (both in {0,180})
    o2 = Orientator("auto-portrait")
    now = 0.0
    for _ in range(8):
        now += 0.2
        o2.update((0, 9.8, 0), now)
    assert o2.current == 180


def test_auto_landscape_never_rotates_to_portrait():
    o = Orientator("auto-landscape")
    o.current = 90
    now = 0.0
    for _ in range(30):
        now += 0.1
        o.update((0, -9.8, 0), now)  # portrait candidate 0 -> disallowed
        assert o.current in (90, 270)


def test_cooldown_blocks_rapid_flapping():
    o = Orientator("auto")
    now = 0.0
    for _ in range(8):
        now += 0.2
        o.update((9.8, 0, 0), now)
    assert o.current == 90
    # immediately back to portrait within cooldown -> refused
    assert o.update((0, -9.8, 0), now + 0.05) is None
    assert o.current == 90
