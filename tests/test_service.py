import unittest

from gateway.buffer import Buffer
from gateway.modbus import with_crc
from gateway.publisher import ListPublisher
from gateway.readers import ModbusTemperatureReader, SimulatedReader
from gateway.service import Gateway


def make(readers=None, **kw):
    pub = ListPublisher()
    return Gateway("gw", readers or [SimulatedReader("a", "dev-a")], Buffer(), pub, **kw), pub


class ServiceTests(unittest.TestCase):
    def test_happy_path_publishes_and_drains(self):
        gw, pub = make()
        r = gw.run_cycle()
        self.assertEqual(r, {"buffered": 1, "published": 1})
        self.assertEqual(gw.buffer.depth(), 0)
        self.assertTrue(pub.sent[0][0].startswith("gateway/gw/dev-a/temperature"))

    def test_outage_buffers_then_replays_in_order(self):
        gw, pub = make()
        pub.online = False
        for _ in range(4):
            gw.run_cycle()
        self.assertEqual(gw.buffer.depth(), 4)
        self.assertFalse(gw.link_up)
        self.assertEqual(pub.sent, [])
        pub.online = True
        gw.run_cycle()
        self.assertEqual(len(pub.sent), 5)
        self.assertEqual(gw.buffer.depth(), 0)
        times = [__import__("json").loads(p)["ts"] for _, p in pub.sent]
        self.assertEqual(times, sorted(times))
        self.assertTrue(gw.link_up)

    def test_partial_failure_keeps_unsent_messages(self):
        gw, pub = make(batch=10)
        pub.online = False
        for _ in range(3):
            gw.poll_once()
        sent_before = []

        class Flaky(ListPublisher):
            def publish(self, topic, payload):
                if len(self.sent) == 2:
                    self.online = False
                super().publish(topic, payload)

        gw.publisher = Flaky()
        gw.flush()
        self.assertEqual(len(gw.publisher.sent), 2)
        self.assertEqual(gw.buffer.depth(), 1)

    def test_failing_reader_does_not_stop_others(self):
        bad = SimulatedReader("bad", "dev-b", fail_on={1})
        gw, pub = make([bad, SimulatedReader("ok", "dev-a")])
        gw.run_cycle()
        self.assertEqual(gw.reader_errors, 1)
        self.assertEqual(len(pub.sent), 1)

    def test_modbus_reader_end_to_end_with_fake_transport(self):
        resp = with_crc(bytes([0x05, 0x03, 0x02, 0x00, 0xFA]))  # 25.0 C
        reader = ModbusTemperatureReader("rtu", "dev-5", 5, 0, lambda req: resp)
        gw, pub = make([reader])
        gw.run_cycle()
        self.assertIn('"v":25.0', pub.sent[0][1])

    def test_modbus_crc_error_counts_as_reader_error(self):
        bad = bytearray(with_crc(bytes([0x05, 0x03, 0x02, 0x00, 0xFA])))
        bad[-1] ^= 1
        gw, pub = make([ModbusTemperatureReader("rtu", "dev-5", 5, 0, lambda req: bytes(bad))])
        gw.run_cycle()
        self.assertEqual((gw.reader_errors, len(pub.sent)), (1, 0))

    def test_health_snapshot(self):
        gw, pub = make()
        pub.online = False
        gw.run_cycle()
        h = gw.health()
        self.assertEqual((h["buffer_depth"], h["link_up"], h["published_total"]), (1, False, 0))


if __name__ == "__main__":
    unittest.main()
