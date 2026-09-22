#!/usr/bin/env python3
"""Daily display controller.

At WALL_ON_TIME, switches to the WALL_DISPLAYS setup and launches the
wall's content, keeping its brightness in sync with the sun every
BRIGHTNESS_INTERVAL_MINUTES. At WALL_OFF_TIME, stops the content and
switches to the INTERNAL_DISPLAY setup.

Runs forever in a polling loop; leave it running in a terminal or under
launchd.
"""

import subprocess
import time
from datetime import datetime, timedelta
from datetime import time as dtime

import display_brightness
import display_setup
import sun_brightness

WALL_ON_TIME = dtime(10, 5)
WALL_OFF_TIME = dtime(10, 10)
BRIGHTNESS_INTERVAL_MINUTES = 5
CHECK_INTERVAL_SECONDS = 30

WALL_CONTENT_COMMAND = ["/Users/voronoi/processing", "cli", "--sketch=example", "--run"]


def stop_content(process):
    """Stop the content, nicely if possible, by force if not."""
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def update_wall_displays_brightness():
    brightness = round(sun_brightness.ideal_brightness())
    for uuid, *_ in display_setup.WALL_DISPLAYS:
        display_brightness.set_brightness(uuid, brightness)


def main():
    content_process = None
    last_brightness_update = None

    while True:
        now = datetime.now()

        if WALL_ON_TIME <= now.time() < WALL_OFF_TIME:

            if not display_setup.is_setup_applied(display_setup.WALL_DISPLAYS):
                display_setup.apply_setup(display_setup.WALL_DISPLAYS)
                time.sleep(10)
            
            if (last_brightness_update is None or now - last_brightness_update >= timedelta(minutes=BRIGHTNESS_INTERVAL_MINUTES)):
                update_wall_displays_brightness()
                last_brightness_update = now

            if content_process is None:
                content_process = subprocess.Popen(WALL_CONTENT_COMMAND)                
        
        else:
            if content_process is not None:
                stop_content(content_process)
                content_process = None
                time.sleep(5)
            
            if not display_setup.is_setup_applied(display_setup.INTERNAL_DISPLAY):
                display_setup.apply_setup(display_setup.INTERNAL_DISPLAY)

        time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
