from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Reading:
    device_id: str
    metric: str
    value: float
    unit: str
    ts: float
    source: str


def normalize(device_id: str, metric: str, raw: float, *, scale: float = 1.0, offset: float = 0.0,
              unit: str = "", ts: Optional[float] = None, source: str = "") -> Reading:
    """Turn a raw register or sensor value into a Reading. Rejects NaN and infinity."""
    if not device_id or not metric:
        raise ValueError("device_id and metric are required")
    value = raw * scale + offset
    if not math.isfinite(value):
        raise ValueError(f"non-finite value for {device_id}/{metric}")
    return Reading(device_id, metric, round(value, 4), unit, time.time() if ts is None else ts, source)


def topic_for(gateway_id: str, r: Reading) -> str:
    return f"gateway/{gateway_id}/{r.device_id}/{r.metric}"


def payload_for(r: Reading) -> str:
    return json.dumps({"v": r.value, "u": r.unit, "ts": r.ts, "src": r.source}, separators=(",", ":"), sort_keys=True)
