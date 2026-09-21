#!/usr/bin/env python3
"""Apply a full monitor setup: which screens are on, and their resolution,
position, refresh rate and scaling.

Combines display_power (enable/disable) and display_mode (mode/layout): turns
on every screen in the setup, turns off every other screen that is
currently on, then applies the requested resolution and position to the
setup.

Requires:  pip install pyobjc-framework-Quartz

Edit the SETUP list at the start of main() and run: python display_setup.py
"""

import display_mode
import display_power

# ---------- UUIDs of the displays. These are stable across reboots, cable swaps and sleep.

MATROX_1_UUID = "12BEF683-8ABC-4EB7-8C4E-030C66B6D9C2"
MATROX_2_UUID = "FDD86D98-63EA-4F83-B015-D71BDDF3678F"
MATROX_3_UUID = "66372FC2-1198-4E25-8782-B2703B807B0B"
INTERNAL_DISPLAY_UUID = "EBCD5892-224C-49EB-8686-695B5C60D2FC"

# ---------- Display modes to be applied (width, height, hz, scaling)

MATROX_MODE = (3240, 1920, 60, False)
INTERNAL_DISPLAY_MODE = (1920, 1080, 60, False)

# ---------- Predefined setups. The display placed at (0, 0) becomes the main display.

WALL_DISPLAYS = [
    [MATROX_1_UUID, 0, 0, *MATROX_MODE],
    [MATROX_2_UUID, MATROX_MODE[0] * 1, 0, *MATROX_MODE],
    [MATROX_3_UUID, MATROX_MODE[0] * 2, 0, *MATROX_MODE],
]

INTERNAL_DISPLAY = [
    [INTERNAL_DISPLAY_UUID, 0, 0, *INTERNAL_DISPLAY_MODE],
]

ALL_DISPLAYS = [
    [MATROX_1_UUID, -MATROX_MODE[0] * 3, 0, *MATROX_MODE],
    [MATROX_2_UUID, -MATROX_MODE[0] * 2, 0, *MATROX_MODE],
    [MATROX_3_UUID, -MATROX_MODE[0] * 1, 0, *MATROX_MODE],
    [INTERNAL_DISPLAY_UUID, 0, 0, *INTERNAL_DISPLAY_MODE],
]

# --------- Apply a setup

def is_setup_applied(setup):
    """True if the current displays match the setup exactly: the same
    displays are on (no more, no fewer), each in the requested mode and
    position. A setup is a list of (uuid, x, y, width, height, hz, scaling)
    tuples."""
    target_uuids = {uuid for uuid, *_ in setup}
    if display_power.get_enabled_display_uuids() != target_uuids:
        return False
    return display_mode.matches_current_setup(setup)


def apply_setup(setup, permanent=True):
    """Turn on the displays in the setup, turn off every other screen,
    and apply their resolution and position. A setup is a list of
    (uuid, x, y, width, height, hz, scaling) tuples."""
    target_uuids = {uuid for uuid, *_ in setup}
    for uuid in target_uuids:
        display_power.set_display_enabled(uuid, True)
    for uuid in display_power.get_enabled_display_uuids() - target_uuids:
        display_power.set_display_enabled(uuid, False)
    display_mode.apply_modes(setup, permanent)



if __name__ == "__main__":
    apply_setup(INTERNAL_DISPLAY, permanent=False)