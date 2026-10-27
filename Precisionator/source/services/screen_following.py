"""Match Transcrinator's compact orb: check every 40 ms, no extra delay."""

# Transcri/app/ui/floating_hub.py: set_state/animate use 40 ms in compact mode
# and clamp_to_screen follows QCursor immediately. Keep this independent of
# decorative animation so the inactive orb follows just as promptly.
FOLLOW_INTERVAL_MS = 40


class ScreenFollower:
    def update(self, now, pointer_screen, orb_screen, blocked=False):
        if blocked or pointer_screen is None or pointer_screen == orb_screen:
            return None
        return pointer_screen
