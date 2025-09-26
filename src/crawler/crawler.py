"""Crawler module for extracting album pages and image links.

This module provides the `Crawler` class, which is responsible for parsing album pages,
extracting image links, and handling reloaded pages.
"""

import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

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
    ) -> None:
        """Initialize the Crawler with album URL, initial soup, and live manager."""
        self.url = url
        self.initial_soup = initial_soup
        self.live_manager = live_manager
        self.album_pages = self._generate_album_pages()

    def get_album_name(self) -> str:
        """Extract the album name from the album page."""
        parsed_url = urlparse(self.url)
        path_parts = parsed_url.path.strip("/").split("/")
        url_path_id = f"{path_parts[0]}_{path_parts[1]}_{path_parts[2]}"

        title_container = self.initial_soup.find("h1", {"id": "gn"})
        album_name = title_container.get_text()
        return f"{album_name}_{url_path_id}"

    def collect_album_pages_soups(self) -> list[BeautifulSoup]:
        """Fetch all album pages and return their parsed HTML content."""
        album_pages_soups = [self.initial_soup]
        album_pages_soups.extend(
            fetch_page(album_page)
            for album_page in self.album_pages
        )
        return album_pages_soups

    def get_reloaded_pages(self, picture_pages: list[str]) -> list[str]:
        """Generate reloaded image page URLs."""
        reloaded_pages = []
        for picture_page in picture_pages:
            soup = fetch_page(picture_page)
            nl_container = soup.find("a", {"id": "loadfail", "onclick": True})
            nl_value = re.search(r"nl\('([^']+)'\)", nl_container["onclick"]).group(1)

            if nl_value:
                reloaded_page = generate_reloaded_page(picture_page, nl_value)
                reloaded_pages.append(reloaded_page)
            else:
                self.live_manager.update_log(
                    "Missing 'nl' value", f"No 'nl' value found for {picture_page}.",
                )

        return reloaded_pages

    def _generate_album_pages(self) -> list[str]:
        """Generate the URLs for all album pages."""
        pattern = re.compile(f"^{re.escape(self.url)}\\?p=")
        next_pages = self.initial_soup.find_all(
            "a",
            {"href": pattern, "onclick": "return false"},
        )

        last_page_url = next_pages[-2].get("href")
        match = re.search(r"\?p=(\d+)", last_page_url)
        last_page = int(match.group(1))
        album_pages = [f"{self.url}?p={page}" for page in range(1, last_page)]
        album_pages.append(last_page_url)
        return album_pages
