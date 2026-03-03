import pytest

from music_archiver.parser import ParseError, parse_song_file


def test_parse_valid_content():
    content = """
[Group A]
Artist 1 - Song 1
Artist 2 - Song 2

[Group B]
Artist 3 - Song 3
"""
    songs = parse_song_file(content)
    assert len(songs) == 3
    assert songs[0].group == "Group A"
    assert songs[2].group == "Group B"


def test_parse_rejects_song_without_group():
    with pytest.raises(ParseError):
        parse_song_file("Artist - Song")


def test_parse_rejects_invalid_song_format():
    with pytest.raises(ParseError):
        parse_song_file("[X]\nArtist: Song")
