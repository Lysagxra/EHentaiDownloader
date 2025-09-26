"""Main module of the project.

This module provides functionality to read URLs from a specified file, validate them,
and download the associated content. It manages the entire download process by
leveraging asynchronous operations, allowing for efficient handling of multiple URLs.

Usage:
    To run the module, execute the script directly. It will process URLs listed in
    'URLs.txt' and log the session activities in 'session.log'.
"""

import asyncio
import sys

from downloader import download_album, initialize_managers
from src.config import SESSION_LOG, URLS_FILE
from src.file_utils import read_file, write_file
from src.general_utils import clear_terminal


async def process_urls(urls: list[str]) -> None:
    """Validate and downloads items for a list of URLs."""
    live_manager = initialize_managers()

    with live_manager.live:
        for url in urls:
            download_album(url, live_manager)

        live_manager.stop()


async def main() -> None:
    """Run the script."""
    # Clear the terminal and session log file
    clear_terminal()
    write_file(SESSION_LOG)

    # Read and process URLs, ignoring empty lines
    urls = [url.strip() for url in read_file(URLS_FILE) if url.strip()]
    await process_urls(urls)

    # Clear URLs file
    write_file(URLS_FILE)


if __name__ == "__main__":
    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        sys.exit(1)
