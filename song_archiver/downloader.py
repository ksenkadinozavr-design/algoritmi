from __future__ import annotations

import importlib
import re
from pathlib import Path

from .matching import similarity_score
from .models import SearchResult, SongRequest


class DownloadError(RuntimeError):
    pass


class DependencyError(DownloadError):
    pass


def _safe_name(value: str) -> str:
    value = re.sub(r"[\\/*?:\"<>|]", "_", value)
    return re.sub(r"\s+", " ", value).strip()


def _load_youtube_dl():
    try:
        module = importlib.import_module("yt_dlp")
        return module.YoutubeDL
    except ModuleNotFoundError as exc:
        raise DependencyError(
            "Не установлен пакет 'yt-dlp'. Установите зависимости: pip install -r requirements.txt"
        ) from exc


def search_song(song: SongRequest, min_score: float = 0.78) -> SearchResult:
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "extract_flat": False,
    }

    youtube_dl = _load_youtube_dl()

    with youtube_dl(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch8:{song.query} official audio", download=False)

    entries = info.get("entries") or []
    if not entries:
        raise DownloadError(f"Ничего не найдено: {song.query}")

    best: SearchResult | None = None
    for entry in entries:
        if not entry:
            continue
        title = entry.get("title", "")
        uploader = entry.get("uploader", "")
        score = similarity_score(song, title, uploader)
        result = SearchResult(
            song=song,
            video_id=entry.get("id", ""),
            video_title=title,
            uploader=uploader,
            duration_seconds=entry.get("duration"),
            score=score,
        )
        if best is None or result.score > best.score:
            best = result

    if best is None or best.score < min_score:
        top = f"{best.video_title} ({best.score:.2f})" if best else "none"
        raise DownloadError(f"Строгая валидация не пройдена для '{song.query}'. Лучший матч: {top}")

    return best


def download_song(result: SearchResult, output_dir: Path) -> Path:
    group_dir = output_dir / _safe_name(result.song.group)
    group_dir.mkdir(parents=True, exist_ok=True)

    filename = _safe_name(result.song.title)
    target_template = str(group_dir / f"{filename}.%(ext)s")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": target_template,
        "noplaylist": True,
        "quiet": True,
        "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}],
    }

    url = f"https://www.youtube.com/watch?v={result.video_id}"
    youtube_dl = _load_youtube_dl()

    with youtube_dl(ydl_opts) as ydl:
        ydl.download([url])

    output_file = group_dir / f"{filename}.mp3"
    if not output_file.exists():
        raise DownloadError(f"Файл не был создан после скачивания: {output_file}")
    return output_file
