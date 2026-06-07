# Spotify Resolver Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Suportar links do Spotify (faixa/álbum/playlist) resolvendo a identidade da faixa via Spotify, baixando o áudio equivalente do YouTube (match por duração) e embutindo os metadados + capa do Spotify.

**Architecture:** Spotify é um **resolver**, não um provider: `spotify.py` resolve a URL em `SpotifyTrack`s (via `spotipy`, credenciais por env); `matching.py` acha o vídeo do YouTube por proximidade de duração; o core baixa pelo fluxo YouTube existente e `tagging.py` re-taggea o arquivo com os dados do Spotify. YouTube/SoundCloud ficam intactos.

**Tech Stack:** Python 3.12, spotipy, yt-dlp, mutagen, ffmpeg, pytest.

---

## File Structure

```
src/music_downloader/
  spotify.py     # NOVO: is_spotify_url, SpotifyTrack, MissingCredentialsError, SpotifyClient (env+resolve)
  matching.py    # NOVO: Candidate, best_match (puro), search_youtube, find_youtube
  tagging.py     # NOVO: apply (mutagen: metadados + capa do Spotify em mp3/flac)
  core.py        # MOD: _run_download (refactor), _final_filepath, _download_spotify, desvio is_spotify_url
  cli.py         # MOD: captura MissingCredentialsError
  pyproject.toml # MOD: dep spotipy
  (downloader.py, formats.py, naming.py, providers.py inalterados)
tests/
  test_spotify.py     # NOVO
  test_matching.py    # NOVO
  test_tagging.py     # NOVO (usa ffmpeg p/ gerar áudio de teste)
  test_core.py        # MOD: +fluxo Spotify
  test_cli.py         # MOD: +erro de credenciais
  test_integration.py # MOD: +Spotify (marcado, precisa creds)
```

**Comando do venv (Windows):** sempre `.\.venv\Scripts\python.exe -m pytest ...`.

---

## Task 1: Dependência spotipy

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Instalar spotipy no venv**

Run:
```powershell
.\.venv\Scripts\python.exe -m pip install spotipy
.\.venv\Scripts\python.exe -m pip show spotipy | Select-String Version
```
Expected: instala; imprime a versão.

- [ ] **Step 2: Adicionar spotipy às dependências**

In `pyproject.toml`, change:
```toml
dependencies = ["yt-dlp", "mutagen"]
```
to:
```toml
dependencies = ["yt-dlp", "mutagen", "spotipy"]
```

- [ ] **Step 3: Confirmar import e suíte atual**

Run:
```powershell
.\.venv\Scripts\python.exe -c "import spotipy; print('spotipy ok')"
.\.venv\Scripts\python.exe -m pytest -q
```
Expected: "spotipy ok"; 52 passed, integração deselected.

- [ ] **Step 4: Commit**

```powershell
git add pyproject.toml
git commit -m "chore: add spotipy dependency"
```

---

## Task 2: Módulo Spotify (`spotify.py`)

**Files:**
- Create: `src/music_downloader/spotify.py`
- Test: `tests/test_spotify.py`

- [ ] **Step 1: Escrever os testes que falham**

