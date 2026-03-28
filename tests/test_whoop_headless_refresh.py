from __future__ import annotations
import json

import urllib.parse

from whoopdata.analysis.whoop_client import Whoop as AnalysisWhoop
from whoopdata.clients.whoop_client import Whoop as LegacyWhoop
from scripts import scheduled_etl


class DummyResponse:
    def __init__(self, payload: dict, status_code: int = 200, text: str = ""):
        self._payload = payload
        self.status_code = status_code
        self.text = text

    def json(self):
        return self._payload


def test_analysis_client_credentials_persists_refresh_metadata(monkeypatch):
    client = AnalysisWhoop(client_id="client-id", client_secret="client-secret")
    saved = {}

    def fake_post(url, data=None, headers=None):
        assert data["grant_type"] == "client_credentials"
        assert "offline" in data["scope"].split()
        return DummyResponse(
            {
                "access_token": "access-123",
                "refresh_token": "refresh-456",
                "expires_in": 3600,
            }
        )

    def fake_save():
        saved["access_token"] = client.access_token
        saved["refresh_token"] = client.refresh_token
        saved["expires_at"] = client.token_expires_at

    monkeypatch.setattr("whoopdata.analysis.whoop_client.requests.post", fake_post)
    monkeypatch.setattr(client, "_save_tokens", fake_save)

    client._authenticate_client_credentials()

    assert saved["access_token"] == "access-123"
    assert saved["refresh_token"] == "refresh-456"
    assert saved["expires_at"] is not None


def test_legacy_client_auth_url_requests_offline_scope(monkeypatch):
    client = LegacyWhoop(client_id="client-id", client_secret="client-secret")
    captured = {}

    class DummyServer:
        def serve_forever(self):
            return None

        def shutdown(self):
            return None

    def fake_http_server(address, handler_cls):
        return DummyServer()

    class DummyThread:
        daemon = False

        def __init__(self, target=None):
            self.target = target

        def start(self):
            return None

    def fake_open(url):
        captured["url"] = url
        return True

    def fake_sleep(_seconds):
        raise RuntimeError("stop after auth url generation")

    monkeypatch.setattr("http.server.HTTPServer", fake_http_server)
    monkeypatch.setattr("threading.Thread", DummyThread)
    monkeypatch.setattr("webbrowser.open", fake_open)
    monkeypatch.setattr("time.sleep", fake_sleep)

    try:
        client._authenticate_authorization_code()
    except RuntimeError as exc:
        assert str(exc) == "stop after auth url generation"
    else:
        raise AssertionError("expected auth flow to stop after URL capture")

    parsed = urllib.parse.urlparse(captured["url"])
    params = urllib.parse.parse_qs(parsed.query)
    scope = params["scope"][0].split()
    assert "offline" in scope
    assert "read:recovery" in scope


def test_scheduled_etl_audit_entry_summarizes_results():
    entry = scheduled_etl._build_audit_entry(
        started_at=100.0,
        finished_at=104.25,
        status="success",
        results={
            "whoop_sleep": {"success": 5, "errors": 0},
            "withings_weight": {"success": 2, "errors": 1},
        },
    )

    assert entry["job"] == "scheduled_etl"
    assert entry["status"] == "success"
    assert entry["duration_seconds"] == 4.25
    assert entry["totals"] == {"success": 7, "errors": 1}
    assert entry["sources"]["withings_weight"] == {"success": 2, "errors": 1}


def test_scheduled_etl_appends_json_line(tmp_path, monkeypatch):
    audit_path = tmp_path / "etl-audit.log"

    monkeypatch.setattr(scheduled_etl, "LOGS_DIR", str(tmp_path))
    monkeypatch.setattr(scheduled_etl, "AUDIT_LOG_PATH", str(audit_path))

    scheduled_etl._append_audit_entry({"job": "scheduled_etl", "status": "success"})

    lines = audit_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0]) == {"job": "scheduled_etl", "status": "success"}
