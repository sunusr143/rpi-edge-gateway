from __future__ import annotations

import math
from typing import List, Optional, Protocol

from .models import Reading, normalize
from .modbus import build_read_holding, parse_read_holding, to_signed


class Reader(Protocol):
    name: str

    def read(self) -> List[Reading]: ...


class ModbusTemperatureReader:
    """Reads one signed holding register (tenths of a degree C) through an injected transport.

    `transport(request: bytes) -> bytes` sends a frame and returns the response frame. With
    pyserial that is a few lines around `Serial.write` and `Serial.read`; tests inject a fake.
    """

    def __init__(self, name: str, device_id: str, slave: int, address: int, transport):
        self.name, self.device_id, self.slave, self.address, self.transport = name, device_id, slave, address, transport

    def read(self) -> List[Reading]:
        frame = self.transport(build_read_holding(self.slave, self.address, 1))
        (raw,) = parse_read_holding(frame, self.slave, 1)
        return [normalize(self.device_id, "temperature", to_signed(raw), scale=0.1, unit="C", source=self.name)]


class SimulatedReader:
    """Deterministic sensor for demos and tests. Fails on the cycles listed in `fail_on`."""

    def __init__(self, name: str, device_id: str, base: float = 21.0, fail_on: Optional[set] = None):
        self.name, self.device_id, self.base, self.fail_on, self.n = name, device_id, base, fail_on or set(), 0

    def read(self) -> List[Reading]:
        self.n += 1
        if self.n in self.fail_on:
            raise IOError("simulated sensor fault")
        return [normalize(self.device_id, "temperature", self.base + 2 * math.sin(self.n / 5), unit="C", source=self.name)]
