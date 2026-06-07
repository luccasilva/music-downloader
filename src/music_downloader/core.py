"""Orquestração do download: detecção de playlist, execução e resumo."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import yt_dlp

from .downloader import build_ydl_options, find_ffmpeg
from .formats import get_format


def is_playlist(url: str) -> bool:
    """True quando a URL deve ser tratada como playlist.

    Regra: precisa do parâmetro ``list`` E (ser caminho /playlist OU não ter um
    vídeo ``v`` específico). Assim, ``watch?v=...&list=...`` baixa só o vídeo.
    """
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    if "list" not in query:
        return False
    return "playlist" in parsed.path or "v" not in query


@dataclass
class DownloadSummary:
    succeeded: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return bool(self.succeeded) and not self.failed

    def report(self) -> str:
        lines = [f"Baixadas: {len(self.succeeded)}"]
        lines += [f"  + {t}" for t in self.succeeded]
        if self.failed:
            lines.append(f"Falharam: {len(self.failed)}")
            lines += [f"  - {t}" for t in self.failed]
        return "\n".join(lines)


def _collect(info: dict | None, summary: DownloadSummary) -> None:
    if info is None:
        summary.failed.append("(download falhou)")
        return
    if "entries" in info:
        for entry in info["entries"]:
            if entry is None:
                summary.failed.append("(item indisponível)")
            else:
                summary.succeeded.append(entry.get("title", "(sem título)"))
    else:
        summary.succeeded.append(info.get("title", "(sem título)"))


def download(
    url: str,
    output_dir: str,
    fmt_name: str,
    ffmpeg_location: str | None = None,
) -> DownloadSummary:
    fmt = get_format(fmt_name)
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    ffmpeg = ffmpeg_location or find_ffmpeg()
    opts = build_ydl_options(
        output_dir, fmt, ffmpeg, noplaylist=not is_playlist(url)
    )
    summary = DownloadSummary()
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
    _collect(info, summary)
    return summary
