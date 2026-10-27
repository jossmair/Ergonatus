import math
import pytest
from core.motion_analyzer import MotionAnalyzer, MotionThresholds

LEGACY = MotionThresholds(15, 185, 310, 130, 300)


def run(speeds, scale=1, thresholds=LEGACY):
    analyzer = MotionAnalyzer(thresholds)
    states = []
    t, x = 0., 0.
    analyzer.update(t, x, 0, scale)
    for speed, duration in speeds:
        for _ in range(round(duration / .016)):
            t += .016
            x += speed * .016 * scale
            states.append((t, analyzer.update(t, x, 0, scale)))
    return analyzer, states, t, x


def test_slowing_after_fast_approach():
    _, states, _, _ = run([(600, .5), (100, .5)])
    assert not any(state.active for t, state in states if t < .5)
    assert any(state.active for t, state in states if t > .65)


def test_sustained_slow_motion_without_fast_sweep():
    _, states, _, _ = run([(65, .8)])
    assert states[-1][1].active
    assert not states[2][1].active


def test_acceleration_exits_quickly():
    _, states, _, _ = run([(80, .8), (900, .2)])
    assert any(s.active for t, s in states if .6 < t < .8)
    assert all(not s.active for t, s in states if t > .87)


def test_stillness_exits_after_approximately_300ms():
    analyzer, _, t, x = run([(80, .8)])
    assert analyzer.active
    stopped = t
    while t < stopped + .4:
        t += .016
        state = analyzer.update(t, x, 0)
        if t < stopped + .26:
            assert state.active
        if t > stopped + .33:
            assert not state.active


@pytest.mark.parametrize("amplitude", [.2, .8, 1.5])
def test_tremor_does_not_start_lens(amplitude):
    analyzer = MotionAnalyzer()
    for i in range(1200):
        t = i * .016
        state = analyzer.update(t, 300 + amplitude * math.sin(i * 2.1), 200 + amplitude * math.cos(i * 1.9))
        assert not state.active


def test_stationary_pointer_never_activates():
    a = MotionAnalyzer()
    assert not any(a.update(i / 60, 120, 250).active for i in range(600))


def test_noise_does_not_reactivate_after_stop():
    analyzer, _, t, x = run([(80, .8), (0, .5)])
    for i in range(500):
        state = analyzer.update(t + (i + 1) * .016, x + math.sin(i) * .9, math.cos(i) * .9)
        assert not state.active


def test_hysteresis_prevents_chatter():
    analyzer, _, t, x = run([(90, .8)])
    for i in range(100):
        t += .016
        x += (190 + 30 * math.sin(i)) * .016
        assert analyzer.update(t, x, 0).active


@pytest.mark.parametrize("scale", [1, 1.5, 2])
def test_same_physical_behavior_scaled_to_dpi(scale):
    _, states, _, _ = run([(90, .8), (700, .3)], scale)
    assert any(s.active for t, s in states if .5 < t < .8)
    assert not states[-1][1].active


def test_resume_gap_resets_motion():
    analyzer, _, t, x = run([(90, .8)])
    assert not analyzer.update(t + 50, x + 100, 0).active
