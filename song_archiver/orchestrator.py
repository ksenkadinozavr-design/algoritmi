from __future__ import annotations

import shutil
from pathlib import Path

from .downloader import DependencyError, DownloadError, download_song, search_song
from .parser import parse_song_list


def process_playlist_file(
    input_file: str | Path,
    workdir: str | Path = "downloads",
    archive_name: str = "songs_archive",
    min_score: float = 0.78,
    proxy_url: str | None = None,
    cookies_path: str | None = None,
    cookies_from_browser: str | None = None,
    js_runtime: str | None = None,
) -> Path:
    """Parse, validate all songs, download, then archive as zip.

    Strict mode: if at least one song is not confidently found, nothing is downloaded.
    """

    songs = parse_song_list(input_file)
    root = Path(workdir)
    root.mkdir(parents=True, exist_ok=True)

    print(f"Проверяю {len(songs)} песен в строгом режиме...")
    matches = []
    errors = []

    for song in songs:
        try:
            result = search_song(
                song,
                min_score=min_score,
                proxy_url=proxy_url,
                cookies_path=cookies_path,
                cookies_from_browser=cookies_from_browser,
                js_runtime=js_runtime,
            )
            matches.append(result)
            print(f"  [OK] {song.query} -> {result.video_title} (score={result.score:.2f})")
        except DependencyError as exc:
            raise DownloadError(str(exc)) from exc
        except DownloadError as exc:
            errors.append(str(exc))
            print(f"  [ERR] {song.query}: {exc}")

    if errors:
        joined = "\n".join(errors)
        raise DownloadError(
            "Строгая валидация не пройдена. Исправьте входной файл, прокси/cookies или снизьте --min-score.\n" + joined
        )

    downloads_dir = root / "songs"
    if downloads_dir.exists():
        shutil.rmtree(downloads_dir)
    downloads_dir.mkdir(parents=True, exist_ok=True)

    for result in matches:
        download_song(
            result,
            downloads_dir,
            proxy_url=proxy_url,
            cookies_path=cookies_path,
            cookies_from_browser=cookies_from_browser,
            js_runtime=js_runtime,
        )

    archive_base = root / archive_name
    archive_path = Path(shutil.make_archive(str(archive_base), "zip", downloads_dir))
    return archive_path
