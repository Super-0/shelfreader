from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
import sys
import zipfile
from urllib import error as urlerror
from urllib.request import Request, urlopen
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List

from PySide6.QtCore import QPoint, QRect, Qt, QSize, Signal
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QImageReader, QKeySequence, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenu,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QStatusBar,
    QStyledItemDelegate,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".gif"}
BOOK_ARCHIVE_EXTENSIONS = {".cbz", ".zip"}
APP_NAME = "GalleryReader"
APP_BRAND = "galleryreader."
APP_VERSION_LABEL = "LOCAL LIBRARY"
STATE_PATH = Path.home() / ".galleryreader.json"
METADATA_PATH = Path.home() / ".galleryreader-library.json"
ARCHIVE_DB_PATH = Path.home() / ".galleryreader-archive.db"
ARCHIVE_TMP_DIR = Path.home() / ".galleryreader-archive-parts"
SORT_OPTIONS = ["Name (A-Z)", "Name (Z-A)", "Recently Read", "Page Count"]
TAG_FILTER_ALL = "All tags"
ARCHIVE_REPO_CONTENTS_URL = "https://example.com/archive"
ARCHIVE_TABLE = "archive_data"
IGNORED_QUERY_TOKENS = {
    "english",
    "digital",
    "translated",
    "uncensored",
    "colorized",
    "full",
    "version",
    "comic",
    "artist",
    "ch",
    "chapter",
}
APP_STYLE = """
QMainWindow {
    background: #eef2f7;
}
QWidget {
    color: #0f172a;
    font-family: "Segoe UI", "SF Pro Text", "Inter", sans-serif;
    font-size: 13px;
}
QStatusBar {
    background: rgba(255, 255, 255, 0.96);
    color: #667085;
    border-top: 1px solid #d8dee8;
}
QWidget#comicIntroPage,
QWidget#introContent,
QScrollArea {
    background: transparent;
    border: none;
}
QWidget#readerPage {
    background: #0b1220;
}
QWidget#readerBottomBar {
    background: rgba(15, 23, 42, 0.78);
    border: 1px solid rgba(148, 163, 184, 0.16);
    border-radius: 20px;
}
QWidget#appHeader,
QWidget#seriesSummaryCard {
    background: rgba(255, 255, 255, 0.96);
    border: 1px solid #dde3ec;
    border-radius: 20px;
}
QWidget#continueReadingCard {
    background: rgba(255, 255, 255, 0.96);
    border: none;
    border-radius: 20px;
}
QLabel#appBrandMark {
    color: #ffffff;
    background: #111827;
    border-radius: 12px;
    min-width: 34px;
    max-width: 34px;
    min-height: 34px;
    max-height: 34px;
    font-size: 15px;
    font-weight: 700;
    qproperty-alignment: AlignCenter;
}
QLabel#appBrandTitle {
    color: #0f172a;
    font-size: 14px;
    font-weight: 700;
}
QLabel#appBrandMeta,
QLabel#seriesSummaryEyebrow,
QLabel#continueEyebrow {
    color: #667085;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.16em;
}
QLabel#seriesSummaryTitle {
    color: #0f172a;
    font-size: 18px;
    font-weight: 700;
}
QLabel#seriesSummaryMeta,
QLabel#continueMeta {
    color: #667085;
    font-size: 13px;
}
QLabel#continueTitle {
    color: #0f172a;
    font-size: 14px;
    font-weight: 700;
}
QWidget#readerTopBar {
    background: rgba(15, 23, 42, 0.78);
    border: 1px solid rgba(148, 163, 184, 0.16);
    border-radius: 20px;
}
QLabel#readerEyebrow {
    color: #94a3b8;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.16em;
}
QLabel#readerTitle,
QLabel#readerMeta {
    color: #e5eefc;
}
QLabel#readerTitle {
    font-size: 15px;
    font-weight: 700;
}
QLabel#readerMeta {
    font-size: 12px;
    color: #94a3b8;
}
QLabel#readerChip {
    color: #e5eefc;
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 999px;
    min-height: 40px;
    padding: 0 16px;
    font-size: 11px;
    font-weight: 600;
}
QPushButton#readerBackButton {
    background: rgba(255, 255, 255, 0.08);
    color: #f8fafc;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 999px;
    min-height: 40px;
    padding: 0 18px;
}
QPushButton#readerBackButton:hover {
    background: rgba(255, 255, 255, 0.14);
    border: 1px solid rgba(255, 255, 255, 0.18);
}
QWidget#introPanel,
QWidget#introHeroPanel,
QWidget#introRelatedPanel {
    background: rgba(255, 255, 255, 0.96);
    border: 1px solid #dde3ec;
    border-radius: 22px;
}
QLabel#introTitle {
    color: #0f172a;
    font-size: 28px;
    font-weight: 700;
}
QLabel#introMeta {
    color: #667085;
    font-size: 13px;
}
QLabel#introBadge {
    color: #334155;
    font-size: 12px;
    font-weight: 600;
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 999px;
    padding: 6px 11px;
}
QLabel#introSection {
    color: #0f172a;
    font-size: 15px;
    font-weight: 700;
    padding-top: 4px;
}
QLabel#introBody,
QLabel#introTags,
QLabel#introChip {
    color: #334155;
    font-size: 13px;
    background: #f8fafc;
    border: 1px solid #e5e7eb;
    border-radius: 16px;
    padding: 14px 16px;
}
QListWidget#relatedList,
QListWidget {
    background: transparent;
    border: none;
    outline: none;
}
QListWidget#libraryGrid::item {
    background: transparent;
    border: none;
    border-radius: 0px;
    padding: 0px;
    margin: 8px;
}
QListWidget#booksList::item,
QListWidget#relatedList::item {
    background: rgba(255, 255, 255, 0.97);
    border: 1px solid #dbe2ea;
    border-radius: 16px;
    padding: 10px 12px;
    margin: 6px 8px;
}
QListWidget::item:hover {
    background: transparent;
    border: none;
}
QListWidget::item:selected {
    background: transparent;
    border: none;
    color: #0f172a;
}
QPushButton#heroReadButton {
    min-width: 190px;
}
QLabel#sectionLabel {
    color: #0f172a;
    font-size: 22px;
    font-weight: 700;
}
QLabel#helperLabel,
QLabel#sortLabel {
    color: #667085;
    font-size: 12px;
}
QComboBox {
    background: rgba(255, 255, 255, 0.96);
    color: #0f172a;
    border: 1px solid #d8dee8;
    border-radius: 14px;
    padding: 8px 12px;
    min-width: 190px;
}
QComboBox:hover,
QComboBox:focus {
    border: 1px solid #b8c4d3;
}
QComboBox QAbstractItemView {
    background: #ffffff;
    color: #0f172a;
    selection-background-color: #eef2ff;
    selection-color: #0f172a;
    border: 1px solid #d8dee8;
}
QPushButton {
    background: rgba(255, 255, 255, 0.96);
    color: #0f172a;
    border: 1px solid #d8dee8;
    border-radius: 999px;
    padding: 10px 15px;
    font-weight: 600;
}
QPushButton:hover {
    background: #eef4ff;
    border: 1px solid #93a4bb;
}
QPushButton#backButton {
    max-width: 180px;
}
QPushButton#headerButton {
    background: rgba(255, 255, 255, 0.96);
    color: #0f172a;
    border: 1px solid #d8dee8;
    border-radius: 20px;
    min-height: 40px;
    padding: 0 20px;
}
QPushButton#headerButton:hover {
    background: #eef4ff;
    border: 1px solid #93a4bb;
}
QMessageBox,
QDialog,
QProgressDialog {
    background: #ffffff;
}
QMessageBox QLabel,
QDialog QLabel,
QProgressDialog QLabel {
    color: #0f172a;
}
QMessageBox QListView,
QDialog QListView,
QMessageBox QComboBox,
QDialog QComboBox,
QMessageBox QLineEdit,
QDialog QLineEdit {
    background: #ffffff;
    color: #0f172a;
    border: 1px solid #d8dee8;
}
QMessageBox QPushButton,
QDialog QPushButton,
QProgressDialog QPushButton {
    min-width: 90px;
}
QScrollBar:vertical {
    background: transparent;
    width: 12px;
    margin: 4px 2px 4px 0;
}
QScrollBar::handle:vertical {
    background: #cbd5e1;
    min-height: 32px;
    border-radius: 6px;
}
QScrollBar::handle:vertical:hover {
    background: #94a3b8;
}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background: transparent;
    border: none;
}
"""

