"""Transport cleanup tests for the serial client wrapper."""

import socket

from client import serial_client


def test_serial_startup_banner_does_not_break_connect(monkeypatch):
    class FakeSerial:
        def __init__(self, **kwargs):
            self.incoming = bytearray(
                b"STM32 SERIAL SERVER READY\r\nOK\r\n"
            )
            self.written = []

        def read(self, size):
            if not self.incoming:
                return b""

            byte = self.incoming[:size]
            del self.incoming[:size]
            return bytes(byte)

        def write(self, data):
            self.written.append(data)
            return len(data)

        def close(self):
            pass

    fake_serial = FakeSerial()
    monkeypatch.setattr(
        serial_client.serial,
        "Serial",
        lambda **kwargs: fake_serial,
    )

    try:
        assert serial_client.connect("COM_TEST") is True
        assert serial_client.send_command("CONNECT") == "OK"
        assert fake_serial.written == [b"CONNECT\n"]
    finally:
        serial_client.disconnect()


def test_incomplete_response_closes_connection_and_reader(monkeypatch):
    client_socket, server_socket = socket.socketpair()
    server_socket.settimeout(1.0)
    server_socket.sendall(b"BOARD:")
    monkeypatch.setattr(serial_client, "TIMEOUT", 0.05)
    monkeypatch.setattr(
        serial_client.socket,
        "create_connection",
        lambda address, timeout: client_socket,
    )

    try:
        assert serial_client.connect("mock") is True
        assert serial_client.send_command("STATE") is None

        assert serial_client.connection is None
        assert serial_client.reader is None
        assert serial_client.transport is None
        assert server_socket.recv(100) == b"STATE\n"
        assert server_socket.recv(100) == b""
    finally:
        serial_client.disconnect()
        server_socket.close()
