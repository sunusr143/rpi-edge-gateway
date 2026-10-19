from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional


class ConfigError(Exception):
    pass


@dataclass(frozen=True)
class Config:
    gateway_id: str
    poll_seconds: float
    buffer_path: str
    buffer_max_rows: int
    device_id: str
    modbus_port: str
    modbus_baud: int
    modbus_slave: int
    modbus_address: int
    mqtt_host: str
    mqtt_port: int
    mqtt_ca: Optional[str]
    mqtt_cert: Optional[str]
    mqtt_key: Optional[str]


def _int(env: Mapping[str, str], key: str, default: int, lo: int, hi: int) -> int:
    raw = env.get(key, str(default))
    try:
        v = int(raw)
    except ValueError:
        raise ConfigError(f"{key} must be an integer, got {raw!r}") from None
    if not lo <= v <= hi:
        raise ConfigError(f"{key} must be between {lo} and {hi}, got {v}")
    return v


def load_config(env: Mapping[str, str]) -> Config:
    """Build a Config from environment variables. Only MQTT_HOST is required."""
    host = env.get("MQTT_HOST", "").strip()
    if not host:
        raise ConfigError("MQTT_HOST is required")
    try:
        poll = float(env.get("POLL_SECONDS", "10"))
    except ValueError:
        raise ConfigError("POLL_SECONDS must be a number") from None
    if not 0.5 <= poll <= 3600:
        raise ConfigError("POLL_SECONDS must be between 0.5 and 3600")
    tls = [env.get("MQTT_CA"), env.get("MQTT_CERT"), env.get("MQTT_KEY")]
    if any(tls) and not all(tls):
        raise ConfigError("MQTT_CA, MQTT_CERT and MQTT_KEY must be set together")
    return Config(
        gateway_id=env.get("GATEWAY_ID", "gw-01"),
        poll_seconds=poll,
        buffer_path=env.get("BUFFER_PATH", "/var/lib/gateway/buffer.db"),
        buffer_max_rows=_int(env, "BUFFER_MAX_ROWS", 50_000, 1, 10_000_000),
        device_id=env.get("DEVICE_ID", "sensor-1"),
        modbus_port=env.get("MODBUS_PORT", "/dev/ttyUSB0"),
        modbus_baud=_int(env, "MODBUS_BAUD", 9600, 1200, 921_600),
        modbus_slave=_int(env, "MODBUS_SLAVE", 1, 1, 247),
        modbus_address=_int(env, "MODBUS_ADDRESS", 0, 0, 65_535),
        mqtt_host=host,
        mqtt_port=_int(env, "MQTT_PORT", 8883, 1, 65_535),
        mqtt_ca=tls[0] or None,
        mqtt_cert=tls[1] or None,
        mqtt_key=tls[2] or None,
    )
