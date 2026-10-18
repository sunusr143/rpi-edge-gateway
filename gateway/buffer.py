from __future__ import annotations

import sqlite3
import threading
from typing import List, Sequence, Tuple


class Buffer:
    """Durable, bounded FIFO queue on SQLite for store-and-forward.

    Messages are replayed oldest first. When the queue is full the oldest messages are dropped
    (and counted), so a long outage cannot fill the SD card.
    """

    def __init__(self, path: str = ":memory:", max_rows: int = 10_000):
        if max_rows < 1:
            raise ValueError("max_rows must be >= 1")
        self.max_rows = max_rows
        self.dropped_total = 0
        self._lock = threading.Lock()
        self._db = sqlite3.connect(path, check_same_thread=False)
        self._db.execute("CREATE TABLE IF NOT EXISTS q (id INTEGER PRIMARY KEY AUTOINCREMENT, topic TEXT NOT NULL, payload TEXT NOT NULL)")
        self._db.commit()

    def put(self, topic: str, payload: str) -> int:
        """Add a message. Returns how many old messages were dropped to make room."""
        with self._lock, self._db:
            self._db.execute("INSERT INTO q (topic, payload) VALUES (?, ?)", (topic, payload))
            (n,) = self._db.execute("SELECT COUNT(*) FROM q").fetchone()
            over = n - self.max_rows
            if over > 0:
                self._db.execute("DELETE FROM q WHERE id IN (SELECT id FROM q ORDER BY id LIMIT ?)", (over,))
                self.dropped_total += over
                return over
        return 0

    def peek(self, n: int) -> List[Tuple[int, str, str]]:
        with self._lock:
            return list(self._db.execute("SELECT id, topic, payload FROM q ORDER BY id LIMIT ?", (n,)))

    def ack(self, ids: Sequence[int]) -> None:
        if not ids:
            return
        with self._lock, self._db:
            self._db.executemany("DELETE FROM q WHERE id = ?", [(i,) for i in ids])

    def depth(self) -> int:
        with self._lock:
            return self._db.execute("SELECT COUNT(*) FROM q").fetchone()[0]

    def close(self) -> None:
        self._db.close()
