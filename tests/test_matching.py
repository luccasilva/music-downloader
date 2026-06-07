import music_downloader.matching as matching
from music_downloader.matching import Candidate, best_match, find_youtube
from music_downloader.spotify import SpotifyTrack


def _track(duration_ms):
    return SpotifyTrack(
        title="Song", artists=("A",), album="Al", release_date="2020",
        track_number=1, total_tracks=1, disc_number=1,
        duration_ms=duration_ms, isrc=None, cover_url=None,
    )


def test_best_match_picks_closest_duration():
    cands = [
        Candidate(url="u1", title="t1", duration=100),
        Candidate(url="u2", title="t2", duration=182),
        Candidate(url="u3", title="t3", duration=250),
    ]
    m = best_match(180000, cands)  # 180s
    assert m.url == "u2"


def test_best_match_returns_none_when_all_out_of_tolerance():
    cands = [Candidate(url="u1", title="t1", duration=100)]
    assert best_match(180000, cands) is None  # 80s de diferença


def test_best_match_empty_is_none():
    assert best_match(180000, []) is None


def test_find_youtube_uses_best_match(monkeypatch):
    cands = [
        Candidate(url="https://youtu.be/right", title="t", duration=181),
        Candidate(url="https://youtu.be/wrong", title="t", duration=300),
    ]
    monkeypatch.setattr(matching, "search_youtube", lambda query, n=5: cands)
    assert find_youtube(_track(180000)) == "https://youtu.be/right"


def test_find_youtube_returns_none_without_good_match(monkeypatch):
    monkeypatch.setattr(matching, "search_youtube", lambda query, n=5: [])
    assert find_youtube(_track(180000)) is None
