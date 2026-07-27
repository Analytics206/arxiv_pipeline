import logging
import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from src.analysis.identity import normalize_arxiv_id

logger = logging.getLogger(__name__)


class ArxivFetchError(RuntimeError):
    """Raised when an exact arXiv metadata request cannot be completed."""


class ArxivClient:
    """Client for fetching papers from arXiv API using Atom XML format."""

    BASE_URL = "https://export.arxiv.org/api/query"

    def __init__(
        self,
        max_results: int = 100,
        sort_by: str = "submittedDate",
        sort_order: str = "descending",
        *,
        timeout: int = 30,
        session=None,
    ):
        self.max_results = max_results
        self.sort_by = sort_by
        self.sort_order = sort_order
        self.timeout = timeout
        self._session = session or requests.Session()

    def fetch_paper_by_id(self, paper_id: str) -> Dict:
        """Fetch one exact paper, retaining the version returned by arXiv."""

        requested = normalize_arxiv_id(paper_id)
        params = {"id_list": requested.version_id, "max_results": 1}
        api_error: Exception | None = None
        try:
            response = self._session.get(
                self.BASE_URL,
                params=params,
                timeout=self.timeout,
                headers={
                    "User-Agent": (
                        "arxiv-pipeline/0.7 "
                        "(local research indexing; contact: local-user)"
                    )
                },
            )
            response.raise_for_status()
        except requests.RequestException as error:
            api_error = error
            logger.warning(
                "arXiv Atom API failed for %s; trying the paper page: %s",
                requested.version_id,
                error,
            )
            papers = []
        else:
            papers = self._parse_response(response.text)

        if not papers:
            try:
                papers = [self._fetch_paper_page(requested.version_id)]
            except (requests.RequestException, ValueError) as page_error:
                raise ArxivFetchError(
                    f"Could not fetch arXiv metadata for {requested.version_id}; "
                    f"Atom API error: {api_error or 'empty response'}; "
                    f"paper page error: {page_error}"
                ) from page_error
        returned = normalize_arxiv_id(papers[0]["id"])
        if returned.base_id != requested.base_id:
            raise ArxivFetchError(
                f"arXiv returned {returned.version_id} for requested "
                f"{requested.version_id}"
            )
        papers[0]["arxiv_id"] = returned.version_id
        papers[0]["base_arxiv_id"] = returned.base_id
        return papers[0]

    def _fetch_paper_page(self, version_id: str) -> Dict:
        """Fallback to citation metadata embedded in the official abs page."""

        url = f"https://arxiv.org/abs/{version_id}"
        response = self._session.get(
            url,
            timeout=self.timeout,
            headers={
                "User-Agent": (
                    "arxiv-pipeline/0.7 "
                    "(local research indexing; contact: local-user)"
                )
            },
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        def meta(name: str) -> str:
            tag = soup.find("meta", attrs={"name": name})
            return str(tag.get("content", "")).strip() if tag else ""

        def metas(name: str) -> list[str]:
            return [
                str(tag.get("content", "")).strip()
                for tag in soup.find_all("meta", attrs={"name": name})
                if str(tag.get("content", "")).strip()
            ]

        title = _clean_whitespace(meta("citation_title"))
        if not title:
            raise ValueError(f"arXiv paper page contains no citation title: {url}")
        page_id = meta("citation_arxiv_id") or version_id
        identity = normalize_arxiv_id(page_id)
        requested = normalize_arxiv_id(version_id)
        if identity.base_id != requested.base_id:
            raise ValueError(
                f"arXiv paper page returned {identity.version_id} for {version_id}"
            )

        categories = metas("citation_primary_category")
        if not categories:
            subject = soup.select_one("span.primary-subject")
            if subject is not None:
                match = re.search(
                    r"\(([a-z-]+(?:\.[A-Za-z-]+)+)\)",
                    subject.get_text(" ", strip=True),
                )
                if match:
                    categories.append(match.group(1))
        return {
            "id": f"https://arxiv.org/abs/{version_id}",
            "title": title,
            "summary": _clean_whitespace(
                meta("citation_abstract") or meta("description")
            ),
            "published": meta("citation_date"),
            "updated": meta("citation_date"),
            "authors": metas("citation_author"),
            "arxiv_url": f"https://arxiv.org/abs/{version_id}",
            "pdf_url": f"https://arxiv.org/pdf/{version_id}",
            "categories": categories or ["uncategorized"],
        }

    def fetch_papers(
        self,
        category: str = "cs.AI",
        search_query: Optional[str] = None,
        start: int = 0,
    ) -> List[Dict]:
        """
        Fetch papers from arXiv API.

        Args:
            category: arXiv category (default: cs.AI)
            search_query: Optional search terms
            start: Starting index for pagination

        Returns:
            List of paper metadata dictionaries
        """
        # Build query
        query_parts = []
        if category:
            query_parts.append(f"cat:{category}")
        if search_query:
            query_parts.append(search_query)

        search_query_str = " AND ".join(query_parts)

        # Build request params
        params = {
            "search_query": search_query_str,
            "start": start,
            "max_results": self.max_results,
            "sortBy": self.sort_by,
            "sortOrder": self.sort_order,
        }

        logger.info("Fetching papers with params: %s", params)

        # Make request
        try:
            response = self._session.get(
                self.BASE_URL,
                params=params,
                timeout=self.timeout,
                headers={
                    "User-Agent": (
                        "arxiv-pipeline/0.7 "
                        "(local research indexing; contact: local-user)"
                    )
                },
            )
        except requests.RequestException as error:
            raise ArxivFetchError(
                f"arXiv request failed for {search_query_str}: {error}"
            ) from error

        if response.status_code != 200:
            raise ArxivFetchError(
                f"arXiv returned HTTP {response.status_code} for "
                f"{search_query_str}: {response.text[:500]}"
            )
            return []

        # Parse XML response
        return self._parse_response(response.text)

    def _parse_response(self, xml_data: str) -> List[Dict]:
        """Parse arXiv API XML response into list of dictionaries."""
        root = ET.fromstring(xml_data)

        # Define XML namespaces
        namespaces = {
            "atom": "http://www.w3.org/2005/Atom",
            "arxiv": "http://arxiv.org/schemas/atom",
        }

        results = []

        # Extract entries
        for entry in root.findall("atom:entry", namespaces):
            paper = {}

            # Basic metadata
            paper["id"] = self._get_text(entry, "atom:id", namespaces)
            paper["title"] = _clean_whitespace(
                self._get_text(entry, "atom:title", namespaces)
            )
            paper["summary"] = _clean_whitespace(
                self._get_text(entry, "atom:summary", namespaces)
            )
            paper["published"] = self._get_text(entry, "atom:published", namespaces)
            paper["updated"] = self._get_text(entry, "atom:updated", namespaces)

            # Authors
            paper["authors"] = []
            for author in entry.findall("atom:author", namespaces):
                name = self._get_text(author, "atom:name", namespaces)
                if name:
                    paper["authors"].append(name)

            # arXiv specific fields
            paper["arxiv_url"] = paper["id"]
            paper["pdf_url"] = paper["id"].replace("/abs/", "/pdf/")

            # Categories
            primary = entry.find("arxiv:primary_category", namespaces)
            categories = []
            if primary is not None and primary.attrib.get("term"):
                categories.append(primary.attrib["term"])
            categories.extend(
                category.attrib["term"]
                for category in entry.findall("atom:category", namespaces)
                if category.attrib.get("term")
            )
            paper["categories"] = list(dict.fromkeys(categories))

            # Add to results
            results.append(paper)

        logger.info("Parsed %d papers from arXiv response", len(results))
        return results

    @staticmethod
    def _get_text(element, xpath, namespaces, default=""):
        """Helper to extract text from XML element with proper error handling."""
        try:
            return element.find(xpath, namespaces).text.strip()
        except (AttributeError, TypeError):
            return default


def _clean_whitespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()
