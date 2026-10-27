"""Continuous, reversible transitions without frame-rate dependencies."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Zoom:
    opacity: float
    factor: float


class ZoomController:
    def __init__(self, factor=2.5):
        self.factor = factor
        self.reset()

    def reset(self):
        self.value = self.start_value = self.target = 0.0
        self.started = 0.0
        self.duration = .15

    def update(self, t, active, reason="idle"):
        self._evaluate(t)
        target = float(active)
        if target != self.target:
            self.start_value = self.value
            self.target = target
            self.started = t
            self.duration = .15 if active else (.10 if reason == "fast" else .15)
        return Zoom(self.value, 1 + (self.factor - 1) * self.value)

    def _evaluate(self, t):
        progress = max(0., min(1., (t - self.started) / self.duration))
        smooth = progress * progress * (3 - 2 * progress)
        self.value = self.start_value + (self.target - self.start_value) * smooth
