"""Aplica metadados e capa do Spotify nos arquivos baixados (via mutagen)."""

from __future__ import annotations

import urllib.request
from pathlib import Path

from .spotify import SpotifyTrack


def _fetch_cover(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=30) as resp:
        return resp.read()


def apply(track: SpotifyTrack, filepaths: list[str]) -> None:
    cover = _fetch_cover(track.cover_url) if track.cover_url else None
    for filepath in filepaths:
        suffix = Path(filepath).suffix.lower()
        if suffix == ".mp3":
            _tag_mp3(filepath, track, cover)
        elif suffix == ".flac":
            _tag_flac(filepath, track, cover)


def _tag_mp3(filepath: str, track: SpotifyTrack, cover: bytes | None) -> None:
    from mutagen.id3 import (
        APIC, ID3, TALB, TDRC, TIT2, TPE1, TPOS, TRCK, TSRC, ID3NoHeaderError,
    )

    try:
        tags = ID3(filepath)
    except ID3NoHeaderError:
        tags = ID3()
    tags.setall("TIT2", [TIT2(encoding=3, text=track.title)])
    tags.setall("TPE1", [TPE1(encoding=3, text=", ".join(track.artists))])
    tags.setall("TALB", [TALB(encoding=3, text=track.album)])
    tags.setall("TRCK", [TRCK(encoding=3, text=f"{track.track_number}/{track.total_tracks}")])
    tags.setall("TPOS", [TPOS(encoding=3, text=str(track.disc_number))])
    if track.release_date:
        tags.setall("TDRC", [TDRC(encoding=3, text=track.release_date)])
    if track.isrc:
        tags.setall("TSRC", [TSRC(encoding=3, text=track.isrc)])
    if cover:
        tags.delall("APIC")
        tags.add(APIC(encoding=3, mime="image/jpeg", type=3, desc="Cover", data=cover))
    tags.save(filepath)


def _tag_flac(filepath: str, track: SpotifyTrack, cover: bytes | None) -> None:
    from mutagen.flac import FLAC, Picture

    audio = FLAC(filepath)
    audio["title"] = track.title
    audio["artist"] = list(track.artists)
    audio["album"] = track.album
    audio["tracknumber"] = str(track.track_number)
    audio["totaltracks"] = str(track.total_tracks)
    audio["discnumber"] = str(track.disc_number)
    if track.release_date:
        audio["date"] = track.release_date
    if track.isrc:
        audio["isrc"] = track.isrc
    if cover:
        picture = Picture()
        picture.type = 3  # front cover
        picture.mime = "image/jpeg"
        picture.data = cover
        audio.clear_pictures()
        audio.add_picture(picture)
    audio.save()
