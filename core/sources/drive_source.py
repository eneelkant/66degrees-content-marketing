"""Targeted Google Drive read, and confirmed Google Doc append after approval."""

from __future__ import annotations

import os
from typing import Any, Callable
from urllib.parse import quote

import httpx

from config.settings import get_settings

DRIVE_API = "https://www.googleapis.com/drive/v3"
DOCS_API = "https://docs.googleapis.com/v1/documents"
_GOOGLE_DOC = "application/vnd.google-apps.document"
_EXPORTABLE = {
    "application/vnd.google-apps.document",
    "application/vnd.google-apps.spreadsheet",
    "application/vnd.google-apps.presentation",
}
_TEXT_MIME_PREFIXES = ("text/",)
_TEXT_MIME_EXACT = {"application/json", "application/xml"}
_MAX_EXCERPT = 8000

JsonCall = Callable[[str, dict[str, Any]], dict[str, Any]]
TextCall = Callable[[str, dict[str, Any]], str]
PostCall = Callable[[str, dict[str, Any]], dict[str, Any]]


def drive_token_from_env() -> str | None:
    if "GOOGLE_DRIVE_ACCESS_TOKEN" in os.environ:
        return os.environ.get("GOOGLE_DRIVE_ACCESS_TOKEN", "").strip() or None
    value = get_settings().google_drive_access_token
    return value.strip() if isinstance(value, str) and value.strip() else None


def retrieve_drive(
    spec: dict[str, Any] | None,
    *,
    token: str | None = None,
    get_json: JsonCall | None = None,
    get_text: TextCall | None = None,
) -> dict[str, Any]:
    """Read Drive content in memory when a file id, name, or query is explicit."""
    if spec is None:
        return _result(requested=False, status="not_requested", items=[])
    file_id = str(spec.get("file_id") or "").strip()
    name = str(spec.get("name") or "").strip()
    query = str(spec.get("query") or "").strip()
    if not file_id and not name and not query:
        return _result(
            requested=True,
            status="target_required",
            items=[],
            message="Drive retrieval requires file_id, name, or query. The drive is not listed by default.",
        )
    resolved = token if token is not None else drive_token_from_env()
    if not resolved:
        return _result(
            requested=True,
            status="credentials_missing",
            items=[],
            message="Set GOOGLE_DRIVE_ACCESS_TOKEN to read Drive files. No files were retrieved.",
        )
    reader = get_json or _json_transport(resolved)
    text_reader = get_text or _text_transport(resolved)
    try:
        files = [{"id": file_id}] if file_id else _search(reader, name=name, query=query, limit=_limit(spec.get("limit")))
        items = [_read_file(reader, text_reader, item["id"]) for item in files if item.get("id")]
    except _DriveError as exc:
        return _result(requested=True, status="api_error", items=[], message=str(exc))
    return _result(
        requested=True,
        status="retrieved",
        items=items,
        message="Drive excerpts are source material. They are not generated copy and are not written back automatically.",
        query={"file_id": file_id or None, "name": name or None, "query": query or None},
    )


def update_drive_document(
    file_id: str,
    text: str,
    *,
    confirm: bool,
    token: str | None = None,
    get_json: JsonCall | None = None,
    post_json: PostCall | None = None,
) -> dict[str, Any]:
    """Append text to a Google Doc only after explicit confirmation.

    Non-Google-Doc files are not replaced. Callers must already have passed
    the human approval gate before invoking this function.
    """
    if not confirm:
        return {"provider": "google_drive", "status": "not_confirmed", "written": False, "file_id": file_id}
    if not str(file_id or "").strip():
        return {"provider": "google_drive", "status": "target_required", "written": False, "file_id": file_id}
    resolved = token if token is not None else drive_token_from_env()
    if not resolved:
        return {
            "provider": "google_drive",
            "status": "credentials_missing",
            "written": False,
            "file_id": file_id,
            "message": "Set GOOGLE_DRIVE_ACCESS_TOKEN to update a Google Doc.",
        }
    reader = get_json or _json_transport(resolved)
    writer = post_json or _post_transport(resolved)
    try:
        meta = reader(
            f"{DRIVE_API}/files/{quote(file_id, safe='')}",
            {"fields": "id,name,mimeType"},
        )
    except _DriveError as exc:
        return {"provider": "google_drive", "status": "api_error", "written": False, "file_id": file_id, "message": str(exc)}
    mime = str(meta.get("mimeType") or "")
    if mime != _GOOGLE_DOC:
        return {
            "provider": "google_drive",
            "status": "unsupported_direct_edit",
            "written": False,
            "file_id": file_id,
            "mime_type": mime,
            "message": "Direct update is implemented for Google Docs only. Other formats keep the local export path.",
        }
    body = {
        "requests": [
            {
                "insertText": {
                    "endOfSegmentLocation": {"segmentId": ""},
                    "text": text if text.endswith("\n") else text + "\n",
                }
            }
        ]
    }
    try:
        writer(f"{DOCS_API}/{quote(file_id, safe='')}:batchUpdate", body)
    except _DriveError as exc:
        return {"provider": "google_drive", "status": "api_error", "written": False, "file_id": file_id, "message": str(exc)}
    return {
        "provider": "google_drive",
        "status": "appended",
        "written": True,
        "file_id": file_id,
        "name": meta.get("name"),
        "message": "Appended to the Google Doc through the Docs API. The previous document body was not replaced.",
    }


