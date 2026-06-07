import pytest

from music_downloader.providers import (
    AuthConfig,
    SoundCloudProvider,
    YouTubeProvider,
    detect_provider,
)


def test_detect_youtube_variants():
    assert isinstance(detect_provider("https://www.youtube.com/watch?v=x"), YouTubeProvider)
    assert isinstance(detect_provider("https://youtu.be/x"), YouTubeProvider)
    assert isinstance(detect_provider("https://music.youtube.com/watch?v=x"), YouTubeProvider)


def test_detect_soundcloud():
    assert isinstance(detect_provider("https://soundcloud.com/artist/track"), SoundCloudProvider)


def test_detect_unknown_raises():
    with pytest.raises(ValueError, match="não suportado"):
        detect_provider("https://example.com/song")


def test_youtube_is_playlist_rules():
    p = YouTubeProvider()
    assert p.is_playlist("https://www.youtube.com/watch?v=a") is False
    assert p.is_playlist("https://www.youtube.com/watch?v=a&list=PL1") is False
    assert p.is_playlist("https://www.youtube.com/playlist?list=PL1") is True
    assert p.is_playlist("https://youtu.be/a") is False


def test_soundcloud_is_playlist_rules():
    p = SoundCloudProvider()
    assert p.is_playlist("https://soundcloud.com/artist/sets/my-set") is True
    assert p.is_playlist("https://soundcloud.com/artist/track") is False


def test_youtube_overrides_are_empty():
    assert YouTubeProvider().ydl_overrides(AuthConfig()) == {}


def test_soundcloud_overrides_browser_is_default():
    ov = SoundCloudProvider().ydl_overrides(AuthConfig(mode="browser", browser="chrome"))
    assert ov == {"cookiesfrombrowser": ("chrome",)}


def test_soundcloud_overrides_cookiefile():
    ov = SoundCloudProvider().ydl_overrides(AuthConfig(mode="cookiefile", cookiefile="c.txt"))
    assert ov == {"cookiefile": "c.txt"}


def test_soundcloud_overrides_none_is_empty():
    assert SoundCloudProvider().ydl_overrides(AuthConfig(mode="none")) == {}
