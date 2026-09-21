#!/usr/bin/env python3
"""Enable and disable macOS displays from Python, addressing them by UUID.

Meant to be imported:

    import display_power

    display_power.set_display_enabled(uuid, False)    # turn a screen off
    display_power.set_display_enabled(uuid, True)     # turn it back on
    display_power.is_display_enabled(uuid)            # True / False
    display_power.get_enabled_display_uuids()         # {uuid, ...} of screens on

Why UUID: macOS gives every display a small numeric id that changes across
reboots, cable swaps and sleep. A display UUID comes from its EDID and stays
put, so that is what this module takes and returns. It keeps no state of its
own; the caller holds the list of UUIDs it cares about.

How it works: there is no public API to switch a display on or off, so we call
a private CoreGraphics function directly. A separate, documented pair of
functions converts between the numeric id and the UUID.

Things to know:
  - A disabled display drops out of every macOS query and can no longer be
    looked up by UUID. To turn one back on we briefly wake every display, note
    which UUID each one has, and switch back off the ones we did not want.
  - Changes only last for the current login session. A logout or reboot brings
    every display back.
  - The private function is undocumented and could stop working after a macOS
    update.
"""

from __future__ import annotations

import ctypes

import Quartz

# Make one ordinary CoreGraphics call before anything else. It opens the
# connection to the window server that the private functions below depend on;
# without it they abort when this module is the first thing to touch
# CoreGraphics in a process.
Quartz.CGMainDisplayID() # type: ignore

MAX_DISPLAYS = 16       # generous upper bound for the display-list calls
_APPLY_FOR_SESSION = 1  # CGConfigureOption value: keep the change until logout


# --- Private CoreGraphics: the only way to enable/disable a display ----------

_core_graphics = ctypes.CDLL(
    "/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics"
)

_core_graphics.CGBeginDisplayConfiguration.argtypes = [
    ctypes.POINTER(ctypes.c_void_p)
]
_core_graphics.CGBeginDisplayConfiguration.restype = ctypes.c_int32

_core_graphics.CGSConfigureDisplayEnabled.argtypes = [
    ctypes.c_void_p,
    ctypes.c_uint32,
    ctypes.c_bool,
]
_core_graphics.CGSConfigureDisplayEnabled.restype = None

_core_graphics.CGCompleteDisplayConfiguration.argtypes = [
    ctypes.c_void_p,
    ctypes.c_uint32,
]
_core_graphics.CGCompleteDisplayConfiguration.restype = ctypes.c_int32

# Lists every display the window server knows about, disabled ones included.
# The public CGGetOnlineDisplayList hides displays that are switched off.
_core_graphics.CGSGetDisplayList.argtypes = [
    ctypes.c_uint32,
    ctypes.POINTER(ctypes.c_uint32),
    ctypes.POINTER(ctypes.c_uint32),
]
_core_graphics.CGSGetDisplayList.restype = ctypes.c_int32


def _set_display_id_enabled(display_id: int, enabled: bool) -> None:
    """Switch one display on or off by its numeric id.

    Raises RuntimeError if macOS refuses the change, which happens for ids that
    are not real displays (internal framebuffers that show up in the id list).
    """
    config = ctypes.c_void_p()
    if _core_graphics.CGBeginDisplayConfiguration(ctypes.byref(config)) != 0:
        raise RuntimeError("could not begin a display configuration")
    _core_graphics.CGSConfigureDisplayEnabled(config, display_id, enabled)
    if _core_graphics.CGCompleteDisplayConfiguration(
        config, _APPLY_FOR_SESSION
    ) != 0:
        raise RuntimeError("could not apply the display configuration")


# --- ColorSync: convert between a display numeric id and its UUID ------------

_color_sync = ctypes.CDLL(
    "/System/Library/Frameworks/ColorSync.framework/ColorSync"
)
_core_foundation = ctypes.CDLL(
    "/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation"
)

_color_sync.CGDisplayCreateUUIDFromDisplayID.argtypes = [ctypes.c_uint32]
_color_sync.CGDisplayCreateUUIDFromDisplayID.restype = ctypes.c_void_p
_color_sync.CGDisplayGetDisplayIDFromUUID.argtypes = [ctypes.c_void_p]
_color_sync.CGDisplayGetDisplayIDFromUUID.restype = ctypes.c_uint32

_core_foundation.CFUUIDCreateString.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
_core_foundation.CFUUIDCreateString.restype = ctypes.c_void_p
_core_foundation.CFUUIDCreateFromString.argtypes = [
    ctypes.c_void_p,
    ctypes.c_void_p,
]
_core_foundation.CFUUIDCreateFromString.restype = ctypes.c_void_p
_core_foundation.CFStringCreateWithCString.argtypes = [
    ctypes.c_void_p,
    ctypes.c_char_p,
    ctypes.c_uint32,
]
_core_foundation.CFStringCreateWithCString.restype = ctypes.c_void_p
_core_foundation.CFStringGetCString.argtypes = [
    ctypes.c_void_p,
    ctypes.c_char_p,
    ctypes.c_long,
    ctypes.c_uint32,
]
_core_foundation.CFStringGetCString.restype = ctypes.c_bool
_core_foundation.CFRelease.argtypes = [ctypes.c_void_p]
_core_foundation.CFRelease.restype = None

_UTF8 = 0x08000100  # kCFStringEncodingUTF8