Create `tests/test_spotify.py`:
```python
import pytest

from music_downloader.spotify import (
    MissingCredentialsError,
    SpotifyClient,
    SpotifyTrack,
    is_spotify_url,
)


def test_is_spotify_url_detects_track_album_playlist():
    assert is_spotify_url("https://open.spotify.com/track/abc") is True
    assert is_spotify_url("https://open.spotify.com/album/abc") is True
    assert is_spotify_url("https://open.spotify.com/playlist/abc") is True
    assert is_spotify_url("spotify:track:abc") is True
    assert is_spotify_url("https://spotify.link/abc") is True


def test_is_spotify_url_rejects_others():
    assert is_spotify_url("https://youtu.be/abc") is False
    assert is_spotify_url("https://soundcloud.com/a/b") is False


def test_track_query_and_display():
    t = SpotifyTrack(
        title="Song", artists=("Artist A", "Artist B"), album="Al",
        release_date="2020-01-01", track_number=3, total_tracks=12,
        disc_number=1, duration_ms=200000, isrc="X", cover_url=None,
    )
    assert t.search_query() == "Artist A Artist B Song"
    assert t.display() == "Artist A, Artist B - Song"


def test_from_env_missing_credentials_raises(monkeypatch):
    with pytest.raises(MissingCredentialsError, match="SPOTIFY_CLIENT_ID"):
        SpotifyClient.from_env({})


def test_from_env_builds_client_when_present():
    client = SpotifyClient.from_env(
        {"SPOTIFY_CLIENT_ID": "x", "SPOTIFY_CLIENT_SECRET": "y"}
    )
    assert isinstance(client, SpotifyClient)


class _FakeSp:
    def __init__(self, *, track=None, album=None, album_tracks=None, playlist=None):
        self._track = track
        self._album = album
        self._album_tracks = album_tracks
        self._playlist = playlist

    def track(self, url):
        return self._track

    def album(self, url):
        return self._album

    def playlist_items(self, url):
        return self._playlist

    def next(self, result):
        return {"items": [], "next": None}


def test_resolve_track():
    sp = _FakeSp(track={
        "name": "Song",
        "artists": [{"name": "A"}],
        "album": {
            "name": "Al", "release_date": "2020", "total_tracks": 10,
            "images": [{"url": "small", "width": 64}, {"url": "big", "width": 640}],
        },
        "track_number": 2, "disc_number": 1, "duration_ms": 180000,
        "external_ids": {"isrc": "ZZ123"},
    })
    [t] = SpotifyClient(sp).resolve("https://open.spotify.com/track/abc")
    assert t.title == "Song"
    assert t.artists == ("A",)
    assert t.album == "Al"
    assert t.duration_ms == 180000
    assert t.isrc == "ZZ123"
    assert t.cover_url == "big"  # maior resolução


def test_resolve_album_injects_album_cover_and_name():
    album = {
        "name": "Al", "release_date": "2019", "total_tracks": 2,
        "images": [{"url": "cover", "width": 640}],
        "tracks": {
            "items": [
                {"name": "T1", "artists": [{"name": "A"}], "track_number": 1,
                 "disc_number": 1, "duration_ms": 100000},
                {"name": "T2", "artists": [{"name": "A"}], "track_number": 2,
                 "disc_number": 1, "duration_ms": 110000},
            ],
            "next": None,
        },
    }
    tracks = SpotifyClient(_FakeSp(album=album)).resolve("https://open.spotify.com/album/abc")
    assert [t.title for t in tracks] == ["T1", "T2"]
    assert all(t.album == "Al" and t.cover_url == "cover" for t in tracks)
    assert tracks[0].total_tracks == 2


def test_resolve_playlist():
    playlist = {
        "items": [
            {"track": {
                "name": "P1", "artists": [{"name": "B"}],
                "album": {"name": "Alb", "release_date": "2021", "total_tracks": 5,
                          "images": [{"url": "c", "width": 300}]},
                "track_number": 1, "disc_number": 1, "duration_ms": 90000,
                "external_ids": {"isrc": "I"},
            }},
        ],
        "next": None,
    }
    tracks = SpotifyClient(_FakeSp(playlist=playlist)).resolve(
        "https://open.spotify.com/playlist/abc"
    )
    assert [t.title for t in tracks] == ["P1"]
    assert tracks[0].album == "Alb"
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_spotify.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'music_downloader.spotify'`.

- [ ] **Step 3: Implementar `spotify.py`**

Create `src/music_downloader/spotify.py`:
```python
"""Resolução de links do Spotify em faixas (metadados via spotipy)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlparse

_SPOTIFY_HOSTS = {"open.spotify.com", "spotify.link"}
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
        artists=tuple(a["name"] for a in obj.get("artists", [])),
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
        artists=tuple(a["name"] for a in item.get("artists", [])),
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
        results = self._sp.playlist_items(url)
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
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_spotify.py -v`
Expected: 8 passed.

- [ ] **Step 5: Commit**

```powershell
git add src/music_downloader/spotify.py tests/test_spotify.py
git commit -m "feat: Spotify URL detection and metadata resolution"
```

