"""Orquestração do download: roteamento por provedor/resolver, execução e resumo."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yt_dlp
from yt_dlp.utils import DownloadError

from .downloader import build_ydl_options, find_ffmpeg
from .formats import get_format
from .matching import find_youtube
from .providers import AuthConfig, detect_provider
from .spotify import SpotifyClient, is_spotify_url
from .tagging import apply as apply_tags


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
    """True só para falhas de LEITURA/DECRIPTAÇÃO de cookies do navegador.

    Não casa erros de "login necessário" (que também citam cookies), para não
    rebaixar a qualidade silenciosamente.
    """
    msg = str(exc).lower()
    markers = (
        "dpapi",
        "decrypt",
        "could not copy",
        "failed to load cookies",
        "could not read cookie",
        "unable to read cookie",
    )
    return any(m in msg for m in markers)


def _extract(url: str, opts: dict) -> dict | None:
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=True)


def _run_download(url: str, opts: dict) -> dict | None:
    """Executa o yt-dlp com fallback se a leitura de cookies do navegador falhar."""
    try:
        return _extract(url, opts)
    except Exception as exc:  # noqa: BLE001 — só para detectar erro de cookies
        if "cookiesfrombrowser" in opts and _is_cookie_error(exc):
            print(
                f"Aviso: não consegui ler cookies do navegador ({exc}). "
                "Seguindo sem login (qualidade pública). Para máxima qualidade, "
                "exporte um cookies.txt e use --cookies CAMINHO."
            )
            opts.pop("cookiesfrombrowser", None)
            return _extract(url, opts)
        raise


def _final_filepath(info: dict | None) -> str | None:
    if not info:
        return None
    downloads = info.get("requested_downloads")
    if downloads:
        return downloads[0].get("filepath")
    return info.get("filepath")


def _download_spotify(
    url: str, output_dir: str, fmt_name: str, ffmpeg: str
) -> DownloadSummary:
    client = SpotifyClient.from_env()  # MissingCredentialsError se faltar
    tracks = client.resolve(url)
    fmt = get_format(fmt_name)
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    summary = DownloadSummary()
    for track in tracks:
        youtube_url = find_youtube(track)
        if not youtube_url:
            summary.failed.append(f"{track.display()}: sem match confiável no YouTube")
            continue
        opts = build_ydl_options(output_dir, fmt, ffmpeg, noplaylist=True)
        try:
            info = _run_download(youtube_url, opts)
        except DownloadError as exc:
            summary.failed.append(f"{track.display()}: {exc}")
            continue
        path = _final_filepath(info)
        if path:
            try:
                apply_tags(track, [path])
            except Exception as exc:  # noqa: BLE001 — tagging não deve abortar o lote
                print(
                    f"Aviso: baixei mas não consegui aplicar metadados de "
                    f"{track.display()} ({exc})."
                )
        summary.succeeded.append(track.display())
    return summary


def download(
    url: str,
    output_dir: str,
    fmt_name: str,
    ffmpeg_location: str | None = None,
    auth: AuthConfig | None = None,
) -> DownloadSummary:
    ffmpeg = ffmpeg_location or find_ffmpeg()
    _ensure_ffmpeg(ffmpeg)
    if is_spotify_url(url):
        return _download_spotify(url, output_dir, fmt_name, ffmpeg)
    auth = auth or AuthConfig()
    provider = detect_provider(url)  # ValueError se provedor desconhecido
    fmt = get_format(fmt_name)
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    opts = build_ydl_options(
        output_dir,
        fmt,
        ffmpeg,
        noplaylist=not provider.is_playlist(url),
        overrides=provider.ydl_overrides(auth),
    )
    summary = DownloadSummary()
    try:
        info = _run_download(url, opts)
    except DownloadError as exc:
        summary.failed.append(f"{url}: {exc}")
        return summary
    _collect(info, summary)
    return summary
