from __future__ import annotations

from typing import Optional


def cpu_temp_c(path: str = "/sys/class/thermal/thermal_zone0/temp") -> Optional[float]:
    """CPU temperature on Linux boards such as the Raspberry Pi. None where unavailable."""
    try:
        with open(path) as f:
            return int(f.read().strip()) / 1000.0
    except (OSError, ValueError):
        return None
