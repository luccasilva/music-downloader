from pathlib import Path

from music_downloader.downloader import build_ydl_options, find_ffmpeg
from music_downloader.formats import get_format


def _pp(opts, key):
    return next(p for p in opts["postprocessors"] if p["key"] == key)


def test_selects_best_audio_and_keeps_original():
    opts = build_ydl_options("out", get_format("mp3"), "C:/ffmpeg/ffmpeg.exe", noplaylist=True)
    assert opts["format"] == "bestaudio/best"
    assert opts["keepvideo"] is True          # mantém o original
    assert opts["writethumbnail"] is True
    assert opts["ignoreerrors"] is True
    assert opts["noplaylist"] is True


def test_outtmpl_points_into_output_dir_with_template():
    opts = build_ydl_options("mymusic", get_format("mp3"), "ff", noplaylist=True)
    assert opts["outtmpl"] == str(Path("mymusic") / "%(artist,uploader)s - %(title)s.%(ext)s")


def test_mp3_postprocessor_uses_320_quality():
    opts = build_ydl_options("out", get_format("mp3"), "ff", noplaylist=True)
    extract = _pp(opts, "FFmpegExtractAudio")
    assert extract["preferredcodec"] == "mp3"
    assert extract["preferredquality"] == "320"


def test_flac_postprocessor_omits_quality():
    opts = build_ydl_options("out", get_format("flac"), "ff", noplaylist=True)
    extract = _pp(opts, "FFmpegExtractAudio")
    assert extract["preferredcodec"] == "flac"
    assert "preferredquality" not in extract


def test_includes_metadata_and_thumbnail_postprocessors():
    opts = build_ydl_options("out", get_format("mp3"), "ff", noplaylist=True)
    keys = [p["key"] for p in opts["postprocessors"]]
    assert "FFmpegMetadata" in keys
    assert "EmbedThumbnail" in keys


def test_ffmpeg_location_is_passed():
    opts = build_ydl_options("out", get_format("mp3"), "C:/ffmpeg/ffmpeg.exe", noplaylist=True)
    assert opts["ffmpeg_location"] == "C:/ffmpeg/ffmpeg.exe"


def test_find_ffmpeg_returns_a_path(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: None)
    assert find_ffmpeg() == r"C:\ffmpeg\ffmpeg.exe"


def test_overrides_are_merged_with_precedence():
    opts = build_ydl_options(
        "out", get_format("mp3"), "ff", noplaylist=True,
        overrides={"cookiesfrombrowser": ("chrome",), "format": "X"},
    )
    assert opts["cookiesfrombrowser"] == ("chrome",)
    assert opts["format"] == "X"  # override tem precedência sobre a base


def test_no_overrides_keeps_base():
    opts = build_ydl_options("out", get_format("mp3"), "ff", noplaylist=True)
    assert "cookiesfrombrowser" not in opts
    assert opts["format"] == "bestaudio/best"