---

## Task 3: Matching com o YouTube (`matching.py`)

**Files:**
- Create: `src/music_downloader/matching.py`
- Test: `tests/test_matching.py`

- [ ] **Step 1: Escrever os testes que falham**

Create `tests/test_matching.py`:
```python
import music_downloader.matching as matching
from music_downloader.matching import Candidate, best_match, find_youtube
from music_downloader.spotify import SpotifyTrack


def _track(duration_ms):
    return SpotifyTrack(
        title="Song", artists=("A",), album="Al", release_date="2020",
        track_number=1, total_tracks=1, disc_number=1,
        duration_ms=duration_ms, isrc=None, cover_url=None,
    )


def test_best_match_picks_closest_duration():
    cands = [
        Candidate(url="u1", title="t1", duration=100),
        Candidate(url="u2", title="t2", duration=182),
        Candidate(url="u3", title="t3", duration=250),
    ]
    m = best_match(180000, cands)  # 180s
    assert m.url == "u2"


def test_best_match_returns_none_when_all_out_of_tolerance():
    cands = [Candidate(url="u1", title="t1", duration=100)]
    assert best_match(180000, cands) is None  # 80s de diferença


def test_best_match_empty_is_none():
    assert best_match(180000, []) is None


def test_find_youtube_uses_best_match(monkeypatch):
    cands = [
        Candidate(url="https://youtu.be/right", title="t", duration=181),
        Candidate(url="https://youtu.be/wrong", title="t", duration=300),
    ]
    monkeypatch.setattr(matching, "search_youtube", lambda query, n=5: cands)
    assert find_youtube(_track(180000)) == "https://youtu.be/right"


def test_find_youtube_returns_none_without_good_match(monkeypatch):
    monkeypatch.setattr(matching, "search_youtube", lambda query, n=5: [])
    assert find_youtube(_track(180000)) is None
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_matching.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'music_downloader.matching'`.

- [ ] **Step 3: Implementar `matching.py`**

Create `src/music_downloader/matching.py`:
```python
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
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_matching.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```powershell
git add src/music_downloader/matching.py tests/test_matching.py
git commit -m "feat: YouTube matching by duration for Spotify tracks"
```

---

## Task 4: Tagging com metadados do Spotify (`tagging.py`)

**Files:**
- Create: `src/music_downloader/tagging.py`
- Test: `tests/test_tagging.py`

- [ ] **Step 1: Escrever os testes que falham**

Create `tests/test_tagging.py`:
```python
import subprocess

import pytest

import music_downloader.tagging as tagging
from music_downloader.spotify import SpotifyTrack

_FFMPEG = r"C:\ffmpeg\ffmpeg.exe"


def _make_audio(path: str) -> None:
    subprocess.run(
        [_FFMPEG, "-y", "-f", "lavfi", "-i",
         "sine=frequency=440:duration=1", path],
        check=True, capture_output=True,
    )


def _track():
    return SpotifyTrack(
        title="My Song", artists=("Artist A", "Artist B"), album="My Album",
        release_date="2020-05-01", track_number=3, total_tracks=12,
        disc_number=1, duration_ms=1000, isrc="ZZ", cover_url="http://x/cover.jpg",
    )


def test_apply_writes_mp3_tags_and_cover(monkeypatch, tmp_path):
    monkeypatch.setattr(tagging, "_fetch_cover", lambda url: b"\xff\xd8\xffFAKEJPEG")
    mp3 = str(tmp_path / "song.mp3")
    _make_audio(mp3)

    tagging.apply(_track(), [mp3])

    from mutagen.id3 import ID3
    tags = ID3(mp3)
    assert tags.getall("TIT2")[0].text[0] == "My Song"
    assert tags.getall("TPE1")[0].text[0] == "Artist A, Artist B"
    assert tags.getall("TALB")[0].text[0] == "My Album"
    assert tags.getall("APIC"), "deveria ter capa embutida"


