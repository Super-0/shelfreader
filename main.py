from __future__ import annotations

import json
import os
import re
import shutil
import sqlite3
import sys
from urllib import error as urlerror
from urllib.request import Request, urlopen
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List

from PySide6.QtCore import QPoint, Qt, QSize, Signal
from PySide6.QtGui import QAction, QColor, QIcon, QImageReader, QKeySequence, QPainter, QPixmap
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
    QToolBar,
    QVBoxLayout,
    QWidget,
)

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".gif"}
APP_NAME = "ShelfReader"
STATE_PATH = Path.home() / ".shelfreader.json"
METADATA_PATH = Path.home() / ".shelfreader-library.json"
ARCHIVE_DB_PATH = Path.home() / ".shelfreader-archive.db"
ARCHIVE_TMP_DIR = Path.home() / ".shelfreader-archive-parts"
SORT_OPTIONS = ["Name (A-Z)", "Name (Z-A)", "Recently Read", "Page Count"]
TAG_FILTER_ALL = "All tags"
ARCHIVE_REPO_CONTENTS_URL = os.environ.get("COMIC_METADATA_ARCHIVE_URL", "https://example.com/community-comic-archive/backend")
ARCHIVE_TABLE = "nh_data"
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
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #1f1633,
        stop:0.45 #251a3d,
        stop:1 #161224);
}
QWidget {
    color: #fdf4ff;
    font-family: "Segoe UI", "Avenir Next", sans-serif;
}
QToolBar {
    background: rgba(49, 33, 79, 0.96);
    border: none;
    border-bottom: 1px solid #5b467f;
    spacing: 8px;
    padding: 10px;
}
QToolButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #ff9bd6,
        stop:0.55 #d8a8ff,
        stop:1 #9ed8ff);
    color: #241334;
    border: 1px solid #ffd6ef;
    border-radius: 14px;
    padding: 9px 14px;
    font-weight: 700;
}
QToolButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #ffb4e1,
        stop:0.55 #e3bcff,
        stop:1 #bae6ff);
}
QToolButton:pressed {
    background: #e7b5ff;
}
QStatusBar {
    background: #140f22;
    color: #e8dff8;
    border-top: 1px solid #4c3968;
}
QWidget#comicIntroPage,
QWidget#introContent {
    background: transparent;
}
QWidget#introPanel,
QWidget#introHeroPanel,
QWidget#introRelatedPanel {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 rgba(43, 31, 69, 0.96),
        stop:1 rgba(29, 22, 47, 0.96));
    border: 1px solid #614b88;
    border-radius: 24px;
}
QLabel#introTitle {
    color: #ffe2f4;
    font-size: 28px;
    font-weight: 900;
}
QLabel#introMeta {
    color: #e8dff8;
    font-size: 14px;
}
QLabel#introBadge {
    color: #251539;
    font-size: 12px;
    font-weight: 800;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #ffc2e6,
        stop:1 #c5ebff);
    border-radius: 12px;
    padding: 6px 10px;
}
QLabel#introSection {
    color: #ffc7ea;
    font-size: 15px;
    font-weight: 800;
    padding-top: 8px;
}
QLabel#introBody {
    color: #f7f1ff;
    font-size: 14px;
    line-height: 1.35em;
    background: rgba(19, 14, 31, 0.55);
    border: 1px solid rgba(118, 93, 158, 0.7);
    border-radius: 18px;
    padding: 14px 16px;
}
QLabel#introTags {
    color: #fdf4ff;
    font-size: 13px;
    line-height: 1.7em;
    background: rgba(19, 14, 31, 0.55);
    border: 1px solid rgba(118, 93, 158, 0.7);
    border-radius: 18px;
    padding: 14px 16px;
}
QLabel#introChip {
    color: #f8efff;
    font-size: 13px;
    background: rgba(19, 14, 31, 0.7);
    border: 1px solid #72579b;
    border-radius: 16px;
    padding: 10px 12px;
}
QListWidget#relatedList {
    background: transparent;
    border: none;
    outline: none;
}
QListWidget#relatedList::item {
    background: rgba(20, 15, 33, 0.78);
    border: 1px solid #604a86;
    border-radius: 18px;
    padding: 12px;
    margin: 4px 0;
}
QListWidget#relatedList::item:hover {
    border: 1px solid #f0a8d8;
    background: rgba(42, 31, 67, 0.92);
}
QListWidget#pagePreviewList {
    background: transparent;
    border: none;
    outline: none;
}
QListWidget#pagePreviewList::item {
    background: rgba(20, 15, 33, 0.78);
    border: 1px solid #604a86;
    border-radius: 18px;
    padding: 8px;
    margin: 4px;
}
QListWidget#pagePreviewList::item:hover {
    border: 1px solid #f0a8d8;
    background: rgba(42, 31, 67, 0.92);
}
QPushButton#heroReadButton {
    min-width: 220px;
    font-size: 15px;
    padding: 13px 18px;
}
QLabel#sectionLabel {
    color: #ffc7ea;
    font-size: 26px;
    font-weight: 800;
}
QLabel#helperLabel {
    color: #d9d0ef;
    font-size: 13px;
    padding-bottom: 6px;
}
QLabel#sortLabel {
    color: #e6dbf7;
    font-size: 12px;
    font-weight: 700;
}
QComboBox {
    background: rgba(62, 44, 96, 0.96);
    color: #fff4fd;
    border: 1px solid #8868b7;
    border-radius: 12px;
    padding: 8px 12px;
    min-width: 190px;
}
QComboBox:hover {
    border: 1px solid #f5b7de;
}
QComboBox QAbstractItemView {
    background: #241934;
    color: #fff4fd;
    selection-background-color: #f0a8d8;
    selection-color: #241334;
    border: 1px solid #6b5390;
}
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #f8a7d8,
        stop:0.55 #ddb0ff,
        stop:1 #aee2ff);
    color: #241334;
    border: 1px solid #ffd7f0;
    border-radius: 16px;
    padding: 10px 16px;
    font-weight: 800;
}
QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #ffb8e3,
        stop:0.55 #e7c2ff,
        stop:1 #c2ecff);
}
QPushButton#backButton {
    max-width: 210px;
}
QMessageBox,
QDialog,
QProgressDialog {
    background: #1b132b;
}
QMessageBox QLabel,
QDialog QLabel,
QProgressDialog QLabel {
    color: #fff4fd;
}
QMessageBox QListView,
QDialog QListView,
QMessageBox QComboBox,
QDialog QComboBox,
QMessageBox QLineEdit,
QDialog QLineEdit {
    background: #241934;
    color: #fff4fd;
    border: 1px solid #6b5390;
    border-radius: 12px;
    padding: 8px 10px;
}
QMessageBox QPushButton,
QDialog QPushButton,
QProgressDialog QPushButton {
    min-width: 110px;
}
QProgressBar {
    background: #241934;
    color: #fff4fd;
    border: 1px solid #6b5390;
    border-radius: 10px;
    text-align: center;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #f8a7d8,
        stop:0.55 #ddb0ff,
        stop:1 #aee2ff);
    border-radius: 9px;
}
QScrollArea {
    background: #120d1f;
    border: none;
}
QListWidget {
    background: transparent;
    border: none;
    outline: none;
    color: #fff4fd;
}
QListWidget::item {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 rgba(57, 39, 90, 0.96),
        stop:1 rgba(38, 28, 62, 0.96));
    border: 1px solid #5e4984;
    border-radius: 22px;
    padding: 12px;
    margin: 6px;
}
QListWidget::item:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 rgba(74, 50, 117, 0.98),
        stop:1 rgba(49, 35, 79, 0.98));
    border: 1px solid #f0a8d8;
}
QListWidget::item:selected {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 rgba(98, 65, 144, 0.98),
        stop:1 rgba(62, 45, 98, 0.98));
    border: 2px solid #f7b6df;
}
QScrollBar:vertical {
    background: transparent;
    width: 14px;
    margin: 6px 4px 6px 0;
}
QScrollBar::handle:vertical {
    background: rgba(240, 168, 216, 0.55);
    min-height: 32px;
    border-radius: 7px;
}
QScrollBar::handle:vertical:hover {
    background: rgba(240, 168, 216, 0.82);
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


def build_cover_pixmap(image_path: Path, size: QSize) -> QPixmap | None:
    cover = QPixmap(str(image_path))
    if cover.isNull():
        return None

    canvas = QPixmap(size)
    canvas.fill(Qt.GlobalColor.transparent)

    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(34, 24, 54, 245))
    painter.drawRoundedRect(canvas.rect(), 18, 18)

    inner = canvas.rect().adjusted(10, 10, -10, -10)
    scaled = cover.scaled(inner.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
    x = inner.x() + (inner.width() - scaled.width()) // 2
    y = inner.y() + (inner.height() - scaled.height()) // 2
    painter.drawPixmap(x, y, scaled)

    painter.end()
    return canvas


def author_comic_folders(author_folder: Path) -> List[Path]:
    return [child for child in list_subfolders(author_folder) if list_image_files(child)]


def count_direct_comics(author_folder: Path) -> int:
    return len(author_comic_folders(author_folder))


def count_pages(folder: Path) -> int:
    return len(list_image_files(folder))


def all_comic_folders(root: Path) -> List[Path]:
    comics: List[Path] = []
    for author in list_subfolders(root):
        comics.extend(author_comic_folders(author))
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
    fit_mode: str = "fit_width"
    zoom_percent: int = 100
    fullscreen: bool = False
    progress: dict[str, int] = field(default_factory=dict)
    author_thumbnail_comics: dict[str, str] = field(default_factory=dict)
    author_sort: str = "Name (A-Z)"
    comic_sort: str = "Name (A-Z)"
    comic_tag_filter: str = ""
    favorite_comics: list[str] = field(default_factory=list)
    page_bookmarks: dict[str, list[int]] = field(default_factory=dict)

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


class GalleryView(QWidget):
    openFolder = Signal(Path)
    sortChanged = Signal(str)
    authorThumbnailMenuRequested = Signal(Path, QPoint)
    tagFilterChanged = Signal(str)

    def __init__(self, empty_text: str, layout_mode: str = "grid") -> None:
        super().__init__()
        self.layout_mode = layout_mode

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        self.title_label = QLabel("My little library ✨")
        self.title_label.setObjectName("sectionLabel")

        self.label = QLabel(empty_text)
        self.label.setObjectName("helperLabel")
        self.label.setWordWrap(True)

        sort_row = QHBoxLayout()
        sort_row.setContentsMargins(0, 0, 0, 0)
        sort_row.setSpacing(10)
        self.sort_label = QLabel("Sort the shelf")
        self.sort_label.setObjectName("sortLabel")
        self.sort_box = QComboBox()
        self.sort_box.addItems(SORT_OPTIONS)
        self.sort_box.currentTextChanged.connect(self.sortChanged.emit)
        self.filter_label = QLabel("Tag filter")
        self.filter_label.setObjectName("sortLabel")
        self.filter_box = QComboBox()
        self.filter_box.addItem(TAG_FILTER_ALL)
        self.filter_box.currentTextChanged.connect(self._emit_tag_filter_changed)
        self.filter_label.hide()
        self.filter_box.hide()
        sort_row.addWidget(self.sort_label, 0)
        sort_row.addWidget(self.sort_box, 0)
        sort_row.addWidget(self.filter_label, 0)
        sort_row.addWidget(self.filter_box, 0)
        sort_row.addStretch(1)

        self.list_widget = QListWidget()
        self.list_widget.setMovement(QListWidget.Movement.Static)
        self.list_widget.setSpacing(18)
        self.list_widget.setUniformItemSizes(False)
        self.list_widget.itemDoubleClicked.connect(self._activate_item)
        self.list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_widget.customContextMenuRequested.connect(self._open_context_menu)
        self.list_widget.verticalScrollBar().setSingleStep(28)
        self.list_widget.verticalScrollBar().setPageStep(180)
        self._configure_list_widget()

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
            self.list_widget.setIconSize(QSize(104, 148))
            self.list_widget.setTextElideMode(Qt.TextElideMode.ElideRight)
        else:
            self.list_widget.setViewMode(QListWidget.ViewMode.IconMode)
            self.list_widget.setResizeMode(QListWidget.ResizeMode.Adjust)
            self.list_widget.setWordWrap(True)
            self.list_widget.setIconSize(QSize(200, 280))
            self.list_widget.setGridSize(QSize(264, 400))
            self.list_widget.setTextElideMode(Qt.TextElideMode.ElideNone)

    def clear_gallery(self, title_text: str, label_text: str) -> None:
        self.title_label.setText(title_text)
        self.label.setText(label_text)
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
            icon_size = QSize(104, 148)
            self.list_widget.setIconSize(icon_size)
        else:
            icon_size = QSize(200, 280) if show_page_count else QSize(208, 300)
            grid_size = QSize(264, 404) if show_page_count else QSize(272, 412)
            item_height = 392 if show_page_count else 372
            self.list_widget.setIconSize(icon_size)
            self.list_widget.setGridSize(grid_size)

        for folder in folders:
            favorite_mark = "♥ " if favorites and str(folder) in favorites else ""
            item = QListWidgetItem(f"{favorite_mark}{folder.name}")
            item.setData(Qt.ItemDataRole.UserRole, str(folder))

            if show_page_count:
                pages = list_image_files(folder)
                if not pages:
                    continue
                page_count = len(pages)
                progress_text = "Unread"
                if str(folder) in progress:
                    progress_text = f"Page {progress[str(folder)] + 1}/{page_count}"
                item.setText(f"{folder.name}\n{page_count} pages\n{progress_text}")
                item.setToolTip(f"{folder.name}\n{page_count} pages\n{progress_text}")
            else:
                comic_count = count_direct_comics(folder)
                item.setText(f"{folder.name}\n{comic_count} comics")
                item.setToolTip(f"{folder.name}\n{comic_count} comics")

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

            cover_path = (
                author_cover_for_display(folder, thumbnail_overrides or {})
                if thumbnail_overrides is not None
                else first_cover_in_folder(folder)
            )
            if cover_path:
                cover = build_cover_pixmap(cover_path, icon_size)
                if cover is not None:
                    item.setIcon(QIcon(cover))

            if self.layout_mode == "list":
                item.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
                item.setSizeHint(QSize(0, 168))
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
        self.pages: List[Path] = []
        self.current_index = 0
        self.base_pixmap: QPixmap | None = None
        self.fit_mode = self.state.fit_mode
        self.zoom_percent = self.state.zoom_percent

        self.setWindowTitle(APP_NAME)
        self.resize(1400, 950)
        self.setStyleSheet(APP_STYLE)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.image_label.setStyleSheet("background: #111;")
        self.scroll_area = ImageScrollArea(self.image_label)

        self.author_gallery = GalleryView("Choose a root folder to build your gallery.", layout_mode="grid")
        self.author_gallery.openFolder.connect(self.open_author)
        self.author_gallery.sortChanged.connect(self.on_author_sort_changed)
        self.author_gallery.authorThumbnailMenuRequested.connect(self.show_author_thumbnail_menu)
        self.author_gallery.set_sort_mode(self.state.author_sort)

        self.comic_gallery = GalleryView("Choose an author.", layout_mode="grid")
        self.comic_gallery.openFolder.connect(self.open_comic)
        self.comic_gallery.sortChanged.connect(self.on_comic_sort_changed)
        self.comic_gallery.tagFilterChanged.connect(self.on_tag_filter_changed)
        self.comic_gallery.set_sort_mode(self.state.comic_sort)
        self.comic_gallery.set_filter_visible(True)

        self.reader_page = QWidget()
        reader_layout = QVBoxLayout(self.reader_page)
        reader_layout.setContentsMargins(0, 0, 0, 0)
        reader_top_row = QHBoxLayout()
        reader_top_row.setContentsMargins(10, 10, 10, 0)
        reader_top_row.setSpacing(10)
        self.back_button = QPushButton("← Back to shelf")
        self.back_button.setObjectName("backButton")
        self.back_button.clicked.connect(self.show_comic_gallery)
        reader_top_row.addWidget(self.back_button, 0)
        reader_top_row.addStretch(1)
        reader_layout.addLayout(reader_top_row)
        reader_layout.addWidget(self.scroll_area, 1)

        self.comic_intro_page = QWidget()
        self.comic_intro_page.setObjectName("comicIntroPage")
        intro_outer = QVBoxLayout(self.comic_intro_page)
        intro_outer.setContentsMargins(0, 0, 0, 0)
        intro_outer.setSpacing(0)

        intro_top = QHBoxLayout()
        intro_top.setContentsMargins(14, 14, 14, 8)
        intro_top.setSpacing(10)
        self.intro_back_button = QPushButton("← Back to comics")
        self.intro_back_button.setObjectName("backButton")
        self.intro_back_button.clicked.connect(self.show_comic_gallery)
        self.intro_read_button = QPushButton("Start reading ✨")
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
        self.intro_cover_label.setStyleSheet("background: rgba(15, 10, 26, 0.9); border: 1px solid #5e4984; border-radius: 24px;")
        cover_panel_layout.addWidget(self.intro_cover_label, 0, Qt.AlignmentFlag.AlignHCenter)
        self.intro_cover_hint = QLabel("Tap start reading when you’re ready 💗")
        self.intro_cover_hint.setObjectName("helperLabel")
        self.intro_cover_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cover_panel_layout.addWidget(self.intro_cover_hint)
        hero_row.addWidget(cover_panel, 0, Qt.AlignmentFlag.AlignTop)

        hero_panel = QWidget()
        hero_panel.setObjectName("introHeroPanel")
        hero_panel_layout = QVBoxLayout(hero_panel)
        hero_panel_layout.setContentsMargins(22, 22, 22, 22)
        hero_panel_layout.setSpacing(10)
        self.intro_title_label = QLabel("Pick a comic 💗")
        self.intro_title_label.setObjectName("introTitle")
        self.intro_title_label.setWordWrap(True)
        self.intro_meta_label = QLabel("")
        self.intro_meta_label.setObjectName("introMeta")
        self.intro_meta_label.setWordWrap(True)
        badges_row = QHBoxLayout()
        badges_row.setSpacing(10)
        self.intro_code_badge = QLabel("Code —")
        self.intro_code_badge.setObjectName("introBadge")
        self.intro_status_badge = QLabel("Tags pending")
        self.intro_status_badge.setObjectName("introBadge")
        self.intro_favorite_badge = QLabel("♡ Not favorite")
        self.intro_favorite_badge.setObjectName("introBadge")
        badges_row.addWidget(self.intro_code_badge, 0)
        badges_row.addWidget(self.intro_status_badge, 0)
        badges_row.addWidget(self.intro_favorite_badge, 0)
        badges_row.addStretch(1)
        action_row = QHBoxLayout()
        action_row.setSpacing(10)
        self.intro_resume_button = QPushButton("Resume from last page")
        self.intro_resume_button.clicked.connect(self.resume_current_comic)
        self.intro_favorite_button = QPushButton("♡ Favorite")
        self.intro_favorite_button.clicked.connect(self.toggle_current_favorite)
        self.intro_random_button = QPushButton("Random comic 🎲")
        self.intro_random_button.clicked.connect(self.open_random_comic)
        self.intro_folder_button = QPushButton("Open comic folder")
        self.intro_folder_button.clicked.connect(self.copy_current_folder_path)
        action_row.addWidget(self.intro_read_button, 0)
        action_row.addWidget(self.intro_resume_button, 0)
        action_row.addWidget(self.intro_favorite_button, 0)
        action_row.addWidget(self.intro_random_button, 0)
        action_row.addWidget(self.intro_folder_button, 0)
        action_row.addStretch(1)
        self.intro_summary_label = QLabel("")
        self.intro_summary_label.setObjectName("introBody")
        self.intro_summary_label.setWordWrap(True)
        self.intro_tags_title = QLabel("Tags")
        self.intro_tags_title.setObjectName("introSection")
        self.intro_tags_label = QLabel("")
        self.intro_tags_label.setObjectName("introTags")
        self.intro_tags_label.setWordWrap(True)
        self.intro_tags_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.LinksAccessibleByMouse
        )
        self.intro_tags_label.setOpenExternalLinks(False)
        self.intro_tags_label.linkActivated.connect(self.apply_tag_filter_from_intro)
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
        hero_panel_layout.addWidget(self.intro_tags_title)
        hero_panel_layout.addWidget(self.intro_tags_label)
        hero_panel_layout.addWidget(self.intro_details_title)
        hero_panel_layout.addLayout(details_grid)
        hero_row.addWidget(hero_panel, 1)
        intro_layout.addLayout(hero_row)

        related_panel = QWidget()
        related_panel.setObjectName("introRelatedPanel")
        related_layout = QVBoxLayout(related_panel)
        related_layout.setContentsMargins(20, 18, 20, 18)
        related_layout.setSpacing(10)
        self.intro_related_title = QLabel("More like this")
        self.intro_related_title.setObjectName("introSection")
        self.intro_related_hint = QLabel("Double-click a related comic to open its info page.")
        self.intro_related_hint.setObjectName("helperLabel")
        self.intro_related_list = QListWidget()
        self.intro_related_list.setObjectName("relatedList")
        self.intro_related_list.setIconSize(QSize(84, 118))
        self.intro_related_list.itemDoubleClicked.connect(self._open_related_comic)
        related_layout.addWidget(self.intro_related_title)
        related_layout.addWidget(self.intro_related_hint)
        related_layout.addWidget(self.intro_related_list)
        intro_layout.addWidget(related_panel)

        preview_panel = QWidget()
        preview_panel.setObjectName("introRelatedPanel")
        preview_layout = QVBoxLayout(preview_panel)
        preview_layout.setContentsMargins(20, 18, 20, 18)
        preview_layout.setSpacing(10)
        self.intro_preview_title = QLabel("Page preview")
        self.intro_preview_title.setObjectName("introSection")
        self.intro_preview_hint = QLabel("Double-click a page to jump straight into the reader there.")
        self.intro_preview_hint.setObjectName("helperLabel")
        self.intro_page_preview_list = QListWidget()
        self.intro_page_preview_list.setObjectName("pagePreviewList")
        self.intro_page_preview_list.setViewMode(QListWidget.ViewMode.IconMode)
        self.intro_page_preview_list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.intro_page_preview_list.setMovement(QListWidget.Movement.Static)
        self.intro_page_preview_list.setSpacing(8)
        self.intro_page_preview_list.setIconSize(QSize(120, 168))
        self.intro_page_preview_list.setGridSize(QSize(150, 230))
        self.intro_page_preview_list.itemDoubleClicked.connect(self._open_preview_page)
        preview_layout.addWidget(self.intro_preview_title)
        preview_layout.addWidget(self.intro_preview_hint)
        preview_layout.addWidget(self.intro_page_preview_list)
        intro_layout.addWidget(preview_panel)

        self.stack = QStackedWidget()
        self.stack.addWidget(self.author_gallery)
        self.stack.addWidget(self.comic_gallery)
        self.stack.addWidget(self.comic_intro_page)
        self.stack.addWidget(self.reader_page)
        self.setCentralWidget(self.stack)

        self.setStatusBar(QStatusBar())
        self._build_toolbar()
        self._build_actions()

        if self.state.last_root:
            root = Path(self.state.last_root)
            if root.exists():
                self.open_root(root)
                if self.state.last_author:
                    author = Path(self.state.last_author)
                    if author.exists():
                        self.open_author(author)
                if self.state.last_folder:
                    folder = Path(self.state.last_folder)
                    if folder.exists():
                        self.open_comic(folder)

        if self.state.fullscreen:
            self.showFullScreen()

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Main")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(16, 16))
        self.addToolBar(toolbar)
        self.toolbar = toolbar

    def _build_actions(self) -> None:
        actions = [
            ("Open Gallery Root", self.choose_root, "Ctrl+O"),
            ("Random Comic", self.open_random_comic, "Ctrl+R"),
            ("Prepare Tag Archive", self.prepare_tag_archive, "Ctrl+Shift+A"),
            ("Import Tags", self.import_tags_for_scope, "Ctrl+I"),
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
            self.toolbar.addAction(action)

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
        self._save_state()
        self.statusBar().showMessage(f"Loaded gallery: {root}")

    def refresh_author_gallery(self) -> None:
        if not self.current_root:
            return
        authors = list_subfolders(self.current_root)
        authors = sort_folders(authors, self.state.author_sort, self.state.progress, author_mode=True)
        subtitle = f"{len(authors)} author folders in {self.current_root}"
        self.author_gallery.populate(
            "Author shelf 💗",
            f"{subtitle} • right-click an author to choose a comic cover",
            authors,
            self.state.progress,
            show_page_count=False,
            thumbnail_overrides=self.state.author_thumbnail_comics,
            favorites=self.favorite_comics_set(),
        )

    def refresh_comic_gallery(self) -> None:
        if not self.current_author:
            return
        self.refresh_tag_filter_options()
        comics = [folder for folder in list_subfolders(self.current_author) if list_image_files(folder)]
        favorite_set = self.favorite_comics_set()
        comics.sort(key=lambda folder: (str(folder) not in favorite_set, natural_key(folder.name)))
        if self.state.comic_tag_filter:
            target = normalize_text(self.state.comic_tag_filter)
            comics = [
                folder
                for folder in comics
                if target in [normalize_text(tag) for tag in self.metadata.comics.get(str(folder), {}).get("tags", [])]
            ]
        comics = sort_folders(comics, self.state.comic_sort, self.state.progress, author_mode=False)
        subtitle = f"{len(comics)} comics by {self.current_author.name}"
        if self.state.comic_tag_filter:
            subtitle += f" • filtered by {self.state.comic_tag_filter}"
        self.comic_gallery.populate(
            f"{self.current_author.name} ✨",
            subtitle,
            comics,
            self.state.progress,
            show_page_count=True,
            metadata_records=self.metadata.comics,
            favorites=self.favorite_comics_set(),
        )

    def refresh_tag_filter_options(self) -> None:
        if not self.current_author:
            self.comic_gallery.set_filter_options([], "")
            return
        tags: set[str] = set()
        for folder in author_comic_folders(self.current_author):
            tags.update(self.metadata.comics.get(str(folder), {}).get("tags", []))
        self.comic_gallery.set_filter_options(sorted(tags, key=str.lower), self.state.comic_tag_filter)

    def pending_review_count(self, scope: Path | None = None) -> int:
        if scope is None:
            return len(self.metadata.review_queue)
        scope_prefix = str(scope)
        return sum(1 for folder in self.metadata.review_queue if folder.startswith(scope_prefix))

    def metadata_for_current_comic(self) -> dict[str, Any]:
        if not self.current_folder:
            return {}
        return self.metadata.comics.get(str(self.current_folder), {})

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
        self.populate_page_previews()
        self._save_state()

    def open_random_comic(self) -> None:
        if not self.current_root:
            QMessageBox.information(self, APP_NAME, "Open your library first so I can pick something random.")
            return
        comics = all_comic_folders(self.current_root)
        if not comics:
            QMessageBox.information(self, APP_NAME, "No comics found yet.")
            return
        import random
        choice = random.choice(comics)
        self.current_author = choice.parent
        self.state.last_author = str(self.current_author)
        self.refresh_comic_gallery()
        self.open_comic(choice)

    def apply_tag_filter_from_intro(self, link: str) -> None:
        if not self.current_author:
            return
        tag = link.replace("tag:", "", 1)
        self.state.comic_tag_filter = tag
        self.refresh_comic_gallery()
        self.stack.setCurrentWidget(self.comic_gallery)
        self.statusBar().showMessage(f"Filtered comics by tag: {tag}")
        self._save_state()

    def _format_tag_pills(self, tags: list[str]) -> str:
        if not tags:
            return "No imported tags yet — run Import Tags first."
        pills = []
        for tag in tags:
            safe = tag.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            pills.append(
                f'<a href="tag:{safe}" style="text-decoration:none; color:#fff4fd;">'
                f'<span style="display:inline-block; margin:4px 6px 4px 0; padding:6px 10px; '
                f'background:rgba(255,185,227,0.18); border:1px solid #9a78c8; border-radius:12px; color:#fff4fd;">{safe}</span></a>'
            )
        return "".join(pills)

    def _chip_text(self, label: str, values: list[str]) -> str:
        clean = [str(v) for v in values if v]
        return f"<b>{label}</b><br>{', '.join(clean) if clean else '—'}"

    def populate_related_comics(self) -> None:
        self.intro_related_list.clear()
        if not self.current_folder:
            return

        current_record = self.metadata_for_current_comic()
        current_path = str(self.current_folder)
        current_tags = set(normalize_text(tag) for tag in current_record.get("tags", []))
        current_artists = set(normalize_text(tag) for tag in current_record.get("artists", []))
        current_parodies = set(normalize_text(tag) for tag in current_record.get("parodies", []))

        scored: list[tuple[int, str, dict[str, Any]]] = []
        for folder_path, record in self.metadata.comics.items():
            if folder_path == current_path:
                continue
            score = 0
            score += 4 * len(current_artists & {normalize_text(v) for v in record.get("artists", [])})
            score += 3 * len(current_parodies & {normalize_text(v) for v in record.get("parodies", [])})
            score += 1 * len(current_tags & {normalize_text(v) for v in record.get("tags", [])})
            if score <= 0:
                continue
            scored.append((score, folder_path, record))

        scored.sort(key=lambda row: (-row[0], natural_key(Path(row[1]).name)))
        for score, folder_path, record in scored[:12]:
            folder = Path(folder_path)
            title = record.get("title") or folder.name
            artist = ", ".join(record.get("artists", [])[:2]) or folder.parent.name
            shared_tags = []
            record_tags = [normalize_text(v) for v in record.get("tags", [])]
            for tag in record.get("tags", []):
                if normalize_text(tag) in current_tags and len(shared_tags) < 3:
                    shared_tags.append(tag)
            subtitle = artist
            if shared_tags:
                subtitle += f" • shared: {', '.join(shared_tags)}"
            item = QListWidgetItem(f"{title}\n{subtitle}")
            item.setData(Qt.ItemDataRole.UserRole, folder_path)
            item.setToolTip(f"Match score: {score}\n{title}\n{subtitle}")
            cover = first_cover_in_folder(folder)
            if cover:
                pix = build_cover_pixmap(cover, QSize(84, 118))
                if pix is not None:
                    item.setIcon(QIcon(pix))
            item.setSizeHint(QSize(0, 82))
            self.intro_related_list.addItem(item)

        if self.intro_related_list.count() == 0:
            empty = QListWidgetItem("No related comics yet — import more tags to build recommendations.")
            empty.setFlags(Qt.ItemFlag.NoItemFlags)
            empty.setSizeHint(QSize(0, 58))
            self.intro_related_list.addItem(empty)

    def populate_page_previews(self) -> None:
        self.intro_page_preview_list.clear()
        if not self.pages:
            return
        bookmarks = set(self.current_bookmarks())
        limit = min(len(self.pages), 18)
        step = max(1, len(self.pages) // max(1, limit))
        chosen_indexes = list(dict.fromkeys(list(range(0, len(self.pages), step))[:limit]))
        for index in chosen_indexes:
            page = self.pages[index]
            item = QListWidgetItem(f"Page {index + 1}")
            item.setData(Qt.ItemDataRole.UserRole, index)
            if index in bookmarks:
                item.setText(f"★ Page {index + 1}")
            pix = build_cover_pixmap(page, QSize(120, 168))
            if pix is not None:
                item.setIcon(QIcon(pix))
            item.setToolTip(page.name)
            item.setSizeHint(QSize(140, 210))
            self.intro_page_preview_list.addItem(item)

    def _open_preview_page(self, item: QListWidgetItem) -> None:
        page_index = item.data(Qt.ItemDataRole.UserRole)
        if page_index is None:
            return
        self.current_index = int(page_index)
        self.start_reading_current_comic()

    def _open_related_comic(self, item: QListWidgetItem) -> None:
        folder = item.data(Qt.ItemDataRole.UserRole)
        if folder:
            self.open_comic(Path(folder))

    def copy_current_folder_path(self) -> None:
        if not self.current_folder:
            return
        QApplication.clipboard().setText(str(self.current_folder))
        self.statusBar().showMessage("Comic folder path copied")

    def resume_current_comic(self) -> None:
        if not self.current_folder or not self.pages:
            return
        self.stack.setCurrentWidget(self.reader_page)
        self.load_current_page()

    def populate_comic_intro(self) -> None:
        if not self.current_folder:
            return

        record = self.metadata_for_current_comic()
        pages = len(self.pages)
        cover_path = first_cover_in_folder(self.current_folder)
        if cover_path:
            cover = build_cover_pixmap(cover_path, self.intro_cover_label.size())
            self.intro_cover_label.setText("")
            self.intro_cover_label.setPixmap(cover)
        else:
            self.intro_cover_label.setPixmap(QPixmap())
            self.intro_cover_label.setText("No cover")

        display_title = record.get("title") or self.current_folder.name
        self.intro_title_label.setText(display_title)

        meta_bits = [f"{pages} pages"]
        if record.get("language"):
            meta_bits.append(str(record["language"]).replace(",", " •"))
        if record.get("category"):
            meta_bits.append(record["category"])
        self.intro_meta_label.setText(" • ".join(meta_bits))

        code = record.get("id") or "—"
        self.intro_code_badge.setText(f"Code {code}")
        self.intro_status_badge.setText("Tags imported" if record.get("tags") else "Tags pending")
        self.intro_favorite_badge.setText("♥ Favorite" if self.is_current_favorite() else "♡ Not favorite")
        self.intro_favorite_button.setText("♥ Unfavorite" if self.is_current_favorite() else "♡ Favorite")

        progress_index = self.state.progress.get(str(self.current_folder), 0)
        is_resumable = str(self.current_folder) in self.state.progress and pages > 1
        self.intro_resume_button.setVisible(is_resumable)
        if is_resumable:
            self.intro_resume_button.setText(f"Resume from page {progress_index + 1}")
        artist_text = ", ".join(record.get("artists", [])[:2]) or self.current_folder.parent.name
        parody_text = ", ".join(record.get("parodies", [])[:2]) or "original"
        self.intro_summary_label.setText(
            f"<b>{artist_text}</b> • {parody_text}<br>"
            f"A glossy library card for this comic before you dive into the pages."
        )

        tags = record.get("tags") or []
        self.intro_tags_label.setText(self._format_tag_pills(tags))
        self.intro_tags_label.setTextFormat(Qt.TextFormat.RichText)

        self.intro_artist_chip.setText(self._chip_text("Artists", record.get("artists") or [self.current_folder.parent.name]))
        self.intro_group_chip.setText(self._chip_text("Groups", record.get("groups") or []))
        self.intro_parody_chip.setText(self._chip_text("Parodies", record.get("parodies") or ["original"]))
        self.intro_character_chip.setText(self._chip_text("Characters", record.get("characters") or []))
        self.populate_related_comics()
        self.populate_page_previews()

    def show_comic_intro(self) -> None:
        if not self.current_folder:
            return
        self.populate_comic_intro()
        self.stack.setCurrentWidget(self.comic_intro_page)
        self.setWindowTitle(f"{APP_NAME} — {self.current_folder.name}")

    def start_reading_current_comic(self) -> None:
        if not self.current_folder or not self.pages:
            return
        self.stack.setCurrentWidget(self.reader_page)
        self.load_current_page()
        self._save_state()

    def on_tag_filter_changed(self, tag: str) -> None:
        self.state.comic_tag_filter = tag
        self.refresh_comic_gallery()
        self._save_state()

    def prepare_tag_archive(self) -> bool:
        if ARCHIVE_DB_PATH.exists() and ARCHIVE_DB_PATH.stat().st_size > 0:
            self.statusBar().showMessage("Tag archive is ready.")
            QMessageBox.information(self, APP_NAME, f"Archive already ready:\n{ARCHIVE_DB_PATH}")
            return True

        progress = QProgressDialog("Preparing local tag archive...", "Cancel", 0, 0, self)
        progress.setWindowTitle(APP_NAME)
        progress.setMinimumDuration(0)
        progress.setValue(0)

        try:
            manifest = archive_part_manifest()
        except Exception as exc:
            QMessageBox.warning(self, APP_NAME, f"Couldn't fetch archive manifest:\n{exc}")
            return False

        total_bytes = sum(int(item.get("size") or 0) for item in manifest) or 1
        progress.setMaximum(total_bytes)
        downloaded_so_far = 0

        def on_progress(written: int, part_total: int | None, label: str) -> None:
            nonlocal downloaded_so_far
            part_total = part_total or 0
            base_done = downloaded_so_far - part_total if downloaded_so_far >= part_total else downloaded_so_far
            progress.setLabelText(label)
            progress.setValue(min(total_bytes, base_done + written))
            QApplication.processEvents()
            if progress.wasCanceled():
                raise RuntimeError("Archive download cancelled")

        try:
            ARCHIVE_TMP_DIR.mkdir(parents=True, exist_ok=True)
            for item in manifest:
                part_path = ARCHIVE_TMP_DIR / item["name"]
                size = int(item.get("size") or 0)
                downloaded_so_far += size
                if part_path.exists() and part_path.stat().st_size == size and size > 0:
                    progress.setLabelText(f"Have {item['name']}")
                    progress.setValue(min(total_bytes, downloaded_so_far))
                    continue
                downloaded_so_far -= size
                download_archive_file(item["download_url"], part_path, progress=on_progress, label=f"Downloading {item['name']}")
                downloaded_so_far += size
                progress.setValue(min(total_bytes, downloaded_so_far))

            progress.setLabelText("Merging archive...")
            QApplication.processEvents()
            ensure_archive_database()
            progress.setValue(total_bytes)
        except Exception as exc:
            QMessageBox.warning(self, APP_NAME, f"Preparing the local archive failed:\n{exc}")
            return False

        self.statusBar().showMessage(f"Tag archive ready: {ARCHIVE_DB_PATH}")
        QMessageBox.information(self, APP_NAME, "Local tag archive is ready now 💗")
        return True

    def import_tags_for_scope(self) -> None:
        if not self.current_root:
            QMessageBox.information(self, APP_NAME, "Open your library first so I know what to tag.")
            return

        if not ARCHIVE_DB_PATH.exists() and not self.prepare_tag_archive():
            return

        if self.current_author:
            comics = author_comic_folders(self.current_author)
            scope_name = self.current_author.name
        else:
            comics = all_comic_folders(self.current_root)
            scope_name = self.current_root.name

        if not comics:
            QMessageBox.information(self, APP_NAME, "No comics found in this scope.")
            return

        self.metadata.review_queue = {}
        progress = QProgressDialog(f"Importing tags for {scope_name}...", "Cancel", 0, len(comics), self)
        progress.setWindowTitle(APP_NAME)
        progress.setMinimumDuration(0)
        progress.setValue(0)

        auto_matched = 0
        unmatched = 0
        skipped = 0
        archive_errors = 0

        for index, folder in enumerate(comics, start=1):
            progress.setValue(index - 1)
            progress.setLabelText(f"Matching {folder.name}")
            QApplication.processEvents()
            if progress.wasCanceled():
                break

            existing = self.metadata.comics.get(str(folder))
            if existing and existing.get("match_status") == "matched":
                skipped += 1
                continue

            candidates = fetch_archive_candidates(folder)
            if candidates is None:
                archive_errors += 1
                continue
            if not candidates:
                unmatched += 1
                continue

            top = candidates[0]
            score = top.get("score", 0.0)
            if score > 0.0:
                self.metadata.comics[str(folder)] = metadata_record_from_candidate(top)
                self.metadata.review_queue.pop(str(folder), None)
                auto_matched += 1
            else:
                unmatched += 1

        progress.setValue(len(comics))
        self.metadata.save()

        if self.current_author:
            self.refresh_comic_gallery()

        self.statusBar().showMessage(
            f"Tag import finished — {auto_matched} imported, {unmatched} unmatched, {skipped} already tagged, {archive_errors} archive errors"
        )
        QMessageBox.information(
            self,
            APP_NAME,
            (
                f"Import finished for {scope_name}.\n\n"
                f"Imported: {auto_matched}\n"
                f"Unmatched: {unmatched}\n"
                f"Already tagged: {skipped}\n"
                f"Archive errors: {archive_errors}"
            ),
        )

    def review_tag_matches(self) -> None:
        if not self.metadata.review_queue:
            QMessageBox.information(self, APP_NAME, "No pending tag matches right now.")
            return

        folder_path = None
        candidates = None
        if self.current_author:
            author_prefix = str(self.current_author)
            for path, rows in self.metadata.review_queue.items():
                if path.startswith(author_prefix):
                    folder_path = path
                    candidates = rows
                    break
        if folder_path is None:
            folder_path, candidates = next(iter(self.metadata.review_queue.items()))

        folder = Path(folder_path)
        labels = [candidate_label(candidate) for candidate in candidates]
        choice, accepted = QInputDialog.getItem(
            self,
            "Review tag match",
            f"Pick the right match for:\n{folder.name}",
            labels,
            0,
            False,
        )
        if not accepted:
            return

        selected = candidates[labels.index(choice)]
        self.metadata.comics[folder_path] = metadata_record_from_candidate(selected)
        self.metadata.review_queue.pop(folder_path, None)
        self.metadata.save()
        if self.current_author and folder.parent == self.current_author:
            self.refresh_comic_gallery()
        chosen_title = selected.get("CLEAN_TITLE") or selected.get("EN_TITLE") or folder.name
        self.statusBar().showMessage(f"Tagged {folder.name} → {chosen_title}")

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
        comics = [folder for folder in list_subfolders(author) if list_image_files(folder)]
        if not comics:
            QMessageBox.information(self, APP_NAME, "No image folders found for that author.")
            return

        self.current_author = author
        self.current_folder = None
        self.state.comic_tag_filter = ""
        self.refresh_comic_gallery()
        self.stack.setCurrentWidget(self.comic_gallery)
        self.state.last_author = str(author)
        self._save_state()

    def show_author_gallery(self) -> None:
        self.stack.setCurrentWidget(self.author_gallery)
        self.setWindowTitle(f"{APP_NAME} — Library")

    def show_comic_gallery(self) -> None:
        if self.current_author:
            self.refresh_comic_gallery()
            self.stack.setCurrentWidget(self.comic_gallery)
            self.setWindowTitle(f"{APP_NAME} — {self.current_author.name}")

    def open_comic(self, folder: Path) -> None:
        try:
            pages = list_image_files(folder)
        except Exception as exc:
            QMessageBox.critical(self, APP_NAME, f"Couldn't open comic:\n{exc}")
            return

        if not pages:
            QMessageBox.information(self, APP_NAME, "No supported images found in that folder.")
            return

        self.current_folder = folder
        self.pages = pages
        self.current_index = max(0, min(self.state.progress.get(str(folder), 0), len(self.pages) - 1))
        self.show_comic_intro()
        self._save_state()

    def load_current_page(self) -> None:
        if not self.pages:
            return

        page = self.pages[self.current_index]
        reader = QImageReader(str(page))
        reader.setAutoTransform(True)
        image = reader.read()
        if image.isNull():
            QMessageBox.warning(self, APP_NAME, f"Failed to load image:\n{page.name}")
            return

        self.base_pixmap = QPixmap.fromImage(image)
        self.apply_view()
        folder_name = self.current_folder.name if self.current_folder else ""
        self.setWindowTitle(f"{APP_NAME} — {folder_name} — {page.name}")
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
        self._save_state()

    def zoom_in(self) -> None:
        if self.stack.currentWidget() is not self.reader_page:
            return
        self.zoom_percent = min(400, self.zoom_percent + 25)
        self.apply_view()
        self._save_state()

    def zoom_out(self) -> None:
        if self.stack.currentWidget() is not self.reader_page:
            return
        self.zoom_percent = max(25, self.zoom_percent - 25)
        self.apply_view()
        self._save_state()

    def reset_zoom(self) -> None:
        self.zoom_percent = 100
        self.apply_view()
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
            self.show_comic_intro()
        elif current is self.comic_intro_page:
            self.show_comic_gallery()
        elif current is self.comic_gallery:
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
