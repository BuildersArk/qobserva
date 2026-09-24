from __future__ import annotations

import socket

import pytest
from qobserva.sanitize import REDACTED, host_identity, sanitize_error_message

IBM_TOKEN = "ab12" * 32  # IBM Quantum API tokens are 128 hex characters

@pytest.mark.parametrize("message,secret", [
    ("auth failed with api_key=sk-live-abc123", "sk-live-abc123"),
    ("login failed: password=hunter2", "hunter2"),
    ('HTTP 401: {"token": "abc.def-123", "ok": false}', "abc.def-123"),
    ("Authorization: Bearer abcdefghijklmnop", "abcdefghijklmnop"),
    ("connect to https://user:pa55w0rd@quantum.example.com failed", "pa55w0rd"),
    ("AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG", "wJalrXUtnFEMI/K7MDENG"),
    ("bad key AKIAIOSFODNN7EXAMPLE", "AKIAIOSFODNN7EXAMPLE"),
    (f"QiskitRuntimeService(token='{IBM_TOKEN}')", IBM_TOKEN),
    (f"invalid credentials {IBM_TOKEN}", IBM_TOKEN),
])
def test_secret_values_are_redacted(message, secret):
    out = sanitize_error_message(message)
    assert secret not in out
    assert REDACTED in out

@pytest.mark.parametrize("message", [
    "Invalid token provided",
    "Circuit depth 42 exceeds max 30 on ibm_brisbane (job d1a2b3c4)",
    "Expected 2 qubits but got 3",
])
def test_ordinary_messages_are_unchanged(message):
    assert sanitize_error_message(message) == message

def test_secret_straddling_truncation_limit_is_not_leaked():
    msg = "x" * 490 + " password=hunter2hunter2"
    out = sanitize_error_message(msg, max_len=500)
    assert "hunter2" not in out and len(out) <= 500

def test_host_is_hashed_by_default(monkeypatch):
    monkeypatch.delenv("QOBSERVA_HOST_MODE", raising=False)
    ident = host_identity()
    assert "host" not in ident
    assert len(ident["host_hash"]) == 12
    assert ident == host_identity()  # stable, so runs still group by machine

def test_host_modes(monkeypatch):
    monkeypatch.setenv("QOBSERVA_HOST_MODE", "raw")
    assert host_identity() == {"host": socket.gethostname()}
    monkeypatch.setenv("QOBSERVA_HOST_MODE", "none")
    assert host_identity() == {}
