"""Orquestração do download: detecção de playlist e resumo."""

from __future__ import annotations

from urllib.parse import urlparse, parse_qs


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
