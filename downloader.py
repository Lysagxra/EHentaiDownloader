"""Album downloader script.

This module provides functionality to download an album from a given URL while tracking
progress and logging events. It initializes necessary managers for live updates and
handles command-line execution.

Usage:
    python3 script.py <album_url>
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from src.config import RETRY_FILE, URL_RETRY_ATTEMPTS
from src.downloader.album_downloader import AlbumDownloader
from src.file_utils import read_file, write_file
from src.general_utils import clear_terminal
from src.managers.live_manager import LiveManager
from src.managers.log_manager import LoggerTable
from src.managers.progress_manager import ProgressManager


def _unique_preserve_order(urls: list[str]) -> list[str]:
    """Return URLs without duplicates while preserving input order."""
    unique_urls: list[str] = []
    seen = set()
    for url in urls:
        if url and url not in seen:
            unique_urls.append(url)
            seen.add(url)
    return unique_urls


def _read_urls_if_exists(filename: str) -> list[str]:
    """Read URLs from a file if it exists, otherwise return an empty list."""
    file_path = Path(filename)
    if not file_path.exists():
        return []
    return [line.strip() for line in read_file(filename) if line.strip()]


def _write_urls(filename: str, urls: list[str]) -> None:
    """Write URLs to file, one URL per line."""
    content = "\n".join(urls)
    if content:
        content += "\n"
    write_file(filename, content)


def load_retry_urls() -> list[str]:
    """Load retry URLs from retry.txt, creating the file if needed."""
    retry_path = Path(RETRY_FILE)
    if not retry_path.exists():
        # Create an empty retry file so first-time runs can persist failures safely.
        retry_path.touch(exist_ok=True)
    return _read_urls_if_exists(RETRY_FILE)


def build_download_queue(primary_urls: list[str]) -> list[str]:
    """Build a queue from URLs.txt plus retry.txt, deduplicated in stable order."""
    retry_urls = load_retry_urls()
    return _unique_preserve_order(primary_urls + retry_urls)


def update_retry_file(successful_urls: list[str], failed_urls: list[str]) -> None:
    """Persist unresolved URLs in retry.txt while removing successful ones."""
    existing_retry_urls = load_retry_urls()
    successful_set = set(successful_urls)
    failed_unique = _unique_preserve_order(failed_urls)

    pending_urls = [url for url in existing_retry_urls if url not in successful_set]
    for failed_url in failed_unique:
        if failed_url not in pending_urls:
            pending_urls.append(failed_url)

    _write_urls(RETRY_FILE, pending_urls)


def download_album(
    url: str,
    live_manager: LiveManager,
    attempts: int = URL_RETRY_ATTEMPTS,
) -> bool:
    """Download one album with URL-level retries.

    Returns True on success and False after all attempts fail.
    """
    attempts = max(1, attempts)
    for attempt in range(1, attempts + 1):
        if attempt > 1:
            live_manager.update_log(
                "Album retry",
                f"Retrying {url} ({attempt}/{attempts})",
            )

        try:
            album_downloader = AlbumDownloader(url=url, live_manager=live_manager)
            album_downloader.download_album()
            return True
        except KeyboardInterrupt:
            sys.exit(1)
        except Exception as err:
            if attempt >= attempts:
                live_manager.update_log(
                    "Album failed",
                    f"Download failed for {url} after {attempts} attempt(s): {err}",
                )
                return False

            live_manager.update_log(
                "Album attempt failed",
                f"Attempt {attempt}/{attempts} failed for {url}: {err}",
            )

    return False


def download_albums(urls: list[str], live_manager: LiveManager) -> tuple[list[str], list[str]]:
    """Download a list of album URLs and return (successful_urls, failed_urls)."""
    successful_urls: list[str] = []
    failed_urls: list[str] = []

    for url in urls:
        if download_album(url, live_manager):
            successful_urls.append(url)
        else:
            failed_urls.append(url)

    return successful_urls, failed_urls


def initialize_managers() -> LiveManager:
    """Initialize and returns the managers for progress tracking and logging."""
    progress_manager = ProgressManager(task_name="Album", item_description="Page")
    logger_table = LoggerTable()
    return LiveManager(progress_manager, logger_table)


def main() -> None:
    """Run the album downloader."""
    if len(sys.argv) != 2:
        script_name = Path(__file__).name
        message = f"Usage: python3 {script_name} <album_url>"
        logging.error(message)
        sys.exit(1)

    clear_terminal()
    live_manager = initialize_managers()
    url = sys.argv[1]

    with live_manager.live:
        success = download_album(url, live_manager)
        failed_urls = [] if success else [url]
        successful_urls = [url] if success else []
        update_retry_file(successful_urls=successful_urls, failed_urls=failed_urls)
        live_manager.stop()

if __name__ == "__main__":
    main()
