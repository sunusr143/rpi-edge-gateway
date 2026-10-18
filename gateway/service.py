from __future__ import annotations

import time
from typing import Callable, Dict, List

from .buffer import Buffer
from .health import cpu_temp_c
from .models import Reading, payload_for, topic_for
from .publisher import PublishError, Publisher
from .readers import Reader


class Gateway:
    """Poll readers, buffer every reading, then forward from the buffer in order.

    Readings are always written to the buffer first and published from it, so an uplink outage
    delays data instead of losing it. A failing reader never stops the others.
    """

    def __init__(self, gateway_id: str, readers: List[Reader], buffer: Buffer, publisher: Publisher,
                 batch: int = 50, clock: Callable[[], float] = time.time):
        self.gateway_id, self.readers, self.buffer, self.publisher, self.batch = gateway_id, readers, buffer, publisher, batch
        self._clock, self._start = clock, clock()
        self.reader_errors = 0
        self.published_total = 0
        self.link_up = True

    def poll_once(self) -> int:
        added = 0
        for reader in self.readers:
            try:
                readings: List[Reading] = reader.read()
            except Exception:  # a bad sensor must not take the gateway down
                self.reader_errors += 1
                continue
            for r in readings:
                self.buffer.put(topic_for(self.gateway_id, r), payload_for(r))
                added += 1
        return added

    def flush(self) -> int:
        """Publish buffered messages oldest first; stop at the first failure and keep the rest."""
        sent = 0
        while True:
            rows = self.buffer.peek(self.batch)
            if not rows:
                break
            done: List[int] = []
            try:
                for id_, topic, payload in rows:
                    self.publisher.publish(topic, payload)
                    done.append(id_)
            except PublishError:
                self.link_up = False
                self.buffer.ack(done)
                sent += len(done)
                break
            self.buffer.ack(done)
            sent += len(done)
            self.link_up = True
        self.published_total += sent
        return sent

    def run_cycle(self) -> Dict[str, int]:
        return {"buffered": self.poll_once(), "published": self.flush()}

    def health(self) -> Dict[str, object]:
        return {
            "gateway_id": self.gateway_id,
            "uptime_s": round(self._clock() - self._start, 1),
            "buffer_depth": self.buffer.depth(),
            "dropped_total": self.buffer.dropped_total,
            "published_total": self.published_total,
            "reader_errors": self.reader_errors,
            "link_up": self.link_up,
            "cpu_temp_c": cpu_temp_c(),
        }
