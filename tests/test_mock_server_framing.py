"""Framing and recovery tests for the local mock server."""

import socket
import threading
import time

import pytest

from client import mock_stm32


def read_response(connection):
    """Read one newline-terminated response from a socket."""
    response = bytearray()

    while True:
        byte = connection.recv(1)

        if not byte:
            raise AssertionError("Mock server closed the connection")

        if byte == b"\n":
            return response.decode("ascii")

        if byte != b"\r":
            response.extend(byte)


@pytest.fixture
def local_server(monkeypatch):
    """Run one mock client handler with a short, deterministic frame timeout."""
    monkeypatch.setattr(mock_stm32, "PARTIAL_FRAME_TIMEOUT", 0.05)
    server_connection, client_connection = socket.socketpair()
    client_connection.settimeout(1.0)

    thread = threading.Thread(
        target=mock_stm32.serve_client,
        args=(server_connection, ("local", 0)),
        daemon=True,
    )
    thread.start()

    yield client_connection

    client_connection.close()
    thread.join(timeout=1.0)
    assert not thread.is_alive()


def test_partial_frame_timeout_recovers_and_idle_connection_survives(
    local_server,
    capsys,
):
    local_server.sendall(b"CON")
    assert read_response(local_server) == "NACK:BADCMD"

    # Repeated idle read timeouts must not close the connection or log errors.
    time.sleep(mock_stm32.PARTIAL_FRAME_TIMEOUT * 2.5)
    assert "Connection error" not in capsys.readouterr().out

    local_server.sendall(b"CONNECT\n")
    assert read_response(local_server) == "OK"


def test_oversized_frame_is_rejected_and_next_frame_is_processed(local_server):
    frame = b"A" * (mock_stm32.MAX_FRAME_LENGTH + 1)
    local_server.sendall(frame + b"\nCONNECT\n")

    assert read_response(local_server) == "NACK:BADCMD"
    assert read_response(local_server) == "OK"


def test_crlf_and_non_ascii_frames(local_server):
    local_server.sendall(b"CONNECT\r\n")
    assert read_response(local_server) == "OK"

    local_server.sendall(b"\xff\n")
    assert read_response(local_server) == "NACK:BADCMD"

    local_server.sendall(b"CONNECT\n")
    assert read_response(local_server) == "OK"


def test_rejected_commands_preserve_board_and_active_new_is_rejected(
    local_server,
):
    local_server.sendall(b"CONNECT\n")
    assert read_response(local_server) == "OK"

    local_server.sendall(b"NEW\n")
    assert read_response(local_server) == "OK:BOARD:........."

    local_server.sendall(b"MOVE:X:0\n")
    assert read_response(local_server) == "OK:BOARD:X........"

    local_server.sendall(b"MOVE:X:1\n")
    assert read_response(local_server) == "NACK:NOTURN"

    local_server.sendall(b"NEW\n")
    assert read_response(local_server) == "NACK:BADCMD"

    local_server.sendall(b"STATE\n")
    assert read_response(local_server) == "BOARD:X........"
