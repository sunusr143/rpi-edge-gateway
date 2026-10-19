from __future__ import annotations

from typing import Callable


def make_rtu_transport(ser, response_len: int = 7) -> Callable[[bytes], bytes]:
    """Wrap a serial-like object (write, read, reset_input_buffer) as a Modbus RTU transport.

    A function-03 response for N registers is 5 + 2*N bytes (address, function, byte count,
    data, 2 CRC bytes), so the default of 7 fits a single register. A short read returns fewer
    bytes and is rejected by the frame parser, which is what we want on a timeout.
    """

    def transport(request: bytes) -> bytes:
        ser.reset_input_buffer()  # drop stale bytes from a previous, timed-out exchange
        ser.write(request)
        return ser.read(response_len)

    return transport


def open_serial(port: str, baud: int, timeout: float = 0.5):
    """Open a real serial port (8N1). Needs `pip install pyserial`; not exercised by unit tests."""
    import serial  # lazy: only needed on the device

    return serial.Serial(port, baudrate=baud, bytesize=8, parity="N", stopbits=1, timeout=timeout)
