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
