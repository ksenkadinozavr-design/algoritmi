import importlib

import pytest

from song_archiver.downloader import DownloadError, _build_ydl_options, _load_youtube_dl
from song_archiver.models import SongRequest


def test_load_youtube_dl_returns_class_when_available() -> None:
    try:
        youtube_dl = _load_youtube_dl()
    except DownloadError:
        pytest.skip("yt_dlp is not installed in this environment")
    assert youtube_dl is not None


def test_load_youtube_dl_raises_friendly_error_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    real_import_module = importlib.import_module

    def fake_import_module(name: str):
        if name == "yt_dlp":
            raise ModuleNotFoundError("No module named 'yt_dlp'")
        return real_import_module(name)

    monkeypatch.setattr(importlib, "import_module", fake_import_module)

    with pytest.raises(DownloadError, match="Не установлен пакет 'yt-dlp'"):
        _load_youtube_dl()


def test_build_ydl_options_adds_proxy() -> None:
    opts = _build_ydl_options(base={"quiet": True}, proxy_url="http://user:pass@127.0.0.1:8080")
    assert opts["proxy"] == "http://user:pass@127.0.0.1:8080"


def test_song_request_can_be_without_source_url_for_search_fallback() -> None:
    song = SongRequest(group="Kino", title="Gruppa Krovi")
    assert song.source_url is None


def test_search_song_rejects_youtube_source_url() -> None:
    with pytest.raises(DownloadError, match="YouTube-ссылки отключены"):
        from song_archiver.downloader import search_song

        search_song(SongRequest(group="A", title="B", source_url="https://youtube.com/watch?v=1"))
