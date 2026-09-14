from datetime import datetime, timezone
from hashlib import sha256

import httpx
from bs4 import BeautifulSoup

from .models import ReferenceRecord


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
    def __init__(self, timeout: float = 30.0):
        self.timeout = timeout

    def fetch_all(self) -> list[ReferenceRecord]:
        records: list[ReferenceRecord] = []

        records.extend(self._fetch_html_source("66degrees_events"))
        records.extend(self._fetch_html_source("66degrees_success_stories"))
        records.extend(self._fetch_google_cloud_events())

        return records

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

        return [self._record(
            source_id=source_id,
            title=title,
            content=content,
            source=source["url"],
            source_type=source["source_type"],
            authority_level=source["authority_level"],
        )]

    def _fetch_google_cloud_events(self) -> list[ReferenceRecord]:
        source_id = "google_cloud_events"
        source = APPROVED_SOURCES[source_id]

        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError(
                "Google Cloud Events refresh requires Playwright."
            ) from exc

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(source["url"], wait_until="networkidle", timeout=60000)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(2000)

            links = page.locator("a[href*='cloudonair.withgoogle.com/events/']")
            records = []

            seen: set[str] = set()

            for i in range(links.count()):
                link = links.nth(i)
                href = link.get_attribute("href")
                title = link.inner_text().strip()

                if not href or href in seen:
                    continue

                seen.add(href)

                if not title:
                    title = "Google Cloud Event"

                records.append(self._record(
                    source_id=source_id,
                    title=title,
                    content=f"{title} — {href}",
                    source=href,
                    source_type=source["source_type"],
                    authority_level=source["authority_level"],
                ))

            browser.close()

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
        record_id = sha256(
            f"{source_id}:{source}:{title}".encode("utf-8")
        ).hexdigest()

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
