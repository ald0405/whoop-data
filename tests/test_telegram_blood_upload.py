"""Tests for the Telegram blood-test upload confirm/cancel flow.

The DB write is mocked so no real data is touched; we assert the confirm path
calls the write service and the cancel path does not, and that pending state is
cleaned up either way.
"""

from __future__ import annotations

import pytest


class _FakeQuery:
    def __init__(self, data: str) -> None:
        self.data = data
        self.edited: str | None = None

    async def answer(self) -> None:  # noqa: D401
        return None

    async def edit_message_text(self, text: str, **_kwargs) -> None:
        self.edited = text


class _FakeUser:
    id = 123


class _FakeChat:
    id = 456
    type = "private"


class _FakeUpdate:
    def __init__(self, data: str) -> None:
        self.callback_query = _FakeQuery(data)
        self.effective_user = _FakeUser()
        self.effective_chat = _FakeChat()


class _FakeGateway:
    def is_authorized(self, **_kwargs) -> bool:
        return True


class _FakeContext:
    def __init__(self) -> None:
        self.application = type("App", (), {"bot_data": {"gateway": _FakeGateway()}})()


def test_pending_roundtrip(tmp_path, monkeypatch):
    import whoopdata.telegram_bot as tb

    monkeypatch.setattr(tb, "_PENDING_BLOODS_DIR", str(tmp_path))
    payload = {"report": {"lab_provider": "L"}, "results": [{"name": "x"}]}

    token = tb._stash_pending_bloods(payload)
    assert tb._load_pending_bloods(token) == payload

    tb._discard_pending_bloods(token)
    assert tb._load_pending_bloods(token) is None
    # malformed token is rejected, not crashed
    assert tb._load_pending_bloods("../etc/passwd") is None


@pytest.mark.anyio
async def test_confirm_writes_and_clears(tmp_path, monkeypatch):
    import whoopdata.biomarkers.ingest_service as svc
    import whoopdata.telegram_bot as tb

    monkeypatch.setattr(tb, "_PENDING_BLOODS_DIR", str(tmp_path))
    payload = {"report": {"lab_provider": "L"}, "results": [{"name": "LDL"}]}
    token = tb._stash_pending_bloods(payload)

    written = {}

    def _fake_write(p):
        written["payload"] = p
        return 7

    monkeypatch.setattr(svc, "write_report", _fake_write)

    update = _FakeUpdate(f"bmconf:{token}")
    await tb.biomarker_document_callback(update, _FakeContext())

    assert written["payload"] == payload
    assert "Saved 7" in update.callback_query.edited
    assert tb._load_pending_bloods(token) is None  # cleaned up


@pytest.mark.anyio
async def test_cancel_does_not_write(tmp_path, monkeypatch):
    import whoopdata.biomarkers.ingest_service as svc
    import whoopdata.telegram_bot as tb

    monkeypatch.setattr(tb, "_PENDING_BLOODS_DIR", str(tmp_path))
    token = tb._stash_pending_bloods({"report": {}, "results": [{"name": "x"}]})

    def _boom(p):
        raise AssertionError("write_report must not run on cancel")

    monkeypatch.setattr(svc, "write_report", _boom)

    update = _FakeUpdate(f"bmcanc:{token}")
    await tb.biomarker_document_callback(update, _FakeContext())

    assert "Cancelled" in update.callback_query.edited
    assert tb._load_pending_bloods(token) is None


@pytest.mark.anyio
async def test_expired_token_is_handled(tmp_path, monkeypatch):
    import whoopdata.telegram_bot as tb

    monkeypatch.setattr(tb, "_PENDING_BLOODS_DIR", str(tmp_path))
    update = _FakeUpdate("bmconf:0123456789abcdef")  # well-formed but absent
    await tb.biomarker_document_callback(update, _FakeContext())
    assert "expired" in update.callback_query.edited.lower()
