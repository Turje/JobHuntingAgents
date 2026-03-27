"""Tests for src/pylon/engine/gmail.py — GmailClient."""

from unittest.mock import MagicMock, patch

import pytest

from pylon.engine.gmail import GmailClient


class TestGmailClient:
    def test_init(self):
        client = GmailClient(credentials_path="creds.json", token_path="token.json")
        assert client.credentials_path == "creds.json"
        assert client.token_path == "token.json"

    def test_create_draft_calls_api(self):
        client = GmailClient()
        mock_service = MagicMock()
        mock_service.users().drafts().create().execute.return_value = {"id": "draft_123"}
        client._service = mock_service

        draft_id = client.create_draft(
            to="ted@statsbomb.com",
            subject="ML Engineer Inquiry",
            body="Hello Ted...",
        )
        assert draft_id == "draft_123"

    def test_raises_on_missing_credentials(self):
        client = GmailClient(credentials_path="", token_path="")
        # Can't get service without credentials
        with pytest.raises((ImportError, ValueError)):
            client._get_service()
