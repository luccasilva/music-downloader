# Provider Routing + SoundCloud Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adicionar suporte a SoundCloud com roteamento automático pelo link (detecta o provedor e aplica o fluxo certo), mantendo o comportamento do YouTube idêntico e priorizando máxima qualidade + todos os metadados.

**Architecture:** Novo módulo `providers.py` com um contrato por provedor (`matches`, `is_playlist`, `ydl_overrides`) + `detect_provider` (roteador) + `AuthConfig`. O `core.download` passa a detectar o provedor e mesclar os ajustes dele nas opções do yt-dlp. SoundCloud usa cookies do navegador (padrão Chrome) com fallback `cookies.txt`, e o download tem retry sem cookies quando a leitura de cookies falha. O YouTube vira um provider e sua lógica `is_playlist` migra do core.

**Tech Stack:** Python 3.12, yt-dlp (lib, já suporta SoundCloud), ffmpeg, pytest.

---

## File Structure

```
src/music_downloader/
  providers.py        # NOVO: AuthConfig, Provider, YouTubeProvider, SoundCloudProvider, detect_provider
  core.py             # MOD: usa detect_provider/provider; +param auth; remove is_playlist; +retry cookies
  downloader.py       # MOD: build_ydl_options aceita overrides e mescla
  cli.py              # MOD: flags --browser/--cookies/--no-cookies; monta AuthConfig; captura ValueError
  formats.py          # (inalterado)
  naming.py           # (inalterado)
tests/
  test_providers.py   # NOVO
  test_core.py        # MOD: remove testes de is_playlist (migram p/ providers); +roteamento/auth/retry
  test_downloader.py  # MOD: +testes de merge de overrides
  test_cli.py         # MOD: lambdas passam a aceitar auth; +testes das flags
  test_integration.py # MOD: +teste SoundCloud público (marcado)
```

**Comando do venv (Windows):** sempre `.\.venv\Scripts\python.exe -m pytest ...` (o `python` puro é stub).

---

## Task 1: Módulo de providers (`providers.py`)

**Files:**
- Create: `src/music_downloader/providers.py`
- Test: `tests/test_providers.py`

- [ ] **Step 1: Escrever os testes que falham**

Create `tests/test_providers.py`:
```python
import pytest

from music_downloader.providers import (
    AuthConfig,
    SoundCloudProvider,
    YouTubeProvider,
    detect_provider,
)


def test_detect_youtube_variants():
    assert isinstance(detect_provider("https://www.youtube.com/watch?v=x"), YouTubeProvider)
    assert isinstance(detect_provider("https://youtu.be/x"), YouTubeProvider)
    assert isinstance(detect_provider("https://music.youtube.com/watch?v=x"), YouTubeProvider)


def test_detect_soundcloud():
    assert isinstance(detect_provider("https://soundcloud.com/artist/track"), SoundCloudProvider)


def test_detect_unknown_raises():
    with pytest.raises(ValueError, match="não suportado"):
        detect_provider("https://example.com/song")


def test_youtube_is_playlist_rules():
    p = YouTubeProvider()
    assert p.is_playlist("https://www.youtube.com/watch?v=a") is False
    assert p.is_playlist("https://www.youtube.com/watch?v=a&list=PL1") is False
    assert p.is_playlist("https://www.youtube.com/playlist?list=PL1") is True
    assert p.is_playlist("https://youtu.be/a") is False


def test_soundcloud_is_playlist_rules():
    p = SoundCloudProvider()
    assert p.is_playlist("https://soundcloud.com/artist/sets/my-set") is True
    assert p.is_playlist("https://soundcloud.com/artist/track") is False


def test_youtube_overrides_are_empty():
    assert YouTubeProvider().ydl_overrides(AuthConfig()) == {}


def test_soundcloud_overrides_browser_is_default():
    ov = SoundCloudProvider().ydl_overrides(AuthConfig(mode="browser", browser="chrome"))
    assert ov == {"cookiesfrombrowser": ("chrome",)}


def test_soundcloud_overrides_cookiefile():
    ov = SoundCloudProvider().ydl_overrides(AuthConfig(mode="cookiefile", cookiefile="c.txt"))
    assert ov == {"cookiefile": "c.txt"}


def test_soundcloud_overrides_none_is_empty():
    assert SoundCloudProvider().ydl_overrides(AuthConfig(mode="none")) == {}
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_providers.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'music_downloader.providers'`.

