#!/usr/bin/env python3
"""Ideal display brightness for a given date/time based on how high the sun is."""

from datetime import datetime
from zoneinfo import ZoneInfo

from astral import Observer
from astral.sun import elevation

# Location for sun elevation calculations
COIMBRA = Observer(latitude=40.18649320910168, longitude=-8.415928720083361)
COIMBRA_TZ = ZoneInfo("Europe/Lisbon")

# Sun elevation, in degrees, at which the sky is considered fully bright.
# Beyond this the brightness stays at its max, even though the sun keeps climbing.
MAX_SUN_ELEVATION = 30

# Brightness range, in percent, for the displays.
# The brightness is scaled linearly based on the sun elevation.
MIN_BRIGHTNESS = 20
MAX_BRIGHTNESS = 100

def ideal_brightness(when=None):
    """Ideal display brightness for a given date/time based on how high the sun is."""
    if when is None:
        when = datetime.now()
    if when.tzinfo is None:
        when = when.replace(tzinfo=COIMBRA_TZ)
    sun_elevation = max(0, min(elevation(COIMBRA, when), MAX_SUN_ELEVATION))
    return MIN_BRIGHTNESS + (MAX_BRIGHTNESS - MIN_BRIGHTNESS) * sun_elevation / MAX_SUN_ELEVATION


if __name__ == "__main__":
    today = datetime.now(COIMBRA_TZ).replace(hour=0, minute=0, second=0, microsecond=0)
    for hour in range(0, 24):
        when = today.replace(hour=hour)
        print(f"{when:%H:%M} -> {round(ideal_brightness(when))}")
