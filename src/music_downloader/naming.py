"""Geração e sanitização de nomes de arquivo."""

from __future__ import annotations

import re

# Template do yt-dlp: "Artista - Título.ext", caindo para uploader se não houver artista.
OUTPUT_TEMPLATE = "%(artist,uploader)s - %(title)s.%(ext)s"

_INVALID = re.compile(r'[<>:"/\\|?*]')
_WHITESPACE = re.compile(r"\s+")


def sanitize_filename(name: str) -> str:
    cleaned = _INVALID.sub("_", name)
    cleaned = _WHITESPACE.sub(" ", cleaned).strip()
    cleaned = cleaned.rstrip(".").strip()
    return cleaned or "untitled"
