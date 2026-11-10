"""Names for what the moth is doing.

The lifecycle the brief asked for is still here: rapid input is "working",
and five quiet minutes is "sleeping". The extra names are the moth's own
voice for those same moments, plus the in-between and the focus ritual.
"""

from __future__ import annotations

SLEEPING = "sleeping"
CALM = "calm"
WORKING = "working"
SCATTER = "scatter"
FOCUS = "focus"

# Asset filenames match these ids. FOCUS is chosen in the window, not by the tracker.
TRACKED_STATES = (SLEEPING, CALM, WORKING, SCATTER)

# (spoken name, plain status)
CAPTION = {
    SLEEPING: ("Dusk", "sleeping"),
    CALM: ("Drift", "with you"),
    WORKING: ("Glimmer", "working"),
    SCATTER: ("Flicker", "working"),
    FOCUS: ("Vigil", "focus"),
}
