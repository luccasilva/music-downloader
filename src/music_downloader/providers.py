"""Provedores de download e roteamento por URL."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable
from urllib.parse import parse_qs, urlparse


@dataclass(frozen=True)
class AuthConfig:
    """Como autenticar; usado por provedores que precisam (ex.: SoundCloud)."""

    mode: str = "browser"            # "browser" | "cookiefile" | "none"
    browser: str = "chrome"          # usado quando mode == "browser"
    cookiefile: str | None = None    # usado quando mode == "cookiefile"


@runtime_checkable
class Provider(Protocol):
    name: str

    def matches(self, url: str) -> bool: ...
    def is_playlist(self, url: str) -> bool: ...
    def ydl_overrides(self, auth: AuthConfig) -> dict[str, Any]: ...


def _host(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


class YouTubeProvider:
    name = "YouTube"
    _HOSTS = {"youtube.com", "youtu.be", "music.youtube.com", "m.youtube.com"}

    def matches(self, url: str) -> bool:
        return _host(url) in self._HOSTS

    def is_playlist(self, url: str) -> bool:
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        if "list" not in query:
            return False
        return "playlist" in parsed.path or "v" not in query

    def ydl_overrides(self, auth: AuthConfig) -> dict[str, Any]:
        return {}


class SoundCloudProvider:
    name = "SoundCloud"
    _HOSTS = {"soundcloud.com", "on.soundcloud.com", "m.soundcloud.com"}

    def matches(self, url: str) -> bool:
        return _host(url) in self._HOSTS

    def is_playlist(self, url: str) -> bool:
        return "/sets/" in urlparse(url).path

    def ydl_overrides(self, auth: AuthConfig) -> dict[str, Any]:
        if auth.mode == "cookiefile" and auth.cookiefile:
            return {"cookiefile": auth.cookiefile}
        if auth.mode == "browser":
            return {"cookiesfrombrowser": (auth.browser,)}
        return {}


PROVIDERS: list[Provider] = [YouTubeProvider(), SoundCloudProvider()]


def detect_provider(url: str) -> Provider:
    for provider in PROVIDERS:
        if provider.matches(url):
            return provider
    suportados = ", ".join(p.name for p in PROVIDERS)
    raise ValueError(f"Provedor não suportado: {url!r}. Suportados: {suportados}")
