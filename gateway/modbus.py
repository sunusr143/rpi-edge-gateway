"""Minimal Modbus RTU framing: CRC-16, read-holding-registers request and response parsing.

Pure Python so it can be tested without hardware. A serial transport (pyserial) is a thin
layer on top and is not exercised by the tests.
"""
from __future__ import annotations

import struct
from typing import List


class ModbusError(Exception):
    pass


def crc16(data: bytes) -> int:
    """CRC-16/MODBUS: polynomial 0xA001 (reflected), initial value 0xFFFF."""
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc


def with_crc(body: bytes) -> bytes:
    return body + struct.pack("<H", crc16(body))  # CRC is sent low byte first


def build_read_holding(slave: int, address: int, count: int) -> bytes:
    if not 1 <= slave <= 247:
        raise ValueError("slave id must be 1..247")
    if not 1 <= count <= 125:
        raise ValueError("register count must be 1..125")
    return with_crc(struct.pack(">BBHH", slave, 0x03, address, count))


def parse_read_holding(frame: bytes, slave: int, count: int) -> List[int]:
    """Validate a function-03 response and return the register values."""
    if len(frame) < 5:
        raise ModbusError("frame too short")
    body, got = frame[:-2], struct.unpack("<H", frame[-2:])[0]
    if crc16(body) != got:
        raise ModbusError("CRC mismatch")
    if body[0] != slave:
        raise ModbusError(f"unexpected slave {body[0]}")
    if body[1] & 0x80:
        raise ModbusError(f"device exception code {body[2]}")
    if body[1] != 0x03:
        raise ModbusError(f"unexpected function {body[1]}")
    if body[2] != count * 2 or len(body) != 3 + body[2]:
        raise ModbusError("byte count does not match request")
    return list(struct.unpack(f">{count}H", body[3:]))


def to_signed(v: int) -> int:
    return v - 0x10000 if v & 0x8000 else v