APP_STYLE_DARK = """
QMainWindow {
    background: #07090d;
}
QWidget {
    color: #eef2f7;
    font-family: "Segoe UI", "SF Pro Text", "Inter", sans-serif;
    font-size: 13px;
}
QStatusBar {
    background: rgba(10, 12, 18, 0.98);
    color: #8d98a7;
    border-top: 1px solid rgba(255, 255, 255, 0.07);
}
QWidget#comicIntroPage,
QWidget#introContent,
QScrollArea,
QWidget#readerPage {
    background: #07090d;
    border: none;
}
QWidget#readerTopBar,
QWidget#readerBottomBar {
    background: rgba(14, 17, 24, 0.9);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 20px;
}
QLabel#readerEyebrow {
    color: #8d98a7;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.16em;
}
QWidget#appHeader,
QWidget#seriesSummaryCard {
    background: rgba(14, 17, 24, 0.96);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 20px;
}
QWidget#continueReadingCard {
    background: rgba(14, 17, 24, 0.96);
    border: none;
    border-radius: 20px;
}
QLabel#appBrandMark {
    color: #f5f7fb;
    background: #171b22;
    border-radius: 12px;
    min-width: 34px;
    max-width: 34px;
    min-height: 34px;
    max-height: 34px;
    font-size: 15px;
    font-weight: 700;
    qproperty-alignment: AlignCenter;
}
QLabel#appBrandTitle {
    color: #f5f7fb;
    font-size: 14px;
    font-weight: 700;
}
QLabel#appBrandMeta,
QLabel#seriesSummaryEyebrow,
QLabel#continueEyebrow {
    color: #8d98a7;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.16em;
}
QLabel#seriesSummaryTitle {
    color: #f5f7fb;
    font-size: 18px;
    font-weight: 700;
}
QLabel#seriesSummaryMeta,
QLabel#continueMeta {
    color: #8d98a7;
    font-size: 13px;
}
QLabel#continueTitle {
    color: #f5f7fb;
    font-size: 14px;
    font-weight: 700;
}
QLabel#readerTitle,
QLabel#readerMeta {
    color: #eef2f7;
}
QLabel#readerTitle {
    font-size: 15px;
    font-weight: 700;
}
QLabel#readerMeta {
    font-size: 12px;
    color: #8d98a7;
}
QLabel#readerChip {
    color: #eef2f7;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 999px;
    min-height: 40px;
    padding: 0 16px;
    font-size: 11px;
    font-weight: 600;
}
QPushButton#readerBackButton {
    background: rgba(255, 255, 255, 0.045);
    color: #eef2f7;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 999px;
    min-height: 40px;
    padding: 0 18px;
}
QPushButton#readerBackButton:hover {
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.12);
}
QWidget#introPanel,
QWidget#introHeroPanel,
QWidget#introRelatedPanel {
    background: rgba(14, 17, 24, 0.96);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 22px;
}
QLabel#introTitle,
QLabel#sectionLabel,
QLabel#introSection {
    color: #f5f7fb;
}
QLabel#introTitle {
    font-size: 28px;
    font-weight: 700;
}
QLabel#introMeta,
QLabel#helperLabel,
QLabel#sortLabel {
    color: #8d98a7;
    font-size: 12px;
}
QLabel#introBadge {
    color: #d6dde7;
    font-size: 12px;
    font-weight: 600;
    background: rgba(255, 255, 255, 0.045);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 999px;
    padding: 6px 11px;
}
QLabel#introBody,
QLabel#introTags,
QLabel#introChip {
    color: #d9e0ea;
    font-size: 13px;
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 16px;
    padding: 14px 16px;
}
QListWidget#relatedList,
QListWidget {
    background: transparent;
    border: none;
    outline: none;
}
QListWidget#libraryGrid::item {
    background: transparent;
    border: none;
    border-radius: 0px;
    padding: 0px;
    margin: 8px;
}
QListWidget#booksList::item,
QListWidget#relatedList::item {
    background: rgba(17, 20, 28, 0.98);
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 16px;
    padding: 10px 12px;
    margin: 6px 8px;
}
QListWidget::item:hover {
    background: transparent;
    border: none;
}
QListWidget::item:selected {
    background: transparent;
    border: none;
    color: #eef2f7;
}
QPushButton#heroReadButton {
    min-width: 190px;
}
QLabel#sectionLabel {
    font-size: 22px;
    font-weight: 700;
}
QComboBox {
    background: rgba(17, 20, 28, 0.98);
    color: #eef2f7;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 14px;
    padding: 8px 12px;
    min-width: 190px;
}
QComboBox:hover,
QComboBox:focus {
    border: 1px solid rgba(255, 255, 255, 0.14);
}
QComboBox QAbstractItemView {
    background: #11141c;
    color: #eef2f7;
    selection-background-color: rgba(255, 255, 255, 0.08);
    selection-color: #eef2f7;
    border: 1px solid rgba(255, 255, 255, 0.08);
}
QPushButton {
    background: rgba(17, 20, 28, 0.98);
    color: #eef2f7;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 999px;
    padding: 10px 15px;
    font-weight: 600;
}
QPushButton:hover {
    background: rgba(255, 255, 255, 0.11);
    border: 1px solid rgba(255, 255, 255, 0.18);
}
QPushButton#backButton {
    max-width: 180px;
}
QPushButton#headerButton {
    background: rgba(255, 255, 255, 0.045);
    color: #eef2f7;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 20px;
    min-height: 40px;
    padding: 0 20px;
}
QPushButton#headerButton:hover {
    background: rgba(255, 255, 255, 0.13);
    border: 1px solid rgba(255, 255, 255, 0.2);
}
QMessageBox,
QDialog,
QProgressDialog {
    background: #11141c;
}
QMessageBox QLabel,
QDialog QLabel,
QProgressDialog QLabel {
    color: #eef2f7;
}
QMessageBox QListView,
QDialog QListView,
QMessageBox QComboBox,
QDialog QComboBox,
QMessageBox QLineEdit,
QDialog QLineEdit {
    background: #171b22;
    color: #eef2f7;
    border: 1px solid rgba(255, 255, 255, 0.08);
}
QMessageBox QPushButton,
QDialog QPushButton,
QProgressDialog QPushButton {
    min-width: 90px;
}
QScrollBar:vertical {
    background: transparent;
    width: 12px;
    margin: 4px 2px 4px 0;
}
QScrollBar::handle:vertical {
    background: #2a303a;
    min-height: 32px;
    border-radius: 6px;
}
QScrollBar::handle:vertical:hover {
    background: #3a414d;
}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical,
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background: transparent;
    border: none;
}
"""


def natural_key(text: str):
    return [int(part) if part.isdigit() else part.lower() for part in re.split(r"(\d+)", text)]


def list_image_files(folder: Path) -> List[Path]:
    files = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS]
    files.sort(key=lambda p: natural_key(p.name))
    return files


def list_archive_books(folder: Path) -> List[Path]:
    files = [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in BOOK_ARCHIVE_EXTENSIONS]
    files.sort(key=lambda p: natural_key(p.name))
    return files


def list_subfolders(folder: Path) -> List[Path]:
    folders = [p for p in folder.iterdir() if p.is_dir()]
    folders.sort(key=lambda p: natural_key(p.name))
    return folders


def first_cover_in_folder(folder: Path) -> Path | None:
    pages = list_image_files(folder)
    if pages:
        return pages[0]
    for child in list_subfolders(folder):
        pages = list_image_files(child)
        if pages:
            return pages[0]
    return None


