# rpi-edge-gateway

A small edge gateway for a Raspberry Pi (or any Linux box). It reads field devices, writes every reading to a durable local buffer, and forwards them over MQTT with TLS. If the uplink drops, data waits in the buffer and is replayed in order when the link returns.

```
Modbus RTU / sensors --> normalize --> SQLite buffer --> MQTT (TLS) --> broker / cloud
                                            ^                 |
                                            +-- replay oldest first on reconnect
```

## What is verified, and what is not

| Part | Status |
|---|---|
| Modbus RTU framing (CRC-16, read holding registers, error handling) | Unit tested, including a published CRC test vector |
| Store-and-forward buffer (order, bounded size, restart survival) | Unit tested |
| Gateway loop (outage then ordered replay, partial failure, failing reader) | Unit tested with a fake publisher |
| `python -m gateway` simulation | Runs with no hardware and no broker |
| Real serial transport and a real RS-485 device | **Not tested.** Needs hardware. The reader takes an injected transport function; pyserial is a few lines on top |
| `MqttPublisher` against a real broker | **Not tested.** Needs a broker and certificates |
| Running on a Raspberry Pi as a systemd service | **Not tested.** Unit file and Dockerfile are provided as a starting point |

## Run

```
python3 -m unittest discover -s tests -t . -v     # 21 tests, standard library only
python3 -m gateway --cycles 12 --outage 4-8       # simulated run with an uplink outage
```

The simulator output shows the buffer filling during the outage and draining in order afterwards.

## Layout

- `gateway/modbus.py` CRC-16/MODBUS, request builder, response parser.
- `gateway/readers.py` `ModbusTemperatureReader` (injected transport) and a deterministic `SimulatedReader`.
- `gateway/buffer.py` bounded SQLite FIFO with drop-oldest and a dropped counter.
- `gateway/service.py` poll, buffer, flush, health snapshot.
- `gateway/publisher.py` `MqttPublisher` (paho, lazy import) and `ListPublisher` for tests.
- `deploy/gateway.service` hardened systemd unit. `Dockerfile` for a container run.

## Design decisions

- **Buffer first, publish from the buffer.** An outage delays data instead of losing it.
- **Bounded queue, drop oldest.** A long outage cannot fill the SD card; drops are counted and visible in `health()`.
- **Oldest first, stop at first failure.** Order is preserved and unsent messages stay queued.
- **A failing sensor never stops the loop.** The error is counted and the other readers continue.
- **Hardware behind an interface.** Transport and publisher are injected, so the logic is testable on a laptop.

## Next steps

Wire a real pyserial transport and test against an RS-485 sensor, add BLE readers, publish the health snapshot as its own MQTT topic, add per-device certificates and a read-only root filesystem profile.
