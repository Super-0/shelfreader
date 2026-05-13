# ShelfReader

A Windows desktop reader for browsing local comic and image-book libraries with a polished gallery UI, metadata views, tag filtering, favorites, bookmarks, and reading progress.

## Overview

ShelfReader started as a local-library reading tool and grew into a richer desktop browsing experience. The app is designed for large folder-based image collections, with author/series browsing, metadata-backed discovery, and a reading flow that feels closer to a full desktop product than a simple file viewer.

## Highlights

- Desktop gallery view for authors and comic folders
- Image-reader mode with fit-width, fit-page, free zoom, panning, and fullscreen
- Natural sorting for folders and pages
- Intro/details page before opening a comic
- Tag-based filtering and metadata display
- Related-title suggestions and page preview thumbnails
- Favorites and per-page bookmarks
- Random-open discovery feature
- Persistent reading state and cover overrides
- Packaged Windows build flow with PyInstaller

## Tech Stack

- Python
- PySide6 / Qt
- Pillow
- SQLite
- PyInstaller

## What This Project Demonstrates

- Desktop application development in Python
- Qt UI design and interaction polish
- File-system-driven content browsing
- Local persistence for app state and metadata
- Metadata import, filtering, and discovery workflows
- Designing a richer reading UX beyond basic file navigation

## Expected Library Layout

```text
LibraryRoot\
LibraryRoot\Author A\
LibraryRoot\Author A\Series 1\001.jpg
LibraryRoot\Author A\Series 2\001.jpg
LibraryRoot\Author B\Series 1\001.jpg
```

Point the app at the root library folder and it will show creators/authors first, then the available series under each one.

## Run on Windows

```bat
cd C:\path\to\ShelfReader
py -m pip install -r requirements.txt
py main.py
```

Or double-click `run.bat`.

## Build the EXE

```bat
cd C:\path\to\ShelfReader
py -m pip install -r requirements.txt
py -m PyInstaller --noconfirm --onefile --windowed --name ShelfReader main.py
```

The built executable will be created at:

```text
dist\ShelfReader.exe
```

## Metadata Notes

The app includes support for importing metadata from a local SQLite archive and can optionally prepare an archive database from an external source. In this public version, the external archive endpoint is intentionally configurable through `COMIC_METADATA_ARCHIVE_URL` instead of being tied to a specific dataset.

## Controls

- `Ctrl+O` open library root
- `Esc` go back
- `Left / Right` previous / next page
- `Space / Backspace` next / previous page
- `1` fit width
- `2` fit page
- `3` free zoom
- `Ctrl + mousewheel` zoom
- `F11` fullscreen
- drag with left mouse button to pan

## Portfolio Note

This repository is the cleaned public version of the project, prepared for portfolio use.
