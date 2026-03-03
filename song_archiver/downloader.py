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


def _build_ydl_options(
    *,
    base: dict,
    proxy_url: str | None = None,
    cookies_path: str | None = None,
    cookies_from_browser: str | None = None,
    js_runtime: str | None = None,
) -> dict:
    options = dict(base)
    if proxy_url:
        options["proxy"] = proxy_url
    if cookies_path:
        options["cookiefile"] = cookies_path
    if cookies_from_browser:
        options["cookiesfrombrowser"] = (cookies_from_browser,)
    if js_runtime:
        options["js_runtimes"] = {js_runtime: {}}
    return options


def _wrap_network_error(exc: Exception) -> DownloadError:
    message = str(exc)
    lowered = message.lower()

    if "sign in to confirm you’re not a bot" in lowered or "sign in to confirm you're not a bot" in lowered:
        return DownloadError(
            "YouTube требует подтверждение 'not a bot'. Добавьте cookies: --cookies-file PATH или "
            "--cookies-from-browser chrome. Детали: "
            f"{message}"
        )

    if "no supported javascript runtime" in lowered:
        return DownloadError(
            "yt-dlp не нашел JS runtime для YouTube. Установите Node.js и запустите с --js-runtime node. "
            f"Детали: {message}"
        )

    if "winerror 10054" in lowered or "unable to download" in lowered or "transporterror" in lowered:
        return DownloadError(
            "Сетевая ошибка при обращении к источнику аудио. Проверьте прокси (--proxy) и доступ в интернет. "
            f"Детали: {message}"
        )

    return DownloadError(message)


def search_song(
    song: SongRequest,
    min_score: float = 0.78,
    proxy_url: str | None = None,
    cookies_path: str | None = None,
    cookies_from_browser: str | None = None,
    js_runtime: str | None = None,
) -> SearchResult:
    if song.source_url:
        return SearchResult(
            song=song,
            video_id=song.source_url,
            video_title=song.title,
            uploader=song.group,
            duration_seconds=None,
            score=1.0,
        )

    ydl_opts = _build_ydl_options(
        base={
            "quiet": True,
            "skip_download": True,
            "extract_flat": False,
            "retries": 3,
        },
        proxy_url=proxy_url,
        cookies_path=cookies_path,
        cookies_from_browser=cookies_from_browser,
        js_runtime=js_runtime,
    )

    youtube_dl = _load_youtube_dl()

    try:
        with youtube_dl(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch8:{song.query} official audio", download=False)
    except Exception as exc:  # noqa: BLE001
        raise _wrap_network_error(exc) from exc

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


def download_song(
    result: SearchResult,
    output_dir: Path,
    proxy_url: str | None = None,
    cookies_path: str | None = None,
    cookies_from_browser: str | None = None,
    js_runtime: str | None = None,
) -> Path:
    group_dir = output_dir / _safe_name(result.song.group)
    group_dir.mkdir(parents=True, exist_ok=True)

    filename = _safe_name(result.song.title)
    target_template = str(group_dir / f"{filename}.%(ext)s")

    ydl_opts = _build_ydl_options(
        base={
            "format": "bestaudio/best",
            "outtmpl": target_template,
            "noplaylist": True,
            "quiet": True,
            "retries": 3,
            "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}],
        },
        proxy_url=proxy_url,
        cookies_path=cookies_path,
        cookies_from_browser=cookies_from_browser,
        js_runtime=js_runtime,
    )

    url = result.video_id if result.video_id.startswith("http://") or result.video_id.startswith("https://") else f"https://www.youtube.com/watch?v={result.video_id}"
    youtube_dl = _load_youtube_dl()

    try:
        with youtube_dl(ydl_opts) as ydl:
            ydl.download([url])
    except Exception as exc:  # noqa: BLE001
        raise _wrap_network_error(exc) from exc

    output_file = group_dir / f"{filename}.mp3"
    if not output_file.exists():
        raise DownloadError(f"Файл не был создан после скачивания: {output_file}")
    return output_file
