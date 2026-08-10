"""Main module of the project.

This module provides functionality to read URLs from a specified file, validate them,
and download the associated content. It manages the entire download process by
leveraging asynchronous operations, allowing for efficient handling of multiple URLs.

Usage:
    To run the module, execute the script directly. It will process URLs listed in
    'URLs.txt' and log the session activities in 'session.log'.
"""

import sys

from downloader import (
    build_download_queue,
    download_albums,
    initialize_managers,
    update_retry_file,
)
from src.config import SESSION_LOG, URLS_FILE
from src.file_utils import read_file, write_file
from src.general_utils import clear_terminal


def process_urls(urls: list[str]) -> None:
    """Download queued URLs and persist failures into retry.txt."""
    live_manager = initialize_managers()

    with live_manager.live:
        successful_urls, failed_urls = download_albums(urls, live_manager)
        update_retry_file(successful_urls=successful_urls, failed_urls=failed_urls)

        live_manager.stop()


def main() -> None:
    """Run the script."""
    # Clear the terminal and session log file
    clear_terminal()
    write_file(SESSION_LOG)

    # Build a retry-aware queue from URLs.txt and retry.txt.
    input_urls = [url.strip() for url in read_file(URLS_FILE) if url.strip()]
    urls = build_download_queue(input_urls)

    if urls:
        process_urls(urls)

    # URLs.txt is cleared so completed items are not re-queued on the next run.
    write_file(URLS_FILE)


if __name__ == "__main__":
    try:
        main()

    except KeyboardInterrupt:
        sys.exit(1)
