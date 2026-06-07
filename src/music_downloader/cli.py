"""Interface de linha de comando do music-downloader."""

from __future__ import annotations

import argparse

from .core import download
from .formats import supported_formats
from .providers import AuthConfig
from .spotify import MissingCredentialsError

_BROWSERS = ["chrome", "firefox", "edge", "brave"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mdl",
        description="Baixa o melhor áudio do YouTube ou SoundCloud e converte para "
        "MP3/FLAC. O arquivo original é sempre guardado.",
    )
    parser.add_argument(
        "url",
        help="URL de vídeo/faixa/playlist/álbum (YouTube, SoundCloud ou Spotify)",
    )
    parser.add_argument(
        "-o", "--output", default="downloads",
        help="Pasta de destino (padrão: downloads)",
    )
    parser.add_argument(
        "-f", "--format", default="mp3", choices=supported_formats(),
        help="Formato da cópia convertida (padrão: mp3)",
    )
    parser.add_argument(
        "--browser", default="chrome", choices=_BROWSERS,
        help="Navegador de onde ler cookies do SoundCloud (padrão: chrome)",
    )
    parser.add_argument(
        "--cookies", default=None, metavar="ARQUIVO",
        help="Caminho de um cookies.txt exportado (fallback; ignora --browser)",
    )
    parser.add_argument(
        "--no-cookies", action="store_true",
        help="Não usar cookies (baixa só a qualidade pública)",
    )
    return parser


def _auth_from_args(args: argparse.Namespace) -> AuthConfig:
    if args.no_cookies:
        return AuthConfig(mode="none")
    if args.cookies:
        return AuthConfig(mode="cookiefile", cookiefile=args.cookies)
    return AuthConfig(mode="browser", browser=args.browser)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    auth = _auth_from_args(args)
    try:
        summary = download(args.url, args.output, args.format, auth=auth)
    except (FileNotFoundError, ValueError, MissingCredentialsError) as exc:
        print(f"Erro: {exc}")
        return 1
    print(summary.report())
    return 0 if summary.ok else 1