def uuid_for_display(display_id: int) -> str | None:
    """The stable UUID for a display id.

    Returns None when the display has no UUID: it is switched off, or it is an
    internal framebuffer rather than a real screen.
    """
    cf_uuid = _color_sync.CGDisplayCreateUUIDFromDisplayID(display_id)
    if not cf_uuid:
        return None
    try:
        cf_string = _core_foundation.CFUUIDCreateString(None, cf_uuid)
        try:
            buffer = ctypes.create_string_buffer(64)
            if not _core_foundation.CFStringGetCString(
                cf_string, buffer, len(buffer), _UTF8
            ):
                return None
            return buffer.value.decode().upper()
        finally:
            _core_foundation.CFRelease(cf_string)
    finally:
        _core_foundation.CFRelease(cf_uuid)


def display_for_uuid(uuid: str) -> int | None:
    """The current display id for a UUID, or None if no display matches.

    Careful: macOS hands back a fallback id for a well-formed but unknown UUID
    instead of nothing. Confirm with uuid_for_display() when it matters.
    """
    cf_string = _core_foundation.CFStringCreateWithCString(
        None, uuid.encode(), _UTF8
    )
    if not cf_string:
        return None
    try:
        cf_uuid = _core_foundation.CFUUIDCreateFromString(None, cf_string)
        if not cf_uuid:
            return None
        try:
            return _color_sync.CGDisplayGetDisplayIDFromUUID(cf_uuid) or None
        finally:
            _core_foundation.CFRelease(cf_uuid)
    finally:
        _core_foundation.CFRelease(cf_string)


# --- Listing displays -------------------------------------------------------

def _get_display_id_list(list_function) -> list[int]:
    error, ids, _ = list_function(MAX_DISPLAYS, None, None)
    if error != 0:
        raise RuntimeError(f"{list_function.__name__} failed (error {error})")
    return list(ids)


def _enabled_display_ids() -> list[int]:
    """Ids of displays that are switched on and part of the desktop."""
    return _get_display_id_list(Quartz.CGGetActiveDisplayList) # type: ignore


def _all_display_ids() -> list[int]:
    """Ids of every display, including the ones currently switched off."""
    buffer = (ctypes.c_uint32 * MAX_DISPLAYS)()
    count = ctypes.c_uint32(0)
    if _core_graphics.CGSGetDisplayList(
        MAX_DISPLAYS, buffer, ctypes.byref(count)
    ) != 0:
        raise RuntimeError("CGSGetDisplayList failed")
    return list(buffer)[: count.value]


# --- Waking a switched-off display ----------------------------------------

def _enable_display(uuid: str) -> None:
    """Switch on the display with this UUID, leaving the others as they are.

    A switched-off display is invisible to macOS until something wakes it, and
    while it is off we cannot tell which id belongs to which UUID. So we wake
    every display, then switch back off everything that just woke up apart from
    the one we actually asked for.
    """
    keep = get_enabled_display_uuids() | {uuid}
    already_on = set(_enabled_display_ids())

    for display_id in _all_display_ids():
        if display_id not in already_on:
            try:
                _set_display_id_enabled(display_id, True)
            except RuntimeError:
                pass  # not a real display; nothing to do

    for display_id in set(_enabled_display_ids()) - already_on:
        if uuid_for_display(display_id) not in keep:
            try:
                _set_display_id_enabled(display_id, False)
            except RuntimeError:
                pass


# --- Public API ------------------------------------------------------------

def get_enabled_display_uuids() -> set[str]:
    """The UUIDs of the displays that are currently switched on.

    A switched-off display has no resolvable UUID, so there is no way to report
    one here: it is simply absent from the set.
    """
    return {
        uuid
        for uuid in (uuid_for_display(d) for d in _enabled_display_ids())
        if uuid
    }


def is_display_enabled(uuid: str) -> bool:
    """True if the display with this UUID is switched on, False otherwise.

    "Otherwise" also covers a display that is switched off or a UUID that does
    not match any display at all: a switched-off display cannot be resolved by
    UUID, so it is indistinguishable from an unknown one.
    """
    return uuid.upper() in get_enabled_display_uuids()


def set_display_enabled(uuid: str, enabled: bool) -> None:
    """Switch one display on or off, addressed by its UUID.

    Enabling touches only this display; whatever is already on stays on.
    Disabling the current main display is fine, macOS moves "main" to another
    screen (and usually moves it back once this one returns). Disabling the
    last screen that is still on is refused.
    """
    uuid = uuid.upper()
    enabled_uuids = get_enabled_display_uuids()

    if enabled:
        if uuid not in enabled_uuids:
            _enable_display(uuid)
        return

    if uuid not in enabled_uuids:
        return  # already off, or not a display we know
    if not (enabled_uuids - {uuid}):
        raise ValueError("refusing to disable the last display that is on")
    display_id = display_for_uuid(uuid)
    if display_id is not None:
        _set_display_id_enabled(display_id, False)


if __name__ == "__main__":
    print(get_enabled_display_uuids())
    # NAMES = {
    #     "5F1A1BE1-9054-4517-AB13-34FD9AF00C00": "top",
    #     "C22E9726-1F0D-4ADE-AC55-C542DFB292B3": "bottom",
    # }
    # for display_uuid in sorted(get_enabled_display_uuids()):
    #     print(f"{NAMES.get(display_uuid, '?'):8} {display_uuid}")