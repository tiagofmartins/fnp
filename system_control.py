#!/usr/bin/env python3
"""Cursor and screen capture control for macOS."""

import platform

import Quartz
from PIL import Image

import display_mode

if platform.system() != "Darwin":
    raise RuntimeError("This script is intended for macOS only.")


def hide_cursor():
    """Hide the mouse cursor by moving it to the bottom-right corner of the rightmost display."""
    displays = display_mode.connected_displays()
    rightmost = max(displays, key=lambda d: d["x"] + d["width"])
    x = rightmost["x"] + rightmost["width"]
    y = rightmost["y"] + rightmost["height"]
    Quartz.CGWarpMouseCursorPosition((x, y)) # type: ignore


def _capture_display(display):
    """Screenshot one display (as returned by display_mode.connected_displays())
    as a PIL Image, sized to its logical width/height."""
    rect = Quartz.CGRectMake(display["x"], display["y"], display["width"], display["height"]) # type: ignore
    cg_image = Quartz.CGWindowListCreateImage(rect, Quartz.kCGWindowListOptionOnScreenOnly, Quartz.kCGNullWindowID, Quartz.kCGWindowImageDefault) # type: ignore
    width = Quartz.CGImageGetWidth(cg_image) # type: ignore
    height = Quartz.CGImageGetHeight(cg_image) # type: ignore
    bytes_per_row = Quartz.CGImageGetBytesPerRow(cg_image) # type: ignore
    data = Quartz.CGDataProviderCopyData(Quartz.CGImageGetDataProvider(cg_image)) # type: ignore
    image = Image.frombuffer("RGBA", (width, height), bytes(data), "raw", "BGRA", bytes_per_row, 1)
    if (width, height) != (display["width"], display["height"]):
        image = image.resize((display["width"], display["height"]))
    return image


def screenshot_all_displays():
    """Screenshot every connected display and combine them into a single
    PIL Image, arranged at their real relative positions."""
    displays = display_mode.connected_displays()
    min_x = min(d["x"] for d in displays)
    min_y = min(d["y"] for d in displays)
    canvas_width = max(d["x"] + d["width"] for d in displays) - min_x
    canvas_height = max(d["y"] + d["height"] for d in displays) - min_y
    canvas = Image.new("RGB", (canvas_width, canvas_height))
    for d in displays:
        canvas.paste(_capture_display(d), (d["x"] - min_x, d["y"] - min_y))
    return canvas


if __name__ == "__main__":
    hide_cursor()
    #screenshot_all_displays().save("screenshot.png")
