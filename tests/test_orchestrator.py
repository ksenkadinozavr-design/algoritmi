from pathlib import Path

from song_archiver import orchestrator
from song_archiver.models import SearchResult, SongRequest


def test_process_playlist_retries_until_success(tmp_path: Path, monkeypatch) -> None:
    input_file = tmp_path / "songs.txt"
    input_file.write_text("[A]\nSong1 | https://example.com/t1\n", encoding="utf-8")

    calls = {"search": 0, "download": 0}

    def fake_search(
        song: SongRequest, proxy_url: str | None = None, search_providers: tuple[str, ...] = ()
    ) -> SearchResult:
        calls["search"] += 1
        return SearchResult(song=song, video_id=song.source_url or "", video_title=song.title, uploader=song.group, duration_seconds=None, score=1)

    def fake_download(result: SearchResult, output_dir: Path, proxy_url: str | None = None) -> Path:
        calls["download"] += 1
        if calls["download"] < 3:
            raise orchestrator.DownloadError("temporary")
        out = output_dir / "A"
        out.mkdir(parents=True, exist_ok=True)
        file = out / "Song1.mp3"
        file.write_bytes(b"ok")
        return file

    monkeypatch.setattr(orchestrator, "search_song", fake_search)
    monkeypatch.setattr(orchestrator, "download_song", fake_download)

    archive = orchestrator.process_playlist_file(input_file=input_file, workdir=tmp_path, max_attempts=5)

    assert archive.exists()
    assert calls["download"] == 3
