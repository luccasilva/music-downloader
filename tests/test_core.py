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
