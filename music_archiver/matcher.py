from __future__ import annotations

from dataclasses import dataclass

from rapidfuzz import fuzz
import yt_dlp

from .parser import SongRequest


@dataclass(frozen=True)
class MatchResult:
    request: SongRequest
    url: str | None
    score: int
    found_title: str | None


class SearchError(RuntimeError):
    """Raised when search fails unexpectedly."""


def _score_candidate(song: SongRequest, candidate: dict) -> int:
    candidate_title = candidate.get("title", "")
    candidate_uploader = candidate.get("uploader", "")

    expected = f"{song.artist} {song.title}".lower()
    actual = f"{candidate_uploader} {candidate_title}".lower()

    return int(fuzz.token_set_ratio(expected, actual))


def find_best_match(song: SongRequest, min_score: int = 75) -> MatchResult:
    query = f"{song.artist} - {song.title}"
    ydl_opts = {
        "quiet": True,
        "skip_download": True,
        "extract_flat": False,
        "noplaylist": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch10:{query}", download=False)
    except Exception as exc:  # noqa: BLE001
        raise SearchError(f"Search failed for '{query}': {exc}") from exc

    entries = (info or {}).get("entries") or []
    best_score = -1
    best_entry: dict | None = None

    for entry in entries:
        score = _score_candidate(song, entry)
        if score > best_score:
            best_score = score
            best_entry = entry

    if best_entry is None or best_score < min_score:
        return MatchResult(
            request=song,
            url=None,
            score=max(0, best_score),
            found_title=best_entry.get("title") if best_entry else None,
        )

    return MatchResult(
        request=song,
        url=best_entry.get("webpage_url") or best_entry.get("url"),
        score=best_score,
        found_title=best_entry.get("title"),
    )