- [ ] **Step 3: Implementar `providers.py`**

Create `src/music_downloader/providers.py`:
```python
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
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_providers.py -v`
Expected: 9 passed.

- [ ] **Step 5: Commit**

```powershell
git add src/music_downloader/providers.py tests/test_providers.py
git commit -m "feat: provider abstraction with YouTube/SoundCloud routing"
```

---

## Task 2: `build_ydl_options` aceita overrides

**Files:**
- Modify: `src/music_downloader/downloader.py`
- Modify: `tests/test_downloader.py`

- [ ] **Step 1: Escrever os testes que falham (append em `tests/test_downloader.py`)**

Append to `tests/test_downloader.py`:
```python
def test_overrides_are_merged_with_precedence():
    opts = build_ydl_options(
        "out", get_format("mp3"), "ff", noplaylist=True,
        overrides={"cookiesfrombrowser": ("chrome",), "format": "X"},
    )
    assert opts["cookiesfrombrowser"] == ("chrome",)
    assert opts["format"] == "X"  # override tem precedência sobre a base


def test_no_overrides_keeps_base():
    opts = build_ydl_options("out", get_format("mp3"), "ff", noplaylist=True)
    assert "cookiesfrombrowser" not in opts
    assert opts["format"] == "bestaudio/best"
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_downloader.py::test_overrides_are_merged_with_precedence -v`
Expected: FAIL com `TypeError: build_ydl_options() got an unexpected keyword argument 'overrides'`.

- [ ] **Step 3: Implementar — adicionar o parâmetro `overrides`**

In `src/music_downloader/downloader.py`, change the signature of `build_ydl_options` to add `overrides` and merge it at the end. Replace the function definition line:
```python
def build_ydl_options(
    output_dir: str,
    fmt: FormatSpec,
    ffmpeg_location: str,
    noplaylist: bool,
    progress_hook: Callable[[dict], None] | None = None,
) -> dict[str, Any]:
```
with:
```python
def build_ydl_options(
    output_dir: str,
    fmt: FormatSpec,
    ffmpeg_location: str,
    noplaylist: bool,
    progress_hook: Callable[[dict], None] | None = None,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
```
Then, at the END of the function, replace the final block:
```python
    if progress_hook is not None:
        opts["progress_hooks"] = [progress_hook]
    return opts
```
with:
```python
    if progress_hook is not None:
        opts["progress_hooks"] = [progress_hook]
    if overrides:
        opts.update(overrides)  # ajustes do provider têm precedência
    return opts
```

- [ ] **Step 4: Rodar e ver passar (arquivo inteiro)**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_downloader.py -v`
Expected: 9 passed (7 antigos + 2 novos).

- [ ] **Step 5: Commit**

```powershell
git add src/music_downloader/downloader.py tests/test_downloader.py
git commit -m "feat: build_ydl_options merges provider overrides"
```

---

## Task 3: Refatorar `core.download` para usar providers + auth

**Files:**
- Modify: `src/music_downloader/core.py`
- Modify: `tests/test_core.py`

- [ ] **Step 1: Atualizar `tests/test_core.py` — remover testes de is_playlist e adicionar testes de roteamento/auth**

REPLACE the ENTIRE contents of `tests/test_core.py` with exactly:
```python
import music_downloader.core as core_mod
from music_downloader.core import DownloadSummary, download
from music_downloader.providers import AuthConfig


class _FakeYDL:
    """Context manager que imita yt_dlp.YoutubeDL."""

    last_opts = None
    info_to_return = None

    def __init__(self, opts):
        _FakeYDL.last_opts = opts

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def extract_info(self, url, download):
        return _FakeYDL.info_to_return


