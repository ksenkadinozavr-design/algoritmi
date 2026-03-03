from __future__ import annotations

import importlib
import re
from pathlib import Path

from .models import SearchResult, SongRequest


class DownloadError(RuntimeError):
    pass


class DependencyError(DownloadError):
    pass


DEFAULT_SEARCH_PROVIDERS = ("scsearch", "bandcampsearch", "ytsearch")


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


def _build_ydl_options(*, base: dict, proxy_url: str | None = None) -> dict:
    options = dict(base)
    if proxy_url:
        options["proxy"] = proxy_url
    return options


def _wrap_network_error(exc: Exception) -> DownloadError:
    message = str(exc)
    lowered = message.lower()

    if "winerror 10054" in lowered or "unable to download" in lowered or "transporterror" in lowered:
        return DownloadError(
            "Сетевая ошибка при обращении к источнику аудио. Проверьте прокси (--proxy) и доступ в интернет. "
            f"Детали: {message}"
        )

    return DownloadError(message)


def _extract_first_entry(info: dict) -> dict | None:
    entries = info.get("entries") or []
    return next((entry for entry in entries if entry), None)


def _search_by_providers(song: SongRequest, *, proxy_url: str | None, providers: tuple[str, ...]) -> SearchResult:
    youtube_dl = _load_youtube_dl()
    ydl_opts = _build_ydl_options(
        base={"quiet": True, "skip_download": True, "extract_flat": False, "retries": 3},
        proxy_url=proxy_url,
    )

    last_error = ""
    for provider in providers:
        query = f"{provider}5:{song.query}"
        try:
            with youtube_dl(ydl_opts) as ydl:
                info = ydl.extract_info(query, download=False)
            first = _extract_first_entry(info)
            if not first:
                continue

            url = first.get("webpage_url")
            if not url and first.get("id") and first.get("extractor") == "youtube":
                url = f"https://www.youtube.com/watch?v={first['id']}"
            if not url and first.get("url"):
                url = first["url"]
            if not url:
                continue

            return SearchResult(
                song=song,
                video_id=url,
                video_title=first.get("title") or song.title,
                uploader=first.get("uploader") or song.group,
                duration_seconds=first.get("duration"),
                score=0.5,
            )
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
            continue

    raise DownloadError(f"Не найдено кандидатов для: {song.query}. Последняя ошибка: {last_error}")


def search_song(
    song: SongRequest,
    proxy_url: str | None = None,
    search_providers: tuple[str, ...] = DEFAULT_SEARCH_PROVIDERS,
) -> SearchResult:
    """Find song source by direct URL or provider search across audio websites."""
    youtube_dl = _load_youtube_dl()

    if song.source_url:
        ydl_opts = _build_ydl_options(
            base={"quiet": True, "skip_download": True, "extract_flat": False, "retries": 3},
            proxy_url=proxy_url,
        )
        try:
            with youtube_dl(ydl_opts) as ydl:
                info = ydl.extract_info(song.source_url, download=False)
        except Exception as exc:  # noqa: BLE001
            raise _wrap_network_error(exc) from exc

        return SearchResult(
            song=song,
            video_id=song.source_url,
            video_title=(info or {}).get("title") or song.title,
            uploader=(info or {}).get("uploader") or song.group,
            duration_seconds=(info or {}).get("duration"),
            score=1.0,
        )

    try:
        return _search_by_providers(song, proxy_url=proxy_url, providers=search_providers)
    except DownloadError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise _wrap_network_error(exc) from exc


def download_song(result: SearchResult, output_dir: Path, proxy_url: str | None = None) -> Path:
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
    )

    youtube_dl = _load_youtube_dl()

    try:
        with youtube_dl(ydl_opts) as ydl:
            ydl.download([result.video_id])
    except Exception as exc:  # noqa: BLE001
        raise _wrap_network_error(exc) from exc

    output_file = group_dir / f"{filename}.mp3"
    if not output_file.exists():
        raise DownloadError(f"Файл не был создан после скачивания: {output_file}")
    return output_file
