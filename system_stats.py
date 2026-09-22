#!/usr/bin/env python3
"""Basic system stats for macOS: CPU load, memory usage and uptime."""

import os
import platform
import re
import subprocess
import time
from datetime import datetime

import psutil

import display_mode

if platform.system() != "Darwin":
    raise RuntimeError("This script is intended for macOS only.")


def cpu_usage():
    """CPU usage as a percentage, overall and per core.
    Takes a few seconds to sample."""
    per_core = psutil.cpu_percent(interval=4, percpu=True)
    return {
        "avg": round(sum(per_core) / len(per_core)),
        "per_core": sorted((round(p) for p in per_core), reverse=True),
    }


def gpu_usage():
    """GPU model, usage percentage and memory in use (GB
    and as a percentage of total system memory — Apple Silicon GPUs share
    unified memory with the rest of the machine, there is no separate VRAM
    budget to measure against). No public API for this exists, so it reads
    the same IORegistry data Activity Monitor's GPU History uses."""
    output = subprocess.run(["ioreg", "-r", "-d", "1", "-c", "IOAccelerator"], capture_output=True, text=True, check=True).stdout
    model = re.search(r'"model" = "([^"]+)"', output).group(1)
    usage = int(re.search(r'"Device Utilization %"=(\d+)', output).group(1))
    memory_in_use = int(re.search(r'"In use system memory"=(\d+)', output).group(1))
    total_memory = psutil.virtual_memory().total
    return {
        "model": model,
        "usage": usage,
        "memory_percent": round(memory_in_use / total_memory * 100),
    }


def memory_usage():
    """Memory usage in GB: total, available and used, plus percent used."""
    memory = psutil.virtual_memory()
    gb = 1024 ** 3
    return {
        "total": round(memory.total / gb, 1),
        "available": round(memory.available / gb, 1),
        "used": round(memory.used / gb, 1),
        "percent": round(memory.percent),
    }


def disk_usage():
    """Disk usage of the main disk, in GB: total, free and used, plus
    percent used. Reads the home directory rather than "/", since on
    modern macOS the user data lives on a separate Data volume,
    reached from the home directory."""
    disk = psutil.disk_usage(os.path.expanduser("~"))
    gb = 1024 ** 3
    return {
        "total": round(disk.total / gb, 1),
        "free": round(disk.free / gb, 1),
        "used": round(disk.used / gb, 1),
        "percent": round(disk.percent),
    }


def uptime():
    """Uptime as a human readable string."""
    uptime_seconds = int(time.time() - psutil.boot_time())
    days, remainder = divmod(uptime_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes = remainder // 60
    return f"{days}d {hours:02d}h {minutes:02d}m"


def boot_date():
    """The date and time the computer booted, as a human readable string."""
    return datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S")


def stats_str():
    """A human-readable string with the main system stats."""
    cpu = cpu_usage()
    gpu = gpu_usage()
    memory = memory_usage()
    disk = disk_usage()
    displays = display_mode.connected_displays()
    up = uptime()
    boot = boot_date()

    displays_str = "\n".join(
        f"Display {i}: {d['width']}x{d['height']} at {d['x']},{d['y']}{' [main]' if d['main'] else ''}"
        for i, d in enumerate(displays, start=1)
    )

    return (
        f"CPU: {cpu['avg']}% usage, {max(cpu['per_core'])}% max core\n"
        f"GPU: {gpu['usage']}% usage, {gpu['memory_percent']}% memory\n"
        f"Memory: {memory['percent']}% ({memory['used']}/{memory['total']}GB)\n"
        f"Disk: {disk['percent']}% ({disk['used']}/{disk['total']}GB)\n"
        f"{displays_str}\n"
        f"Uptime: {up}\n"
        f"Boot date: {boot}"
    )


if __name__ == "__main__":
    print(stats_str())
