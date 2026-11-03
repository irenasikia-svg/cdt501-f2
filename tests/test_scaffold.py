import socket

import pytest

import f2agent
from tests.conftest import NetworkBlockedError


def test_package_imports():
    assert f2agent.__doc__


def test_network_is_blocked_in_tests():
    with pytest.raises(NetworkBlockedError):
        socket.create_connection(("example.invalid", 80))