def is_archive_book(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in BOOK_ARCHIVE_EXTENSIONS


def is_image_folder_book(path: Path) -> bool:
    return path.is_dir() and bool(list_image_files(path))


def list_books_in_series(series_folder: Path) -> List[Path]:
    books = list_archive_books(series_folder)
    books.extend(child for child in list_subfolders(series_folder) if is_image_folder_book(child))
    books.sort(key=lambda p: natural_key(p.name))
    return books


def count_books_in_series(series_folder: Path) -> int:
    return len(list_books_in_series(series_folder))


def all_series_folders(root: Path) -> List[Path]:
    series: List[Path] = []
    for folder, dirnames, _ in os.walk(root, topdown=True):
        path = Path(folder)
        if count_books_in_series(path):
            series.append(path)
            dirnames[:] = []
    series.sort(key=lambda p: natural_key(p.name))
    return series


@dataclass
class PageEntry:
    book_path: Path
    page_path: Path | None = None
    archive_member: str | None = None

    @property
    def name(self) -> str:
        return self.page_path.name if self.page_path else Path(self.archive_member or "").name


def list_pages_for_book(book: Path) -> List[PageEntry]:
    if is_archive_book(book):
        try:
            with zipfile.ZipFile(book) as archive:
                names = [
                    name for name in archive.namelist()
                    if not name.endswith("/") and Path(name).suffix.lower() in SUPPORTED_EXTENSIONS
                ]
        except Exception:
            return []
        names.sort(key=lambda name: natural_key(Path(name).name))
        return [PageEntry(book_path=book, archive_member=name) for name in names]

    if is_image_folder_book(book):
        return [PageEntry(book_path=book, page_path=page) for page in list_image_files(book)]

    return []


def count_pages_in_book(book: Path) -> int:
    return len(list_pages_for_book(book))


def load_page_pixmap(page: PageEntry) -> QPixmap | None:
    if page.page_path:
        pixmap = QPixmap(str(page.page_path))
        return None if pixmap.isNull() else pixmap

    if page.archive_member:
        try:
            with zipfile.ZipFile(page.book_path) as archive:
                data = archive.read(page.archive_member)
        except Exception:
            return None
        pixmap = QPixmap()
        if not pixmap.loadFromData(data):
            return None
        return pixmap

    return None


def first_page_for_book(book: Path) -> PageEntry | None:
    pages = list_pages_for_book(book)
    return pages[0] if pages else None


def first_cover_for_series(series_folder: Path) -> Path | None:
    books = list_books_in_series(series_folder)
    if not books:
        return None
    first_book = books[0]
    if is_image_folder_book(first_book):
        return first_cover_in_folder(first_book)
    return None


def build_cover_pixmap_from_base(cover: QPixmap, size: QSize, radius: float = 18.0) -> QPixmap | None:
    if cover.isNull():
        return None

    canvas = QPixmap(size)
    canvas.fill(Qt.GlobalColor.transparent)

    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

    target = canvas.rect().adjusted(4, 4, -4, -4)
    clip_path = QPainterPath()
    clip_path.addRoundedRect(float(target.x()), float(target.y()), float(target.width()), float(target.height()), radius, radius)
    painter.setClipPath(clip_path)

    scaled = cover.scaled(target.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
    x = target.x() + (target.width() - scaled.width()) // 2
    y = target.y() + (target.height() - scaled.height()) // 2
    painter.drawPixmap(x, y, scaled)

    painter.end()
    return canvas


def build_cover_pixmap(image_path: Path, size: QSize, radius: float = 18.0) -> QPixmap | None:
    cover = QPixmap(str(image_path))
    return build_cover_pixmap_from_base(cover, size, radius)


def build_cover_pixmap_for_book(book: Path, size: QSize, radius: float = 18.0) -> QPixmap | None:
    first_page = first_page_for_book(book)
    if not first_page:
        return None
    pixmap = load_page_pixmap(first_page)
    if pixmap is None:
        return None
    return build_cover_pixmap_from_base(pixmap, size, radius)


def author_comic_folders(author_folder: Path) -> List[Path]:
    return [child for child in list_subfolders(author_folder) if list_image_files(child)]


def count_direct_comics(author_folder: Path) -> int:
    return count_books_in_series(author_folder)


def count_pages(folder: Path) -> int:
    return count_pages_in_book(folder)


def all_comic_folders(root: Path) -> List[Path]:
    comics: List[Path] = []
    for series_folder in all_series_folders(root):
        comics.extend(list_books_in_series(series_folder))
    return comics


def sort_folders(folders: List[Path], mode: str, progress: dict[str, int], author_mode: bool) -> List[Path]:
    items = list(folders)
    if mode == "Name (A-Z)":
        items.sort(key=lambda p: natural_key(p.name))
    elif mode == "Name (Z-A)":
        items.sort(key=lambda p: natural_key(p.name), reverse=True)
    elif mode == "Recently Read":
        def recent_key(path: Path):
            val = progress.get(str(path), -1)
            return (val >= 0, val, natural_key(path.name))
        items.sort(key=recent_key, reverse=True)
    elif mode == "Page Count":
        if author_mode:
            items.sort(key=lambda p: (count_direct_comics(p), natural_key(p.name)), reverse=True)
        else:
            items.sort(key=lambda p: (count_pages(p), natural_key(p.name)), reverse=True)
    return items


def author_cover_for_display(author_folder: Path, overrides: dict[str, str]) -> Path | None:
    comics = author_comic_folders(author_folder)
    if not comics:
        return None

    preferred = overrides.get(str(author_folder))
    if preferred:
        preferred_path = Path(preferred)
        if preferred_path.exists() and author_folder in preferred_path.parents and preferred_path.suffix.lower() in SUPPORTED_EXTENSIONS:
            return preferred_path

    return first_cover_in_folder(comics[0])


def normalize_text(text: Any) -> str:
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", text.lower())).strip()


def tokenize(text: Any) -> list[str]:
    return [token for token in normalize_text(text).split() if len(token) > 1 and token not in IGNORED_QUERY_TOKENS]


def split_csv_field(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, str):
        value = str(value)
    return [part.strip() for part in value.split(",") if part.strip()]


def strip_leading_metadata(name: str) -> str:
    text = name.strip()
    while True:
        updated = re.sub(r"^\s*(\([^)]+\)|\[[^\]]+\])\s*", "", text)
        if updated == text:
            break
        text = updated.strip()
    text = re.sub(r"\s*(\[[^\]]+\]|\([^)]+\))\s*$", "", text).strip(" -")
    return text.strip()


def parse_folder_profile(folder: Path) -> dict[str, Any]:
    name = folder.name
    credit_match = re.search(r"\[([^\]]+)\]", name)
    artist = folder.parent.name if folder.parent != folder else ""
    group = ""
    if credit_match:
        credit = credit_match.group(1).strip()
        paren_match = re.match(r"(.+?)\((.+)\)$", credit)
        if paren_match:
            group = paren_match.group(1).strip()
            artist = paren_match.group(2).strip()
        else:
            artist = credit

    title = strip_leading_metadata(name)
    if not title:
        title = name

    return {
        "title": title,
        "artist": artist,
        "group": group,
        "page_count": count_pages(folder),
    }


def score_candidate(profile: dict[str, Any], candidate: dict[str, Any]) -> float:
    title_tokens = set(tokenize(profile.get("title", "")))
    candidate_title = candidate.get("CLEAN_TITLE") or candidate.get("EN_TITLE") or candidate.get("JP_TITLE") or ""
    candidate_tokens = set(tokenize(candidate_title))

    overlap = 0.0
    if title_tokens and candidate_tokens:
        overlap = len(title_tokens & candidate_tokens) / max(1, len(title_tokens | candidate_tokens))

    normalized_title = normalize_text(profile.get("title", ""))
    normalized_candidate_title = normalize_text(candidate_title)
    title_bonus = 0.0
    if normalized_title and normalized_candidate_title:
        if normalized_title == normalized_candidate_title:
            title_bonus = 0.35
        elif normalized_title in normalized_candidate_title or normalized_candidate_title in normalized_title:
            title_bonus = 0.2

    artist_bonus = 0.0
    artist = normalize_text(profile.get("artist", ""))
    group = normalize_text(profile.get("group", ""))
    candidate_artist = normalize_text(candidate.get("ARTIST", ""))
    candidate_group = normalize_text(candidate.get("GROUP_NAME", ""))
    if artist and (artist in candidate_artist or artist in candidate_group):
        artist_bonus += 0.2
    if group and (group in candidate_group or group in candidate_artist):
        artist_bonus += 0.2

    page_bonus = 0.0
    local_pages = profile.get("page_count", 0) or 0
    remote_pages = int(candidate.get("PAGES") or 0)
    if local_pages and remote_pages:
        gap = abs(local_pages - remote_pages)
        page_bonus = max(0.0, 0.1 - min(gap, 25) * 0.004)

    return round(min(1.0, overlap + title_bonus + artist_bonus + page_bonus), 3)


def fetch_json(url: str, timeout: int = 20) -> Any:
    request = Request(url, headers={"User-Agent": f"{APP_NAME}/1.0"})
    with urlopen(request, timeout=timeout) as response:
        return json.load(response)


def archive_part_manifest() -> list[dict[str, Any]]:
    data = fetch_json(ARCHIVE_REPO_CONTENTS_URL)
    if not isinstance(data, list):
        raise ValueError("Unexpected archive manifest response")
    parts = [item for item in data if item.get("name", "").startswith("database.part")]
    parts.sort(key=lambda item: int(str(item["name"]).split("part")[-1]))
    return parts


def download_archive_file(url: str, destination: Path, progress=None, label: str = "") -> None:
    request = Request(url, headers={"User-Agent": f"{APP_NAME}/1.0"})
    with urlopen(request, timeout=60) as response, destination.open("wb") as handle:
        total = response.headers.get("Content-Length")
        total_bytes = int(total) if total and total.isdigit() else None
        written = 0
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            handle.write(chunk)
            written += len(chunk)
            if progress:
                progress(written, total_bytes, label)


def ensure_archive_database(progress=None) -> Path:
    if ARCHIVE_DB_PATH.exists() and ARCHIVE_DB_PATH.stat().st_size > 0:
        return ARCHIVE_DB_PATH

    parts = archive_part_manifest()
    ARCHIVE_TMP_DIR.mkdir(parents=True, exist_ok=True)
    merged_tmp = ARCHIVE_TMP_DIR / "database_merged.db"

    for item in parts:
        part_path = ARCHIVE_TMP_DIR / item["name"]
        size = int(item.get("size") or 0)
        if part_path.exists() and part_path.stat().st_size == size and size > 0:
            if progress:
                progress(size, size, f"Have {item['name']}")
            continue
        download_archive_file(item["download_url"], part_path, progress=progress, label=f"Downloading {item['name']}")

    with merged_tmp.open("wb") as merged:
        for item in parts:
            with (ARCHIVE_TMP_DIR / item["name"]).open("rb") as part_handle:
                shutil.copyfileobj(part_handle, merged)

    final_tmp = ARCHIVE_TMP_DIR / "database_ready.db"
    if final_tmp.exists():
        final_tmp.unlink()
    merged_tmp.replace(final_tmp)
    build_archive_indexes(final_tmp)
    final_tmp.replace(ARCHIVE_DB_PATH)
    return ARCHIVE_DB_PATH


def build_archive_indexes(db_path: Path) -> None:
    with sqlite3.connect(db_path) as con:
        cur = con.cursor()
        cur.execute(f"CREATE INDEX IF NOT EXISTS idx_{ARCHIVE_TABLE}_clean_title ON {ARCHIVE_TABLE}(CLEAN_TITLE)")
        cur.execute(f"CREATE INDEX IF NOT EXISTS idx_{ARCHIVE_TABLE}_artist ON {ARCHIVE_TABLE}(ARTIST)")
        cur.execute(f"CREATE INDEX IF NOT EXISTS idx_{ARCHIVE_TABLE}_group_name ON {ARCHIVE_TABLE}(GROUP_NAME)")
        cur.execute(f"CREATE INDEX IF NOT EXISTS idx_{ARCHIVE_TABLE}_pages ON {ARCHIVE_TABLE}(PAGES)")
        con.commit()


def fetch_archive_candidates(folder: Path, limit: int = 8) -> list[dict[str, Any]] | None:
    if not ARCHIVE_DB_PATH.exists():
        return None

    profile = parse_folder_profile(folder)
    title_tokens = sorted(set(tokenize(profile.get("title", ""))), key=len, reverse=True)
    primary_tokens = title_tokens[:4] or [normalize_text(profile.get("title", ""))[:24]]
    if not primary_tokens or not primary_tokens[0]:
        return []

    queries: list[tuple[str, list[Any]]] = []
    title_where = " OR ".join(["CLEAN_TITLE LIKE ? OR EN_TITLE LIKE ? OR JP_TITLE LIKE ?" for _ in primary_tokens])
    title_params: list[Any] = []
    for token in primary_tokens:
        like = f"%{token}%"
        title_params.extend([like, like, like])

    artist_terms = [term for term in [profile.get("artist", ""), profile.get("group", "")] if term]
    if artist_terms:
        artist_where = " OR ".join(["ARTIST LIKE ? OR GROUP_NAME LIKE ?" for _ in artist_terms])
        artist_params: list[Any] = []
        for term in artist_terms:
            like = f"%{term}%"
            artist_params.extend([like, like])
        queries.append(
            (
                f"SELECT * FROM {ARCHIVE_TABLE} WHERE ({artist_where}) AND ({title_where}) LIMIT 120",
                artist_params + title_params,
            )
        )

    queries.append((f"SELECT * FROM {ARCHIVE_TABLE} WHERE ({title_where}) LIMIT 160", title_params))

    seen_ids: set[int] = set()
    candidates: list[dict[str, Any]] = []
    try:
        with sqlite3.connect(ARCHIVE_DB_PATH) as con:
            con.row_factory = sqlite3.Row
            cur = con.cursor()
            for sql, params in queries:
                for row in cur.execute(sql, params).fetchall():
                    row_id = int(row["ID"])
                    if row_id in seen_ids:
                        continue
                    seen_ids.add(row_id)
                    candidate = {key: row[key] for key in row.keys()}
                    candidate["score"] = score_candidate(profile, candidate)
                    candidates.append(candidate)
    except sqlite3.Error:
        return None

    candidates.sort(key=lambda row: row.get("score", 0.0), reverse=True)
    return candidates[:limit]


def metadata_record_from_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    title = candidate.get("CLEAN_TITLE") or candidate.get("EN_TITLE") or candidate.get("JP_TITLE") or ""
    return {
        "id": candidate.get("ID"),
        "title": title,
        "jp_title": candidate.get("JP_TITLE", ""),
        "language": candidate.get("LANGUAGE", ""),
        "artists": split_csv_field(candidate.get("ARTIST", "")),
        "groups": split_csv_field(candidate.get("GROUP_NAME", "")),
        "category": candidate.get("CATEGORY", ""),
        "parodies": split_csv_field(candidate.get("PARODY", "")),
        "characters": split_csv_field(candidate.get("CHARACTER", "")),
        "tags": split_csv_field(candidate.get("TAGS", "")),
        "pages": int(candidate.get("PAGES") or 0),
        "upload_date": candidate.get("UPLOAD_DATE"),
        "source": "archive",
        "score": candidate.get("score", 0.0),
        "match_status": "matched",
    }


def candidate_label(candidate: dict[str, Any]) -> str:
    title = candidate.get("CLEAN_TITLE") or candidate.get("EN_TITLE") or candidate.get("JP_TITLE") or "Untitled"
    artist = candidate.get("ARTIST") or candidate.get("GROUP_NAME") or "unknown"
    pages = candidate.get("PAGES") or "?"
    score = candidate.get("score", 0.0)
    return f"{title} — {artist} — {pages} pages — score {score:.2f}"


@dataclass
class ReaderState:
    last_root: str = ""
    last_author: str = ""
    last_folder: str = ""
    last_page: int = 0
    fit_mode: str = "fit_page"
    zoom_percent: int = 100
    fullscreen: bool = False
    progress: dict[str, int] = field(default_factory=dict)
    author_thumbnail_comics: dict[str, str] = field(default_factory=dict)
    author_sort: str = "Name (A-Z)"
    comic_sort: str = "Name (A-Z)"
    comic_tag_filter: str = ""
    favorite_comics: list[str] = field(default_factory=list)
    page_bookmarks: dict[str, list[int]] = field(default_factory=dict)
    dark_mode: bool = False

    @classmethod
    def load(cls) -> "ReaderState":
        try:
            return cls(**json.loads(STATE_PATH.read_text(encoding="utf-8")))
        except Exception:
            return cls()

    def save(self) -> None:
        STATE_PATH.write_text(json.dumps(self.__dict__, indent=2), encoding="utf-8")


@dataclass
class LibraryMetadata:
    comics: dict[str, dict[str, Any]] = field(default_factory=dict)
    review_queue: dict[str, list[dict[str, Any]]] = field(default_factory=dict)

    @classmethod
    def load(cls) -> "LibraryMetadata":
        try:
            data = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
            return cls(
                comics=data.get("comics", {}),
                review_queue=data.get("review_queue", {}),
            )
        except Exception:
            return cls()

    def save(self) -> None:
        METADATA_PATH.write_text(
            json.dumps(
                {
                    "comics": self.comics,
                    "review_queue": self.review_queue,
                },
                indent=2,
            ),
            encoding="utf-8",
        )


class ImageScrollArea(QScrollArea):
    def __init__(self, image_label: QLabel) -> None:
        super().__init__()
        self.setWidget(image_label)
        self.setWidgetResizable(False)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setBackgroundRole(image_label.backgroundRole())
        self.setFrameShape(QScrollArea.Shape.NoFrame)
        self.verticalScrollBar().setSingleStep(32)
        self.verticalScrollBar().setPageStep(220)
        self.horizontalScrollBar().setSingleStep(32)
        self.horizontalScrollBar().setPageStep(220)
        self._dragging = False
        self._last_pos = QPoint()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._last_pos = event.position().toPoint()
            self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._dragging:
            pos = event.position().toPoint()
            delta = pos - self._last_pos
            self._last_pos = pos
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = False
            self.viewport().unsetCursor()
        super().mouseReleaseEvent(event)


class GridTextDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing, True)

        widget = option.widget
        is_dark = bool(widget.property("darkMode")) if widget else False
        text = str(index.data(Qt.ItemDataRole.DisplayRole) or "")
        lines = text.split("\n")
        title = lines[0] if lines else ""
        meta = lines[1] if len(lines) > 1 else ""

        icon = index.data(Qt.ItemDataRole.DecorationRole)
        text_top = option.rect.top() + 4
        if isinstance(icon, QIcon):
            icon_size = option.decorationSize
            icon_x = option.rect.x() + (option.rect.width() - icon_size.width()) // 2
            icon_y = option.rect.y() + 4
            icon_rect = QRect(icon_x, icon_y, icon_size.width(), icon_size.height())
            icon.paint(painter, icon_rect, Qt.AlignmentFlag.AlignCenter)
            text_top = icon_rect.bottom() + 14

        bottom_padding = 10
        meta_height = 18
        gap = 8
        meta_rect = QRect(
            option.rect.x() + 16,
            option.rect.bottom() - bottom_padding - meta_height + 1,
            option.rect.width() - 32,
            meta_height,
        )
        title_rect = QRect(
            option.rect.x() + 14,
            text_top,
            option.rect.width() - 28,
            max(24, meta_rect.y() - gap - text_top),
        )

        title_font = QFont(option.font)
        title_font.setPointSize(12)
        title_font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(title_font)
        painter.setPen(QColor("#f8fafc") if is_dark else QColor("#0f172a"))
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop | Qt.TextFlag.TextWordWrap, title)

        meta_font = QFont(option.font)
        meta_font.setPointSize(10)
        meta_font.setWeight(QFont.Weight.Medium)
        meta_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.8)
        painter.setFont(meta_font)
        painter.setPen(QColor("#94a3b8") if is_dark else QColor("#667085"))
        painter.drawText(meta_rect, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom, meta.upper())

        painter.restore()


