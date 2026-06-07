from pathlib import Path

import pytest

from music_downloader.core import download


@pytest.mark.integration
def test_real_download_creates_mp3_and_keeps_original(tmp_path):
    summary = download(
        "https://www.youtube.com/watch?v=aqz-KE-bpKQ", str(tmp_path), "mp3"
    )
    assert summary.ok
    assert list(tmp_path.glob("*.mp3")), "deveria gerar um .mp3"
    originais = list(tmp_path.glob("*.webm")) + list(tmp_path.glob("*.m4a"))
    assert originais, "deveria guardar o arquivo original"


@pytest.mark.integration
def test_real_soundcloud_download_creates_mp3_and_keeps_original(tmp_path):
    from music_downloader.providers import AuthConfig

    summary = download(
        "https://soundcloud.com/forss/flickermood", str(tmp_path), "mp3",
        auth=AuthConfig(mode="none"),
    )
    assert summary.ok
    assert list(tmp_path.glob("*.mp3")), "deveria gerar um .mp3"
    audio = []
    for ext in ("*.mp3", "*.m4a", "*.opus", "*.webm", "*.flac", "*.wav"):
        audio += list(tmp_path.glob(ext))
    # além do mp3 convertido, deve haver o arquivo original guardado
    assert len(audio) >= 2, "deveria guardar o arquivo original além do mp3 convertido"


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
