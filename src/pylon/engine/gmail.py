"""
Gmail API client for creating draft emails.
Requires google-api-python-client and google-auth-oauthlib.
"""

from __future__ import annotations

import base64
import logging
from email.mime.text import MIMEText
from typing import Any, Optional

_logger = logging.getLogger("engine.gmail")


class GmailClient:
    """
    Creates Gmail draft emails via the Gmail API.
    Requires OAuth2 credentials configured via GMAIL_CREDENTIALS_PATH.
    """

    def __init__(self, credentials_path: str = "", token_path: str = "") -> None:
        self.credentials_path = credentials_path
        self.token_path = token_path
        self._service: Optional[Any] = None

    def _get_service(self) -> Any:
        """Lazy-initialize the Gmail API service."""
        if self._service is not None:
            return self._service

        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
        except ImportError:
            raise ImportError(
                "Gmail integration requires: pip install pylon[gmail]\n"
                "  google-api-python-client google-auth-oauthlib"
            )

        SCOPES = ["https://www.googleapis.com/auth/gmail.compose"]
        creds = None

        if self.token_path:
            try:
                creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
            except Exception:
                pass

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            elif self.credentials_path:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, SCOPES
                )
                creds = flow.run_local_server(port=0)

                if self.token_path:
                    with open(self.token_path, "w") as f:
                        f.write(creds.to_json())
            else:
                raise ValueError(
                    "Gmail credentials not configured. Set GMAIL_CREDENTIALS_PATH."
                )

        self._service = build("gmail", "v1", credentials=creds)
        return self._service

    def create_draft(
        self,
        to: str,
        subject: str,
        body: str,
        sender: str = "me",
    ) -> str:
        """
        Create a Gmail draft.

        Args:
            to: Recipient email
            subject: Email subject
            body: Email body (plain text)
            sender: Sender (default "me" for authenticated user)

        Returns:
            Gmail draft ID
        """
        service = self._get_service()

        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        draft_body = {"message": {"raw": raw}}

        draft = service.users().drafts().create(
            userId=sender, body=draft_body
        ).execute()

        draft_id = draft.get("id", "")
        _logger.info("Gmail draft created: %s (to=%s, subject=%s)", draft_id, to, subject[:50])
        return draft_id
