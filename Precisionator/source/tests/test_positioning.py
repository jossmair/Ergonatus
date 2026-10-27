import random
from services.orb_positioning import Rect, choose_position, clamp, companions_on_screen, obstacles_on_screen


AREA = Rect(0, 0, 1920, 1040)


def test_stack_above_both_with_actual_spacing():
    f, t = Rect(1868, 910, 36, 36), Rect(1868, 966, 36, 36)
    assert choose_position([AREA], [("fortinatus", f, 0), ("transcrinator", t, 0)]) == (1868, 854)


def test_only_fortinatus():
    assert choose_position([AREA], [("fortinatus", Rect(200, 400, 36, 36), 0)]) == (200, 354)


def test_family_stack_overrides_old_custom_position():
    assert choose_position([AREA], [("fortinatus", Rect(500, 500, 36, 36), 0)], (10, 900)) == (500, 454)


def test_no_companions_uses_discreet_corner():
    assert choose_position([AREA]) == (1868, 896)


def test_negative_monitor_and_custom_position():
    left = Rect(-1920, -200, 1920, 1080)
    assert choose_position([AREA, left], [], (-1800, -150)) == (-1800, -150)


def test_disconnected_monitor_recovers_position():
    p = choose_position([AREA], [], (-1800, -150))
    assert AREA.contains(Rect(*p, 36, 36))


def test_top_edge_never_overlaps_existing_orbs():
    companions = [("fortinatus", Rect(10, 0, 36, 36), 0), ("transcrinator", Rect(10, 46, 36, 36), 0)]
    p = choose_position([AREA], companions)
    assert AREA.contains(Rect(*p, 36, 36))
    assert all(not Rect(*p, 36, 36).intersects(r) for _, r, _ in companions)


def test_secondary_monitor_anchor():
    area2 = Rect(1920, 0, 1280, 680)
    assert choose_position([AREA, area2], [("fortinatus", Rect(3100, 500, 36, 36), 1)]) == (3100, 454)


def test_random_out_of_bounds_positions_are_recovered():
    rng = random.Random(192)
    for _ in range(1000):
        saved = (rng.randint(-10000, 10000), rng.randint(-10000, 10000))
        p = choose_position([AREA], [], saved)
        assert AREA.contains(Rect(*p, 36, 36))


def test_screen_crossing_reserves_companion_slots_before_their_timer_ticks():
    target = Rect(1920, 0, 1920, 1040)
    previous = [("fortinatus", Rect(1868, 942, 36, 36), "left"),
                ("transcrinator", Rect(1868, 988, 36, 36), "left")]
    companions = companions_on_screen(target, previous, "right")
    assert choose_position([target], companions) == (3788, 896)
    assert all(not Rect(3788, 896, 36, 36).intersects(r) for _, r, _ in companions)


def test_actual_destination_companions_win_over_predicted_positions():
    target = Rect(-1280, 0, 1280, 700)
    companions = companions_on_screen(target, [
        ("fortinatus", Rect(-90, 400, 36, 36), "left"),
        ("transcrinator", Rect(1868, 988, 36, 36), "right")], "left")
    assert choose_position([target], companions) == (-90, 354)


def test_screen_crossing_keeps_extra_spacing_used_by_fortinatus():
    previous = [("fortinatus", Rect(1868, 894, 36, 36), "left"),
                ("transcrinator", Rect(1868, 988, 36, 36), "left")]
    companions = companions_on_screen(AREA, previous, "new")
    assert choose_position([AREA], companions) == (1868, 800)


def test_no_running_companion_does_not_reserve_empty_slots():
    assert companions_on_screen(AREA, [], "primary") == []


def test_transcrinator_only_keeps_precisionator_in_third_slot():
    companions = companions_on_screen(AREA, [("transcrinator", Rect(1868, 988, 36, 36), "primary")], "primary")
    assert choose_position([AREA], companions, (10, 10)) == (1868, 896)


def test_above_both_even_when_companion_order_is_temporarily_inverted():
    companions = [("fortinatus", Rect(500, 700, 36, 36), 0), ("transcrinator", Rect(500, 500, 36, 36), 0)]
    assert choose_position([AREA], companions) == (500, 454)


def test_no_transcrinator_preserves_ten_pixels_above_upper_scroll_arrow():
    fort = Rect(500, 500, 36, 36)
    arrows = [Rect(491, 482, 54, 28), Rect(491, 526, 54, 28)]
    p = choose_position([AREA], [("fortinatus", fort, 0)], obstacles=arrows)
    assert p == (500, 436)
    assert arrows[0].y - (p[1] + 36) == 10


def test_arrows_hidden_do_not_leave_a_phantom_extra_gap():
    assert choose_position([AREA], [("fortinatus", Rect(500, 500, 36, 36), 0)], obstacles=[]) == (500, 454)


def test_negative_monitor_arrow_clearance():
    area = Rect(-1920, -200, 1920, 1080)
    p = choose_position([area], [("fortinatus", Rect(-100, 600, 36, 36), 0)],
                        obstacles=[Rect(-109, 582, 54, 28)])
    assert p == (-100, 536)


def test_top_edge_fallback_never_overlaps_scroll_arrows():
    arrows = [Rect(491, 0, 54, 28)]
    p = choose_position([AREA], [("fortinatus", Rect(500, 18, 36, 36), 0)], obstacles=arrows)
    assert AREA.contains(Rect(*p, 36, 36))
    assert not Rect(*p, 36, 36).intersects(Rect(481, -10, 74, 48))


def test_arrow_space_is_projected_while_other_orbs_catch_up_on_new_monitor():
    target = Rect(1920, 0, 1920, 1040)
    raw = [("fortinatus", Rect(1868, 942, 36, 36), "left")]
    projected = companions_on_screen(target, raw, "right")
    obstacles = obstacles_on_screen(raw, [(Rect(1859, 924, 54, 28), "left")], "right", projected)
    p = choose_position([target], projected, obstacles=obstacles)
    fort = projected[0][1]
    assert p[1] + 36 == fort.y - 28


def test_arrow_catches_up_one_message_after_fort_orb():
    raw = [("fortinatus", Rect(3788, 942, 36, 36), "right")]
    projected = [("fortinatus", raw[0][1], 0)]
    result = obstacles_on_screen(raw, [(Rect(1859, 924, 54, 28), "left")], "right", projected)
    assert result == [Rect(3779, 924, 54, 28)]
