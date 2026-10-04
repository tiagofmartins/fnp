#!/usr/bin/env python3
"""Watches the actions/ folder for action files and carries them out.

An action file's name is either just the action's name (applied once, then
removed immediately), or "<action> <expiry-unix-timestamp>" (kept in
effect — re-applied on every check — until the timestamp is reached, at
which point it is removed without being applied again).

telegram_bot.py writes these files; run this script alongside
controller.py to act on them.
"""

import time
from pathlib import Path

import display_brightness
import display_setup
import sun_brightness

ACTIONS_DIR = Path(__file__).parent / "actions"
CHECK_INTERVAL_SECONDS = 30


def _set_wall_brightness(brightness):
    for uuid, *_ in display_setup.WALL_DISPLAYS:
        display_brightness.set_brightness(uuid, brightness)


def brightness_auto():
    _set_wall_brightness(round(sun_brightness.ideal_brightness()))


def brightness_max():
    _set_wall_brightness(100)


def _parse_action_file(path):
    """(action_name, action_expiry) from an action file's name.
    action_expiry is None if the file has no timestamp suffix. Splits on
    the last space."""
    if " " not in path.name:
        return path.name, None
    action_name, _, action_expiry = path.name.rpartition(" ")
    return action_name, int(action_expiry)


def _group_by_prefix(paths):
    """Group action files by the part of their action name before the
    first underscore (e.g. "content_auto" and "content_random 123" are
    both in the "content" group), since only one action per group should
    ever be in effect at a time."""
    groups = {}
    for path in paths:
        action_name, action_expiry = _parse_action_file(path)
        prefix = action_name.split("_", 1)[0]
        groups.setdefault(prefix, []).append((path, action_name, action_expiry))
    return groups


def check_actions():
    """For each group of action files (see _group_by_prefix), keep only
    the most recently created one and act on it; every other, now
    superseded file in that group is deleted unconditionally."""
    for entries in _group_by_prefix(ACTIONS_DIR.iterdir()).values():
        entries.sort(key=lambda entry: entry[0].stat().st_birthtime, reverse=True)
        winner_path, action_name, action_expiry = entries[0]

        for stale_path, _, _ in entries[1:]:
            stale_path.unlink()

        if action_name == "brightness_auto":
            action = brightness_auto
        elif action_name == "brightness_max":
            action = brightness_max
        else:
            continue

        if action_expiry is None:
            action()
            winner_path.unlink()
        elif time.time() < action_expiry:
            action()
        else:
            winner_path.unlink()


if __name__ == "__main__":
    ACTIONS_DIR.mkdir(exist_ok=True)
    while True:
        check_actions()
        time.sleep(CHECK_INTERVAL_SECONDS)