def _patch_ydl(monkeypatch, info):
    _FakeYDL.info_to_return = info
    monkeypatch.setattr(core_mod.yt_dlp, "YoutubeDL", _FakeYDL)


def test_summary_report_lists_succeeded_and_failed():
    s = DownloadSummary(succeeded=["A", "B"], failed=["C"])
    report = s.report()
    assert "Baixadas: 2" in report
    assert "A" in report and "B" in report
    assert "Falharam: 1" in report
    assert "C" in report


def test_summary_ok_true_when_some_succeed_and_none_fail():
    assert DownloadSummary(succeeded=["A"]).ok is True
    assert DownloadSummary(succeeded=["A"], failed=["B"]).ok is False
    assert DownloadSummary().ok is False


def test_download_single_video_records_title(monkeypatch, tmp_path):
    _patch_ydl(monkeypatch, {"title": "Song One"})
    summary = download("https://youtu.be/abc", str(tmp_path), "mp3")
    assert summary.succeeded == ["Song One"]
    assert summary.failed == []


def test_download_playlist_counts_entries_and_failures(monkeypatch, tmp_path):
    _patch_ydl(monkeypatch, {"entries": [{"title": "One"}, None, {"title": "Three"}]})
    summary = download("https://www.youtube.com/playlist?list=PL1", str(tmp_path), "mp3")
    assert summary.succeeded == ["One", "Three"]
    assert len(summary.failed) == 1


def test_download_passes_noplaylist_based_on_url(monkeypatch, tmp_path):
    _patch_ydl(monkeypatch, {"title": "X"})
    download("https://www.youtube.com/watch?v=abc&list=PL1", str(tmp_path), "mp3")
    assert _FakeYDL.last_opts["noplaylist"] is True


def test_download_creates_output_dir(monkeypatch, tmp_path):
    _patch_ydl(monkeypatch, {"title": "X"})
    target = tmp_path / "new" / "nested"
    download("https://youtu.be/abc", str(target), "mp3")
    assert target.exists()


def test_download_raises_when_ffmpeg_missing(tmp_path):
    import pytest
    with pytest.raises(FileNotFoundError, match="ffmpeg"):
        download(
            "https://youtu.be/abc", str(tmp_path), "mp3",
            ffmpeg_location=str(tmp_path / "nope" / "ffmpeg.exe"),
        )


def test_download_handles_download_error_gracefully(monkeypatch, tmp_path):
    from yt_dlp.utils import DownloadError

    class _RaisingYDL(_FakeYDL):
        def extract_info(self, url, download):
            raise DownloadError("vídeo indisponível")

    monkeypatch.setattr(core_mod.yt_dlp, "YoutubeDL", _RaisingYDL)
    summary = download(
        "https://youtu.be/bad", str(tmp_path), "mp3",
        ffmpeg_location=r"C:\ffmpeg\ffmpeg.exe",
    )
    assert summary.ok is False
    assert summary.failed and "indisponível" in summary.failed[0]


def test_download_applies_soundcloud_cookie_override(monkeypatch, tmp_path):
    _patch_ydl(monkeypatch, {"title": "SC"})
    download(
        "https://soundcloud.com/a/b", str(tmp_path), "mp3",
        ffmpeg_location=r"C:\ffmpeg\ffmpeg.exe",
        auth=AuthConfig(mode="browser", browser="chrome"),
    )
    assert _FakeYDL.last_opts["cookiesfrombrowser"] == ("chrome",)


def test_download_youtube_has_no_cookie_override(monkeypatch, tmp_path):
    _patch_ydl(monkeypatch, {"title": "Y"})
    download(
        "https://youtu.be/abc", str(tmp_path), "mp3",
        ffmpeg_location=r"C:\ffmpeg\ffmpeg.exe",
        auth=AuthConfig(mode="browser", browser="chrome"),
    )
    assert "cookiesfrombrowser" not in _FakeYDL.last_opts


