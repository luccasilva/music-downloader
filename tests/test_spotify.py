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


def test_is_spotify_url_rejects_others():
    assert is_spotify_url("https://youtu.be/abc") is False
    assert is_spotify_url("https://soundcloud.com/a/b") is False
    assert is_spotify_url("https://spotify.link/abc") is False  # short links ainda não suportados


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

    def playlist_items(self, url, additional_types=None):
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
