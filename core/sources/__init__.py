"""Explicit Slack and Google Drive source retrieval.

Nothing in this package reads Slack or Drive unless a caller passes a request.
Credentials are read from the environment at call time and are never logged.
"""

from core.sources.drive_source import retrieve_drive, update_drive_document
from core.sources.retrieve import retrieve_requested_sources
from core.sources.slack_source import retrieve_slack

__all__ = [
    "retrieve_drive",
    "retrieve_requested_sources",
    "retrieve_slack",
    "update_drive_document",
]