def test_download_unknown_provider_raises(tmp_path):
    import pytest
    with pytest.raises(ValueError, match="não suportado"):
        download(
            "https://example.com/x", str(tmp_path), "mp3",
            ffmpeg_location=r"C:\ffmpeg\ffmpeg.exe",
        )
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_core.py -v`
Expected: FAIL no import (`cannot import name 'AuthConfig'` ainda usado OK, mas) — na prática falha porque `download` ainda não aceita `auth` e não roteia provider (ex.: `test_download_applies_soundcloud_cookie_override`, `test_download_unknown_provider_raises`).

- [ ] **Step 3: Reescrever `core.py`**

REPLACE the ENTIRE contents of `src/music_downloader/core.py` with exactly:
```python
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
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
    except DownloadError as exc:
        summary.failed.append(f"{url}: {exc}")
        return summary
    _collect(info, summary)
    return summary
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_core.py -v`
Expected: 11 passed.

- [ ] **Step 5: Rodar a suíte completa (garante que nada quebrou)**

Run: `.\.venv\Scripts\python.exe -m pytest -v`
Expected: tudo passa exceto a integração (deselected). cli ainda passa porque `main` chama `download(url, output, fmt)` sem `auth` (compatível). Se algum teste de cli falhar aqui, NÃO conserte agora — a Task 4 ajusta o cli.

- [ ] **Step 6: Commit**

```powershell
git add src/music_downloader/core.py tests/test_core.py
git commit -m "refactor: route downloads through providers with auth config"
```

---

## Task 4: Flags de cookies no CLI

**Files:**
- Modify: `src/music_downloader/cli.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Reescrever `tests/test_cli.py`**

REPLACE the ENTIRE contents of `tests/test_cli.py` with exactly:
```python
import pytest

import music_downloader.cli as cli_mod
from music_downloader.cli import _auth_from_args, build_parser, main
from music_downloader.core import DownloadSummary
from music_downloader.providers import AuthConfig


def _parse(argv):
    return build_parser().parse_args(argv)


def test_defaults_are_mp3_and_downloads_dir():
    args = _parse(["https://youtu.be/abc"])
    assert args.url == "https://youtu.be/abc"
    assert args.format == "mp3"
    assert args.output == "downloads"


def test_accepts_flac_and_custom_output():
    args = _parse(["URL", "-f", "flac", "-o", "C:/Music"])
    assert args.format == "flac"
    assert args.output == "C:/Music"


def test_invalid_format_exits():
    with pytest.raises(SystemExit):
        _parse(["URL", "-f", "ogg"])


def test_auth_default_is_browser_chrome():
    assert _auth_from_args(_parse(["URL"])) == AuthConfig(mode="browser", browser="chrome")


def test_auth_browser_override():
    assert _auth_from_args(_parse(["URL", "--browser", "firefox"])) == AuthConfig(
        mode="browser", browser="firefox"
    )


def test_auth_cookiefile():
    assert _auth_from_args(_parse(["URL", "--cookies", "c.txt"])) == AuthConfig(
        mode="cookiefile", cookiefile="c.txt"
    )


def test_auth_no_cookies():
    assert _auth_from_args(_parse(["URL", "--no-cookies"])) == AuthConfig(mode="none")


def test_invalid_browser_exits():
    with pytest.raises(SystemExit):
        _parse(["URL", "--browser", "netscape"])


def test_main_returns_zero_on_success(monkeypatch, capsys):
    monkeypatch.setattr(
        cli_mod, "download",
        lambda url, output, fmt, auth: DownloadSummary(succeeded=["Song"]),
    )
    code = main(["https://youtu.be/abc"])
    assert code == 0
    assert "Song" in capsys.readouterr().out


def test_main_returns_one_when_failures(monkeypatch):
    monkeypatch.setattr(
        cli_mod, "download",
        lambda url, output, fmt, auth: DownloadSummary(succeeded=[], failed=["X"]),
    )
    assert main(["https://youtu.be/abc"]) == 1


def test_main_reports_missing_ffmpeg_cleanly(monkeypatch, capsys):
    def _raise(url, output, fmt, auth):
        raise FileNotFoundError("ffmpeg não encontrado em 'X'. Instale o ffmpeg ou adicione-o ao PATH.")
    monkeypatch.setattr(cli_mod, "download", _raise)
    code = main(["https://youtu.be/abc"])
    assert code == 1
    assert "ffmpeg" in capsys.readouterr().out


def test_main_reports_unknown_provider_cleanly(monkeypatch, capsys):
    def _raise(url, output, fmt, auth):
        raise ValueError("Provedor não suportado: 'x'. Suportados: YouTube, SoundCloud")
    monkeypatch.setattr(cli_mod, "download", _raise)
    code = main(["https://example.com/x"])
    assert code == 1
    assert "suportado" in capsys.readouterr().out.lower()
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_cli.py -v`
Expected: FAIL com `ImportError: cannot import name '_auth_from_args'`.

