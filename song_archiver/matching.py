from __future__ import annotations

import re
from difflib import SequenceMatcher

from .models import SongRequest


def _normalize(value: str) -> str:
    lowered = value.lower()
    lowered = re.sub(r"\([^)]*\)", "", lowered)
    lowered = re.sub(r"\[[^]]*\]", "", lowered)
    lowered = re.sub(r"[^a-zа-я0-9]+", " ", lowered, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", lowered).strip()


def similarity_score(song: SongRequest, candidate_title: str, candidate_uploader: str = "") -> float:
    """Return score from 0 to 1 where higher means better match."""

    query = _normalize(song.query)
    title = _normalize(candidate_title)
    uploader = _normalize(candidate_uploader)

    title_ratio = SequenceMatcher(None, query, title).ratio()
    group_ratio = SequenceMatcher(None, _normalize(song.group), f"{title} {uploader}".strip()).ratio()

    bonus = 0.0
    if _normalize(song.group) in title:
        bonus += 0.1
    if _normalize(song.title) in title:
        bonus += 0.1

    return min(1.0, 0.75 * title_ratio + 0.25 * group_ratio + bonus)
