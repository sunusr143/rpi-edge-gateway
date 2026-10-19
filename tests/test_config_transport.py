import unittest

from gateway.config import ConfigError, load_config
from gateway.modbus import build_read_holding, with_crc
from gateway.readers import ModbusTemperatureReader
from gateway.transport import make_rtu_transport


class FakeSerial:
    """Records writes and returns a canned response, like a serial port with one device on it."""

    def __init__(self, response=b""):
        self.response, self.written, self.reset_calls = response, [], 0

    def reset_input_buffer(self):
        self.reset_calls += 1

    def write(self, data):
        self.written.append(data)

    def read(self, n):
        return self.response[:n]


class ConfigTests(unittest.TestCase):
    def test_defaults_with_only_required_value(self):
        c = load_config({"MQTT_HOST": "broker.example"})
        self.assertEqual((c.mqtt_port, c.modbus_baud, c.modbus_slave, c.poll_seconds), (8883, 9600, 1, 10.0))
        self.assertIsNone(c.mqtt_ca)

    def test_host_is_required(self):
        with self.assertRaisesRegex(ConfigError, "MQTT_HOST"):
            load_config({})

    def test_invalid_numbers_and_ranges(self):
        for bad in ({"MODBUS_SLAVE": "0"}, {"MODBUS_SLAVE": "x"}, {"MQTT_PORT": "70000"}, {"POLL_SECONDS": "0.1"}, {"POLL_SECONDS": "abc"}):
            with self.assertRaises(ConfigError, msg=str(bad)):
                load_config({"MQTT_HOST": "h", **bad})

    def test_tls_files_must_be_set_together(self):
        with self.assertRaisesRegex(ConfigError, "together"):
            load_config({"MQTT_HOST": "h", "MQTT_CA": "/ca.pem"})
        c = load_config({"MQTT_HOST": "h", "MQTT_CA": "/ca", "MQTT_CERT": "/c", "MQTT_KEY": "/k"})
        self.assertEqual((c.mqtt_ca, c.mqtt_cert, c.mqtt_key), ("/ca", "/c", "/k"))


class TransportTests(unittest.TestCase):
    def test_sends_request_clears_stale_input_and_reads_response(self):
        resp = with_crc(bytes([0x01, 0x03, 0x02, 0x00, 0xFA]))
        ser = FakeSerial(resp)
        out = make_rtu_transport(ser)(build_read_holding(1, 0, 1))
        self.assertEqual((out, ser.reset_calls), (resp, 1))
        self.assertEqual(ser.written, [build_read_holding(1, 0, 1)])

    def test_reader_works_through_the_transport(self):
        ser = FakeSerial(with_crc(bytes([0x01, 0x03, 0x02, 0xFF, 0xCE])))  # 0xFFCE = -50 -> -5.0 C
        r = ModbusTemperatureReader("rtu", "dev", 1, 0, make_rtu_transport(ser)).read()[0]
        self.assertEqual((r.value, r.unit), (-5.0, "C"))

    def test_timeout_gives_short_frame_that_is_rejected(self):
        from gateway.modbus import ModbusError

        reader = ModbusTemperatureReader("rtu", "dev", 1, 0, make_rtu_transport(FakeSerial(b"")))
        with self.assertRaisesRegex(ModbusError, "short"):
            reader.read()


if __name__ == "__main__":
    unittest.main()