class GalleryView(QWidget):
    openFolder = Signal(Path)
    sortChanged = Signal(str)
    authorThumbnailMenuRequested = Signal(Path, QPoint)
    tagFilterChanged = Signal(str)

    def __init__(self, empty_text: str, layout_mode: str = "grid") -> None:
        super().__init__()
        self.layout_mode = layout_mode

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 20, 28, 24)
        layout.setSpacing(16)

        self.title_label = QLabel("Library")
        self.title_label.setObjectName("sectionLabel")

        self.label = QLabel(empty_text)
        self.label.setObjectName("helperLabel")
        self.label.setWordWrap(True)

        self.meta_label = QLabel("LIBRARY")
        self.meta_label.setObjectName("sortLabel")

        sort_row = QHBoxLayout()
        sort_row.setContentsMargins(0, 0, 0, 0)
        sort_row.setSpacing(10)
        self.sort_label = QLabel("Sort")
        self.sort_label.setObjectName("sortLabel")
        self.sort_box = QComboBox()
        self.sort_box.addItems(SORT_OPTIONS)
        self.sort_box.currentTextChanged.connect(self.sortChanged.emit)
        self.filter_label = QLabel("Tag filter")
        self.filter_label.setObjectName("sortLabel")
        self.filter_box = QComboBox()
        self.filter_box.addItem(TAG_FILTER_ALL)
        self.filter_box.currentTextChanged.connect(self._emit_tag_filter_changed)
        self.sort_label.hide()
        self.sort_box.hide()
        self.filter_label.hide()
        self.filter_box.hide()
        sort_row.addStretch(1)

        self.list_widget = QListWidget()
        self.list_widget.setObjectName("booksList" if layout_mode == "list" else "libraryGrid")
        self.list_widget.setMovement(QListWidget.Movement.Static)
        self.list_widget.setSpacing(14 if layout_mode == "list" else 20)
        self.list_widget.setUniformItemSizes(False)
        self.list_widget.itemDoubleClicked.connect(self._activate_item)
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._open_context_menu)
        self.list_widget.verticalScrollBar().setSingleStep(28)
        self.list_widget.verticalScrollBar().setPageStep(180)
        self._configure_list_widget()
        if self.layout_mode != "list":
            self.list_widget.setItemDelegate(GridTextDelegate(self.list_widget))

        layout.addWidget(self.meta_label)
        layout.addWidget(self.title_label)
        layout.addWidget(self.label)
        layout.addLayout(sort_row)
        layout.addWidget(self.list_widget, 1)

    def _configure_list_widget(self) -> None:
        if self.layout_mode == "list":
            self.list_widget.setViewMode(QListWidget.ViewMode.ListMode)
            self.list_widget.setResizeMode(QListWidget.ResizeMode.Adjust)
            self.list_widget.setWrapping(False)
            self.list_widget.setWordWrap(False)
            self.list_widget.setIconSize(QSize(96, 136))
            self.list_widget.setTextElideMode(Qt.TextElideMode.ElideRight)
        else:
            self.list_widget.setViewMode(QListWidget.ViewMode.IconMode)
            self.list_widget.setResizeMode(QListWidget.ResizeMode.Adjust)
            self.list_widget.setWordWrap(True)
            self.list_widget.setIconSize(QSize(236, 338))
            self.list_widget.setGridSize(QSize(296, 452))
            self.list_widget.setTextElideMode(Qt.TextElideMode.ElideNone)

    def clear_gallery(self, title_text: str, label_text: str) -> None:
        self.title_label.setText(title_text)
        self.label.setText(label_text)
        self.meta_label.setText("AVAILABLE FILES" if self.layout_mode == "list" else "LIBRARY CATALOG")
        self.list_widget.clear()

    def set_sort_mode(self, mode: str) -> None:
        index = self.sort_box.findText(mode)
        if index >= 0 and index != self.sort_box.currentIndex():
            self.sort_box.setCurrentIndex(index)

    def set_filter_visible(self, visible: bool) -> None:
        self.filter_label.setVisible(visible)
        self.filter_box.setVisible(visible)

    def set_filter_options(self, options: list[str], current: str = "") -> None:
        selected = current or TAG_FILTER_ALL
        self.filter_box.blockSignals(True)
        self.filter_box.clear()
        self.filter_box.addItem(TAG_FILTER_ALL)
        for option in options:
            if option and option != TAG_FILTER_ALL:
                self.filter_box.addItem(option)
        index = self.filter_box.findText(selected)
        self.filter_box.setCurrentIndex(index if index >= 0 else 0)
        self.filter_box.blockSignals(False)

    def _emit_tag_filter_changed(self, text: str) -> None:
        self.tagFilterChanged.emit("" if text == TAG_FILTER_ALL else text)

    def populate(
        self,
        title: str,
        subtitle: str,
        folders: List[Path],
        progress: dict[str, int],
        show_page_count: bool,
        thumbnail_overrides: dict[str, str] | None = None,
        metadata_records: dict[str, dict[str, Any]] | None = None,
        favorites: set[str] | None = None,
    ) -> None:
        self.clear_gallery(title, subtitle)

        if self.layout_mode == "list":
            icon_size = QSize(96, 136)
            self.list_widget.setIconSize(icon_size)
        else:
            icon_size = QSize(236, 338)
            grid_size = QSize(296, 452)
            item_height = 438
            self.list_widget.setIconSize(icon_size)
            self.list_widget.setGridSize(grid_size)

        for idx, folder in enumerate(folders, start=1):
            favorite_mark = "Saved · " if favorites and str(folder) in favorites else ""
            item = QListWidgetItem(f"{favorite_mark}{folder.name}")
            item.setData(Qt.ItemDataRole.UserRole, str(folder))

            if show_page_count:
                page_count = count_pages_in_book(folder)
                if not page_count:
                    continue
                progress_text = "Unread"
                if str(folder) in progress:
                    progress_text = f"Page {progress[str(folder)] + 1}/{page_count}"
                if self.layout_mode == "list":
                    item.setText(f"#{idx:02d}  {folder.name}\n{page_count} PAGES · {progress_text.upper()}")
                    item.setToolTip(f"{folder.name}\n{page_count} pages\n{progress_text}")
                else:
                    item.setText(f"{folder.name}\n{page_count} pages")
                    item.setToolTip(f"{folder.name}\n{page_count} pages\n{progress_text}")
            else:
                comic_count = count_books_in_series(folder)
                item.setText(f"{folder.name}\n{comic_count} issues")
                item.setToolTip(f"{folder.name}\n{comic_count} issues")

            metadata = (metadata_records or {}).get(str(folder))
            if metadata:
                tooltip_lines = [item.toolTip()]
                if metadata.get("title"):
                    tooltip_lines.append(f"Match: {metadata['title']}")
                if metadata.get("language"):
                    tooltip_lines.append(f"Language: {metadata['language']}")
                if metadata.get("parodies"):
                    tooltip_lines.append(f"Parodies: {', '.join(metadata['parodies'][:4])}")
                if metadata.get("tags"):
                    tooltip_lines.append(f"Tags: {', '.join(metadata['tags'][:10])}")
                item.setToolTip("\n".join(line for line in tooltip_lines if line))

            cover = None
            if show_page_count:
                cover = build_cover_pixmap_for_book(folder, icon_size)
            else:
                books = list_books_in_series(folder)
                if books:
                    cover = build_cover_pixmap_for_book(books[0], icon_size)
            if cover is not None:
                item.setIcon(QIcon(cover))

            if self.layout_mode == "list":
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                item.setSizeHint(QSize(0, 144))
            else:
                item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
                item.setSizeHint(QSize(grid_size.width() - 14, item_height))

            self.list_widget.addItem(item)

    def _activate_item(self, item: QListWidgetItem) -> None:
        folder = item.data(Qt.ItemDataRole.UserRole)
        if folder:
            self.openFolder.emit(Path(folder))

    def _open_context_menu(self, pos: QPoint) -> None:
        item = self.list_widget.itemAt(pos)
        if not item:
            return
        folder = item.data(Qt.ItemDataRole.UserRole)
        if not folder:
            return
        self.authorThumbnailMenuRequested.emit(Path(folder), self.list_widget.viewport().mapToGlobal(pos))


