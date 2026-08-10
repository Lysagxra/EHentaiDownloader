"""Crawler module for extracting album pages and image links.

This module provides the `Crawler` class, which is responsible for parsing album pages,
extracting image links, and handling reloaded pages.
"""

import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from requests import Session

from src.config import NL_VALUE_PATTERN
from src.general_utils import fetch_page
from src.managers.live_manager import LiveManager

from .crawler_utils import generate_reloaded_page


class Crawler:
    """Handles crawling and extracting information from album pages.

    This class fetches and processes album pages, retrieves album names, and handles
    reloaded image pages.
    """

    def __init__(
        self,
        url: str,
        initial_soup: BeautifulSoup,
        live_manager: LiveManager,
        session: Session,
    ) -> None:
        """Initialize the Crawler with album URL, initial soup, and live manager."""
        parsed = urlparse(url)
        path = parsed.path if parsed.path.endswith("/") else f"{parsed.path}/"
        self.url = f"{parsed.scheme}://{parsed.netloc}{path}"
        self.initial_soup = initial_soup
        self.live_manager = live_manager
        self.session = session
        self.album_pages = self._generate_album_pages()

    def get_album_name(self) -> str:
        """Extract the album name from the album page."""
        parsed_url = urlparse(self.url)
        path_parts = parsed_url.path.strip("/").split("/")
        if len(path_parts) >= 3:
            url_path_id = f"{path_parts[0]}_{path_parts[1]}_{path_parts[2]}"
        else:
            url_path_id = "unknown_id"

        title_container = self.initial_soup.find("h1", {"id": "gn"})
        if not title_container:
            title_container = self.initial_soup.find("h1", {"id": "gj"})

        if title_container:
            album_name = title_container.get_text().strip()
        else:
            # Check if this is an IP ban page or has specific error keywords
            title_tag = self.initial_soup.find("title")
            page_title = title_tag.get_text(strip=True) if title_tag else ""
            body_text = self.initial_soup.body.get_text() if self.initial_soup.body else ""

            if "ip address has been temporarily banned" in body_text.lower() or "banned" in page_title.lower():
                raise RuntimeError(
                    f"Access denied: Your IP address might be temporarily banned/restricted by E-Hentai.\n"
                    f"Page Title: {page_title}"
                )

            # Fallback to the page <title> tag
            if page_title and page_title != "E-Hentai Galleries":
                album_name = page_title.replace(" - E-Hentai Galleries", "").strip()
            else:
                sample_text = body_text[:500].replace("\n", " ").strip() if body_text else "Empty response"
                raise ValueError(
                    f"Could not extract album name from the page. The page might be a warning/login page, "
                    f"or E-Hentai returned an error.\n"
                    f"Page Title: {page_title}\n"
                    f"Page snippet: {sample_text}..."
                )

        return f"{album_name}_{url_path_id}"

    def collect_album_pages_soups(self) -> list[BeautifulSoup]:
        """Fetch all album pages and return their parsed HTML content."""
        album_pages_soups = [self.initial_soup]
        album_pages_soups.extend(
            fetch_page(album_page, session=self.session, referer=self.url)
            for album_page in self.album_pages
        )
        return album_pages_soups

    def get_reloaded_page(self, picture_page: str, referer: str | None = None) -> str | None:
        """Generate reloaded image page URL for a single picture page."""
        try:
            soup = fetch_page(
                picture_page,
                session=self.session,
                referer=referer or self.url,
            )
            nl_container = soup.find("a", {"id": "loadfail", "onclick": True})
            nl_value = re.search(NL_VALUE_PATTERN, nl_container.get("onclick")).group(1)

            match = re.search(r"nl\('([^']+)'\)", nl_container["onclick"])
            if not match:
                self.live_manager.update_log(
                    "Missing 'nl' value",
                    f"No 'nl' value found in onclick for {picture_page}.",
                )
                return None

            nl_value = match.group(1)
            return generate_reloaded_page(picture_page, nl_value)
        except Exception as err:
            self.live_manager.update_log(
                "Crawler error",
                f"Error getting reloaded page for {picture_page}: {err}",
            )
            return None

    def get_reloaded_pages(self, picture_pages: list[str]) -> list[str]:
        """Generate reloaded image page URLs."""
        reloaded_pages = []
        for picture_page in picture_pages:
            reloaded_page = self.get_reloaded_page(picture_page, referer=self.url)
            if reloaded_page:
                reloaded_pages.append(reloaded_page)
        return reloaded_pages

    def _generate_album_pages(self) -> list[str]:
        """Generate the URLs for all album pages."""
        pattern = re.compile(f"^{re.escape(self.url)}\\?p=")
        next_pages = self.initial_soup.find_all(
            "a",
            {"href": pattern, "onclick": "return false"},
        )

        if not next_pages:
            return []

        page_numbers = []
        for a in next_pages:
            href = a.get("href")
            if href:
                match = re.search(r"\?p=(\d+)", href)
                if match:
                    page_numbers.append(int(match.group(1)))

        if not page_numbers:
            return []

        last_page = max(page_numbers)
        album_pages = [f"{self.url}?p={page}" for page in range(1, last_page + 1)]
        return album_pages