- [ ] **Step 3: Reescrever `cli.py`**

REPLACE the ENTIRE contents of `src/music_downloader/cli.py` with exactly:
```python
"""Interface de linha de comando do music-downloader."""

from __future__ import annotations

import argparse

from .core import download
from .formats import supported_formats
from .providers import AuthConfig

_BROWSERS = ["chrome", "firefox", "edge", "brave"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mdl",
        description="Baixa o melhor áudio do YouTube ou SoundCloud e converte para "
        "MP3/FLAC. O arquivo original é sempre guardado.",
    )
    parser.add_argument(
        "url", help="URL de um vídeo/faixa ou playlist (YouTube ou SoundCloud)"
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
    except (FileNotFoundError, ValueError) as exc:
        print(f"Erro: {exc}")
        return 1
    print(summary.report())
    return 0 if summary.ok else 1
```

- [ ] **Step 4: Rodar e ver passar (cli + suíte completa)**

Run: `.\.venv\Scripts\python.exe -m pytest -v`
Expected: tudo passa (integração deselected).

- [ ] **Step 5: Commit**

```powershell
git add src/music_downloader/cli.py tests/test_cli.py
git commit -m "feat: CLI cookie flags (--browser/--cookies/--no-cookies)"
```

---

## Task 5: Resiliência a falha de cookies (retry sem cookies)

**Files:**
- Modify: `src/music_downloader/core.py`
- Modify: `tests/test_core.py`

Objetivo: se a leitura de cookies do navegador falhar (ex.: App-Bound Encryption do Chrome → erro de DPAPI/decrypt), avisar de forma clara e tentar de novo SEM cookies, em vez de quebrar ou ficar mudo.

- [ ] **Step 1: Escrever o teste que falha (append em `tests/test_core.py`)**

Append to `tests/test_core.py`:
```python
def test_download_retries_without_cookies_on_cookie_error(monkeypatch, tmp_path, capsys):
    constructions = []

    class _CookieFailYDL(_FakeYDL):
        def __init__(self, opts):
            constructions.append(dict(opts))
            self._opts = opts

        def extract_info(self, url, download):
            if "cookiesfrombrowser" in self._opts:
                raise Exception("Failed to decrypt with DPAPI: could not read cookies")
            return {"title": "SC Track"}

    monkeypatch.setattr(core_mod.yt_dlp, "YoutubeDL", _CookieFailYDL)
    summary = download(
        "https://soundcloud.com/a/b", str(tmp_path), "mp3",
        ffmpeg_location=r"C:\ffmpeg\ffmpeg.exe",
        auth=AuthConfig(mode="browser", browser="chrome"),
    )
    assert summary.succeeded == ["SC Track"]
    assert len(constructions) == 2
    assert "cookiesfrombrowser" in constructions[0]
    assert "cookiesfrombrowser" not in constructions[1]
    out = capsys.readouterr().out.lower()
    assert "cookies" in out
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_core.py::test_download_retries_without_cookies_on_cookie_error -v`
Expected: FAIL (a exceção genérica de cookies não é tratada; o `Exception` propaga e o teste não vê o retry).

- [ ] **Step 3: Implementar o retry em `core.py`**

