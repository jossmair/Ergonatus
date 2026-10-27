"""Time-based motion classification; no input hooks or generated events."""
from collections import deque
from dataclasses import dataclass
import math


@dataclass(frozen=True)
class MotionThresholds:
    minimum_speed: int = 10
    trigger_speed: int = 650
    exit_speed: int = 1100
    activation_delay_ms: int = 50
    idle_delay_ms: int = 2000


@dataclass(frozen=True)
class Motion:
    active: bool
    reason: str
    speed: float


class MotionAnalyzer:
    """EMA + 180 ms path coherence + hysteresis + deliberate-motion evidence.

    Distances are monitor-independent logical pixels. Holding still preserves
    the current state for the configured aim time, never starting a new activation.
    """
    def __init__(self, thresholds=None):
        self.thresholds = thresholds or MotionThresholds()
        self.reset()

    def configure(self, thresholds):
        self.thresholds = thresholds
        self.reset()

    def reset(self):
        self.samples = deque()
        self.previous = None
        self.speed = self.peak = 0.0
        self.active = False
        self.last_progress = None
        self.candidate_since = None
        self.last_fast = -math.inf

    def update(self, t, x, y, scale=1.0):
        if self.previous is None:
            self.previous = (t, x, y)
            self.samples.append((t, x, y))
            self.last_progress = t
            return Motion(False, "idle", 0)
        pt, px, py = self.previous
        dt = t - pt
        if dt <= 0:
            return Motion(self.active, "unchanged", self.speed)
        if dt > .25:
            self.reset()
            return self.update(t, x, y, scale)
        distance = math.hypot(x - px, y - py) / max(.5, scale)
        raw = distance / dt
        self.previous = (t, x, y)
        self.speed += (raw - self.speed) * (1 - math.exp(-dt / .065))
        self.peak = max(self.speed, self.peak * math.exp(-dt / .65))
        self.samples.append((t, x, y))
        while len(self.samples) > 2 and self.samples[1][0] < t - .18:
            self.samples.popleft()
        path = sum(math.hypot(b[1] - a[1], b[2] - a[2]) for a, b in zip(self.samples, list(self.samples)[1:])) / scale
        first = self.samples[0]
        net = math.hypot(x - first[1], y - first[2]) / scale
        span = t - first[0]
        limits = self.thresholds
        coherent = net >= max(.8, limits.minimum_speed * .18) and net / max(path, .001) >= .62
        moving = coherent and span >= .08 and net / max(span, .001) >= limits.minimum_speed * .8
        if moving and distance >= .5:
            self.last_progress = t
        # A single anomalous sample does not trigger; sustained acceleration
        # crosses the filtered exit threshold in roughly 30–60 ms.
        if self.speed > limits.exit_speed or (raw > limits.exit_speed * 2 and self.speed > limits.trigger_speed):
            self.active = False
            self.last_fast = t
            self.candidate_since = None
            return Motion(False, "fast", self.speed)
        if t - self.last_progress >= limits.idle_delay_ms / 1000:
            self.active = False
            self.candidate_since = None
            return Motion(False, "idle", self.speed)
        if self.active:
            return Motion(True, "tracking", self.speed)
        # Sustained slow approach also works without requiring a fast sweep.
        eligible = moving and limits.minimum_speed <= self.speed <= limits.trigger_speed and t - self.last_fast >= .07
        if eligible:
            if self.candidate_since is None:
                self.candidate_since = t
            if t - self.candidate_since >= limits.activation_delay_ms / 1000:
                self.active = True
        else:
            self.candidate_since = None
        return Motion(self.active, "approach" if self.active else "waiting", self.speed)
