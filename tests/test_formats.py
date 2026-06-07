import pytest
from music_downloader.formats import get_format, supported_formats, FormatSpec


def test_supported_formats_lists_mp3_and_flac():
    assert set(supported_formats()) == {"mp3", "flac"}


def test_get_mp3_has_320_quality():
    fmt = get_format("mp3")
    assert isinstance(fmt, FormatSpec)
    assert fmt.codec == "mp3"
    assert fmt.quality == "320"
    assert fmt.ext == "mp3"


def test_get_flac_is_lossless_without_quality():
    fmt = get_format("flac")
    assert fmt.codec == "flac"
    assert fmt.quality is None
    assert fmt.ext == "flac"


def test_unknown_format_raises_valueerror():
    with pytest.raises(ValueError, match="não suportado"):
        get_format("ogg")
