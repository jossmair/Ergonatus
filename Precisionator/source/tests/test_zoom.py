import pytest
from core.zoom_controller import ZoomController


@pytest.mark.parametrize("factor", [1.8, 2.5, 3])
def test_appearance_is_monotonic_and_finishes_at_150ms(factor):
    z = ZoomController(factor)
    states = [z.update(i / 1000, True) for i in range(151)]
    assert states[0].factor == 1
    assert states[-1].factor == pytest.approx(factor)
    assert states[-1].opacity == 1
    assert all(a.opacity <= b.opacity for a, b in zip(states, states[1:]))


def test_fast_fade_finishes_in_100ms():
    z = ZoomController()
    z.update(0, True)
    z.update(.2, True)
    z.update(.3, False, "fast")
    assert z.update(.35, False, "fast").opacity == pytest.approx(.5)
    assert z.update(.401, False, "fast").opacity == 0


def test_interrupted_animation_is_continuous():
    z = ZoomController()
    z.update(0, True)
    before = z.update(.075, True)
    after = z.update(.075, False)
    assert before == after
    assert z.update(.08, False).opacity < before.opacity


def test_reset_is_immediate():
    z = ZoomController()
    z.update(0, True)
    z.update(1, True)
    z.reset()
    assert z.update(2, False).opacity == 0
