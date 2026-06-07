import pytest

import music_downloader.cli as cli_mod
from music_downloader.cli import _auth_from_args, build_parser, main
from music_downloader.core import DownloadSummary
from music_downloader.providers import AuthConfig


def _parse(argv):
    return build_parser().parse_args(argv)


def test_defaults_are_mp3_and_downloads_dir():
    args = _parse(["https://youtu.be/abc"])
    assert args.url == "https://youtu.be/abc"
    assert args.format == "mp3"
    assert args.output == "downloads"


def test_accepts_flac_and_custom_output():
    args = _parse(["URL", "-f", "flac", "-o", "C:/Music"])
    assert args.format == "flac"
    assert args.output == "C:/Music"


def test_invalid_format_exits():
    with pytest.raises(SystemExit):
        _parse(["URL", "-f", "ogg"])


def test_auth_default_is_browser_chrome():
    assert _auth_from_args(_parse(["URL"])) == AuthConfig(mode="browser", browser="chrome")


def test_auth_browser_override():
    assert _auth_from_args(_parse(["URL", "--browser", "firefox"])) == AuthConfig(
        mode="browser", browser="firefox"
    )


def test_auth_cookiefile():
    assert _auth_from_args(_parse(["URL", "--cookies", "c.txt"])) == AuthConfig(
        mode="cookiefile", cookiefile="c.txt"
    )


def test_auth_no_cookies():
    assert _auth_from_args(_parse(["URL", "--no-cookies"])) == AuthConfig(mode="none")


def test_invalid_browser_exits():
    with pytest.raises(SystemExit):
        _parse(["URL", "--browser", "netscape"])


def test_main_returns_zero_on_success(monkeypatch, capsys):
    monkeypatch.setattr(
        cli_mod, "download",
        lambda url, output, fmt, auth: DownloadSummary(succeeded=["Song"]),
    )
    code = main(["https://youtu.be/abc"])
    assert code == 0
    assert "Song" in capsys.readouterr().out


def test_main_returns_one_when_failures(monkeypatch):
    monkeypatch.setattr(
        cli_mod, "download",
        lambda url, output, fmt, auth: DownloadSummary(succeeded=[], failed=["X"]),
    )
    assert main(["https://youtu.be/abc"]) == 1


def test_main_reports_missing_ffmpeg_cleanly(monkeypatch, capsys):
    def _raise(url, output, fmt, auth):
        raise FileNotFoundError("ffmpeg não encontrado em 'X'. Instale o ffmpeg ou adicione-o ao PATH.")
    monkeypatch.setattr(cli_mod, "download", _raise)
    code = main(["https://youtu.be/abc"])
    assert code == 1
    assert "ffmpeg" in capsys.readouterr().out


def test_main_reports_unknown_provider_cleanly(monkeypatch, capsys):
    def _raise(url, output, fmt, auth):
        raise ValueError("Provedor não suportado: 'x'. Suportados: YouTube, SoundCloud")
    monkeypatch.setattr(cli_mod, "download", _raise)
    code = main(["https://example.com/x"])
    assert code == 1
    assert "suportado" in capsys.readouterr().out.lower()


def test_main_reports_missing_spotify_credentials_cleanly(monkeypatch, capsys):
    from music_downloader.spotify import MissingCredentialsError

    def _raise(url, output, fmt, auth):
        raise MissingCredentialsError(
            "Credenciais do Spotify ausentes. ... SPOTIFY_CLIENT_ID ..."
        )

    monkeypatch.setattr(cli_mod, "download", _raise)
    code = main(["https://open.spotify.com/track/abc"])
    assert code == 1
    assert "spotify" in capsys.readouterr().out.lower()


def test_load_dotenv_sets_env_without_overriding(tmp_path, monkeypatch):
    from music_downloader.cli import _load_dotenv

    env_file = tmp_path / ".env"
    env_file.write_text(
        '# comentário\nMDL_TEST_A=valor1\nMDL_TEST_B="com aspas"\n',
        encoding="utf-8",
    )
    monkeypatch.delenv("MDL_TEST_A", raising=False)
    monkeypatch.setenv("MDL_TEST_B", "ja_definido")  # não deve ser sobrescrito

    _load_dotenv(str(env_file))

    import os
    assert os.environ["MDL_TEST_A"] == "valor1"
    assert os.environ["MDL_TEST_B"] == "ja_definido"  # env existente vence
