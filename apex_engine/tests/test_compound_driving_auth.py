import importlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import requests

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def auth(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "research/scripts"))
    return importlib.import_module("acquire_compound_driving")


def test_sign_in_exchanges_credentials_without_printing_or_saving_them(auth, monkeypatch, capsys):
    calls = []

    def post(url, **kwargs):
        calls.append((url, kwargs))
        return SimpleNamespace(status_code=200, json=lambda: {"access_token": "private-test-token"})

    monkeypatch.setattr(auth.requests, "post", post)
    assert auth.obtain_token("test-user", "test-password") == "private-test-token"
    assert calls == [
        (
            "https://api.openf1.org/token",
            {
                "data": {"username": "test-user", "password": "test-password"},
                "timeout": (10, 60),
                "allow_redirects": False,
            },
        )
    ]
    captured = capsys.readouterr()
    assert captured.out == captured.err == ""


@pytest.mark.parametrize(
    "payload",
    [
        {},
        None,
        {"access_token": None},
        {"access_token": ""},
        {"access_token": "two words"},
        {"access_token": 123},
    ],
)
def test_sign_in_rejects_invalid_token_payloads_without_reflecting_credentials(auth, monkeypatch, payload):
    monkeypatch.setattr(
        auth.requests, "post", lambda *args, **kwargs: SimpleNamespace(status_code=200, json=lambda: payload)
    )
    with pytest.raises(RuntimeError) as caught:
        auth.obtain_token("private-user", "private-password")
    assert "private-user" not in str(caught.value)
    assert "private-password" not in str(caught.value)


def test_sign_in_failure_messages_do_not_include_server_body_or_connection_details(auth, monkeypatch):
    secret = "private-credential-must-stay-local"
    response = SimpleNamespace(status_code=401, text=secret)
    monkeypatch.setattr(auth.requests, "post", lambda *args, **kwargs: response)
    with pytest.raises(RuntimeError, match="HTTP 401") as caught:
        auth.obtain_token("private-user", secret)
    assert secret not in str(caught.value)

    def fail(*args, **kwargs):
        raise requests.ConnectionError(secret)

    monkeypatch.setattr(auth.requests, "post", fail)
    with pytest.raises(RuntimeError, match="connection failed") as caught:
        auth.obtain_token("private-user", secret)
    assert secret not in str(caught.value)
    assert caught.value.__suppress_context__


def test_sign_in_rejects_missing_credentials_before_network_access(auth, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Missing credentials must fail before a network request")

    monkeypatch.setattr(auth.requests, "post", forbidden)
    for username, password in [("", "password"), ("   ", "password"), ("user", "")]:
        with pytest.raises(ValueError, match="required"):
            auth.obtain_token(username, password)


def test_sign_in_hides_invalid_json_error_details(auth, monkeypatch):
    def decode():
        raise ValueError("private-response-body")

    monkeypatch.setattr(
        auth.requests, "post", lambda *args, **kwargs: SimpleNamespace(status_code=200, json=decode)
    )
    with pytest.raises(RuntimeError, match="invalid sign-in response") as caught:
        auth.obtain_token("private-user", "private-password")
    assert "private-response-body" not in str(caught.value)
    assert caught.value.__suppress_context__


@pytest.mark.parametrize("token", ["private-test-bearer", None])
def test_download_uses_optional_header_only_in_memory_and_cleans_it_after_success(
    auth, monkeypatch, tmp_path, token
):
    client = SimpleNamespace(session=SimpleNamespace(headers={"Accept": "application/json"}), closed=False)

    def close():
        assert "Authorization" not in client.session.headers
        client.closed = True

    client.close = close
    monkeypatch.setattr(auth, "OpenF1Client", lambda policy: client)
    expected = {"schema": "test-public-source", "samples": 3}

    def prepare(root, snapshots, used_client):
        assert used_client is client
        assert root == tmp_path / "native" and snapshots == tmp_path / "snapshots"
        assert client.session.headers.get("Authorization") == (f"Bearer {token}" if token else None)
        return expected

    monkeypatch.setattr(auth, "prepare", prepare)
    output = tmp_path / "public-result.json"
    auth.acquire(tmp_path / "native", tmp_path / "snapshots", output, token)
    assert client.closed and "Authorization" not in client.session.headers
    assert client.session.headers["Accept"] == "application/json"
    assert json.loads(output.read_text(encoding="utf-8")) == expected
    assert "private-test-bearer" not in output.read_text(encoding="utf-8")


@pytest.mark.parametrize("failure_stage", ["prepare", "write"])
def test_download_removes_header_and_closes_client_after_failure(auth, monkeypatch, tmp_path, failure_stage):
    client = SimpleNamespace(session=SimpleNamespace(headers={}), closed=False)

    def close():
        assert "Authorization" not in client.session.headers
        client.closed = True

    client.close = close
    monkeypatch.setattr(auth, "OpenF1Client", lambda policy: client)

    def prepare(*args):
        assert client.session.headers["Authorization"] == "Bearer private-test-bearer"
        if failure_stage == "prepare":
            raise RuntimeError("Test source unavailable")
        return {"schema": "test-public-source"}

    def write(*args):
        raise RuntimeError("Test output unavailable")

    monkeypatch.setattr(auth, "prepare", prepare)
    monkeypatch.setattr(auth, "write_manifest", write)
    output = tmp_path / "result.json"
    with pytest.raises(RuntimeError, match="Test"):
        auth.acquire(tmp_path / "native", tmp_path / "snapshots", output, "private-test-bearer")
    assert client.closed and "Authorization" not in client.session.headers
    assert not output.exists()


@pytest.mark.parametrize("token", ["", "a b", "a\nb"])
def test_download_rejects_malformed_token_before_constructing_client(auth, monkeypatch, tmp_path, token):
    def forbidden(*args):
        pytest.fail("Malformed token must fail before client creation")

    monkeypatch.setattr(auth, "OpenF1Client", forbidden)
    with pytest.raises(ValueError, match="Invalid OpenF1 access token"):
        auth.acquire(tmp_path, tmp_path, tmp_path / "output.json", token)
