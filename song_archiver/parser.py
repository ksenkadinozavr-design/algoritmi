from __future__ import annotations

from pathlib import Path

from .models import SongRequest


class ParseError(ValueError):
    pass


def parse_song_list(path: str | Path) -> list[SongRequest]:
    """Parse text file with groups and song titles.

    Supported formats:
    1) [Group Name]\nSong 1\nSong 2
    2) Group: Group Name\n- Song 1\n- Song 2
    3) Group Name - Song Title (single line)
    """

    file_path = Path(path)
    if not file_path.exists():
        raise ParseError(f"Файл не найден: {file_path}")

    songs: list[SongRequest] = []
    current_group: str | None = None

    for line_no, raw in enumerate(file_path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith("[") and line.endswith("]") and len(line) > 2:
            current_group = line[1:-1].strip()
            if not current_group:
                raise ParseError(f"Пустое имя группы в строке {line_no}")
            continue

        if line.lower().startswith("group:"):
            current_group = line.split(":", 1)[1].strip()
            if not current_group:
                raise ParseError(f"После 'Group:' должно быть имя группы (строка {line_no})")
            continue

        cleaned = line.removeprefix("-").strip()

        if " - " in cleaned and not line.startswith("-"):
            group, title = [item.strip() for item in cleaned.split(" - ", 1)]
            if group and title:
                songs.append(SongRequest(group=group, title=title))
                continue

        if current_group is None:
            raise ParseError(
                f"Строка {line_no} не относится к группе. Используйте [Group], Group: или формат 'Group - Song'."
            )

        if not cleaned:
            raise ParseError(f"Пустое название песни в строке {line_no}")

        songs.append(SongRequest(group=current_group, title=cleaned))

    if not songs:
        raise ParseError("В файле не найдено ни одной песни")

    return songs