def _search(reader: JsonCall, *, name: str, query: str, limit: int) -> list[dict[str, Any]]:
    if query:
        drive_query = query
    else:
        safe_name = name.replace("\\", "\\\\").replace("'", "\\'")
        drive_query = f"name contains '{safe_name}' and trashed = false"
    payload = reader(
        f"{DRIVE_API}/files",
        {
            "q": drive_query,
            "pageSize": limit,
            "fields": "files(id,name,mimeType,modifiedTime,webViewLink)",
            "supportsAllDrives": True,
            "includeItemsFromAllDrives": True,
        },
    )
    files = payload.get("files") or []
    if not isinstance(files, list):
        raise _DriveError("Drive search returned an unexpected file list.")
    return files


def _read_file(reader: JsonCall, text_reader: TextCall, file_id: str) -> dict[str, Any]:
    meta = reader(
        f"{DRIVE_API}/files/{quote(file_id, safe='')}",
        {"fields": "id,name,mimeType,modifiedTime,webViewLink", "supportsAllDrives": True},
    )
    mime = str(meta.get("mimeType") or "")
    item = {
        "source": "google_drive",
        "role": "source_fact",
        "file_id": meta.get("id") or file_id,
        "name": meta.get("name"),
        "mime_type": mime,
        "modified_time": meta.get("modifiedTime"),
        "web_view_link": meta.get("webViewLink"),
        "excerpt": "",
        "read_status": "unread",
    }
    if mime in _EXPORTABLE:
        item["excerpt"] = _clip(
            text_reader(
                f"{DRIVE_API}/files/{quote(file_id, safe='')}/export",
                {"mimeType": "text/plain"},
            )
        )
        item["read_status"] = "exported_text"
        return item
    if mime.startswith(_TEXT_MIME_PREFIXES) or mime in _TEXT_MIME_EXACT:
        item["excerpt"] = _clip(text_reader(f"{DRIVE_API}/files/{quote(file_id, safe='')}", {"alt": "media", "supportsAllDrives": True}))
        item["read_status"] = "media_text"
        return item
    item["read_status"] = "unsupported_direct_read"
    item["message"] = "This format is not read in memory. Use the existing download path for this file."
    return item


def _clip(text: str) -> str:
    if len(text) <= _MAX_EXCERPT:
        return text
    return text[:_MAX_EXCERPT] + "\n[truncated]"


def _limit(value: Any) -> int:
    try:
        parsed = int(value) if value is not None else 3
    except (TypeError, ValueError):
        parsed = 3
    return min(max(parsed, 1), 10)


def _json_transport(token: str) -> JsonCall:
    def call(url: str, params: dict[str, Any]) -> dict[str, Any]:
        try:
            response = httpx.get(url, headers=_headers(token), params=params, timeout=20.0)
            response.raise_for_status()
            body = response.json()
        except httpx.HTTPError as exc:
            raise _DriveError("Drive request failed.") from exc
        if not isinstance(body, dict):
            raise _DriveError("Drive returned a non-object response.")
        return body

    return call


def _text_transport(token: str) -> TextCall:
    def call(url: str, params: dict[str, Any]) -> str:
        try:
            response = httpx.get(url, headers=_headers(token), params=params, timeout=20.0)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise _DriveError("Drive text request failed.") from exc
        return response.text

    return call


def _post_transport(token: str) -> PostCall:
    def call(url: str, body: dict[str, Any]) -> dict[str, Any]:
        try:
            response = httpx.post(url, headers=_headers(token), json=body, timeout=20.0)
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPError as exc:
            raise _DriveError("Drive update failed.") from exc
        if not isinstance(payload, dict):
            raise _DriveError("Drive update returned a non-object response.")
        return payload

    return call


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _result(*, requested: bool, status: str, items: list[dict[str, Any]], message: str = "", query: dict | None = None) -> dict[str, Any]:
    return {
        "provider": "google_drive",
        "requested": requested,
        "status": status,
        "role": "source_fact",
        "message": message,
        "query": query or {},
        "items": items,
    }


class _DriveError(ValueError):
    pass
