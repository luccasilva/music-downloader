"""Construção das opções do yt-dlp e descoberta do ffmpeg."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any, Callable

from .formats import FormatSpec
from .naming import OUTPUT_TEMPLATE

_FALLBACK_FFMPEG = r"C:\ffmpeg\ffmpeg.exe"


def find_ffmpeg() -> str:
    """Retorna o caminho do ffmpeg: PATH primeiro, depois o local conhecido."""
    return shutil.which("ffmpeg") or _FALLBACK_FFMPEG


def build_ydl_options(
    output_dir: str,
    fmt: FormatSpec,
    ffmpeg_location: str,
    noplaylist: bool,
    progress_hook: Callable[[dict], None] | None = None,
) -> dict[str, Any]:
    extract: dict[str, Any] = {
        "key": "FFmpegExtractAudio",
        "preferredcodec": fmt.codec,
    }
    if fmt.quality is not None:
        extract["preferredquality"] = fmt.quality

    opts: dict[str, Any] = {
        "format": "bestaudio/best",
        "outtmpl": str(Path(output_dir) / OUTPUT_TEMPLATE),
        "writethumbnail": True,
        "keepvideo": True,          # guarda o arquivo original (bestaudio)
        "ignoreerrors": True,        # continua a playlist se um item falhar
        "noplaylist": noplaylist,
        "quiet": True,
        "no_warnings": True,
        "ffmpeg_location": ffmpeg_location,
        "postprocessors": [
            extract,
            {"key": "FFmpegMetadata"},
            {"key": "EmbedThumbnail"},
        ],
    }
    if progress_hook is not None:
        opts["progress_hooks"] = [progress_hook]
    return opts
