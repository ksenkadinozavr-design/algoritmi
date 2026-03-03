from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class SongRequest:
    group: str
    artist: str
    title: str


class ParseError(ValueError):
    """Raised when input file format is invalid."""


def parse_song_file(content: str) -> List[SongRequest]:
    """Parse song list from text content.

    Strict format:
    [Group Name]
    Artist - Song title

    Empty lines are allowed between entries.
    """
    current_group: str | None = None
    items: list[SongRequest] = []

    for line_no, raw_line in enumerate(content.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue

        if line.startswith("[") and line.endswith("]"):
            group_name = line[1:-1].strip()
            if not group_name:
                raise ParseError(f"Line {line_no}: group name cannot be empty")
            current_group = group_name
            continue

        if current_group is None:
            raise ParseError(
                f"Line {line_no}: song entry must be inside a group header [Group]"
            )

        if " - " not in line:
            raise ParseError(
                f"Line {line_no}: song must be in format 'Artist - Title'"
            )

        artist, title = line.split(" - ", 1)
        artist = artist.strip()
        title = title.strip()

        if not artist or not title:
            raise ParseError(
                f"Line {line_no}: both artist and title must be non-empty"
            )

        items.append(SongRequest(group=current_group, artist=artist, title=title))

    if not items:
        raise ParseError("File contains no songs")

    return items
