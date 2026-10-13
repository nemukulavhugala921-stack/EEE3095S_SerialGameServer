
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

    assert serial_client.send_command("CONNECT") == "OK"

    yield

    serial_client.disconnect()


def test_connect_and_disconnect(connected_client):
    assert serial_client.send_command("STATE") == "BOARD:........."


def test_new_game(connected_client):
    response = serial_client.send_command("NEW")

    assert response == "OK:BOARD:........."
    assert serial_client.send_command("STATE") == "BOARD:........."


def test_legal_move(connected_client):
    serial_client.send_command("NEW")

    response = serial_client.send_command("MOVE:X:0")

    assert response == "OK:BOARD:X........"
    assert serial_client.send_command("STATE") == "BOARD:X........"


def test_occupied_cell(connected_client):
    serial_client.send_command("NEW")

    assert serial_client.send_command("MOVE:X:0") == "OK:BOARD:X........"

    # O is the correct player, but square 0 is already occupied.
    response = serial_client.send_command("MOVE:O:0")

    assert response == "NACK:OCCUPIED"
    assert serial_client.send_command("STATE") == "BOARD:X........"


def test_out_of_range_move(connected_client):
    serial_client.send_command("NEW")

    response = serial_client.send_command("MOVE:X:9")

    assert response == "NACK:RANGE"
    assert serial_client.send_command("STATE") == "BOARD:........."


def test_out_of_turn_move(connected_client):
    serial_client.send_command("NEW")

    # X starts, so O must not be allowed to move first.
    assert serial_client.send_command("MOVE:O:4") == "NACK:NOTURN"
    assert serial_client.send_command("STATE") == "BOARD:........."

    # X makes a legal move.
    assert serial_client.send_command("MOVE:X:4") == "OK:BOARD:....X...."

    # It is now O's turn, so X cannot move again.
    assert serial_client.send_command("MOVE:X:0") == "NACK:NOTURN"

    # The rejected move must not change the board.
    assert serial_client.send_command("STATE") == "BOARD:....X...."


def test_unknown_command(connected_client):
    response = serial_client.send_command("HELLO")

    assert response == "NACK:BADCMD"
    assert serial_client.send_command("STATE") == "BOARD:........."


def test_win_and_game_over(connected_client):
    serial_client.send_command("NEW")

    moves = [
        "MOVE:X:0",
        "MOVE:O:3",
        "MOVE:X:1",
        "MOVE:O:4",
    ]

    for move in moves:
        response = serial_client.send_command(move)
        assert response is not None

    assert serial_client.send_command("MOVE:X:2") == "WIN:X"
    assert serial_client.send_command("MOVE:O:5") == "NACK:NOGAME"
    assert serial_client.send_command("STATE") == "BOARD:XXXOO...."


def test_draw(connected_client):
    serial_client.send_command("NEW")

    moves = [
        "MOVE:X:0",
        "MOVE:O:1",
        "MOVE:X:2",
        "MOVE:O:4",
        "MOVE:X:3",
        "MOVE:O:5",
        "MOVE:X:7",
        "MOVE:O:6",
    ]

    for move in moves:
        response = serial_client.send_command(move)
        assert response is not None

    assert serial_client.send_command("MOVE:X:8") == "DRAW"
    assert serial_client.send_command("STATE") == "BOARD:XOXXOOOXX"
