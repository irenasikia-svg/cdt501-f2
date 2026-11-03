"""Test-wide guard: tests must never open network connections (hard rule 2)."""

import socket

import pytest


class NetworkBlockedError(RuntimeError):
    pass


def _blocked(*_args, **_kwargs):
    raise NetworkBlockedError("network access is blocked in tests")


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    monkeypatch.setattr(socket.socket, "connect", _blocked)
    monkeypatch.setattr(socket.socket, "connect_ex", _blocked)
    monkeypatch.setattr(socket, "create_connection", _blocked)
