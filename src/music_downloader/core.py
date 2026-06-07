"""Orquestração do download: roteamento por provedor, execução e resumo."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yt_dlp
from yt_dlp.utils import DownloadError

from .downloader import build_ydl_options, find_ffmpeg
from .formats import get_format
from .providers import AuthConfig, detect_provider


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


def _ensure_ffmpeg(path: str) -> None:
    if not Path(path).exists():
        raise FileNotFoundError(
            f"ffmpeg não encontrado em {path!r}. "
            "Instale o ffmpeg ou adicione-o ao PATH."
        )


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


def _is_cookie_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(s in msg for s in ("cookie", "dpapi", "decrypt"))


def _extract(url: str, opts: dict) -> dict | None:
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=True)


def download(
    url: str,
    output_dir: str,
    fmt_name: str,
    ffmpeg_location: str | None = None,
    auth: AuthConfig | None = None,
) -> DownloadSummary:
    auth = auth or AuthConfig()
    provider = detect_provider(url)  # ValueError se provedor desconhecido
    fmt = get_format(fmt_name)
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    ffmpeg = ffmpeg_location or find_ffmpeg()
    _ensure_ffmpeg(ffmpeg)
    opts = build_ydl_options(
        output_dir,
        fmt,
        ffmpeg,
        noplaylist=not provider.is_playlist(url),
        overrides=provider.ydl_overrides(auth),
    )
    summary = DownloadSummary()
    try:
        try:
            info = _extract(url, opts)
        except Exception as exc:  # noqa: BLE001 — só para detectar erro de cookies
            if "cookiesfrombrowser" in opts and _is_cookie_error(exc):
                print(
                    f"Aviso: não consegui ler cookies do navegador ({exc}). "
                    "Seguindo sem login (qualidade pública). Para máxima qualidade, "
                    "exporte um cookies.txt e use --cookies CAMINHO."
                )
                opts.pop("cookiesfrombrowser", None)
                info = _extract(url, opts)
            else:
                raise
    except DownloadError as exc:
        summary.failed.append(f"{url}: {exc}")
        return summary
    _collect(info, summary)
    return summary
