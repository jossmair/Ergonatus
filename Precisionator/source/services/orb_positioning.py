"""Pure geometry. All rectangles here use Qt logical desktop coordinates."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Rect:
    x: int
    y: int
    w: int
    h: int

    def intersects(self, other):
        return self.x < other.x + other.w and other.x < self.x + self.w and self.y < other.y + other.h and other.y < self.y + self.h

    def contains(self, other):
        return self.x <= other.x and self.y <= other.y and self.x + self.w >= other.x + other.w and self.y + self.h >= other.y + other.h


def clamp(position, area, size=36):
    return (max(area.x, min(position[0], area.x + area.w - size)),
            max(area.y, min(position[1], area.y + area.h - size)))


def companions_on_screen(area, companions, screen_name, size=36):
    """Reserve the family pile while its independent timers catch up.

    Rectangles are already logical and tagged with their source screen name.
    Transcrinator resets to the bottom-right corner on a new monitor; Fortinatus
    follows above it. Predict those slots only when a visible companion still
    exists on another monitor, so our first 40 ms tick cannot land on its slot.
    Actual positions on the destination always take priority.
    """
    found = {name: bounds for name, bounds, source in companions if source == screen_name}
    elsewhere = {name for name, _, source in companions if source != screen_name}
    fallback = Rect(area.x + area.w - size - 16, area.y + area.h - size - 16, size, size)
    if "transcrinator" not in found and "transcrinator" in elsewhere:
        found["transcrinator"] = fallback
    if "fortinatus" not in found and ("fortinatus" in elsewhere or "transcrinator" in found):
        gap = 10
        for name, fort, source in companions:
            if name == "fortinatus":
                trans = next((r for n, r, s in companions if n == "transcrinator" and s == source and r.y > fort.y), None)
                if trans:
                    gap = max(4, min(120, trans.y - fort.y - fort.h))
                    break
        anchor = found.get("transcrinator", fallback)
        found["fortinatus"] = Rect(anchor.x + (anchor.w - size) // 2, anchor.y - size - gap, size, size)
    return [(name, bounds, 0) for name, bounds in found.items()]


def obstacles_on_screen(companions, obstacles, screen_name, projected_companions):
    """Include real destination arrows and their slots during a screen crossing."""
    result = [bounds for bounds, screen in obstacles if screen == screen_name]
    fort = next((r for name, r, _ in projected_companions if name == "fortinatus"), None)
    if fort is None or any(r.y < fort.y for r in result):
        return result
    remote = [(bounds, screen) for bounds, screen in obstacles if screen != screen_name]
    for arrow, source in remote:
        old_fort = next((r for name, r, screen in companions if name == "fortinatus" and screen == source), None)
        if old_fort is not None and arrow.y < old_fort.y:
            result.append(Rect(fort.x + arrow.x - old_fort.x, fort.y + arrow.y - old_fort.y, arrow.w, arrow.h))
            return result
    if remote:
        # Claviernator's orb can arrive one native message before its arrows.
        # Its current arrow design extends 18 logical pixels above the orb.
        arrow = remote[0][0]
        result.append(Rect(fort.x + (fort.w - arrow.w) // 2, fort.y - 18, arrow.w, arrow.h))
    return result


def choose_position(areas, companions=(), saved=None, preferred=0, size=36, obstacles=()):
    """Always occupy the top/third family slot when companions are present.

    companions: (name, rectangle, screen index). Never move another program.
    A cramped top edge cannot satisfy strict order and alignment; use a free
    adjacent column above its centre, then any free visible location.
    """
    if not areas:
        return (0, 0)
    occupied = [r for _, r, _ in companions]
    occupied.extend(Rect(r.x - 10, r.y - 10, r.w + 20, r.h + 20) for r in obstacles)

    def free(p, area):
        rect = Rect(*p, size, size)
        return area.contains(rect) and not any(rect.intersects(r) for r in occupied)

    if saved is not None and not companions:
        for area in areas:
            if free(saved, area):
                return saved
        # Recover on the closest remaining screen, without snapping to the pile.
        nearest = min(areas, key=lambda a: (saved[0] - clamp(saved, a, size)[0]) ** 2 + (saved[1] - clamp(saved, a, size)[1]) ** 2)
        p = clamp(saved, nearest, size)
        if free(p, nearest):
            return p
    anchor = next((c for c in companions if c[0] == "fortinatus"), None)
    anchor = anchor or next(iter(companions), None)
    area = areas[anchor[2] if anchor else min(preferred, len(areas) - 1)]
    if anchor:
        r = min((c[1] for c in companions if c[2] == anchor[2]), key=lambda r: r.y)
        gap = 10
        lower = next((c[1] for c in companions if c[0] == "transcrinator" and c[2] == anchor[2]
                      and c[1].y > r.y and abs(c[1].x + c[1].w / 2 - r.x - r.w / 2) < max(r.w, c[1].w)), None)
        if lower:
            gap = max(4, min(60, lower.y - (r.y + r.h)))
        p = (r.x + (r.w - size) // 2, r.y - gap - size)
        # Keep 10 logical pixels above the upper scroll arrow as well as the
        # orb. Without Transcrinator its spacing cannot be inferred from a pair.
        upper = [o for o in obstacles if o.y < r.y and o.x < p[0] + size and p[0] < o.x + o.w]
        if upper:
            p = (p[0], min(p[1], min(o.y for o in upper) - 10 - size))
    else:
        # Reserve all three family slots even if the other apps start later.
        p = (area.x + area.w - size - 16, area.y + area.h - size - 16 - 2 * (size + 10))
    if free(p, area):
        return p
    x, y = clamp(p, area, size)
    for dy in (0, -size - 10, size + 10):
        for dx in (0, -size - 10, size + 10, -2 * (size + 10), 2 * (size + 10)):
            candidate = clamp((x + dx, y + dy), area, size)
            if free(candidate, area):
                return candidate
    # Bounded scan is only used for exceptional crowded/offscreen layouts.
    for a in areas:
        for yy in range(a.y, a.y + max(1, a.h - size + 1), size + 4):
            for xx in range(a.x, a.x + max(1, a.w - size + 1), size + 4):
                if free((xx, yy), a):
                    return xx, yy
    return clamp(p, area, size)
