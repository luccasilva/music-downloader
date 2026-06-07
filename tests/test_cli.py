import pytest

import music_downloader.cli as cli_mod
from music_downloader.cli import build_parser, main
from music_downloader.core import DownloadSummary


def test_defaults_are_mp3_and_downloads_dir():
    args = build_parser().parse_args(["https://youtu.be/abc"])
    assert args.url == "https://youtu.be/abc"
    assert args.format == "mp3"
    assert args.output == "downloads"


def test_accepts_flac_and_custom_output():
    args = build_parser().parse_args(["URL", "-f", "flac", "-o", "C:/Music"])
    assert args.format == "flac"
    assert args.output == "C:/Music"


def test_invalid_format_exits():
    with pytest.raises(SystemExit):
        build_parser().parse_args(["URL", "-f", "ogg"])


def test_main_returns_zero_on_success(monkeypatch, capsys):
    monkeypatch.setattr(
        cli_mod, "download",
        lambda url, output, fmt: DownloadSummary(succeeded=["Song"]),
    )
    code = main(["https://youtu.be/abc"])
    assert code == 0
    assert "Song" in capsys.readouterr().out


def test_main_returns_one_when_failures(monkeypatch):
    monkeypatch.setattr(
        cli_mod, "download",
        lambda url, output, fmt: DownloadSummary(succeeded=[], failed=["X"]),
    )
    assert main(["URL"]) == 1


def test_main_reports_missing_ffmpeg_cleanly(monkeypatch, capsys):
    def _raise(url, output, fmt):
        raise FileNotFoundError("ffmpeg não encontrado em 'X'. Instale o ffmpeg ou adicione-o ao PATH.")
    monkeypatch.setattr(cli_mod, "download", _raise)
    code = main(["https://youtu.be/abc"])
    assert code == 1
    assert "ffmpeg" in capsys.readouterr().out
