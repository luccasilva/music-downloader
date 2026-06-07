"""Casa uma faixa do Spotify com o melhor vídeo do YouTube (por duração)."""

from __future__ import annotations

from dataclasses import dataclass

import yt_dlp

from .spotify import SpotifyTrack

_TOLERANCE_S = 7


@dataclass(frozen=True)
class Candidate:
    url: str
    title: str
    duration: int  # segundos


def best_match(
    duration_ms: int, candidates: list[Candidate], tolerance_s: int = _TOLERANCE_S
) -> Candidate | None:
    if not candidates:
        return None
    target = duration_ms / 1000
    best = min(candidates, key=lambda c: abs(c.duration - target))
    return best if abs(best.duration - target) <= tolerance_s else None


def search_youtube(query: str, n: int = 5) -> list[Candidate]:
    opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": "in_playlist",
        "skip_download": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(f"ytsearch{n}:{query}", download=False)
    candidates: list[Candidate] = []
    for entry in (info or {}).get("entries", []) or []:
        if not entry:
            continue
        duration = entry.get("duration")
        vid = entry.get("id")
        if duration is None or not vid:
            continue
        candidates.append(
            Candidate(
                url=f"https://www.youtube.com/watch?v={vid}",
                title=entry.get("title", ""),
                duration=int(duration),
            )
        )
    return candidates


def find_youtube(track: SpotifyTrack, n: int = 5) -> str | None:
    candidates = search_youtube(track.search_query(), n)
    match = best_match(track.duration_ms, candidates)
    return match.url if match else None
