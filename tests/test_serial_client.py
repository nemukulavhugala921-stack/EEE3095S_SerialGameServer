"""Transport cleanup tests for the serial client wrapper."""

import socket

from client import serial_client


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
