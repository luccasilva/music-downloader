"""Interface de linha de comando do music-downloader."""

from __future__ import annotations

import argparse

from .core import download
from .formats import supported_formats


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mdl",
        description="Baixa o melhor áudio do YouTube e converte para MP3/FLAC. "
        "O arquivo original é sempre guardado.",
    )
    parser.add_argument("url", help="URL de um vídeo ou de uma playlist do YouTube")
    parser.add_argument(
        "-o", "--output", default="downloads",
        help="Pasta de destino (padrão: downloads)",
    )
    parser.add_argument(
        "-f", "--format", default="mp3", choices=supported_formats(),
        help="Formato da cópia convertida (padrão: mp3)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        summary = download(args.url, args.output, args.format)
    except FileNotFoundError as exc:
        print(f"Erro: {exc}")
        return 1
    print(summary.report())
    return 0 if summary.ok else 1
