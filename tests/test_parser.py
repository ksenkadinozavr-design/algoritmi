from pathlib import Path

import pytest

from song_archiver.parser import ParseError, parse_song_list


def test_parse_mixed_formats(tmp_path: Path) -> None:
    input_file = tmp_path / "songs.txt"
    input_file.write_text("[A]\nSong1\nGroup: B\n- Song2\nC - Song3\n", encoding="utf-8")

    songs = parse_song_list(input_file)

    assert [(s.group, s.title) for s in songs] == [
        ("A", "Song1"),
        ("B", "Song2"),
        ("C", "Song3"),
    ]


def test_parse_lines_with_direct_urls(tmp_path: Path) -> None:
    input_file = tmp_path / "songs_urls.txt"
    input_file.write_text(
        "[Kino]\n"
        "Gruppa Krovi | https://example.com/track1\n"
        "DDT - Rodina | https://example.com/track2\n",
        encoding="utf-8",
    )

    songs = parse_song_list(input_file)

    assert songs[0].group == "Kino"
    assert songs[0].title == "Gruppa Krovi"
    assert songs[0].source_url == "https://example.com/track1"
    assert songs[1].group == "DDT"
    assert songs[1].title == "Rodina"
    assert songs[1].source_url == "https://example.com/track2"


def test_parse_error_without_group(tmp_path: Path) -> None:
    input_file = tmp_path / "bad.txt"
    input_file.write_text("Song without group\n", encoding="utf-8")

    with pytest.raises(ParseError):
        parse_song_list(input_file)