def test_apply_writes_flac_tags_and_cover(monkeypatch, tmp_path):
    monkeypatch.setattr(tagging, "_fetch_cover", lambda url: b"\xff\xd8\xffFAKEJPEG")
    flac = str(tmp_path / "song.flac")
    _make_audio(flac)

    tagging.apply(_track(), [flac])

    from mutagen.flac import FLAC
    audio = FLAC(flac)
    assert audio["title"][0] == "My Song"
    assert audio["artist"] == ["Artist A", "Artist B"]
    assert audio["album"][0] == "My Album"
    assert audio.pictures, "deveria ter capa embutida"


def test_apply_without_cover_url_skips_picture(monkeypatch, tmp_path):
    called = []
    monkeypatch.setattr(tagging, "_fetch_cover", lambda url: called.append(url) or b"")
    mp3 = str(tmp_path / "song.mp3")
    _make_audio(mp3)
    track = _track()
    object.__setattr__(track, "cover_url", None)

    tagging.apply(track, [mp3])

    from mutagen.id3 import ID3
    tags = ID3(mp3)
    assert tags.getall("TIT2")[0].text[0] == "My Song"
    assert not tags.getall("APIC")
    assert called == []  # não tentou baixar capa
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_tagging.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'music_downloader.tagging'`.

- [ ] **Step 3: Implementar `tagging.py`**

Create `src/music_downloader/tagging.py`:
```python
"""Aplica metadados e capa do Spotify nos arquivos baixados (via mutagen)."""

from __future__ import annotations

import urllib.request
from pathlib import Path

from .spotify import SpotifyTrack


def _fetch_cover(url: str) -> bytes:
    with urllib.request.urlopen(url) as resp:
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
        APIC, ID3, TALB, TDRC, TIT2, TPE1, TPOS, TRCK, ID3NoHeaderError,
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
    if cover:
        picture = Picture()
        picture.type = 3  # front cover
        picture.mime = "image/jpeg"
        picture.data = cover
        audio.clear_pictures()
        audio.add_picture(picture)
    audio.save()
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_tagging.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```powershell
git add src/music_downloader/tagging.py tests/test_tagging.py
git commit -m "feat: embed Spotify metadata and cover via mutagen"
```

---

## Task 5: Integração no core (desvio Spotify)

**Files:**
- Modify: `src/music_downloader/core.py`
- Modify: `tests/test_core.py`

- [ ] **Step 1: Escrever os testes que falham (append em `tests/test_core.py`)**

Append to `tests/test_core.py`:
```python
from music_downloader.spotify import MissingCredentialsError, SpotifyTrack


def _sp_track(duration_ms=180000, title="T", artist="A"):
    return SpotifyTrack(
        title=title, artists=(artist,), album="Al", release_date="2020",
        track_number=1, total_tracks=1, disc_number=1,
        duration_ms=duration_ms, isrc=None, cover_url=None,
    )


def test_download_spotify_resolves_matches_downloads_and_tags(monkeypatch, tmp_path):
    track = _sp_track()

    class _FakeClient:
        @classmethod
        def from_env(cls):
            return cls()

        def resolve(self, url):
            return [track]

    monkeypatch.setattr(core_mod, "SpotifyClient", _FakeClient)
    monkeypatch.setattr(core_mod, "find_youtube", lambda t: "https://www.youtube.com/watch?v=x")
    tagged = []
    monkeypatch.setattr(core_mod, "apply_tags", lambda t, paths: tagged.append((t, paths)))
    _patch_ydl(monkeypatch, {
        "title": "yt title",
        "requested_downloads": [{"filepath": str(tmp_path / "A - T.mp3")}],
    })

    summary = download(
        "https://open.spotify.com/track/abc", str(tmp_path), "mp3",
        ffmpeg_location=r"C:\ffmpeg\ffmpeg.exe",
    )
    assert summary.succeeded == ["A - T"]
    assert tagged and tagged[0][1] == [str(tmp_path / "A - T.mp3")]


def test_download_spotify_no_match_is_failure(monkeypatch, tmp_path):
    class _FakeClient:
        @classmethod
        def from_env(cls):
            return cls()

        def resolve(self, url):
            return [_sp_track(title="NoMatch")]

    monkeypatch.setattr(core_mod, "SpotifyClient", _FakeClient)
    monkeypatch.setattr(core_mod, "find_youtube", lambda t: None)
    _patch_ydl(monkeypatch, {"title": "x"})

    summary = download(
        "https://open.spotify.com/track/abc", str(tmp_path), "mp3",
        ffmpeg_location=r"C:\ffmpeg\ffmpeg.exe",
    )
    assert summary.succeeded == []
    assert summary.failed and "NoMatch" in summary.failed[0]


def test_download_spotify_missing_credentials_propagates(monkeypatch, tmp_path):
    class _FakeClient:
        @classmethod
        def from_env(cls):
            raise MissingCredentialsError("faltam credenciais")

    monkeypatch.setattr(core_mod, "SpotifyClient", _FakeClient)
    import pytest
    with pytest.raises(MissingCredentialsError):
        download(
            "https://open.spotify.com/track/abc", str(tmp_path), "mp3",
            ffmpeg_location=r"C:\ffmpeg\ffmpeg.exe",
        )
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_core.py -k spotify -v`
Expected: FAIL (download trata URL do Spotify como provider desconhecido → ValueError; e core não tem SpotifyClient/find_youtube/apply_tags).

