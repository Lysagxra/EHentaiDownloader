"""Main module of the project.

This module provides functionality to read URLs from a specified file,
validate them, and download the associated content. It manages the entire
download process by leveraging asynchronous operations, allowing for
efficient handling of multiple URLs.

Usage:
    To run the module, execute the script directly. It will process URLs
    listed in 'URLs.txt' and log the session activities in 'session_log.txt'.
"""

import asyncio
import sys

from downloader import download_album, initialize_managers
from helpers.config import SESSION_LOG, URLS_FILE
from helpers.file_utils import read_file, write_file
from helpers.general_utils import clear_terminal


async def process_urls(urls: list[str]) -> None:
    """Validate and downloads items for a list of URLs."""
    live_manager = initialize_managers()

    try:
        with live_manager.live:
            for url in urls:
                download_album(url, live_manager)

            live_manager.stop()

    except KeyboardInterrupt:
        sys.exit(1)


async def main() -> None:
    """Run the script.

    Clears the session log, reads URLs from a file, processes them,
    and clears the URLs file at the end.
    """
    clear_terminal()
    write_file(SESSION_LOG)

    urls = read_file(URLS_FILE)
    await process_urls(urls)
    write_file(URLS_FILE)


if __name__ == "__main__":
    asyncio.run(main())
