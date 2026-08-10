# E-Hentai Downloader

> A Python-based tool for downloading E-Hentai albums. This tool reads a list of URLs from a file and processes the downloads accordingly.

![Demo](https://github.com/Lysagxra/EHentaiDownloader/blob/e6e408181db6bb6707c29135c7fd04b4859830d5/misc/Demo.gif)

## Features

- Downloads multiple files concurrently.
- Supports [batch downloading](https://github.com/Lysagxra/EHentaiDownloader/tree/main?tab=readme-ov-file#batch-download) via a list of URLs.
- Tracks download progress with a progress bar.
- Automatically creates a directory structure for organized storage.
- URL-level retry for both batch and single-album runs.
- Automatic `retry.txt` generation and persistent recovery queue.
- Bidirectional domain fallback: `e-hentai.org <-> exhentai.org`.
- Partial resume support by skipping already downloaded files.

## Dependencies

- Python 3
- `BeautifulSoup` (bs4) - for HTML parsing
- `fake_useragent` - for generating fake user agents for web scraping
- `requests` - for HTTP requests
- `rich` - for progress display in the terminal

<details>

<summary>Show directory structure</summary>

```
project-root/
├── src/
│ ├── crawlers/
│ │ ├── crawler.py           # Main crawler module used across the project
│ │ └── crawler_utils.py     # Utilities for extracting media download links
│ ├── downloaders/
│ │ ├── album_downloader.py  # Manages the downloading of entire albums
│ │ └── download_utils.py    # Utilities for managing the download process
│ ├── managers/
│ │ ├── live_manager.py      # Manages a real-time live display
│ │ ├── log_manager.py       # Manages real-time log updates
│ │ └── progress_manager.py  # Manages progress bars
│ ├── config.py              # Manages constants and settings used across the project
│ ├── file_utils.py          # Utilities for managing file operations
│ └── general_utils.py       # Miscellaneous utility functions
├── downloader.py            # Module for initiating downloads from specified EHentai URLs
├── main.py                  # Main script to run the downloader
├── URLs.txt                 # Text file listing album URLs to be downloaded
└── session_log.txt          # Log file for recording session details
```

</details>

## Installation

1. Clone the repository:

```bash
git clone https://github.com/Lysagxra/EHentaiDownloader.git
```

2. Navigate to the project directory:

```bash
cd EHentaiDownloader
```

3. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Single Album Download

To download a single album from an URL, you can use `downloader.py`, running the script with a valid album URL.

### Usage

```bash
python3 downloader.py <album_url>
```

### Example

```
python3 downloader.py https://e-hentai.org/g/3392858/1a77348e16/
```

## Batch Download

To batch download from multiple album URLs, you can use the `main.py` script. This script reads URLs from a file named `URLs.txt` and downloads each one using the album downloader.

### Usage

1. Create a file named `URLs.txt` in the root of your project, listing each URL on a new line.

- Example of `URLs.txt`:

```
https://e-hentai.org/g/2466603/ab9b9e04c9/
https://e-hentai.org/g/2486673/e24cf9d5d8/
https://e-hentai.org/g/2490534/e80e7c554c/
```

- Ensure that each URL is on its own line without any extra spaces.
- You can add as many URLs as you need, following the same format.

2. Run the batch download script:

```bash
python3 main.py
```

3. The downloaded files will be saved in the `Downloads` directory.


## Recovery / Retry Workflow

The downloader now supports recovery across runs through `retry.txt`.

- `retry.txt` is created automatically if it does not exist.
- Failed URLs are written to `retry.txt`.
- Successful URLs are removed from `retry.txt`.
- Batch mode reads URLs from both `URLs.txt` and `retry.txt` (deduplicated, stable order).
- `URLs.txt` is cleared at the end of a run; unresolved URLs remain in `retry.txt`.

### Typical recovery flow (batch)

1. Put new gallery URLs in `URLs.txt`.
2. Run:

```
python3 main.py
```

3. If some URLs fail, rerun the same command. Pending entries from `retry.txt` are retried automatically.

### Typical recovery flow (single URL)

1. Run:

```bash
python3 downloader.py <album_url>
```

2. If it fails after retries, the URL is added to `retry.txt`.
3. Run again later; if successful, that URL is removed from `retry.txt`.


## Retry and Resume Settings

- URL-level retries are configured by `URL_RETRY_ATTEMPTS` in `src/config.py`.
- Image-level retries are handled internally in the downloader utilities.
- Already downloaded image files are skipped to resume interrupted downloads.


## Domain Fallback Behavior

When a gallery page is unavailable or unusable on one domain, the downloader automatically
tries the alternate domain:

- `e-hentai.org` -> `exhentai.org`
- `exhentai.org` -> `e-hentai.org`

Note: `exhentai.org` may require valid cookies to avoid the "Sad Panda" page.


## Logging

The application logs issues encountered during the download process in `session.log`.

Failed URL tracking is persisted in `retry.txt`.
