"""Resolução de links do Spotify em faixas (metadados via spotipy)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlparse

_SPOTIFY_HOSTS = {"open.spotify.com"}
_KINDS = ("track", "album", "playlist")


def is_spotify_url(url: str) -> bool:
    if url.startswith("spotify:"):
        return True
    host = (urlparse(url).hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host in _SPOTIFY_HOSTS


def _resource_type(url: str) -> str:
    for kind in _KINDS:
        if f"/{kind}/" in url or url.startswith(f"spotify:{kind}:"):
            return kind
    raise ValueError(
        f"URL de Spotify não suportada: {url!r} (use track, album ou playlist)"
    )


class MissingCredentialsError(Exception):
    """Faltam credenciais do Spotify nas variáveis de ambiente."""


@dataclass(frozen=True)
class SpotifyTrack:
    title: str
    artists: tuple[str, ...]
    album: str
    release_date: str
    track_number: int
    total_tracks: int
    disc_number: int
    duration_ms: int
    isrc: str | None
    cover_url: str | None

    def search_query(self) -> str:
        return f"{' '.join(self.artists)} {self.title}"

    def display(self) -> str:
        return f"{', '.join(self.artists)} - {self.title}"


def _largest_cover(images: list | None) -> str | None:
    if not images:
        return None
    return max(images, key=lambda im: im.get("width") or 0).get("url")


def _track_from_full(obj: dict) -> SpotifyTrack:
    album = obj.get("album") or {}
    return SpotifyTrack(
        title=obj.get("name", ""),
        artists=tuple(a.get("name", "") for a in obj.get("artists", [])),
        album=album.get("name", ""),
        release_date=album.get("release_date", ""),
        track_number=obj.get("track_number", 0),
        total_tracks=album.get("total_tracks", 0),
        disc_number=obj.get("disc_number", 1),
        duration_ms=obj.get("duration_ms", 0),
        isrc=(obj.get("external_ids") or {}).get("isrc"),
        cover_url=_largest_cover(album.get("images")),
    )


def _track_from_album_item(item: dict, album: dict) -> SpotifyTrack:
    return SpotifyTrack(
        title=item.get("name", ""),
        artists=tuple(a.get("name", "") for a in item.get("artists", [])),
        album=album.get("name", ""),
        release_date=album.get("release_date", ""),
        track_number=item.get("track_number", 0),
        total_tracks=album.get("total_tracks", 0),
        disc_number=item.get("disc_number", 1),
        duration_ms=item.get("duration_ms", 0),
        isrc=(item.get("external_ids") or {}).get("isrc"),
        cover_url=_largest_cover(album.get("images")),
    )


class SpotifyClient:
    def __init__(self, sp):
        self._sp = sp

    @classmethod
    def from_env(cls, env: dict | None = None) -> "SpotifyClient":
        env = env if env is not None else os.environ
        cid = env.get("SPOTIFY_CLIENT_ID")
        secret = env.get("SPOTIFY_CLIENT_SECRET")
        if not cid or not secret:
            raise MissingCredentialsError(
                "Credenciais do Spotify ausentes. Crie um app gratuito em "
                "https://developer.spotify.com/dashboard e defina as variáveis "
                "de ambiente SPOTIFY_CLIENT_ID e SPOTIFY_CLIENT_SECRET."
            )
        import spotipy
        from spotipy.oauth2 import SpotifyClientCredentials

        sp = spotipy.Spotify(
            auth_manager=SpotifyClientCredentials(
                client_id=cid, client_secret=secret
            )
        )
        return cls(sp)

    def resolve(self, url: str) -> list[SpotifyTrack]:
        kind = _resource_type(url)
        if kind == "track":
            return [_track_from_full(self._sp.track(url))]
        if kind == "album":
            album = self._sp.album(url)
            results = album.get("tracks", {}) or {}
            items = list(results.get("items", []))
            while results.get("next"):
                results = self._sp.next(results)
                items.extend(results.get("items", []))
            return [_track_from_album_item(it, album) for it in items]
        # playlist
        results = self._sp.playlist_items(url, additional_types=("track",))
        items = list(results.get("items", []))
        while results.get("next"):
            results = self._sp.next(results)
            items.extend(results.get("items", []))
        out: list[SpotifyTrack] = []
        for it in items:
            track = it.get("track")
            if track:
                out.append(_track_from_full(track))
        return out
