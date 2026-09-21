#!/usr/bin/env python3
"""Apply resolution, refresh rate, position and scaling to displays
identified by UUID, via Quartz Display Services.
A display already in the requested mode is left untouched.
The display placed at x=0, y=0 becomes the main display.
"""

import Quartz

import display_power


def display_by_uuid(uuid):
    """Resolve a UUID to a display id, or None if not connected."""
    err, ids, count = Quartz.CGGetActiveDisplayList(16, None, None) # type: ignore
    if err:
        raise RuntimeError(f"Unable to get active display list: {err}")
    target = uuid.strip().upper()
    for id in ids[:count]:
        if (display_power.uuid_for_display(id) or "").upper() == target:
            return id
    return None


def mode_matches(mode, width, height, hz, scaling):
    """True if a Quartz display mode satisfies the requested width, height, hz and scaling."""
    mode_logical = (Quartz.CGDisplayModeGetWidth(mode), Quartz.CGDisplayModeGetHeight(mode)) # type: ignore
    mode_hz = Quartz.CGDisplayModeGetRefreshRate(mode) # type: ignore
    mode_pixels = (Quartz.CGDisplayModeGetPixelWidth(mode), Quartz.CGDisplayModeGetPixelHeight(mode)) # type: ignore
    if mode_logical != (width, height):
        return False
    if (mode_pixels != mode_logical) != scaling:
        return False
    if mode_hz and round(mode_hz) != round(hz):
        return False
    return True


def find_mode(display_id, width, height, hz, scaling):
    """Look up the matching mode."""
    options = {"CGDisplayShowDuplicateLowResolutionModes": True}
    modes = Quartz.CGDisplayCopyAllDisplayModes(display_id, options) # type: ignore
    if not modes:
        raise RuntimeError(f"No display modes available for display {display_id}")
    for mode in modes:
        if mode_matches(mode, width, height, hz, scaling):
            return mode
    return None


def matches_current_setup(setup):
    """True if every display in setup is already connected,
    in the requested mode, and at the requested position.
    setup is a list of (uuid, x, y, width, height, hz, scaling)."""
    for uuid, x, y, width, height, hz, scaling in setup:
        display_id = display_by_uuid(uuid)
        if display_id is None:
            return False
        mode = Quartz.CGDisplayCopyDisplayMode(display_id) # type: ignore
        if mode is None or not mode_matches(mode, width, height, hz, scaling):
            return False
        bounds = Quartz.CGDisplayBounds(display_id) # type: ignore
        if (bounds.origin.x, bounds.origin.y) != (x, y):
            return False
    return True


def apply_modes(setup, permanent=True):
    """Apply resolution and position to each display in setup.
    If any display fails, none of the changes take effect.
    setup is a list of (uuid, x, y, width, height, hz, scaling)."""

    # Check that at least one display is placed at (0, 0), so it can become the main display
    if not any((x, y) == (0, 0) for _, x, y, *_ in setup):
        raise RuntimeError("No display is placed at (0, 0), so none would become the main display")

    # Nothing below takes effect until the configuration completes, at the end
    err, cfg = Quartz.CGBeginDisplayConfiguration(None) # type: ignore
    if err:
        raise RuntimeError(f"Could not begin the display configuration: {err}")

    # Iterate over the requested displays, applying their resolution and position.
    # If any of them fails, the whole configuration is cancelled and nothing takes effect.
    try:
        for uuid, x, y, width, height, hz, scaling in setup:
            display_id = display_by_uuid(uuid)
            if display_id is None:
                continue
            curr_mode = Quartz.CGDisplayCopyDisplayMode(display_id) # type: ignore
            if curr_mode is None or not mode_matches(curr_mode, width, height, hz, scaling):
                mode = find_mode(display_id, width, height, hz, scaling)
                if mode is None:
                    raise RuntimeError(f"Could not find display mode {[width, height, hz, scaling]} for {uuid}")
                err = Quartz.CGConfigureDisplayWithDisplayMode(cfg, display_id, mode, None) # type: ignore
                if err:
                    raise RuntimeError(f"Could not set display mode {[width, height, hz, scaling]} for {uuid}: {err}")
            err = Quartz.CGConfigureDisplayOrigin(cfg, display_id, x, y) # type: ignore
            if err:
                raise RuntimeError(f"Could not set display origin ({x}, {y}) for {uuid}: {err}")
    except Exception:
        Quartz.CGCancelDisplayConfiguration(cfg) # type: ignore
        raise

    # Complete the display configuration
    scope = (Quartz.kCGConfigurePermanently if permanent else Quartz.kCGConfigureForSession) # type: ignore
    err = Quartz.CGCompleteDisplayConfiguration(cfg, scope) # type: ignore
    if err:
        raise RuntimeError(f"Could not complete the display configuration: {err}")


if __name__ == "__main__":
    setup = [
        ["E42C0358-631A-4751-8F07-9D5845943151", 0, 0, 3240, 1920, 60, False]
    ]
    apply_modes(setup, permanent=False)