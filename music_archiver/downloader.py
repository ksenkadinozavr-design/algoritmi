from __future__ import annotations

import re
import tempfile
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import yt_dlp

from .matcher import MatchResult


def _safe_name(value: str) -> str:
    value = re.sub(r"[^\w\-. ]+", "_", value, flags=re.UNICODE).strip()
    return value or "untitled"


def download_archive(matches: list[MatchResult]) -> Path:
    """Download audio for all matched songs and return zip archive path."""
    temp_dir = Path(tempfile.mkdtemp(prefix="music_archiver_"))
    download_root = temp_dir / "songs"
    download_root.mkdir(parents=True, exist_ok=True)

    for match in matches:
        if not match.url:
            raise ValueError("Cannot download archive with unresolved matches")

        group_dir = download_root / _safe_name(match.request.group)
        group_dir.mkdir(parents=True, exist_ok=True)

        output_tpl = str(group_dir / f"{_safe_name(match.request.artist)} - {_safe_name(match.request.title)}.%(ext)s")

        ydl_opts = {
            "format": "bestaudio/best",
            "quiet": True,
            "noplaylist": True,
            "outtmpl": output_tpl,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": "192",
                }
            ],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([match.url])

    archive_path = temp_dir / "songs_archive.zip"
    with ZipFile(archive_path, "w", compression=ZIP_DEFLATED) as zip_file:
        for path in download_root.rglob("*"):
            if path.is_file():
                zip_file.write(path, arcname=path.relative_to(download_root))

    return archive_path
