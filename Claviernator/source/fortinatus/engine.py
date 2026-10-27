"""Deterministic input state machine, independent of Qt and Windows.

Every synthetic held output has an owner. Reconfiguration, pause, shutdown and
emergency release those owners; source releases are still consumed afterwards.
"""
from collections import Counter, deque
from dataclasses import dataclass, field
import time

from .config import Mapping, Profile
from .keys import ALT, CTRL, EMERGENCY, MODIFIERS, SHIFT, SYMBOLS, WIN


@dataclass
class Press:
    mapping: Mapping
    outputs: list[tuple] = field(default_factory=list)
    repeat_text: str = ""


@dataclass
class SequenceRun:
    mapping: Mapping
    index: int = 0
    press: Press | None = None
    due: float = 0.


class Engine:
    def __init__(self, emit, notify=lambda text: None, clock=time.monotonic):
        self.emit, self.notify, self.clock = emit, notify, clock
        self.profile = Profile()
        self.enabled = False
        self.physical = set()
        self.forwarded = set()
        self.active: dict[int, Press] = {}
        self.owners = Counter()
        self.toggled = set()
        self.drain = set()
        self.rejected = set()
        self.last_release = {}
        self.latched = set()
        self.modifier_used = set()
        self.rules = {}
        self.sequences = deque()
        self.paste_controls = set()

    def configure(self, profile, enabled=True):
        profile.validate()
        self.release_all()
        self.profile = profile
        self.rules = {m.source: m for m in profile.mappings if m.enabled}
        self.enabled = enabled

    def acquire(self, output, press):
        self.owners[output] += 1
        press.outputs.append(output)
        if self.owners[output] == 1 and not (output[0] == "key" and output[1] in self.forwarded):
            self.emit((*output, True))

    def release(self, press):
        for output in reversed(press.outputs):
            self.owners[output] -= 1
            if self.owners[output] <= 0:
                del self.owners[output]
                if not (output[0] == "key" and output[1] in self.forwarded):
                    self.emit((*output, False))

    def release_all(self):
        had_toggle = bool(self.toggled)
        self.drain.update(self.active)
        self.drain.update(self.rejected)
        if self.profile.sticky_modifiers:
            self.drain.update((self.physical & MODIFIERS) - self.rules.keys() - self.forwarded)
        outputs = list(self.owners)
        self.active.clear()
        self.sequences.clear()
        self.owners.clear()
        self.toggled.clear()
        self.rejected.clear()
        self.latched.clear()
        self.modifier_used.clear()
        self.paste_controls.clear()
        errors = []
        for output in reversed(outputs):
            try:
                if not (output[0] == "key" and output[1] in self.forwarded):
                    self.emit((*output, False))
            except Exception as exc:
                errors.append(str(exc))
        if errors:
            self.notify("Windows n’a pas accepté toutes les libérations : " + errors[0])
        elif had_toggle:
            self.notify("Clics verrouillés libérés.")

    def pause(self):
        self.enabled = False
        self.release_all()

    def event(self, vk, down):
        swallowed = self._event(vk, down)
        if not swallowed:
            if down:
                self.forwarded.add(vk)
            else:
                self.forwarded.discard(vk)
                if self.owners[("key", vk)]:
                    return True
        return swallowed

    def _event(self, vk, down):
        now = self.clock()
        repeated = vk in self.physical
        if down:
            self.physical.add(vk)
        else:
            self.physical.discard(vk)
        if vk == EMERGENCY and down and self.enabled:
            self.pause()
            self.drain.add(vk)
            self.notify("Pause d’urgence : les touches et les clics ont été libérés.")
            return True
        if vk in self.drain:
            if not down:
                self.drain.discard(vk)
            return True
        if not down:
            self.last_release[vk] = now
            self.paste_controls.discard(vk)
            if vk in self.rejected:
                self.rejected.remove(vk)
                return True
            press = self.active.pop(vk, None)
            if press:
                self.release(press)
                return True
        if not self.enabled:
            return False
        if (down and not repeated and vk == 0x56 and not self.physical & (ALT | WIN)
                and self.start_paste()):
            return True
        mapping = self.rules.get(vk)
        if mapping is not None and mapping.kind == "original":
            return False
        if down and vk in self.rejected:
            return True
        if down and repeated:
            press = self.active.get(vk)
            if press:
                if not self.profile.suppress_repeat:
                    if press.repeat_text:
                        self.emit(("text", press.repeat_text))
                    elif press.mapping.kind == "key" and len(press.mapping.keys) == 1:
                        self.emit(("key", press.mapping.keys[-1], True))
                    elif press.mapping.kind == "wheel":
                        self.emit(("wheel", press.mapping.amount))
                return True
            return self.profile.suppress_repeat or (
                self.profile.sticky_modifiers and vk in MODIFIERS and vk not in self.rules)
        if (down and self.profile.debounce_ms and vk not in MODIFIERS
                and (now - self.last_release.get(vk, -100)) * 1000 < self.profile.debounce_ms):
            self.rejected.add(vk)
            return True
        mapping = self.rules.get(vk)
        if self.profile.sticky_modifiers and vk in MODIFIERS and mapping is None and vk not in self.forwarded:
            if down:
                self.modifier_used.discard(vk)
            else:
                if vk not in self.modifier_used:
                    if vk in self.latched:
                        self.latched.remove(vk)
                    else:
                        self.latched.add(vk)
                self.modifier_used.discard(vk)
                self.notify("Modificateurs en attente" if self.latched else "Clavier prêt")
            return True
        if not down:
            return False
        owned_modifiers = {output[1] for output in self.owners if output[0] == "key" and output[1] in MODIFIERS}
        modifiers = (((self.physical & MODIFIERS) - self.rules.keys())
                     | (self.forwarded & MODIFIERS) | self.latched | owned_modifiers)
        # Right Alt and Windows shortcuts retain their original number-row behavior.
        inverted = (self.profile.invert_numbers and vk in SYMBOLS and mapping is None
                    and not modifiers & (CTRL | ALT | WIN))
        sticky = self.profile.sticky_modifiers and bool(modifiers)
        if mapping is None and not inverted and not sticky:
            return False
        if mapping is None:
            mapping = Mapping(vk, "text", text=SYMBOLS[vk] if modifiers & SHIFT else chr(vk)) if inverted else Mapping(vk, keys=[vk])
        press = Press(mapping)
        self.active[vk] = press
        if sticky:
            self.modifier_used.update(self.physical & MODIFIERS)
            self.latched.clear()
            # Inverted text represents Shift directly as a character.
            if not inverted and mapping.kind in ("key", "mouse_click", "mouse_hold", "mouse_toggle", "double_click"):
                for modifier in sorted(modifiers):
                    if modifier not in mapping.keys:
                        self.acquire(("key", modifier), press)
        kind = mapping.kind
        if kind == "key":
            for key in mapping.keys:
                self.acquire(("key", key), press)
        elif kind == "sequence":
            if len(self.sequences) < 32:
                self.sequences.append(SequenceRun(mapping))
                self.tick_sequence()
        elif kind == "text":
            self.emit(("text", mapping.text))
            if inverted:
                press.repeat_text = mapping.text
        elif kind in ("mouse_click", "mouse_hold"):
            self.acquire(("mouse", mapping.button), press)
        elif kind == "mouse_toggle":
            output = ("mouse", mapping.button)
            if output in self.toggled:
                self.toggled.remove(output)
                self.release(Press(mapping, [output]))
                self.notify("Clic relâché.")
            else:
                self.toggled.add(output)
                owner = Press(mapping)
                self.acquire(output, owner)
                self.notify("Clic verrouillé · même touche pour relâcher, F12 pour mettre en pause.")
        elif kind == "double_click":
            # A currently held left button cannot produce a fresh double click.
            if not self.owners[("mouse", "left")]:
                self.emit(("double_click",))
        elif kind == "wheel":
            self.emit(("wheel", mapping.amount))
        elif kind == "move":
            self.move(mapping.direction)
        return True

    def start_paste(self):
        """A mouse-mapped Ctrl becomes a real Ctrl until its physical release.

        Consume V too: queuing Ctrl and letting native V pass through would
        race the action worker. All shortcut events instead use its FIFO.
        """
        controls = sorted(vk for vk in self.physical & CTRL if vk in self.rules
                          and self.rules[vk].kind in ("mouse_click", "mouse_hold", "mouse_toggle", "double_click"))
        if not controls:
            return False
        for vk in controls:
            mapping = self.rules[vk]
            press = self.active.setdefault(vk, Press(Mapping(vk, "disabled")))
            mouse_outputs = [output for output in press.outputs if output[0] == "mouse"]
            self.release(Press(mapping, mouse_outputs))
            press.outputs[:] = [output for output in press.outputs if output[0] != "mouse"]
            output = ("mouse", mapping.button)
            if mapping.kind == "mouse_toggle" and output in self.toggled:
                self.toggled.remove(output)
                self.release(Press(mapping, [output]))
            press.mapping = Mapping(vk, "disabled")
        for vk in controls:
            press = self.active[vk]
            if ("key", vk) not in press.outputs:
                self.acquire(("key", vk), press)
            self.paste_controls.add(vk)
        press = Press(Mapping(0x56, keys=[0x56]))
        self.active[0x56] = press
        was_held = self.owners[("key", 0x56)] or 0x56 in self.forwarded
        self.acquire(("key", 0x56), press)
        if was_held:
            self.emit(("key", 0x56, True))
        return True

    def move(self, direction):
        x, y = {"left": (-1, 0), "right": (1, 0), "up": (0, -1), "down": (0, 1)}[direction]
        speed = self.profile.pointer_speed
        self.emit(("move", x * speed, y * speed))

    def tick(self):
        if self.enabled:
            self.tick_sequence()
            for press in tuple(self.active.values()):
                if press.mapping.kind == "move":
                    self.move(press.mapping.direction)

    def tick_sequence(self):
        if not self.enabled or not self.sequences or self.forwarded & MODIFIERS or self.paste_controls:
            return
        now = self.clock()
        run = self.sequences[0]
        if now < run.due:
            return
        if run.press is not None:
            self.release(run.press)
            run.press = None
            run.index += 1
            if run.index == len(run.mapping.sequence):
                self.sequences.popleft()
                if self.sequences:
                    self.sequences[0].due = now + run.mapping.interval_ms / 1000
            else:
                run.due = now + run.mapping.interval_ms / 1000
        else:
            run.press = Press(run.mapping)
            for key in run.mapping.sequence[run.index]:
                self.acquire(("key", key), run.press)
            run.due = now + .02


