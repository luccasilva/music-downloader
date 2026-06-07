"""Registro de formatos de conversão suportados."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FormatSpec:
    name: str            # nome no CLI, ex.: "mp3"
    codec: str           # codec do FFmpegExtractAudio, ex.: "mp3", "flac"
    quality: str | None  # preferredquality (kbps) p/ lossy; None p/ lossless
    ext: str             # extensão do arquivo final


FORMATS: dict[str, FormatSpec] = {
    "mp3": FormatSpec(name="mp3", codec="mp3", quality="320", ext="mp3"),
    "flac": FormatSpec(name="flac", codec="flac", quality=None, ext="flac"),
}


def supported_formats() -> list[str]:
    return list(FORMATS)


def get_format(name: str) -> FormatSpec:
    try:
        return FORMATS[name]
    except KeyError:
        disponiveis = ", ".join(FORMATS)
        raise ValueError(
            f"Formato não suportado: {name!r}. Disponíveis: {disponiveis}"
        ) from None