- [ ] **Step 3: Reescrever `core.py`**

REPLACE the ENTIRE contents of `src/music_downloader/core.py` with exactly:
```python
"""Orquestração do download: roteamento por provedor/resolver, execução e resumo."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yt_dlp
from yt_dlp.utils import DownloadError

from .downloader import build_ydl_options, find_ffmpeg
from .formats import get_format
from .matching import find_youtube
from .providers import AuthConfig, detect_provider
from .spotify import SpotifyClient, is_spotify_url
from .tagging import apply as apply_tags


@dataclass
class DownloadSummary:
    succeeded: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return bool(self.succeeded) and not self.failed

    def report(self) -> str:
        lines = [f"Baixadas: {len(self.succeeded)}"]
        lines += [f"  + {t}" for t in self.succeeded]
        if self.failed:
            lines.append(f"Falharam: {len(self.failed)}")
            lines += [f"  - {t}" for t in self.failed]
        return "\n".join(lines)


def _ensure_ffmpeg(path: str) -> None:
    if not Path(path).exists():
        raise FileNotFoundError(
            f"ffmpeg não encontrado em {path!r}. "
            "Instale o ffmpeg ou adicione-o ao PATH."
        )


def _collect(info: dict | None, summary: DownloadSummary) -> None:
    if info is None:
        summary.failed.append("(download falhou)")
        return
    if "entries" in info:
        for entry in info["entries"]:
            if entry is None:
                summary.failed.append("(item indisponível)")
            else:
                summary.succeeded.append(entry.get("title", "(sem título)"))
    else:
        summary.succeeded.append(info.get("title", "(sem título)"))


def _is_cookie_error(exc: Exception) -> bool:
    """True só para falhas de LEITURA/DECRIPTAÇÃO de cookies do navegador.

    Não casa erros de "login necessário" (que também citam cookies), para não
    rebaixar a qualidade silenciosamente.
    """
    msg = str(exc).lower()
    markers = (
        "dpapi",
        "decrypt",
        "could not copy",
        "failed to load cookies",
        "could not read cookie",
        "unable to read cookie",
    )
    return any(m in msg for m in markers)


def _extract(url: str, opts: dict) -> dict | None:
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=True)


def _run_download(url: str, opts: dict) -> dict | None:
    """Executa o yt-dlp com fallback se a leitura de cookies do navegador falhar."""
    try:
        return _extract(url, opts)
    except Exception as exc:  # noqa: BLE001 — só para detectar erro de cookies
        if "cookiesfrombrowser" in opts and _is_cookie_error(exc):
            print(
                f"Aviso: não consegui ler cookies do navegador ({exc}). "
                "Seguindo sem login (qualidade pública). Para máxima qualidade, "
                "exporte um cookies.txt e use --cookies CAMINHO."
            )
            opts.pop("cookiesfrombrowser", None)
            return _extract(url, opts)
        raise


def _final_filepath(info: dict | None) -> str | None:
    if not info:
        return None
    downloads = info.get("requested_downloads")
    if downloads:
        return downloads[0].get("filepath")
    return info.get("filepath")


def _download_spotify(
    url: str, output_dir: str, fmt_name: str, ffmpeg: str
) -> DownloadSummary:
    client = SpotifyClient.from_env()  # MissingCredentialsError se faltar
    tracks = client.resolve(url)
    fmt = get_format(fmt_name)
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    summary = DownloadSummary()
    for track in tracks:
        youtube_url = find_youtube(track)
        if not youtube_url:
            summary.failed.append(f"{track.display()}: sem match confiável no YouTube")
            continue
        opts = build_ydl_options(output_dir, fmt, ffmpeg, noplaylist=True)
        try:
            info = _run_download(youtube_url, opts)
        except DownloadError as exc:
            summary.failed.append(f"{track.display()}: {exc}")
            continue
        path = _final_filepath(info)
        if path:
            apply_tags(track, [path])
        summary.succeeded.append(track.display())
    return summary


def download(
    url: str,
    output_dir: str,
    fmt_name: str,
    ffmpeg_location: str | None = None,
    auth: AuthConfig | None = None,
) -> DownloadSummary:
    ffmpeg = ffmpeg_location or find_ffmpeg()
    _ensure_ffmpeg(ffmpeg)
    if is_spotify_url(url):
        return _download_spotify(url, output_dir, fmt_name, ffmpeg)
    auth = auth or AuthConfig()
    provider = detect_provider(url)  # ValueError se provedor desconhecido
    fmt = get_format(fmt_name)
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    opts = build_ydl_options(
        output_dir,
        fmt,
        ffmpeg,
        noplaylist=not provider.is_playlist(url),
        overrides=provider.ydl_overrides(auth),
    )
    summary = DownloadSummary()
    try:
        info = _run_download(url, opts)
    except DownloadError as exc:
        summary.failed.append(f"{url}: {exc}")
        return summary
    _collect(info, summary)
    return summary
```

