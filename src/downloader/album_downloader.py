"""Album downloading module.

This module provides the `AlbumDownloader` class for downloading image albums from a
given URL. It handles page crawling, image extraction, and downloading with progress
tracking.
"""

import random
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from requests import Response, Session

from concurrent.futures import ThreadPoolExecutor, as_completed

from src.config import (
    CHUNK_SIZE,
    HTTP_RATE_LIMIT,
    MAX_WORKERS,
    RATE_LIMIT_SLEEPING_TIME,
)
from src.crawler.crawler import Crawler
from src.crawler.crawler_utils import get_picture_pages
from src.file_utils import create_download_directory, write_on_session_log
from src.general_utils import create_session, fetch_page
from src.managers.live_manager import LiveManager

from .download_utils import fetch_with_retries, prepare_headers


class AlbumDownloader:
    """Handles the process of downloading an image album.

    This class fetches the album's pages, extracts image links, and downloads the images
    while tracking progress.
    """

    def __init__(self, url: str, live_manager: LiveManager) -> None:
        """Initialize the AlbumDownloader with album URL and live manager."""
        parsed = urlparse(url)
        path = parsed.path if parsed.path.endswith("/") else f"{parsed.path}/"
        self.url = f"{parsed.scheme}://{parsed.netloc}{path}"
        self.live_manager = live_manager
        self.session = create_session()
        self.initial_soup = fetch_page(
            self.url,
            session=self.session,
            referer=self.url,
        )
        if hasattr(self.initial_soup, "fetched_url"):
            self.url = self.initial_soup.fetched_url

        self.crawler = Crawler(
            url=self.url,
            initial_soup=self.initial_soup,
            live_manager=self.live_manager,
            session=self.session,
        )
        self.album_name = self.crawler.get_album_name()
        self.download_path = create_download_directory(self.album_name)

    def download_album(self) -> None:
        """Download all images from the album while tracking progress."""
        album_pages_soups = self.crawler.collect_album_pages_soups()
        num_pages = len(album_pages_soups)
        total_failed_downloads = 0
        self.live_manager.add_overall_task(
            description=self.album_name,
            num_tasks=num_pages,
        )

        for current_task, soup in enumerate(album_pages_soups):
            containers = soup.find_all("a", {"href": True})
            picture_pages = get_picture_pages(containers)

            failed_downloads = self._extract_and_download(
                self.session, picture_pages, current_task,
            )
            total_failed_downloads += len(failed_downloads)

            if failed_downloads:
                self.live_manager.update_log(
                    "Failed downloads",
                    f"Failed downloads for page {current_task + 1}. "
                    "Check the log file.",
                )

            if current_task < num_pages - 1:
                self.live_manager.update_log(
                    "Preparing to resume",
                    "Pausing before resuming the download...",
                )
                time.sleep(random.uniform(1, 5))  # noqa: S311

        if total_failed_downloads > 0:
            raise RuntimeError(
                f"Album download completed with {total_failed_downloads} failed image(s)."
            )

    def download_picture(
            self,
            response: Response,
            filename: str,
            task: int,
        ) -> None:
        """Save an image response to a file and update the progress."""
        final_path = Path(self.download_path) / filename
        with Path(final_path).open("wb") as file:
            for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                file.write(chunk)

        self.live_manager.update_task(task, advance=1)

    # Private methods
    def _extract_and_download(
        self,
        session: Session,
        picture_pages: list[str],
        current_task: int,
    ) -> list[str]:
        """Extract image links and download them concurrently."""
        failed_downloads = []
        num_pictures = len(picture_pages)
        task = self.live_manager.add_task(current_task=current_task, total=num_pictures)

        # Thread lock for safely appending to failed_downloads list
        import threading
        failed_lock = threading.Lock()

        def download_worker(picture_page: str) -> None:
            nonlocal failed_downloads

            # 1. Fetch the picture page to extract the 'nl' value
            reloaded_page = self.crawler.get_reloaded_page(
                picture_page,
                referer=self.url,
            )
            if not reloaded_page:
                with failed_lock:
                    failed_downloads.append(picture_page)
                self.live_manager.update_task(task, advance=1)
                return

            # 2. Fetch the reloaded page to extract the direct image source link
            try:
                soup = fetch_page(
                    reloaded_page,
                    session=self.session,
                    referer=picture_page,
                )
                download_link_container = soup.find("img", {"id": "img", "src": True})
                if not download_link_container:
                    self.live_manager.update_log(
                        "Image not found",
                        f"Could not find img with id='img' on {reloaded_page}.",
                    )
                    with failed_lock:
                        failed_downloads.append(picture_page)
                    self.live_manager.update_task(task, advance=1)
                    return
                download_link = download_link_container["src"]
            except Exception as err:
                self.live_manager.update_log(
                    "Page fetch error",
                    f"Error reading reloaded page {reloaded_page}: {err}",
                )
                with failed_lock:
                    failed_downloads.append(picture_page)
                self.live_manager.update_task(task, advance=1)
                return

            filename = download_link.split("/")[-1]
            final_path = Path(self.download_path) / filename
            # Resume support: skip files already present from previous runs.
            if final_path.exists() and final_path.stat().st_size > 0:
                self.live_manager.update_task(task, advance=1)
                return

            # 3. Download the actual image file with retries
            headers = prepare_headers(download_link)
            response = fetch_with_retries(
                session=session,
                url=download_link,
                live_manager=self.live_manager,
                headers=headers,
            )

            if response is None:
                self.live_manager.update_log(
                    "Failed download",
                    f"None response from {download_link}, check the log file",
                )
                with failed_lock:
                    failed_downloads.append(download_link)
                write_on_session_log(download_link)
                self.live_manager.update_task(task, advance=1)
                return

            self.download_picture(response, filename, task)

            # Polite sleep between tasks in each thread
            time.sleep(random.uniform(1.0, 3.0))  # noqa: S311

        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [
                executor.submit(download_worker, picture_page)
                for picture_page in picture_pages
            ]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as err:
                    self.live_manager.update_log(
                        "Worker error",
                        f"Unhandled exception in download worker: {err}",
                    )

        return failed_downloads
