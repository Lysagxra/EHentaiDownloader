# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **CBZ archive creation**: after an album finishes downloading, all images are packaged
  into a `.cbz` comic archive (zero-padded for correct page order). The archive is saved
  inside the album's own folder and the extracted images are removed afterwards.
- **CLI album URL**: `python3 main.py <album_url>` downloads a single album directly;
  the `URLs.txt` batch file is only used (and cleared) when no URL is given.

### Changed

- **Overall progress accuracy**: the overall progress bar now tracks downloaded images
  against the album's total image count, instead of one tick per finished page.
- **Resume support**: already-downloaded images are skipped, and downloads write to
  `.part` temp files first so an interrupted run never fakes a completed image.

### Fixed

- Crash on single-page albums (`next_pages[-2]` IndexError).
- Crash when an image page lacks the expected `nl` element or download link.
- Wrong CBZ page order (images were sorted by hash filename instead of download order).
- CBZ path failing when the album title contains path-hostile characters like `/`.

## [1.0.1] - 2026-03-19

### Changed

- Migrated project to a `src/` layout for a cleaner, more modular structure.

## [1.0.0] - 2025-08-04

### Added

- Single-album and batch downloads from E-Hentai URLs.
- Concurrent image downloads with rate limiting and retry handling.
- Live progress tracking and session logging.