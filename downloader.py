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

from src.downloader.album_downloader import AlbumDownloader
from src.general_utils import clear_terminal
from src.managers.live_manager import LiveManager
from src.managers.log_manager import LoggerTable
from src.managers.progress_manager import ProgressManager


def download_album(url: str, live_manager: LiveManager) -> None:
    """Download an album using the provided live manager."""
    album_downloader = AlbumDownloader(url=url, live_manager=live_manager)

    try:
        with live_manager.live:
            album_downloader.download_album()
            live_manager.stop()

    except KeyboardInterrupt:
        sys.exit(1)


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
    download_album(url, live_manager)

if __name__ == "__main__":
    main()
