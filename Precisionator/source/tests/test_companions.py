from services.orb_positioning import Rect
from services.win32 import discover_companions, discover_companion_obstacles


def test_recognises_current_claviernator_name_and_ignores_scroll_arrows():
    orb = Rect(100, 500, 54, 54)
    windows = [(1, 10, "claviernator", Rect(0, 0, 720, 600), False),
               (2, 10, "claviernator · orbe du clavier", orb, True),
               (3, 10, "claviernator · défiler vers le haut", Rect(90, 475, 81, 42), True),
               (4, 10, "tooltip", Rect(10, 10, 40, 40), True)]
    assert discover_companions(windows) == [("fortinatus", orb)]


def test_still_recognises_legacy_fortinatus_and_untitled_transcrinator_orb():
    fort, trans = Rect(50, 400, 36, 36), Rect(50, 446, 36, 36)
    windows = [(1, 10, "fortinatus", Rect(0, 0, 480, 600), False),
               (2, 10, "", fort, True),
               (3, 20, "transcrinator", Rect(0, 0, 600, 700), False),
               (4, 20, "", trans, True)]
    assert discover_companions(windows) == [("fortinatus", fort), ("transcrinator", trans)]


def test_original_widgets_can_be_distinguished_in_same_validation_process():
    fort, trans = Rect(50, 400, 36, 36), Rect(50, 446, 36, 36)
    windows = [(1, 10, "claviernator · orbe du clavier", fort, True),
               (2, 10, "transcrinator · validation", trans, True)]
    assert discover_companions(windows) == [("fortinatus", fort), ("transcrinator", trans)]


def test_visible_arrows_are_separate_obstacles_even_without_transcrinator():
    arrow = Rect(90, 475, 81, 42)
    windows = [(1, 10, "claviernator · orbe du clavier", Rect(100, 500, 54, 54), True),
               (2, 10, "claviernator · défiler vers le haut", arrow, True),
               (3, 10, "claviernator · défiler vers le bas", Rect(90, 540, 81, 42), False)]
    assert discover_companion_obstacles(windows) == [arrow]
