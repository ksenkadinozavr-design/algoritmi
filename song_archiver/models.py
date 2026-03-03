from dataclasses import dataclass


@dataclass(slots=True)
class SongRequest:
    group: str
    title: str

    @property
    def query(self) -> str:
        return f"{self.group} {self.title}".strip()


@dataclass(slots=True)
class SearchResult:
    song: SongRequest
    video_id: str
    video_title: str
    uploader: str
    duration_seconds: int | None
    score: float