- [ ] **Step 4: Rodar e ver passar (arquivo + suíte completa)**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_core.py -v`
Expected: 15 passed (12 antigos + 3 novos do Spotify).
Run: `.\.venv\Scripts\python.exe -m pytest -v`
Expected: tudo passa (integração deselected). Os testes de cli ainda passam porque `main` chama `download(url, output, fmt, auth=auth)` e o desvio Spotify só dispara para URLs do Spotify.

- [ ] **Step 5: Commit**

```powershell
git add src/music_downloader/core.py tests/test_core.py
git commit -m "feat: route Spotify URLs through resolver (metadata + YouTube audio)"
```

---

## Task 6: CLI, teste de integração e docs

**Files:**
- Modify: `src/music_downloader/cli.py`
- Modify: `tests/test_cli.py`
- Modify: `tests/test_integration.py`
- Modify: `README.md`

- [ ] **Step 1: Escrever o teste de CLI que falha (append em `tests/test_cli.py`)**

Append to `tests/test_cli.py`:
```python
def test_main_reports_missing_spotify_credentials_cleanly(monkeypatch, capsys):
    from music_downloader.spotify import MissingCredentialsError

    def _raise(url, output, fmt, auth):
        raise MissingCredentialsError(
            "Credenciais do Spotify ausentes. ... SPOTIFY_CLIENT_ID ..."
        )

    monkeypatch.setattr(cli_mod, "download", _raise)
    code = main(["https://open.spotify.com/track/abc"])
    assert code == 1
    assert "spotify" in capsys.readouterr().out.lower()
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_cli.py::test_main_reports_missing_spotify_credentials_cleanly -v`
Expected: FAIL (MissingCredentialsError não é capturada → propaga em vez de retornar 1).

- [ ] **Step 3: Atualizar `cli.py` para capturar `MissingCredentialsError`**

In `src/music_downloader/cli.py`, add the import after the existing `from .providers import AuthConfig` line:
```python
from .spotify import MissingCredentialsError
```
Then change the `except` clause in `main` from:
```python
    except (FileNotFoundError, ValueError) as exc:
        print(f"Erro: {exc}")
        return 1
