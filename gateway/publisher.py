from __future__ import annotations

from typing import List, Optional, Protocol, Tuple


class PublishError(Exception):
    pass


class Publisher(Protocol):
    def publish(self, topic: str, payload: str) -> None: ...


class ListPublisher:
    """In-memory publisher for tests and the simulator. Toggle `online` to simulate an outage."""

    def __init__(self) -> None:
        self.online = True
        self.sent: List[Tuple[str, str]] = []

    def publish(self, topic: str, payload: str) -> None:
        if not self.online:
            raise PublishError("link down")
        self.sent.append((topic, payload))


class MqttPublisher:
    """MQTT over TLS using paho-mqtt (imported lazily; `pip install paho-mqtt`).

    Not exercised by the unit tests: it needs a broker. Use per-device certificates in production.
    """

    def __init__(self, host: str, port: int = 8883, client_id: str = "gateway", ca: Optional[str] = None,
                 cert: Optional[str] = None, key: Optional[str] = None, qos: int = 1):
        import paho.mqtt.client as mqtt  # noqa: WPS433 (deliberately lazy)

        self._qos = qos
        self._c = mqtt.Client(client_id=client_id)
        if ca:
            self._c.tls_set(ca_certs=ca, certfile=cert, keyfile=key)
        self._c.connect(host, port, keepalive=60)
        self._c.loop_start()

    def publish(self, topic: str, payload: str) -> None:
        info = self._c.publish(topic, payload, qos=self._qos)
        info.wait_for_publish(timeout=5)
        if not info.is_published():
            raise PublishError("publish not acknowledged")
