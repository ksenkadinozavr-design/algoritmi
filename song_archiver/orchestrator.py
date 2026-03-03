from __future__ import annotations

import shutil
import time
from pathlib import Path

from .downloader import DependencyError, DownloadError, download_song, search_song
from .parser import parse_song_list


def process_playlist_file(
    input_file: str | Path,
    workdir: str | Path = "downloads",
    archive_name: str = "songs_archive",
    min_score: float = 0.78,
    proxy_url: str | None = None,
    max_attempts: int = 5,
) -> Path:
    """Parse songs and keep trying search+download for each song until success or attempts exhausted."""
    _ = min_score  # kept for backward-compatible CLI args

    songs = parse_song_list(input_file)
    root = Path(workdir)
    root.mkdir(parents=True, exist_ok=True)

    downloads_dir = root / "songs"
    if downloads_dir.exists():
        shutil.rmtree(downloads_dir)
    downloads_dir.mkdir(parents=True, exist_ok=True)

    print(f"Обрабатываю {len(songs)} песен (мягкая валидация, до {max_attempts} попыток на песню)...")
    failed: list[str] = []
    success_count = 0

    for song in songs:
        downloaded = False
        last_error = ""

        for attempt in range(1, max_attempts + 1):
            try:
                result = search_song(song, proxy_url=proxy_url)
                download_song(result, downloads_dir, proxy_url=proxy_url)
                print(f"  [OK] {song.query} (попытка {attempt}/{max_attempts})")
                downloaded = True
                success_count += 1
                break
            except DependencyError as exc:
                raise DownloadError(str(exc)) from exc
            except DownloadError as exc:
                last_error = str(exc)
                print(f"  [WARN] {song.query}: попытка {attempt}/{max_attempts} не удалась: {exc}")
                if attempt < max_attempts:
                    time.sleep(1)

        if not downloaded:
            failed.append(f"{song.query}: {last_error}")

    if success_count == 0:
        joined = "\n".join(failed)
        raise DownloadError("Не удалось скачать ни одной песни.\n" + joined)

    archive_base = root / archive_name
    archive_path = Path(shutil.make_archive(str(archive_base), "zip", downloads_dir))

    if failed:
        print("\nВнимание: некоторые песни не скачались:")
        for row in failed:
            print(f"  - {row}")

    return archive_path