In `src/music_downloader/core.py`, add this helper right ABOVE the `download` function:
```python
def _is_cookie_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(s in msg for s in ("cookie", "dpapi", "decrypt"))


def _extract(url: str, opts: dict) -> dict | None:
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=True)
```
Then REPLACE the `try/except DownloadError` block inside `download` (the part from `summary = DownloadSummary()` to `return summary` at the end) with exactly:
```python
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
```

- [ ] **Step 4: Rodar e ver passar (arquivo + suíte completa)**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_core.py -v`
Expected: 12 passed.
Run: `.\.venv\Scripts\python.exe -m pytest -v`
Expected: tudo passa (integração deselected).

- [ ] **Step 5: Commit**

```powershell
git add src/music_downloader/core.py tests/test_core.py
git commit -m "feat: warn and retry without cookies when browser cookie read fails"
```

---

## Task 6: Validação real do SoundCloud, teste de integração e docs

**Files:**
- Modify: `tests/test_integration.py`
- Modify: `README.md`

- [ ] **Step 1: Smoke test real — SoundCloud público SEM cookies (determinístico)**

Run (PowerShell) — faixa Creative Commons; `--no-cookies` evita depender do navegador:
```powershell
.\.venv\Scripts\python.exe -m music_downloader.cli "https://soundcloud.com/forss/flickermood" -o "downloads" -f mp3 --no-cookies
Get-ChildItem downloads
```
VALIDATE: imprime "Baixadas: 1"; a pasta `downloads/` contém o `.mp3` final E o arquivo original (ex.: `.m4a`/`.opus`/`.mp3`). Confirme tags/capa abrindo o arquivo, se possível.

- [ ] **Step 2: Smoke test com cookies do Chrome (qualidade máxima — pode falhar pelo caveat do Chrome)**

Run (PowerShell):
```powershell
.\.venv\Scripts\python.exe -m music_downloader.cli "https://soundcloud.com/forss/flickermood" -o "downloads" -f flac
```
OBSERVE: se os cookies do Chrome forem lidos, pode baixar o original (lossless) quando o artista permite. Se aparecer o aviso "não consegui ler cookies do navegador", está funcionando o fallback — nesse caso o caminho confiável é exportar um cookies.txt e usar `--cookies cookies.txt`. Registre no relatório qual caminho funcionou (cookies do Chrome OK, ou caiu no fallback). Não trave o plano se o Chrome falhar — é esperado pelo caveat.

- [ ] **Step 3: Limpar os arquivos de teste (são gitignored)**

Run (PowerShell):
```powershell
Get-ChildItem downloads -File | ForEach-Object { Remove-Item -LiteralPath $_.FullName -Force }
```

- [ ] **Step 4: Adicionar teste de integração do SoundCloud (append em `tests/test_integration.py`)**

Append to `tests/test_integration.py`:
```python
@pytest.mark.integration
def test_real_soundcloud_download_creates_mp3_and_keeps_original(tmp_path):
    from music_downloader.providers import AuthConfig

    summary = download(
        "https://soundcloud.com/forss/flickermood", str(tmp_path), "mp3",
        auth=AuthConfig(mode="none"),
    )
    assert summary.ok
    assert list(tmp_path.glob("*.mp3")), "deveria gerar um .mp3"
    audio = []
    for ext in ("*.mp3", "*.m4a", "*.opus", "*.webm", "*.flac", "*.wav"):
        audio += list(tmp_path.glob(ext))
    # além do mp3 convertido, deve haver o arquivo original guardado
    assert len(audio) >= 2, "deveria guardar o arquivo original além do mp3 convertido"
```

- [ ] **Step 5: Rodar o teste de integração sob demanda**

Run: `.\.venv\Scripts\python.exe -m pytest -m integration -v`
Expected: 2 passed (YouTube + SoundCloud).

- [ ] **Step 6: Confirmar que a suíte normal ignora integração**

Run: `.\.venv\Scripts\python.exe -m pytest -v`
Expected: integração deselected; todos os unitários passam.

- [ ] **Step 7: Atualizar o `README.md`**

REPLACE the ENTIRE contents of `README.md` with exactly:
```markdown
# music-downloader