class ComicReader(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.state = ReaderState.load()
        self.metadata = LibraryMetadata.load()
        self.current_root: Path | None = None
        self.current_author: Path | None = None
        self.current_folder: Path | None = None
        self.pages: List[PageEntry] = []
        self.current_index = 0
        self.base_pixmap: QPixmap | None = None
        self.fit_mode = self.state.fit_mode
        self.zoom_percent = self.state.zoom_percent

        self.setWindowTitle(APP_NAME)
        self.resize(1400, 950)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.image_label.setStyleSheet("background: #0f172a; border-radius: 18px;")
        self.scroll_area = ImageScrollArea(self.image_label)

        self.author_gallery = GalleryView("Choose a library to begin.", layout_mode="grid")

        self.author_gallery_page = QWidget()
        author_gallery_layout = QVBoxLayout(self.author_gallery_page)
        author_gallery_layout.setContentsMargins(0, 0, 0, 0)
        author_gallery_layout.setSpacing(0)
        author_gallery_top_row = QHBoxLayout()
        author_gallery_top_row.setContentsMargins(28, 22, 28, 0)
        author_gallery_top_row.setSpacing(12)
        self.author_header = QWidget()
        self.author_header.setObjectName("appHeader")
        author_header_layout = QHBoxLayout(self.author_header)
        author_header_layout.setContentsMargins(18, 14, 18, 14)
        author_header_layout.setSpacing(14)
        self.author_brand_mark = QLabel("GR")
        self.author_brand_mark.setObjectName("appBrandMark")
        author_brand_stack = QVBoxLayout()
        author_brand_stack.setContentsMargins(0, 0, 0, 0)
        author_brand_stack.setSpacing(2)
        self.author_brand_title = QLabel(APP_BRAND)
        self.author_brand_title.setObjectName("appBrandTitle")
        self.author_brand_meta = QLabel(APP_VERSION_LABEL)
        self.author_brand_meta.setObjectName("appBrandMeta")
        author_brand_stack.addWidget(self.author_brand_title)
        author_brand_stack.addWidget(self.author_brand_meta)
        self.author_theme_button = QPushButton("Light mode")
        self.author_theme_button.setObjectName("headerButton")
        self.author_theme_button.setMinimumHeight(40)
        self.author_theme_button.clicked.connect(self.toggle_dark_mode)
        self.author_open_library_button = QPushButton("Local Disk")
        self.author_open_library_button.setObjectName("headerButton")
        self.author_open_library_button.setMinimumHeight(40)
        self.author_open_library_button.clicked.connect(self.choose_root)
        author_header_layout.addWidget(self.author_brand_mark, 0)
        author_header_layout.addLayout(author_brand_stack, 0)
        author_header_layout.addStretch(1)
        author_header_layout.addWidget(self.author_theme_button, 0)
        author_header_layout.addWidget(self.author_open_library_button, 0)
        author_gallery_top_row.addWidget(self.author_header, 1)
        author_gallery_layout.addLayout(author_gallery_top_row)
        author_gallery_layout.addSpacing(22)
        self.continue_card = QWidget()
        self.continue_card.setObjectName("continueReadingCard")
        continue_layout = QHBoxLayout(self.continue_card)
        continue_layout.setContentsMargins(16, 14, 16, 14)
        continue_layout.setSpacing(14)
        self.continue_cover = QLabel()
        self.continue_cover.setFixedSize(48, 72)
        self.continue_cover.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.continue_cover.setStyleSheet("background: transparent; border: none; border-radius: 10px;")
        continue_text = QVBoxLayout()
        continue_text.setContentsMargins(0, 0, 0, 0)
        continue_text.setSpacing(2)
        self.continue_eyebrow = QLabel("CONTINUE READING")
        self.continue_eyebrow.setObjectName("continueEyebrow")
        self.continue_title = QLabel("")
        self.continue_title.setObjectName("continueTitle")
        self.continue_meta = QLabel("")
        self.continue_meta.setObjectName("continueMeta")
        continue_text.addWidget(self.continue_eyebrow)
        continue_text.addWidget(self.continue_title)
        continue_text.addWidget(self.continue_meta)
        continue_actions = QHBoxLayout()
        continue_actions.setContentsMargins(0, 0, 0, 0)
        continue_actions.setSpacing(8)
        self.clear_continue_button = QPushButton("Clear Progress")
        self.clear_continue_button.clicked.connect(self.clear_continue_reading)
        self.resume_continue_button = QPushButton("Resume")
        self.resume_continue_button.clicked.connect(self.resume_last_read_comic)
        continue_actions.addWidget(self.clear_continue_button, 0)
        continue_actions.addWidget(self.resume_continue_button, 0)
        continue_shell = QVBoxLayout()
        continue_shell.setContentsMargins(0, 0, 0, 0)
        continue_shell.setSpacing(8)
        continue_shell.addLayout(continue_text)
        continue_shell.addLayout(continue_actions)
        continue_layout.addWidget(self.continue_cover, 0)
        continue_layout.addLayout(continue_shell, 1)
        self.continue_card.hide()
        author_gallery_layout.addWidget(self.continue_card, 0)
        author_gallery_layout.addWidget(self.author_gallery, 1)
        self.author_gallery.openFolder.connect(self.open_author)
        self.author_gallery.sortChanged.connect(self.on_author_sort_changed)
        self.author_gallery.authorThumbnailMenuRequested.connect(self.show_author_thumbnail_menu)
        self.author_gallery.set_sort_mode(self.state.author_sort)

        self.comic_gallery = GalleryView("Choose a series to see its books.", layout_mode="grid")
        self.comic_gallery.openFolder.connect(self.open_comic)
        self.comic_gallery.sortChanged.connect(self.on_comic_sort_changed)
        self.comic_gallery.tagFilterChanged.connect(self.on_tag_filter_changed)
        self.comic_gallery.set_sort_mode(self.state.comic_sort)
        self.comic_gallery.set_filter_visible(False)

        self.comic_gallery_page = QWidget()
        comic_gallery_layout = QVBoxLayout(self.comic_gallery_page)
        comic_gallery_layout.setContentsMargins(0, 0, 0, 0)
        comic_gallery_layout.setSpacing(0)
        comic_gallery_top_row = QHBoxLayout()
        comic_gallery_top_row.setContentsMargins(28, 22, 28, 0)
        comic_gallery_top_row.setSpacing(12)
        self.comic_header = QWidget()
        self.comic_header.setObjectName("appHeader")
        comic_header_layout = QHBoxLayout(self.comic_header)
        comic_header_layout.setContentsMargins(18, 14, 18, 14)
        comic_header_layout.setSpacing(12)
        self.series_back_button = QPushButton("← Back to series")
        self.series_back_button.setObjectName("headerButton")
        self.series_back_button.clicked.connect(self.show_author_gallery)
        comic_title_stack = QVBoxLayout()
        comic_title_stack.setContentsMargins(0, 0, 0, 0)
        comic_title_stack.setSpacing(2)
        self.comic_brand_title = QLabel("Series")
        self.comic_brand_title.setObjectName("appBrandTitle")
        self.comic_brand_meta = QLabel("AVAILABLE FILES")
        self.comic_brand_meta.setObjectName("appBrandMeta")
        comic_title_stack.addWidget(self.comic_brand_title)
        comic_title_stack.addWidget(self.comic_brand_meta)
        self.comic_theme_button = QPushButton("Light mode")
        self.comic_theme_button.setObjectName("headerButton")
        self.comic_theme_button.setMinimumHeight(40)
        self.comic_theme_button.clicked.connect(self.toggle_dark_mode)
        self.change_root_button = QPushButton("Local Disk")
        self.change_root_button.setObjectName("headerButton")
        self.change_root_button.setMinimumHeight(40)
        self.change_root_button.clicked.connect(self.choose_root)
        comic_header_layout.addWidget(self.series_back_button, 0)
        comic_header_layout.addLayout(comic_title_stack, 0)
        comic_header_layout.addStretch(1)
        comic_header_layout.addWidget(self.comic_theme_button, 0)
        comic_header_layout.addWidget(self.change_root_button, 0)
        comic_gallery_top_row.addWidget(self.comic_header, 1)
        comic_gallery_layout.addLayout(comic_gallery_top_row)
        comic_gallery_layout.addSpacing(22)
        self.series_summary_card = QWidget()
        self.series_summary_card.setObjectName("seriesSummaryCard")
        self.series_summary_card.hide()
        summary_layout = QHBoxLayout(self.series_summary_card)
        summary_layout.setContentsMargins(18, 18, 18, 18)
        summary_layout.setSpacing(16)
        self.series_summary_cover = QLabel()
        self.series_summary_cover.setFixedSize(76, 108)
        self.series_summary_cover.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.series_summary_cover.setStyleSheet("background: #e5e7eb; border: 1px solid #d8dee8; border-radius: 14px;")
        summary_text = QVBoxLayout()
        summary_text.setContentsMargins(0, 0, 0, 0)
        summary_text.setSpacing(4)
        self.series_summary_eyebrow = QLabel("ACTIVE FOLDER")
        self.series_summary_eyebrow.setObjectName("seriesSummaryEyebrow")
        self.series_summary_title = QLabel("Series")
        self.series_summary_title.setObjectName("seriesSummaryTitle")
        self.series_summary_meta = QLabel("")
        self.series_summary_meta.setObjectName("seriesSummaryMeta")
        self.series_summary_meta.setWordWrap(True)
        summary_text.addWidget(self.series_summary_eyebrow)
        summary_text.addWidget(self.series_summary_title)
        summary_text.addWidget(self.series_summary_meta)
        summary_layout.addWidget(self.series_summary_cover, 0)
        summary_layout.addLayout(summary_text, 1)
        comic_gallery_layout.addWidget(self.series_summary_card, 0)
        comic_gallery_layout.addSpacing(8)
        comic_gallery_layout.addWidget(self.comic_gallery, 1)

        self.reader_page = QWidget()
        self.reader_page.setObjectName("readerPage")
        reader_layout = QVBoxLayout(self.reader_page)
        reader_layout.setContentsMargins(24, 18, 24, 24)
        reader_layout.setSpacing(14)
        self.reader_top_bar = QWidget()
        self.reader_top_bar.setObjectName("readerTopBar")
        reader_top_row = QHBoxLayout(self.reader_top_bar)
        reader_top_row.setContentsMargins(18, 14, 18, 14)
        reader_top_row.setSpacing(12)
        self.back_button = QPushButton("← Back to books")
        self.back_button.setObjectName("readerBackButton")
        self.back_button.setMinimumHeight(40)
        self.back_button.clicked.connect(self.show_comic_gallery)
        self.reader_eyebrow_label = QLabel("READING")
        self.reader_eyebrow_label.setObjectName("readerEyebrow")
        self.reader_title_label = QLabel("Reader")
        self.reader_title_label.setObjectName("readerTitle")
        self.reader_meta_label = QLabel("")
        self.reader_meta_label.setObjectName("readerMeta")
        self.reader_mode_chip = QLabel("FIT PAGE")
        self.reader_mode_chip.setObjectName("readerChip")
        self.reader_mode_chip.setMinimumHeight(40)
        reader_title_stack = QVBoxLayout()
        reader_title_stack.setContentsMargins(0, 0, 0, 0)
        reader_title_stack.setSpacing(1)
        reader_title_stack.addWidget(self.reader_eyebrow_label)
        reader_title_stack.addWidget(self.reader_title_label)
        reader_title_stack.addWidget(self.reader_meta_label)
        reader_top_row.addWidget(self.back_button, 0)
        reader_top_row.addLayout(reader_title_stack, 1)
        reader_top_row.addWidget(self.reader_mode_chip, 0)
        reader_layout.addWidget(self.reader_top_bar, 0)
        reader_layout.addWidget(self.scroll_area, 1)
        self.reader_bottom_bar = QWidget()
        self.reader_bottom_bar.setObjectName("readerBottomBar")
        reader_bottom_row = QHBoxLayout(self.reader_bottom_bar)
        reader_bottom_row.setContentsMargins(18, 12, 18, 12)
        reader_bottom_row.setSpacing(12)
        self.reader_prev_button = QPushButton("Previous")
        self.reader_prev_button.setObjectName("readerBackButton")
        self.reader_prev_button.setMinimumHeight(40)
        self.reader_prev_button.clicked.connect(self.prev_page)
        self.reader_next_button = QPushButton("Next")
        self.reader_next_button.setObjectName("readerBackButton")
        self.reader_next_button.setMinimumHeight(40)
        self.reader_next_button.clicked.connect(self.next_page)
        self.reader_progress_label = QLabel("0 / 0")
        self.reader_progress_label.setObjectName("readerChip")
        self.reader_progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.reader_progress_label.setMinimumHeight(40)
        reader_bottom_row.addWidget(self.reader_prev_button, 0)
        reader_bottom_row.addWidget(self.reader_progress_label, 1)
        reader_bottom_row.addWidget(self.reader_next_button, 0)
        reader_layout.addWidget(self.reader_bottom_bar, 0)

        self.comic_intro_page = QWidget()
        self.comic_intro_page.setObjectName("comicIntroPage")
        intro_outer = QVBoxLayout(self.comic_intro_page)
        intro_outer.setContentsMargins(0, 0, 0, 0)
        intro_outer.setSpacing(0)

        intro_top = QHBoxLayout()
        intro_top.setContentsMargins(24, 18, 24, 8)
        intro_top.setSpacing(10)
        self.intro_back_button = QPushButton("← Back to books")
        self.intro_back_button.setObjectName("headerButton")
        self.intro_back_button.clicked.connect(self.show_comic_gallery)
        self.intro_read_button = QPushButton("Open book")
        self.intro_read_button.setObjectName("heroReadButton")
        self.intro_read_button.clicked.connect(self.start_reading_current_comic)
        intro_top.addWidget(self.intro_back_button, 0)
        intro_top.addStretch(1)
        intro_outer.addLayout(intro_top)

        self.intro_scroll = QScrollArea()
        self.intro_scroll.setWidgetResizable(True)
        self.intro_scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        intro_content = QWidget()
        intro_content.setObjectName("introContent")
        self.intro_scroll.setWidget(intro_content)
        intro_outer.addWidget(self.intro_scroll, 1)

        intro_layout = QVBoxLayout(intro_content)
        intro_layout.setContentsMargins(24, 16, 24, 24)
        intro_layout.setSpacing(18)

        hero_row = QHBoxLayout()
        hero_row.setSpacing(24)

        cover_panel = QWidget()
        cover_panel.setObjectName("introHeroPanel")
        cover_panel_layout = QVBoxLayout(cover_panel)
        cover_panel_layout.setContentsMargins(18, 18, 18, 18)
        cover_panel_layout.setSpacing(12)
        self.intro_cover_label = QLabel()
        self.intro_cover_label.setFixedSize(300, 420)
        self.intro_cover_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.intro_cover_label.setStyleSheet("background: #e2e8f0; border: 1px solid #d8dee8; border-radius: 20px;")
        cover_panel_layout.addWidget(self.intro_cover_label, 0, Qt.AlignmentFlag.AlignHCenter)
        self.intro_cover_hint = QLabel("Open the book when you're ready to read.")
        self.intro_cover_hint.setObjectName("helperLabel")
        self.intro_cover_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cover_panel_layout.addWidget(self.intro_cover_hint)
        hero_row.addWidget(cover_panel, 0, Qt.AlignmentFlag.AlignTop)

        hero_panel = QWidget()
        hero_panel.setObjectName("introHeroPanel")
        hero_panel_layout = QVBoxLayout(hero_panel)
        hero_panel_layout.setContentsMargins(22, 22, 22, 22)
        hero_panel_layout.setSpacing(10)
        self.intro_title_label = QLabel("Book details")
        self.intro_title_label.setObjectName("introTitle")
        self.intro_title_label.setWordWrap(True)
        self.intro_meta_label = QLabel("")
        self.intro_meta_label.setObjectName("introMeta")
        self.intro_meta_label.setWordWrap(True)
        badges_row = QHBoxLayout()
        badges_row.setSpacing(10)
        self.intro_code_badge = QLabel("Book")
        self.intro_code_badge.setObjectName("introBadge")
        self.intro_status_badge = QLabel("Ready")
        self.intro_status_badge.setObjectName("introBadge")
        self.intro_favorite_badge = QLabel("Not saved")
        self.intro_favorite_badge.setObjectName("introBadge")
        badges_row.addWidget(self.intro_code_badge, 0)
        badges_row.addWidget(self.intro_status_badge, 0)
        badges_row.addWidget(self.intro_favorite_badge, 0)
        badges_row.addStretch(1)
        action_row = QHBoxLayout()
        action_row.setSpacing(10)
        self.intro_resume_button = QPushButton("Resume")
        self.intro_resume_button.clicked.connect(self.resume_current_comic)
        self.intro_folder_button = QPushButton("Copy path")
        self.intro_folder_button.clicked.connect(self.copy_current_folder_path)
        action_row.addWidget(self.intro_read_button, 0)
        action_row.addWidget(self.intro_resume_button, 0)
        action_row.addWidget(self.intro_folder_button, 0)
        action_row.addStretch(1)
        self.intro_summary_label = QLabel("")
        self.intro_summary_label.setObjectName("introBody")
        self.intro_summary_label.setWordWrap(True)
        self.intro_details_title = QLabel("Details")
        self.intro_details_title.setObjectName("introSection")
        details_grid = QGridLayout()
        details_grid.setHorizontalSpacing(12)
        details_grid.setVerticalSpacing(12)
        self.intro_artist_chip = QLabel("")
        self.intro_artist_chip.setObjectName("introChip")
        self.intro_group_chip = QLabel("")
        self.intro_group_chip.setObjectName("introChip")
        self.intro_parody_chip = QLabel("")
        self.intro_parody_chip.setObjectName("introChip")
        self.intro_character_chip = QLabel("")
        self.intro_character_chip.setObjectName("introChip")
        for label in [self.intro_artist_chip, self.intro_group_chip, self.intro_parody_chip, self.intro_character_chip]:
            label.setWordWrap(True)
            label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        details_grid.addWidget(self.intro_artist_chip, 0, 0)
        details_grid.addWidget(self.intro_group_chip, 0, 1)
        details_grid.addWidget(self.intro_parody_chip, 1, 0)
        details_grid.addWidget(self.intro_character_chip, 1, 1)
        hero_panel_layout.addWidget(self.intro_title_label)
        hero_panel_layout.addWidget(self.intro_meta_label)
        hero_panel_layout.addLayout(badges_row)
        hero_panel_layout.addLayout(action_row)
        hero_panel_layout.addWidget(self.intro_summary_label)
        hero_panel_layout.addWidget(self.intro_details_title)
        hero_panel_layout.addLayout(details_grid)
        hero_row.addWidget(hero_panel, 1)
        intro_layout.addLayout(hero_row)

        related_panel = QWidget()
        related_panel.setObjectName("introRelatedPanel")
        related_layout = QVBoxLayout(related_panel)
        related_layout.setContentsMargins(20, 18, 20, 18)
        related_layout.setSpacing(10)
        self.intro_related_title = QLabel("More books")
        self.intro_related_title.setObjectName("introSection")
        self.intro_related_hint = QLabel("Open another book from here when you want to keep browsing.")
        self.intro_related_hint.setObjectName("helperLabel")
        self.intro_related_list = QListWidget()
        self.intro_related_list.setObjectName("relatedList")
        self.intro_related_list.setIconSize(QSize(84, 118))
        self.intro_related_list.itemDoubleClicked.connect(self._open_related_comic)
        related_layout.addWidget(self.intro_related_title)
        related_layout.addWidget(self.intro_related_hint)
        related_layout.addWidget(self.intro_related_list)
        intro_layout.addWidget(related_panel)

        self.stack = QStackedWidget()
        self.stack.addWidget(self.author_gallery_page)
        self.stack.addWidget(self.comic_gallery_page)
        self.stack.addWidget(self.comic_intro_page)
        self.stack.addWidget(self.reader_page)
        self.setCentralWidget(self.stack)

        self.setStatusBar(QStatusBar())
        self._theme_buttons = [self.author_theme_button, self.comic_theme_button]
        self.apply_theme()
        self._build_toolbar()
        self._build_actions()

        if self.state.last_root:
            root = Path(self.state.last_root)
            if root.exists():
                self.open_root(root)
                if self.state.last_author:
                    series = Path(self.state.last_author)
                    if series.exists():
                        self.open_author(series)
                if self.state.last_folder:
                    folder = Path(self.state.last_folder)
                    if folder.exists():
                        self.open_comic(folder)

        if self.state.fullscreen:
            self.showFullScreen()

    def _build_toolbar(self) -> None:
        self.toolbar = None

    def _build_actions(self) -> None:
        actions = [
            ("Open Gallery Root", self.choose_root, "Ctrl+O"),
            ("Random Book", self.open_random_comic, "Ctrl+R"),
            ("Toggle Favorite", self.toggle_current_favorite, "Ctrl+D"),
            ("Toggle Page Bookmark", self.toggle_current_page_bookmark, "Ctrl+B"),
            ("Back", self.go_back, "Escape"),
            ("Previous Page", self.prev_page, "Left"),
            ("Next Page", self.next_page, "Right"),
            ("Fit Width", lambda: self.set_fit_mode("fit_width"), "1"),
            ("Fit Page", lambda: self.set_fit_mode("fit_page"), "2"),
            ("Free Zoom", lambda: self.set_fit_mode("free"), "3"),
            ("Zoom In", self.zoom_in, "Ctrl+="),
            ("Zoom Out", self.zoom_out, "Ctrl+-"),
            ("Reset Zoom", self.reset_zoom, "Ctrl+0"),
            ("Toggle Fullscreen", self.toggle_fullscreen, "F11"),
        ]
        for text, handler, shortcut in actions:
            action = QAction(text, self)
            action.triggered.connect(handler)
            if shortcut:
                action.setShortcut(QKeySequence(shortcut))
            self.addAction(action)

    def apply_theme(self) -> None:
        is_dark = self.state.dark_mode
        self.setStyleSheet(APP_STYLE_DARK if is_dark else APP_STYLE)
        self.image_label.setStyleSheet(
            "background: #04060a; border-radius: 18px;"
            if is_dark
            else "background: #0f172a; border-radius: 18px;"
        )
        self.intro_cover_label.setStyleSheet(
            "background: #11141c; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 20px;"
            if is_dark
            else "background: #e2e8f0; border: 1px solid #d8dee8; border-radius: 20px;"
        )
        self.continue_cover.setStyleSheet(
            "background: transparent; border: none; border-radius: 10px;"
        )
        self.author_gallery.list_widget.setProperty("darkMode", is_dark)
        self.comic_gallery.list_widget.setProperty("darkMode", is_dark)
        self.author_gallery.list_widget.viewport().update()
        self.comic_gallery.list_widget.viewport().update()
        for button in self.findChildren(QPushButton):
            button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._apply_reader_capsule_styles(is_dark)
        label = "Light mode" if is_dark else "Dark mode"
        for button in getattr(self, "_theme_buttons", []):
            button.setText(label)

    def _apply_reader_capsule_styles(self, is_dark: bool) -> None:
        button_style = (
            "QPushButton {"
            "background: rgba(255, 255, 255, 0.045);"
            "color: #eef2f7;"
            "border: 1px solid rgba(255, 255, 255, 0.08);"
            "border-radius: 22px;"
            "min-height: 44px;"
            "padding: 0 20px;"
            "font-weight: 600;"
            "}"
            "QPushButton:hover {"
            "background: rgba(255, 255, 255, 0.13);"
            "border: 1px solid rgba(255, 255, 255, 0.2);"
            "}"
            "QPushButton:disabled {"
            "background: rgba(255, 255, 255, 0.025);"
            "color: rgba(238, 242, 247, 0.38);"
            "border: 1px solid rgba(255, 255, 255, 0.05);"
            "}"
        ) if is_dark else (
            "QPushButton {"
            "background: rgba(255, 255, 255, 0.98);"
            "color: #0f172a;"
            "border: 1px solid #d8dee8;"
            "border-radius: 22px;"
            "min-height: 44px;"
            "padding: 0 20px;"
            "font-weight: 600;"
            "}"
            "QPushButton:hover {"
            "background: #eef4ff;"
            "border: 1px solid #93a4bb;"
            "}"
            "QPushButton:disabled {"
            "background: rgba(255, 255, 255, 0.72);"
            "color: rgba(15, 23, 42, 0.4);"
            "border: 1px solid #e2e8f0;"
            "}"
        )
        chip_style = (
            "QLabel {"
            "background: rgba(255, 255, 255, 0.04);"
            "color: #eef2f7;"
            "border: 1px solid rgba(255, 255, 255, 0.08);"
            "border-radius: 22px;"
            "min-height: 44px;"
            "padding: 0 18px;"
            "font-size: 11px;"
            "font-weight: 600;"
            "}"
        ) if is_dark else (
            "QLabel {"
            "background: rgba(255, 255, 255, 0.98);"
            "color: #0f172a;"
            "border: 1px solid #d8dee8;"
            "border-radius: 22px;"
            "min-height: 44px;"
            "padding: 0 18px;"
            "font-size: 11px;"
            "font-weight: 600;"
            "}"
        )
        for button in [
            self.back_button,
            self.reader_prev_button,
            self.reader_next_button,
            self.clear_continue_button,
            self.resume_continue_button,
            self.intro_resume_button,
            self.intro_read_button,
            self.intro_folder_button,
        ]:
            button.setFixedHeight(44)
            button.setStyleSheet(button_style)
        for chip in [self.reader_mode_chip, self.reader_progress_label]:
            chip.setFixedHeight(44)
            chip.setAlignment(Qt.AlignmentFlag.AlignCenter)
            chip.setStyleSheet(chip_style)

    def toggle_dark_mode(self) -> None:
        self.state.dark_mode = not self.state.dark_mode
        self.apply_theme()
        self.statusBar().showMessage("Dark mode on" if self.state.dark_mode else "Dark mode off")
        self._save_state()

    def choose_root(self) -> None:
        start = str(self.current_root or Path.home())
        folder = QFileDialog.getExistingDirectory(self, "Choose gallery root folder", start)
        if folder:
            self.open_root(Path(folder))
            self.show_author_gallery()

    def open_root(self, root: Path) -> None:
        self.current_root = root
        self.current_author = None
        self.current_folder = None
        self.pages = []
        self.state.comic_tag_filter = ""
        self.refresh_author_gallery()
        self.state.last_root = str(root)
        self.state.last_author = ""
        self._save_state()
        self.statusBar().showMessage(f"Loaded gallery: {root}")

    def _last_read_folder(self) -> Path | None:
        if not self.state.last_folder:
            return None
        folder = Path(self.state.last_folder)
        if not folder.exists():
            return None
        if self.current_root and self.current_root not in folder.parents and folder != self.current_root:
            return None
        return folder

    def refresh_continue_card(self) -> None:
        folder = self._last_read_folder()
        if not folder:
            self.continue_card.hide()
            return
        series_folder = folder.parent if folder.parent != folder else folder
        self.continue_title.setText(folder.name)
        self.continue_meta.setText(f"In {series_folder.name}")
        progress_index = self.state.progress.get(str(folder), 0)
        self.resume_continue_button.setText("Resume" if progress_index <= 0 else f"Resume from page {progress_index + 1}")
        cover = build_cover_pixmap_for_book(folder, self.continue_cover.size(), radius=12.0)
        if cover is not None:
            self.continue_cover.setPixmap(cover)
            self.continue_cover.setText("")
        else:
            self.continue_cover.setPixmap(QPixmap())
            self.continue_cover.setText("No\ncover")
        self.continue_card.show()

    def refresh_author_gallery(self) -> None:
        if not self.current_root:
            return
        series_folders = all_series_folders(self.current_root)
        subtitle = (
            f"{len(series_folders)} series in {self.current_root.name}"
            if series_folders
            else "No series found here yet. Pick another library folder to begin."
        )
        self.author_brand_meta.setText(self.current_root.name.upper())
        self.refresh_continue_card()
        self.author_gallery.populate(
            "Graphic series",
            subtitle,
            series_folders,
            self.state.progress,
            show_page_count=False,
        )
        self.author_gallery.label.setText(subtitle)

    def refresh_comic_gallery(self) -> None:
        if not self.current_author:
            return
        comics = list_books_in_series(self.current_author)
        favorite_set = self.favorite_comics_set()
        comics.sort(key=lambda folder: (str(folder) not in favorite_set, natural_key(folder.name)))
        comics = sort_folders(comics, self.state.comic_sort, self.state.progress, author_mode=False)
        subtitle = (
            f"{len(comics)} books in {self.current_author.name}"
            if comics
            else "No books in this series yet."
        )
        self.comic_brand_title.setText(self.current_author.name)
        self.comic_brand_meta.setText(subtitle)
        self.series_summary_card.hide()
        self.comic_gallery.populate(
            self.current_author.name,
            subtitle,
            comics,
            self.state.progress,
            show_page_count=True,
            favorites=self.favorite_comics_set(),
        )
        self.comic_gallery.label.setText(subtitle)

    def refresh_tag_filter_options(self) -> None:
        self.comic_gallery.set_filter_options([], "")

    def pending_review_count(self, scope: Path | None = None) -> int:
        if scope is None:
            return len(self.metadata.review_queue)
        scope_prefix = str(scope)
        return sum(1 for folder in self.metadata.review_queue if folder.startswith(scope_prefix))

    def metadata_for_current_comic(self) -> dict[str, Any]:
        return {}

    def favorite_comics_set(self) -> set[str]:
        return set(self.state.favorite_comics)

    def current_bookmarks(self) -> list[int]:
        if not self.current_folder:
            return []
        return sorted(set(self.state.page_bookmarks.get(str(self.current_folder), [])))

    def is_current_favorite(self) -> bool:
        return bool(self.current_folder and str(self.current_folder) in self.favorite_comics_set())

    def toggle_current_favorite(self) -> None:
        if not self.current_folder:
            return
        favorites = self.favorite_comics_set()
        key = str(self.current_folder)
        if key in favorites:
            favorites.remove(key)
            self.statusBar().showMessage(f"Removed {self.current_folder.name} from favorites")
        else:
            favorites.add(key)
            self.statusBar().showMessage(f"Favorited {self.current_folder.name}")
        self.state.favorite_comics = sorted(favorites)
        self.populate_comic_intro()
        self._save_state()

    def toggle_current_page_bookmark(self) -> None:
        if not self.current_folder or not self.pages:
            return
        key = str(self.current_folder)
        bookmarks = set(self.state.page_bookmarks.get(key, []))
        if self.current_index in bookmarks:
            bookmarks.remove(self.current_index)
            self.statusBar().showMessage(f"Removed bookmark from page {self.current_index + 1}")
        else:
            bookmarks.add(self.current_index)
            self.statusBar().showMessage(f"Bookmarked page {self.current_index + 1}")
        self.state.page_bookmarks[key] = sorted(bookmarks)
        self._refresh_reader_header(self.pages[self.current_index].name if self.pages else "")
        self._save_state()

    def clear_continue_reading(self) -> None:
        self.state.last_folder = ""
        self.state.last_author = ""
        self.refresh_continue_card()
        self._save_state()
        self.statusBar().showMessage("Cleared continue reading")

    def resume_last_read_comic(self) -> None:
        folder = self._last_read_folder()
        if not folder:
            return
        author = folder.parent if folder.parent != folder else folder
        if author.exists():
            self.current_author = author
            self.state.last_author = str(author)
            self.refresh_comic_gallery()
        self.current_folder = folder
        self.state.last_folder = str(folder)
        if not self._ensure_current_pages_loaded():
            return
        self.start_reading_current_comic()

    def open_random_comic(self) -> None:
        if not self.current_root:
            QMessageBox.information(self, APP_NAME, "Choose a library first.")
            return
        comics = list_books_in_series(self.current_author) if self.current_author else all_comic_folders(self.current_root)
        if not comics:
            QMessageBox.information(self, APP_NAME, "No books found in this library yet.")
            return
        import random
        choice = random.choice(comics)
        self.open_comic(choice)

    def apply_tag_filter_from_intro(self, link: str) -> None:
        return

    def _format_tag_pills(self, tags: list[str]) -> str:
        return ""

    def _chip_text(self, label: str, values: list[str]) -> str:
        clean = [str(v) for v in values if v]
        return f"<b>{label}</b><br>{', '.join(clean) if clean else '—'}"

    def populate_related_comics(self) -> None:
        self.intro_related_list.clear()
        if not self.current_root or not self.current_folder:
            return

        current_path = str(self.current_folder)
        candidate_scope = list_books_in_series(self.current_author) if self.current_author else all_comic_folders(self.current_root)
        favorites = [Path(path) for path in self.state.favorite_comics if path != current_path and Path(path).exists()]
        recents = [
            Path(path)
            for path, _ in sorted(self.state.progress.items(), key=lambda item: item[1], reverse=True)
            if path != current_path and Path(path).exists()
        ]

        candidates: list[Path] = []
        seen: set[str] = set()
        for folder in favorites + recents + candidate_scope:
            key = str(folder)
            if key == current_path or key in seen or not count_pages_in_book(folder):
                continue
            seen.add(key)
            candidates.append(folder)
            if len(candidates) >= 12:
                break

        for folder in candidates:
            page_count = count_pages(folder)
            progress_text = self.state.progress.get(str(folder))
            subtitle = f"{page_count} pages"
            if progress_text is not None:
                subtitle += f" • last opened page {progress_text + 1}"
            item = QListWidgetItem(f"{folder.name}\n{subtitle}")
            item.setData(Qt.ItemDataRole.UserRole, str(folder))
            item.setToolTip(f"{folder}\n{subtitle}")
            pix = build_cover_pixmap_for_book(folder, QSize(84, 118))
            if pix is not None:
                item.setIcon(QIcon(pix))
            item.setSizeHint(QSize(0, 138))
            self.intro_related_list.addItem(item)

        if self.intro_related_list.count() == 0:
            empty = QListWidgetItem("Saved books and recently opened ones will show up here.")
            empty.setFlags(Qt.ItemFlag.NoItemFlags)
            empty.setSizeHint(QSize(0, 58))
            self.intro_related_list.addItem(empty)

    def _open_related_comic(self, item: QListWidgetItem) -> None:
        folder = item.data(Qt.ItemDataRole.UserRole)
        if folder:
            self.open_comic(Path(folder))

    def copy_current_folder_path(self) -> None:
        if not self.current_folder:
            return
        QApplication.clipboard().setText(str(self.current_folder))
        self.statusBar().showMessage("Folder path copied")

    def _ensure_current_pages_loaded(self) -> bool:
        if not self.current_folder:
            return False
        if self.pages:
            return True
        try:
            self.pages = list_pages_for_book(self.current_folder)
        except Exception:
            self.pages = []
        if not self.pages:
            return False
        self.current_index = max(0, min(self.state.progress.get(str(self.current_folder), 0), len(self.pages) - 1))
        return True

    def resume_current_comic(self) -> None:
        if not self.current_folder or not self._ensure_current_pages_loaded():
            return
        self.fit_mode = "fit_page"
        self.zoom_percent = 100
        self.stack.setCurrentWidget(self.reader_page)
        self.load_current_page()

    def populate_comic_intro(self) -> None:
        if not self.current_folder:
            return

        pages = len(self.pages)
        cover = build_cover_pixmap_for_book(self.current_folder, self.intro_cover_label.size())
        if cover is not None:
            self.intro_cover_label.setText("")
            self.intro_cover_label.setPixmap(cover)
        else:
            self.intro_cover_label.setPixmap(QPixmap())
            self.intro_cover_label.setText("No cover")

        self.intro_title_label.setText(self.current_folder.name)

        progress_index = self.state.progress.get(str(self.current_folder), 0)
        is_resumable = str(self.current_folder) in self.state.progress and pages > 1
        meta_bits = [f"{pages} pages"]
        if self.current_root:
            try:
                meta_bits.append(str(self.current_folder.relative_to(self.current_root).parent))
            except ValueError:
                pass
        self.intro_meta_label.setText(" • ".join(bit for bit in meta_bits if bit and bit != '.'))

        self.intro_code_badge.setText("Issue")
        self.intro_status_badge.setText(f"Page {progress_index + 1} ready" if pages else "Ready")
        self.intro_favorite_badge.setText("Saved" if self.is_current_favorite() else "Not saved")

        self.intro_resume_button.setVisible(is_resumable)
        if is_resumable:
            self.intro_resume_button.setText(f"Resume from page {progress_index + 1}")

        parent_name = self.current_folder.parent.name if self.current_folder.parent != self.current_folder else "Library"
        self.intro_summary_label.setText(f"<b>{parent_name}</b><br>{pages} pages in this file")

        self.intro_artist_chip.setText(self._chip_text("Folder", [self.current_folder.name]))
        self.intro_group_chip.setText(self._chip_text("Parent", [parent_name]))
        self.intro_parody_chip.setText(self._chip_text("Pages", [str(pages)]))
        self.intro_character_chip.setText(self._chip_text("Last opened", [str(progress_index + 1)] if is_resumable else ["Not started"]))
        self.populate_related_comics()

    def show_comic_intro(self) -> None:
        if not self.current_folder:
            return
        self.populate_comic_intro()
        self.stack.setCurrentWidget(self.comic_intro_page)
        self.setWindowTitle(f"{APP_NAME} — {self.current_folder.name}")

    def start_reading_current_comic(self) -> None:
        if not self.current_folder or not self._ensure_current_pages_loaded():
            return
        self.fit_mode = "fit_page"
        self.zoom_percent = 100
        self.stack.setCurrentWidget(self.reader_page)
        self.load_current_page()
        self._save_state()

    def on_tag_filter_changed(self, tag: str) -> None:
        return

    def prepare_tag_archive(self) -> bool:
        QMessageBox.information(self, APP_NAME, "This SFW build does not use external tag archives.")
        return False

    def import_tags_for_scope(self) -> None:
        QMessageBox.information(self, APP_NAME, "This SFW build does not import external tags or metadata.")

    def review_tag_matches(self) -> None:
        QMessageBox.information(self, APP_NAME, "This SFW build has no pending external metadata reviews.")

    def set_author_cover_from_comic(self, author: Path, comic_folder: Path) -> None:
        cover = first_cover_in_folder(comic_folder)
        if not cover:
            return

        self.state.author_thumbnail_comics[str(author)] = str(cover)
        self.refresh_author_gallery()
        self.statusBar().showMessage(f"{author.name} cover → {comic_folder.name}")
        self._save_state()

    def show_author_thumbnail_menu(self, author: Path, global_pos: QPoint) -> None:
        comics = author_comic_folders(author)
        if not comics:
            return

        menu = QMenu(self)
        current = self.state.author_thumbnail_comics.get(str(author))
        current_parent = Path(current).parent if current else None

        for comic in comics:
            action = menu.addAction(comic.name)
            action.setCheckable(True)
            action.setChecked(current_parent == comic)
            action.triggered.connect(lambda checked=False, a=author, c=comic: self.set_author_cover_from_comic(a, c))

        menu.exec(global_pos)

    def on_author_sort_changed(self, mode: str) -> None:
        self.state.author_sort = mode
        self.refresh_author_gallery()
        self._save_state()

    def on_comic_sort_changed(self, mode: str) -> None:
        self.state.comic_sort = mode
        self.refresh_comic_gallery()
        self._save_state()

    def open_author(self, author: Path) -> None:
        books = list_books_in_series(author)
        if not books:
            QMessageBox.information(self, APP_NAME, "No books in this series yet.")
            return
        self.current_author = author
        self.current_folder = None
        self.refresh_comic_gallery()
        self.stack.setCurrentWidget(self.comic_gallery_page)
        self.setWindowTitle(f"{APP_NAME} — {author.name}")
        self.state.last_author = str(author)
        self._save_state()

    def show_author_gallery(self) -> None:
        if self.current_root:
            self.refresh_author_gallery()
        self.stack.setCurrentWidget(self.author_gallery_page)
        self.setWindowTitle(f"{APP_NAME} — Library")

    def show_comic_gallery(self) -> None:
        if self.current_author:
            self.refresh_comic_gallery()
            self.stack.setCurrentWidget(self.comic_gallery_page)
            self.setWindowTitle(f"{APP_NAME} — {self.current_author.name}")

    def open_comic(self, folder: Path) -> None:
        try:
            pages = list_pages_for_book(folder)
        except Exception as exc:
            QMessageBox.critical(self, APP_NAME, f"Couldn't open album:\n{exc}")
            return

        if not pages:
            QMessageBox.information(self, APP_NAME, "This book doesn't have any supported pages.")
            return

        self.current_folder = folder
        self.pages = pages
        self.current_index = max(0, min(self.state.progress.get(str(folder), 0), len(self.pages) - 1))
        self.start_reading_current_comic()
        self._save_state()

    def _reader_mode_label(self) -> str:
        if self.fit_mode == "fit_width":
            return "FIT WIDTH"
        if self.fit_mode == "fit_page":
            return "FIT PAGE"
        return f"FREE ZOOM {self.zoom_percent}%"

    def _refresh_reader_header(self, page_name: str = "") -> None:
        total_pages = len(self.pages)
        current_page = self.current_index + 1 if total_pages else 0
        self.reader_mode_chip.setText(self._reader_mode_label())
        self.reader_progress_label.setText(f"PAGE {current_page} / {total_pages}" if total_pages else "PAGE 0 / 0")
        self.reader_prev_button.setEnabled(total_pages > 0 and self.current_index > 0)
        self.reader_next_button.setEnabled(total_pages > 0 and self.current_index < total_pages - 1)
        if page_name:
            bookmark_mark = " • BOOKMARKED" if self.current_index in self.current_bookmarks() else ""
            self.reader_meta_label.setText(f"{page_name}{bookmark_mark}")

    def load_current_page(self) -> None:
        if not self.pages:
            return

        page = self.pages[self.current_index]
        pixmap = load_page_pixmap(page)
        if pixmap is None:
            QMessageBox.warning(self, APP_NAME, f"Failed to load page:\n{page.name}")
            return

        self.base_pixmap = pixmap
        self.apply_view()
        folder_name = self.current_folder.name if self.current_folder else ""
        self.setWindowTitle(f"{APP_NAME} — {folder_name} — {page.name}")
        self.reader_title_label.setText(folder_name or "Reader")
        self._refresh_reader_header(page.name)
        bookmark_mark = " ★" if self.current_index in self.current_bookmarks() else ""
        self.statusBar().showMessage(f"{self.current_index + 1}/{len(self.pages)} — {page.name}{bookmark_mark}")
        if self.current_folder:
            self.state.progress[str(self.current_folder)] = self.current_index
        self._save_state()

    def apply_view(self) -> None:
        if not self.base_pixmap:
            return

        pixmap = self.base_pixmap
        viewport = self.scroll_area.viewport().size()
        target = pixmap

        if self.fit_mode == "fit_width" and viewport.width() > 0:
            width = max(1, int(viewport.width() * self.zoom_percent / 100))
            target = pixmap.scaledToWidth(width, Qt.TransformationMode.SmoothTransformation)
        elif self.fit_mode == "fit_page" and viewport.width() > 0 and viewport.height() > 0:
            target_size = QSize(
                max(1, int(viewport.width() * self.zoom_percent / 100)),
                max(1, int(viewport.height() * self.zoom_percent / 100)),
            )
            target = pixmap.scaled(target_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        elif self.fit_mode == "free":
            size = pixmap.size()
            target = pixmap.scaled(
                max(1, int(size.width() * self.zoom_percent / 100)),
                max(1, int(size.height() * self.zoom_percent / 100)),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )

        self.image_label.setPixmap(target)
        self.image_label.resize(target.size())

    def set_fit_mode(self, mode: str) -> None:
        self.fit_mode = mode
        if mode in {"fit_width", "fit_page"} and self.zoom_percent < 100:
            self.zoom_percent = 100
        self.apply_view()
        self._refresh_reader_header(self.pages[self.current_index].name if self.pages else "")
        self._save_state()

    def zoom_in(self) -> None:
        if self.stack.currentWidget() is not self.reader_page:
            return
        self.zoom_percent = min(400, self.zoom_percent + 25)
        self.apply_view()
        self._refresh_reader_header(self.pages[self.current_index].name if self.pages else "")
        self._save_state()

    def zoom_out(self) -> None:
        if self.stack.currentWidget() is not self.reader_page:
            return
        self.zoom_percent = max(25, self.zoom_percent - 25)
        self.apply_view()
        self._refresh_reader_header(self.pages[self.current_index].name if self.pages else "")
        self._save_state()

    def reset_zoom(self) -> None:
        self.zoom_percent = 100
        self.apply_view()
        self._refresh_reader_header(self.pages[self.current_index].name if self.pages else "")
        self._save_state()

    def next_page(self) -> None:
        if self.stack.currentWidget() is self.reader_page and self.pages and self.current_index < len(self.pages) - 1:
            self.current_index += 1
            self.load_current_page()

    def prev_page(self) -> None:
        if self.stack.currentWidget() is self.reader_page and self.pages and self.current_index > 0:
            self.current_index -= 1
            self.load_current_page()

    def go_back(self) -> None:
        current = self.stack.currentWidget()
        if current is self.reader_page:
            self.show_comic_gallery()
        elif current is self.comic_intro_page:
            self.show_comic_gallery()
        elif current is self.comic_gallery_page:
            self.show_author_gallery()

    def toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()
        self._save_state()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self.fit_mode in {"fit_width", "fit_page"}:
            self.apply_view()

    def wheelEvent(self, event) -> None:
        if self.stack.currentWidget() is self.reader_page and event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            if event.angleDelta().y() > 0:
                self.zoom_in()
            else:
                self.zoom_out()
            event.accept()
            return
        super().wheelEvent(event)

    def keyPressEvent(self, event) -> None:
        if self.stack.currentWidget() is self.comic_intro_page:
            if event.key() in {Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space}:
                self.start_reading_current_comic()
                return
        if self.stack.currentWidget() is self.reader_page:
            if event.key() == Qt.Key.Key_Space:
                self.next_page()
                return
            if event.key() == Qt.Key.Key_Backspace:
                self.prev_page()
                return
        super().keyPressEvent(event)

    def closeEvent(self, event) -> None:
        self._save_state()
        super().closeEvent(event)

    def _save_state(self) -> None:
        self.state.last_root = str(self.current_root) if self.current_root else ""
        self.state.last_author = str(self.current_author) if self.current_author else ""
        self.state.last_folder = str(self.current_folder) if self.current_folder else ""
        self.state.last_page = self.current_index
        self.state.fit_mode = self.fit_mode
        self.state.zoom_percent = self.zoom_percent
        self.state.fullscreen = self.isFullScreen()
        try:
            self.state.save()
        except Exception:
            pass


def main() -> int:
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    window = ComicReader()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
