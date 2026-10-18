import math
import os
import tempfile
import unittest

from gateway.buffer import Buffer
from gateway.models import normalize, payload_for, topic_for


class BufferTests(unittest.TestCase):
    def test_fifo_order_and_ack(self):
        b = Buffer()
        for i in range(3):
            b.put("t", f"m{i}")
        rows = b.peek(10)
        self.assertEqual([r[2] for r in rows], ["m0", "m1", "m2"])
        b.ack([rows[0][0]])
        self.assertEqual([r[2] for r in b.peek(10)], ["m1", "m2"])
        self.assertEqual(b.depth(), 2)

    def test_bounded_drops_oldest_and_counts(self):
        b = Buffer(max_rows=3)
        dropped = sum(b.put("t", f"m{i}") for i in range(5))
        self.assertEqual(dropped, 2)
        self.assertEqual(b.dropped_total, 2)
        self.assertEqual([r[2] for r in b.peek(10)], ["m2", "m3", "m4"])

    def test_survives_restart(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "buf.db")
            b = Buffer(path)
            b.put("t", "kept")
            b.close()
            self.assertEqual([r[2] for r in Buffer(path).peek(5)], ["kept"])

    def test_invalid_size(self):
        with self.assertRaises(ValueError):
            Buffer(max_rows=0)


class ModelTests(unittest.TestCase):
    def test_scaling(self):
        r = normalize("d1", "temperature", 215, scale=0.1, unit="C", ts=1.0, source="s")
        self.assertEqual(r.value, 21.5)
        self.assertEqual(topic_for("gw", r), "gateway/gw/d1/temperature")
        self.assertEqual(payload_for(r), '{"src":"s","ts":1.0,"u":"C","v":21.5}')

    def test_rejects_non_finite_and_missing_ids(self):
        with self.assertRaises(ValueError):
            normalize("d1", "t", math.nan)
        with self.assertRaises(ValueError):
            normalize("d1", "t", math.inf)
        with self.assertRaises(ValueError):
            normalize("", "t", 1)


if __name__ == "__main__":
    unittest.main()
