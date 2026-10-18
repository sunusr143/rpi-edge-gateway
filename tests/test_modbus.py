import unittest

from gateway.modbus import ModbusError, build_read_holding, crc16, parse_read_holding, to_signed, with_crc


class ModbusTests(unittest.TestCase):
    def test_crc16_known_vector(self):
        # Widely published example: read 10 holding registers from slave 1 starting at 0.
        self.assertEqual(crc16(bytes([0x01, 0x03, 0x00, 0x00, 0x00, 0x0A])), 0xCDC5)

    def test_request_frame_matches_known_bytes(self):
        self.assertEqual(build_read_holding(1, 0, 10).hex(), "010300000" "00ac5cd")

    def test_parse_valid_response(self):
        frame = with_crc(bytes([0x01, 0x03, 0x04, 0x00, 0xFA, 0xFF, 0xF6]))
        self.assertEqual(parse_read_holding(frame, 1, 2), [250, 65526])
        self.assertEqual(to_signed(65526), -10)

    def test_bad_crc_rejected(self):
        frame = bytearray(with_crc(bytes([0x01, 0x03, 0x02, 0x00, 0xFA])))
        frame[3] ^= 0xFF
        with self.assertRaisesRegex(ModbusError, "CRC"):
            parse_read_holding(bytes(frame), 1, 1)

    def test_exception_response_rejected(self):
        with self.assertRaisesRegex(ModbusError, "exception code 2"):
            parse_read_holding(with_crc(bytes([0x01, 0x83, 0x02])), 1, 1)

    def test_wrong_slave_and_short_frame(self):
        with self.assertRaisesRegex(ModbusError, "slave"):
            parse_read_holding(with_crc(bytes([0x02, 0x03, 0x02, 0x00, 0x01])), 1, 1)
        with self.assertRaisesRegex(ModbusError, "short"):
            parse_read_holding(b"\x01\x03", 1, 1)

    def test_byte_count_mismatch(self):
        with self.assertRaisesRegex(ModbusError, "byte count"):
            parse_read_holding(with_crc(bytes([0x01, 0x03, 0x04, 0x00, 0x01, 0x00, 0x02])), 1, 1)

    def test_request_argument_limits(self):
        with self.assertRaises(ValueError):
            build_read_holding(0, 0, 1)
        with self.assertRaises(ValueError):
            build_read_holding(1, 0, 126)


if __name__ == "__main__":
    unittest.main()
