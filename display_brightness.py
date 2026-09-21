#!/usr/bin/env python3
"""Set a display's brightness by UUID, via the BetterDisplay CLI.

Requires BetterDisplay (https://betterdisplay.pro) to be installed,
with "Enable CLI access" turned on in its settings.
"""

import subprocess

BETTERDISPLAY = "/Applications/BetterDisplay.app/Contents/MacOS/BetterDisplay"


def set_brightness(uuid, brightness):
    """Set the brightness of the display with this UUID. brightness is 0-100."""
    subprocess.run([BETTERDISPLAY, "set", f"-UUID={uuid}", f"-brightness={brightness / 100}"], check=True)


if __name__ == "__main__":
    set_brightness("E42C0358-631A-4751-8F07-9D5845943151", 80)
