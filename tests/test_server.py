
"""Automated tests for the Tic-Tac-Toe client and mock server."""

import pytest

from client import serial_client


@pytest.fixture
def connected_client():
    """Connect to the running mock server before a test."""
    connected = serial_client.connect("mock")

    if not connected:
        pytest.fail(
            "Could not connect to mock server. "
            "Start it with: python client/mock_stm32.py"
        )

    # Reset the server session for a clean test.
    assert serial_client.send_command("CONNECT") == "OK"

    yield

    serial_client.disconnect()


def test_connect_and_disconnect(connected_client):
    """The client can connect and communicate with the server."""
    assert serial_client.send_command("STATE") == "BOARD:........."


def test_new_game(connected_client):
    """A new game starts with an empty board."""
    response = serial_client.send_command("NEW")

    assert response == "OK:BOARD:........."
    assert serial_client.send_command("STATE") == "BOARD:........."


def test_legal_move(connected_client):
    """A legal move updates the board."""
    serial_client.send_command("NEW")

    response = serial_client.send_command("MOVE:0")

    assert response == "OK:BOARD:X........"
    assert serial_client.send_command("STATE") == "BOARD:X........"


def test_occupied_cell(connected_client):
    """A player cannot use a cell that is already occupied."""
    serial_client.send_command("NEW")
    serial_client.send_command("MOVE:0")

    response = serial_client.send_command("MOVE:0")

    assert response == "NACK:OCCUPIED"
    assert serial_client.send_command("STATE") == "BOARD:X........"


def test_out_of_range_move(connected_client):
    """An index outside 0 to 8 is rejected."""
    serial_client.send_command("NEW")

    response = serial_client.send_command("MOVE:9")

    assert response == "NACK:RANGE"
    assert serial_client.send_command("STATE") == "BOARD:........."


def test_unknown_command(connected_client):
    """An unknown command is rejected without breaking the connection."""
    response = serial_client.send_command("HELLO")

    assert response == "NACK:BADCMD"
    assert serial_client.send_command("STATE") == "BOARD:........."


def test_win_and_game_over(connected_client):
    """A winning move ends the game and further moves are rejected."""
    serial_client.send_command("NEW")

    moves = ["MOVE:0", "MOVE:3", "MOVE:1", "MOVE:4"]

    for move in moves:
        response = serial_client.send_command(move)
        assert response is not None

    assert serial_client.send_command("MOVE:2") == "WIN:X"
    assert serial_client.send_command("MOVE:5") == "NACK:NOGAME"
    assert serial_client.send_command("STATE") == "BOARD:XXXOO...."


def test_draw(connected_client):
    """A full board without a winner ends in a draw."""
    serial_client.send_command("NEW")

    moves = [
        "MOVE:0", "MOVE:1",
        "MOVE:2", "MOVE:4",
        "MOVE:3", "MOVE:5",
        "MOVE:7", "MOVE:6",
    ]

    for move in moves:
        response = serial_client.send_command(move)
        assert response is not None

    assert serial_client.send_command("MOVE:8") == "DRAW"
    assert serial_client.send_command("STATE") == "BOARD:XOXXOOOXX"
