from music_downloader.core import is_playlist


def test_plain_video_url_is_not_playlist():
    assert is_playlist("https://www.youtube.com/watch?v=abc123") is False


def test_video_with_list_param_is_treated_as_single_video():
    # watch?v=...&list=... -> intenção é o vídeo; não baixa a playlist toda
    assert is_playlist("https://www.youtube.com/watch?v=abc123&list=PL999") is False


def test_playlist_url_is_playlist():
    assert is_playlist("https://www.youtube.com/playlist?list=PL999") is True


def test_youtu_be_short_link_is_not_playlist():
    assert is_playlist("https://youtu.be/abc123") is False


import music_downloader.core as core_mod
from music_downloader.core import DownloadSummary, download


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