```
to:
```python
    except (FileNotFoundError, ValueError, MissingCredentialsError) as exc:
        print(f"Erro: {exc}")
        return 1
```
Also update the `url` argument help text from:
```python
        "url", help="URL de um vídeo/faixa ou playlist (YouTube ou SoundCloud)"
```
to:
```python
        "url",
        help="URL de vídeo/faixa/playlist/álbum (YouTube, SoundCloud ou Spotify)",
```

- [ ] **Step 4: Rodar e ver passar (suíte completa)**

Run: `.\.venv\Scripts\python.exe -m pytest -v`
Expected: tudo passa (integração deselected).

- [ ] **Step 5: Smoke test real do Spotify (precisa das credenciais)**

Check whether credentials are set:
```powershell
"ID set? " + [bool]$env:SPOTIFY_CLIENT_ID; "SECRET set? " + [bool]$env:SPOTIFY_CLIENT_SECRET
```
IF both are set, run a real track download and inspect tags:
```powershell
.\.venv\Scripts\python.exe -m music_downloader.cli "https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT" -o "downloads" -f mp3
Get-ChildItem downloads
$mp3 = (Get-ChildItem downloads\*.mp3 | Select-Object -First 1).FullName
& C:\ffmpeg\ffmpeg.exe -i "$mp3" -f null - 2>&1 | Select-String -Pattern "title|artist|album|attached pic|Audio:" | Select-Object -First 15
```
VALIDATE: prints "Baixadas: 1"; the mp3 has Spotify title/artist/album + embedded cover (attached pic).

CONTINGENCY — if EVERY track reports "sem match confiável no YouTube": the flat
search (`extract_flat`) may not be returning `duration`. Fix in
`src/music_downloader/matching.py` → `search_youtube`: drop the `"extract_flat"`
option (do a full extraction) so each entry has a reliable `duration`. Re-run the
smoke test to confirm. Report this deviation if applied.

Then clean up:
```powershell
Get-ChildItem downloads -File | ForEach-Object { Remove-Item -LiteralPath $_.FullName -Force }
```
IF credentials are NOT set: report that the real smoke test was SKIPPED because `SPOTIFY_CLIENT_ID`/`SPOTIFY_CLIENT_SECRET` are not in the environment, and that the user must set them and run the command above manually. Do NOT treat this as a failure — the unit suite already covers the logic.

- [ ] **Step 6: Adicionar teste de integração do Spotify (append em `tests/test_integration.py`)**

Append to `tests/test_integration.py`:
```python
import os


@pytest.mark.integration
@pytest.mark.skipif(
    not (os.environ.get("SPOTIFY_CLIENT_ID") and os.environ.get("SPOTIFY_CLIENT_SECRET")),
    reason="precisa de SPOTIFY_CLIENT_ID/SPOTIFY_CLIENT_SECRET",
)
def test_real_spotify_track_downloads_and_tags(tmp_path):
    summary = download(
        "https://open.spotify.com/track/4cOdK2wGLETKBW3PvgPWqT",
        str(tmp_path), "mp3",
    )
    assert summary.ok
    mp3s = list(tmp_path.glob("*.mp3"))
    assert mp3s, "deveria gerar um .mp3"
    from mutagen.id3 import ID3
    tags = ID3(str(mp3s[0]))
    assert tags.getall("TIT2"), "deveria ter título do Spotify"
    assert tags.getall("APIC"), "deveria ter capa do Spotify"
```

- [ ] **Step 7: Rodar a suíte (integração roda só se houver creds)**

Run: `.\.venv\Scripts\python.exe -m pytest -v`
Expected: unit tests todos passam; integração deselected.
Run (se houver creds): `.\.venv\Scripts\python.exe -m pytest -m integration -v`
Expected: testes de integração passam (ou Spotify é skipped se sem creds).

- [ ] **Step 8: Atualizar o `README.md`**

REPLACE the ENTIRE contents of `README.md` with exactly:
```markdown
# music-downloader

