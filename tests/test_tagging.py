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
    assert tags.getall("TSRC")[0].text[0] == "ZZ"


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
    assert audio["isrc"][0] == "ZZ"


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
