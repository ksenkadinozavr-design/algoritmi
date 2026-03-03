import importlib

import pytest

from song_archiver.downloader import DownloadError, _load_youtube_dl


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
