import music_downloader.core as core_mod
from music_downloader.core import DownloadSummary, download
from music_downloader.providers import AuthConfig


class _FakeYDL:
    """Context manager que imita yt_dlp.YoutubeDL."""

    last_opts = None
    info_to_return = None

    def __init__(self, opts):
        _FakeYDL.last_opts = opts

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def extract_info(self, url, download):
        return _FakeYDL.info_to_return


def _patch_ydl(monkeypatch, info):
    _FakeYDL.info_to_return = info
    monkeypatch.setattr(core_mod.yt_dlp, "YoutubeDL", _FakeYDL)


def test_summary_report_lists_succeeded_and_failed():
    s = DownloadSummary(succeeded=["A", "B"], failed=["C"])
    report = s.report()
    assert "Baixadas: 2" in report
    assert "A" in report and "B" in report
    assert "Falharam: 1" in report
    assert "C" in report


def test_summary_ok_true_when_some_succeed_and_none_fail():
    assert DownloadSummary(succeeded=["A"]).ok is True
    assert DownloadSummary(succeeded=["A"], failed=["B"]).ok is False
    assert DownloadSummary().ok is False


def test_download_single_video_records_title(monkeypatch, tmp_path):
    _patch_ydl(monkeypatch, {"title": "Song One"})
    summary = download("https://youtu.be/abc", str(tmp_path), "mp3")
    assert summary.succeeded == ["Song One"]
    assert summary.failed == []


def test_download_playlist_counts_entries_and_failures(monkeypatch, tmp_path):
    _patch_ydl(monkeypatch, {"entries": [{"title": "One"}, None, {"title": "Three"}]})
    summary = download("https://www.youtube.com/playlist?list=PL1", str(tmp_path), "mp3")
    assert summary.succeeded == ["One", "Three"]
    assert len(summary.failed) == 1


def test_download_passes_noplaylist_based_on_url(monkeypatch, tmp_path):
    _patch_ydl(monkeypatch, {"title": "X"})
    download("https://www.youtube.com/watch?v=abc&list=PL1", str(tmp_path), "mp3")
    assert _FakeYDL.last_opts["noplaylist"] is True


def test_download_creates_output_dir(monkeypatch, tmp_path):
    _patch_ydl(monkeypatch, {"title": "X"})
    target = tmp_path / "new" / "nested"
    download("https://youtu.be/abc", str(target), "mp3")
    assert target.exists()


def test_download_raises_when_ffmpeg_missing(tmp_path):
    import pytest
    with pytest.raises(FileNotFoundError, match="ffmpeg"):
        download(
            "https://youtu.be/abc", str(tmp_path), "mp3",
            ffmpeg_location=str(tmp_path / "nope" / "ffmpeg.exe"),
        )


def test_download_handles_download_error_gracefully(monkeypatch, tmp_path):
    from yt_dlp.utils import DownloadError

    class _RaisingYDL(_FakeYDL):
        def extract_info(self, url, download):
            raise DownloadError("vídeo indisponível")

    monkeypatch.setattr(core_mod.yt_dlp, "YoutubeDL", _RaisingYDL)
    summary = download(
        "https://youtu.be/bad", str(tmp_path), "mp3",
        ffmpeg_location=r"C:\ffmpeg\ffmpeg.exe",
    )
    assert summary.ok is False
    assert summary.failed and "indisponível" in summary.failed[0]


def test_download_applies_soundcloud_cookie_override(monkeypatch, tmp_path):
    _patch_ydl(monkeypatch, {"title": "SC"})
    download(
        "https://soundcloud.com/a/b", str(tmp_path), "mp3",
        ffmpeg_location=r"C:\ffmpeg\ffmpeg.exe",
        auth=AuthConfig(mode="browser", browser="chrome"),
    )
    assert _FakeYDL.last_opts["cookiesfrombrowser"] == ("chrome",)


def test_download_youtube_has_no_cookie_override(monkeypatch, tmp_path):
    _patch_ydl(monkeypatch, {"title": "Y"})
    download(
        "https://youtu.be/abc", str(tmp_path), "mp3",
        ffmpeg_location=r"C:\ffmpeg\ffmpeg.exe",
        auth=AuthConfig(mode="browser", browser="chrome"),
    )
    assert "cookiesfrombrowser" not in _FakeYDL.last_opts


def test_download_unknown_provider_raises(tmp_path):
    import pytest
    with pytest.raises(ValueError, match="não suportado"):
        download(
            "https://example.com/x", str(tmp_path), "mp3",
            ffmpeg_location=r"C:\ffmpeg\ffmpeg.exe",
        )


def test_download_retries_without_cookies_on_cookie_error(monkeypatch, tmp_path, capsys):
    constructions = []

    class _CookieFailYDL(_FakeYDL):
        def __init__(self, opts):
            constructions.append(dict(opts))
            self._opts = opts

        def extract_info(self, url, download):
            if "cookiesfrombrowser" in self._opts:
                raise Exception("Failed to decrypt with DPAPI: could not read cookies")
            return {"title": "SC Track"}

    monkeypatch.setattr(core_mod.yt_dlp, "YoutubeDL", _CookieFailYDL)
    summary = download(
        "https://soundcloud.com/a/b", str(tmp_path), "mp3",
        ffmpeg_location=r"C:\ffmpeg\ffmpeg.exe",
        auth=AuthConfig(mode="browser", browser="chrome"),
    )
    assert summary.succeeded == ["SC Track"]
    assert len(constructions) == 2
    assert "cookiesfrombrowser" in constructions[0]
    assert "cookiesfrombrowser" not in constructions[1]
    out = capsys.readouterr().out.lower()
    assert "cookies" in out


def test_download_does_not_retry_on_login_required_error(monkeypatch, tmp_path, capsys):
    from yt_dlp.utils import DownloadError

    calls = []

    class _LoginRequiredYDL(_FakeYDL):
        def __init__(self, opts):
            calls.append(dict(opts))

        def extract_info(self, url, download):
            raise DownloadError(
                "Sign in to confirm... Use --cookies-from-browser or --cookies "
                "to provide account credentials"
            )

    monkeypatch.setattr(core_mod.yt_dlp, "YoutubeDL", _LoginRequiredYDL)
    summary = download(
        "https://soundcloud.com/a/b", str(tmp_path), "mp3",
        ffmpeg_location=r"C:\ffmpeg\ffmpeg.exe",
        auth=AuthConfig(mode="browser", browser="chrome"),
    )
    assert summary.ok is False
    assert summary.failed and "credentials" in summary.failed[0]
    assert len(calls) == 1  # não deve ter havido retry
    assert "não consegui ler cookies" not in capsys.readouterr().out
