"""Production entrypoint:  python -m gateway.run   (configured through environment variables).

Reads one Modbus RTU temperature register, buffers it, and forwards over MQTT with TLS.
Stops cleanly on SIGTERM or SIGINT so systemd and Docker can restart or stop it safely.
"""
from __future__ import annotations

import json
import os
import signal
import sys
import threading

from .buffer import Buffer
from .config import ConfigError, load_config
from .publisher import MqttPublisher
from .readers import ModbusTemperatureReader
from .service import Gateway
from .transport import make_rtu_transport, open_serial

HEALTH_EVERY_N_CYCLES = 6


def main() -> int:
    try:
        cfg = load_config(os.environ)
    except ConfigError as e:
        print(f"configuration error: {e}", file=sys.stderr)
        return 2

    stop = threading.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stop.set())

    reader = ModbusTemperatureReader(
        "rtu-1", cfg.device_id, cfg.modbus_slave, cfg.modbus_address,
        make_rtu_transport(open_serial(cfg.modbus_port, cfg.modbus_baud)),
    )
    buf = Buffer(cfg.buffer_path, cfg.buffer_max_rows)
    pub = MqttPublisher(cfg.mqtt_host, cfg.mqtt_port, cfg.gateway_id, cfg.mqtt_ca, cfg.mqtt_cert, cfg.mqtt_key)
    gw = Gateway(cfg.gateway_id, [reader], buf, pub)

    cycle = 0
    while not stop.is_set():
        cycle += 1
        gw.run_cycle()
        if cycle % HEALTH_EVERY_N_CYCLES == 0:
            print(json.dumps(gw.health()), flush=True)
        stop.wait(cfg.poll_seconds)  # sleeps, but wakes immediately on shutdown
    buf.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