CLI que baixa o melhor áudio do **YouTube** ou **SoundCloud** e converte para
MP3 ou FLAC, guardando sempre o arquivo original (máxima fidelidade). Metadados e
capa são embutidos no arquivo final. Você passa só o link — o programa detecta o
provedor automaticamente.

> **Qualidade.** O YouTube serve áudio lossy (~160 kbps Opus no melhor caso). No
> SoundCloud, o arquivo **original** do artista (potencialmente WAV/FLAC) só é
> liberado com login — por isso o suporte a cookies abaixo. O original baixado é
> sempre guardado; FLAC preserva sem segunda perda, MP3 320 é a opção compatível.

## Requisitos

- Python 3.12+
- ffmpeg (em `C:\ffmpeg\ffmpeg.exe` ou no PATH)

## Instalação

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
```

## Uso

```powershell
# YouTube — MP3 320 (padrão)
mdl "https://www.youtube.com/watch?v=VIDEO_ID"

# SoundCloud — FLAC (usa cookies do Chrome por padrão p/ máxima qualidade)
mdl "https://soundcloud.com/artista/faixa" -f flac

# Playlist / set
mdl "https://soundcloud.com/artista/sets/minha-playlist"
```

| Opção           | Descrição                                            | Padrão       |
|-----------------|------------------------------------------------------|--------------|
| `url`           | URL de vídeo/faixa ou playlist (YouTube/SoundCloud)  | (obrigatório)|
| `-f, --format`  | `mp3` ou `flac`                                      | `mp3`        |
| `-o, --output`  | Pasta de destino                                     | `downloads`  |
| `--browser`     | Navegador p/ cookies do SoundCloud (chrome/firefox/edge/brave) | `chrome` |
| `--cookies`     | Caminho de um `cookies.txt` (fallback confiável)     | —            |
| `--no-cookies`  | Não usar cookies (qualidade pública)                 | desligado    |

### Cookies do SoundCloud (qualidade máxima)

Para baixar o arquivo original/lossless do SoundCloud é preciso estar logado. Por
padrão o programa lê os cookies do **Chrome**. O Chrome recente (v127+) pode
bloquear essa leitura (App-Bound Encryption); se aparecer o aviso de falha de
cookies, exporte um `cookies.txt` (extensão de navegador "Get cookies.txt") e use:

```powershell
mdl "https://soundcloud.com/artista/faixa" -f flac --cookies "C:/caminho/cookies.txt"
```

## Testes

```powershell
.\.venv\Scripts\python.exe -m pytest                  # unitários (sem rede)
.\.venv\Scripts\python.exe -m pytest -m integration   # downloads reais
```
```

- [ ] **Step 8: Commit**

```powershell
git add tests/test_integration.py README.md
git commit -m "test: SoundCloud integration test and updated docs"
```

---

## Self-review (cobertura da spec)

- Roteamento automático por link → Task 1 (`detect_provider`), Task 3 (core usa provider).
- SoundCloud via yt-dlp, mesmo motor → Task 1/3.
- Detecção YouTube vs SoundCloud vs desconhecido → Task 1 (matches, detect_provider) + Task 3/4 (erro no core e cli).
- Playlist por provedor (YouTube list=/playlist; SoundCloud /sets/) → Task 1.
- Cookies do Chrome por padrão + fallback cookies.txt + --no-cookies → Task 1 (overrides), Task 4 (flags).
- Falha de cookies → aviso claro + continua → Task 5.
- bestaudio + guardar original + metadados + capa (inalterado) → herdado de downloader.py (Task 2 só adiciona merge).
- Provedor desconhecido → erro claro → Task 1 (ValueError) + Task 4 (cli imprime, retorna 1).
- YouTube idêntico → Task 3 mantém comportamento; testes de YouTube preservados.
- Testes unitários sem rede + integração opcional → Tasks 1-6.
```
