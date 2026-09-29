"""Approved source fetchers with retries and actionable errors."""
from __future__ import annotations

import logging
import re
import time
from datetime import datetime, timezone
from hashlib import sha256

import httpx
from bs4 import BeautifulSoup

from .models import ReferenceRecord

logger = logging.getLogger(__name__)

APPROVED_SOURCES = {
    "66degrees_events": {
        "url": "https://www.66degrees.com/events",
        "source_type": "internal",
        "authority_level": "authoritative",
        "fetcher": "html",
    },
    "66degrees_success_stories": {
        "url": "https://www.66degrees.com/success-stories",
        "source_type": "internal",
        "authority_level": "authoritative",
        "fetcher": "html",
    },
    "google_cloud_events": {
        "url": "https://cloud.google.com/events",
        "source_type": "external",
        "authority_level": "approved",
        "fetcher": "playwright",
    },
}


class ApprovedSourceFetcher:
    def __init__(
        self,
        timeout: float = 30.0,
        *,
        max_attempts: int = 3,
        backoff_seconds: float = 1.5,
    ):
        self.timeout = timeout
        self.max_attempts = max(1, max_attempts)
        self.backoff_seconds = backoff_seconds

    def fetch_all(self) -> list[ReferenceRecord]:
        records: list[ReferenceRecord] = []
        errors: list[str] = []

        for source_id, source in APPROVED_SOURCES.items():
            try:
                if source["fetcher"] == "html":
                    records.extend(self._with_retries(source_id, lambda: self._fetch_html_source(source_id)))
                elif source["fetcher"] == "playwright":
                    records.extend(self._with_retries(source_id, self._fetch_google_cloud_events))
                else:
                    raise RuntimeError(f"Unknown fetcher type '{source['fetcher']}' for {source_id}")
            except Exception as exc:  # noqa: BLE001 — collect all source failures for one report
                errors.append(f"{source_id}: {exc}")
                logger.exception("reference_source_failed", extra={"source_id": source_id})

        if errors:
            raise RuntimeError(
                "Reference refresh failed for required approved source(s): "
                + "; ".join(errors)
                + ". Fix network/source availability and retry."
            )
        if not records:
            raise RuntimeError(
                "Reference refresh produced zero records from approved sources. "
                "Refuse to sync empty payload."
            )
        return records

    def _with_retries(self, source_id: str, fn):
        last_error: Exception | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                return fn()
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                logger.warning(
                    "reference_source_retry",
                    extra={"source_id": source_id, "attempt": attempt, "error": str(exc)},
                )
                if attempt < self.max_attempts:
                    time.sleep(self.backoff_seconds * attempt)
        assert last_error is not None
        raise last_error

    def _fetch_html_source(self, source_id: str) -> list[ReferenceRecord]:
        source = APPROVED_SOURCES[source_id]

        with httpx.Client(
            timeout=self.timeout,
            follow_redirects=True,
            headers={"User-Agent": "66degrees-reference-refresh/1.0"},
        ) as client:
            response = client.get(source["url"])
            response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        for element in soup(["script", "style", "noscript"]):
            element.decompose()

        title = soup.title.get_text(" ", strip=True) if soup.title else source_id
        content = soup.get_text(" ", strip=True)
        if not content.strip():
            raise RuntimeError(f"HTML source '{source_id}' returned empty content from {source['url']}")

        return [
            self._record(
                source_id=source_id,
                title=title,
                content=content,
                source=source["url"],
                source_type=source["source_type"],
                authority_level=source["authority_level"],
            )
        ]

    def _fetch_google_cloud_events(self) -> list[ReferenceRecord]:
        source_id = "google_cloud_events"
        source = APPROVED_SOURCES[source_id]

        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError(
                "Google Cloud Events refresh requires Playwright. "
                "Run: python -m playwright install chromium"
            ) from exc

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(source["url"], wait_until="networkidle", timeout=60000)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(2000)

            links = page.locator("a[href*='cloudonair.withgoogle.com/events/']")
            records: list[ReferenceRecord] = []
            seen: set[str] = set()
            skipped = 0

            for i in range(links.count()):
                try:
                    link = links.nth(i)
                    href = link.get_attribute("href")
                    if href:
                        match = re.match(r"^\[([^\]]+)\]\(([^\)]+)\)$", href)
                        if match:
                            href = match.group(1)

                    if not href or href in seen:
                        continue
                    seen.add(href)

                    title = (
                        link.get_attribute("track-metadata-child_headline")
                        or "Google Cloud Event"
                    ).strip()

                    lines = [
                        line.strip()
                        for line in link.inner_text(timeout=5000).splitlines()
                        if line.strip()
                    ]
                    if lines and lines[0].lower() == title.lower():
                        lines = lines[1:]
                    content = "\n".join(lines)

                    records.append(
                        self._record(
                            source_id=source_id,
                            title=title or "Google Cloud Event",
                            content=content,
                            source=href,
                            source_type=source["source_type"],
                            authority_level=source["authority_level"],
                        )
                    )
                except Exception as exc:  # noqa: BLE001 — skip malformed optional event cards
                    skipped += 1
                    logger.warning(
                        "google_cloud_event_card_skipped",
                        extra={"index": i, "error": str(exc)},
                    )

            browser.close()

        if not records:
            raise RuntimeError(
                "Google Cloud Events refresh found no usable event links at "
                f"{source['url']} (skipped_malformed={skipped})."
            )
        logger.info(
            "google_cloud_events_fetched",
            extra={"count": len(records), "skipped_malformed": skipped},
        )
        return records

    @staticmethod
    def _record(
        *,
        source_id: str,
        title: str,
        content: str,
        source: str,
        source_type: str,
        authority_level: str,
    ) -> ReferenceRecord:
        fetched_at = datetime.now(timezone.utc)
        record_id = sha256(f"{source_id}:{source}:{title}".encode("utf-8")).hexdigest()
        return ReferenceRecord(
            id=record_id,
            title=title,
            content=content,
            source=source,
            source_type=source_type,
            authority_level=authority_level,
            performance_score=0.0,
            semantic_similarity=0.0,
            fetched_at=fetched_at,
            version=fetched_at.strftime("%Y-%m-%d"),
            metadata={
                "source_id": source_id,
                "refresh_method": "approved_source_fetch",
            },
        )