CLI que baixa o melhor áudio do **YouTube**, **SoundCloud** ou **Spotify** e
converte para MP3 ou FLAC, guardando sempre o arquivo original (máxima fidelidade).
Metadados e capa são embutidos no arquivo final. Você passa só o link — o programa
detecta a fonte automaticamente.

> **Qualidade & Spotify.** O áudio do Spotify é DRM e não pode ser baixado. Para
> links do Spotify, o programa usa os **metadados do Spotify** (título, artista,
> álbum, capa) e baixa o áudio equivalente do **YouTube** (match por duração) — o
> teto de qualidade é o do YouTube (~160 kbps Opus). YouTube/SoundCloud baixam
> direto; no SoundCloud o original do artista (potencialmente lossless) sai com login.

## Requisitos

- Python 3.12+
- ffmpeg (em `C:\ffmpeg\ffmpeg.exe` ou no PATH)
- Para Spotify: credenciais (veja abaixo)

## Instalação

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
```

## Uso

```powershell
# YouTube
mdl "https://www.youtube.com/watch?v=VIDEO_ID"

# SoundCloud (FLAC; cookies do Chrome por padrão p/ máxima qualidade)
mdl "https://soundcloud.com/artista/faixa" -f flac

# Spotify (faixa, álbum ou playlist)
mdl "https://open.spotify.com/track/TRACK_ID"
mdl "https://open.spotify.com/album/ALBUM_ID" -f flac
mdl "https://open.spotify.com/playlist/PLAYLIST_ID"
```

| Opção           | Descrição                                            | Padrão       |
|-----------------|------------------------------------------------------|--------------|
| `url`           | Link do YouTube, SoundCloud ou Spotify               | (obrigatório)|
| `-f, --format`  | `mp3` ou `flac`                                      | `mp3`        |
| `-o, --output`  | Pasta de destino                                     | `downloads`  |
| `--browser`     | Navegador p/ cookies do SoundCloud                   | `chrome`     |
| `--cookies`     | Caminho de um `cookies.txt` (fallback SoundCloud)    | —            |
| `--no-cookies`  | Não usar cookies (qualidade pública)                 | desligado    |

### Credenciais do Spotify

Para links do Spotify, crie um app gratuito em
<https://developer.spotify.com/dashboard>, pegue o **Client ID** e **Client Secret**
e defina as variáveis de ambiente:

```powershell
$env:SPOTIFY_CLIENT_ID = "seu_client_id"
$env:SPOTIFY_CLIENT_SECRET = "seu_client_secret"
```

(Para persistir, use as Variáveis de Ambiente do Windows.)

## Testes

```powershell
.\.venv\Scripts\python.exe -m pytest                  # unitários (sem rede)
.\.venv\Scripts\python.exe -m pytest -m integration   # downloads reais
```
```

- [ ] **Step 9: Commit**

```powershell
git add src/music_downloader/cli.py tests/test_cli.py tests/test_integration.py README.md
git commit -m "feat: Spotify CLI error handling, integration test, and docs"
```

---

## Self-review (cobertura da spec)

- Spotify é resolver, não provider → Task 5 (desvio is_spotify_url antes de detect_provider).
- Metadados via spotipy + credenciais por env + erro claro → Task 2 (SpotifyClient.from_env, MissingCredentialsError), Task 6 (CLI captura).
- Resolve track/album/playlist → Task 2 (resolve + parsing dos 3 tipos).
- Match por duração (top-N + tolerância, None se fora) → Task 3 (best_match/find_youtube).
- Áudio YouTube bestaudio + guardar original + converte -f → reutiliza build_ydl_options no _download_spotify (Task 5).
- Metadados + capa do Spotify embutidos (mp3/flac) → Task 4 (tagging.apply).
- Faixa sem match → falha registrada, segue o lote → Task 5 (_download_spotify).
- YouTube/SoundCloud inalterados → Task 5 mantém o fluxo de providers; testes preservados.
- Testes unit sem rede + integração opt-in (creds) → Tasks 2-6.
- dep spotipy → Task 1.
```
