# Music Downloader CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** CLI em Python que baixa o melhor áudio do YouTube (vídeo ou playlist), guarda sempre o original e entrega uma cópia convertida em MP3 320 ou FLAC, com metadados e capa embutidos.

**Architecture:** Pacote Python com layout `src/`, dividido em módulos de responsabilidade única (`formats`, `naming`, `downloader`, `core`, `cli`). O `downloader` encapsula o `yt-dlp` usado como biblioteca; o `core` orquestra vídeo único vs. playlist e agrega o resumo. Funções puras (config de opções, seleção de formato, detecção de playlist, sanitização) são testadas sem rede; o `core` é testado com mock do `yt-dlp`.

**Tech Stack:** Python 3.12, yt-dlp (lib), ffmpeg (já instalado em `C:\ffmpeg\ffmpeg.exe`), pytest.

---

## File Structure

```
music-downloader/
  pyproject.toml                     # metadata, deps, entry point `mdl`, pytest config
  src/music_downloader/
    __init__.py
    formats.py                       # registro de formatos (mp3, flac) -> params ffmpeg
    naming.py                        # template de saída + sanitização de nome
    downloader.py                    # monta opções do yt-dlp + localiza ffmpeg
    core.py                          # orquestra: is_playlist, download, DownloadSummary
    cli.py                           # argparse + main()
  tests/
    test_formats.py
    test_naming.py
    test_downloader.py
    test_core.py
    test_cli.py
    test_integration.py              # opcional, marcado @pytest.mark.integration
  README.md
```

**Convenção de comandos (Windows / PowerShell):** depois da Task 0, sempre use o Python do venv por caminho absoluto para evitar o stub da Store:
- Python: `.\.venv\Scripts\python.exe`
- pytest: `.\.venv\Scripts\python.exe -m pytest`

---

## Task 0: Ambiente e scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `src/music_downloader/__init__.py`
- Create: `.gitignore`

- [ ] **Step 1: Instalar Python 3.12 via winget**

Run (PowerShell):
```powershell
winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements
```
Expected: instalação concluída (ou "já instalado").

- [ ] **Step 2: Localizar o python.exe real e criar o venv**

Run (PowerShell):
```powershell
$py = (Get-ChildItem "$env:LOCALAPPDATA\Programs\Python\Python3*\python.exe" | Select-Object -First 1).FullName
"Usando: $py"
& $py -m venv .venv
.\.venv\Scripts\python.exe --version
```
Expected: imprime `Python 3.12.x` a partir do venv. (Se `$py` vier vazio, abrir nova janela de terminal para atualizar o PATH e repetir o Get-ChildItem.)

- [ ] **Step 3: Instalar dependências no venv**

Run (PowerShell):
```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install yt-dlp pytest
.\.venv\Scripts\python.exe -m pip show yt-dlp | Select-String Version
```
Expected: pip atualiza e yt-dlp/pytest instalam; imprime a versão do yt-dlp.

- [ ] **Step 4: Criar `.gitignore`**

Create `.gitignore`:
```
.venv/
__pycache__/
*.pyc
downloads/
*.egg-info/
.pytest_cache/
```

- [ ] **Step 5: Criar `pyproject.toml`**

Create `pyproject.toml`:
```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "music-downloader"
version = "0.1.0"
description = "Baixa o melhor áudio do YouTube e converte para MP3/FLAC"
requires-python = ">=3.12"
dependencies = ["yt-dlp"]

[project.scripts]
mdl = "music_downloader.cli:main"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = ["integration: testes que acessam a rede (rodar sob demanda)"]
addopts = "-m 'not integration'"
```

- [ ] **Step 6: Criar o pacote vazio**

Create `src/music_downloader/__init__.py`:
```python
"""music-downloader: baixa o melhor áudio do YouTube e converte para MP3/FLAC."""

__version__ = "0.1.0"
```

- [ ] **Step 7: Instalar o pacote em modo editável e verificar pytest**

Run (PowerShell):
```powershell
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m pytest
```
Expected: instala o pacote; pytest roda e reporta "no tests ran" (sem erros de coleta).

- [ ] **Step 8: Commit**

```powershell
git add .gitignore pyproject.toml src/music_downloader/__init__.py
git commit -m "chore: scaffold Python package and dev environment"
```

---

## Task 1: Registro de formatos (`formats.py`)

**Files:**
- Create: `src/music_downloader/formats.py`
- Test: `tests/test_formats.py`

- [ ] **Step 1: Escrever os testes que falham**

Create `tests/test_formats.py`:
```python
import pytest
from music_downloader.formats import get_format, supported_formats, FormatSpec


def test_supported_formats_lists_mp3_and_flac():
    assert set(supported_formats()) == {"mp3", "flac"}


def test_get_mp3_has_320_quality():
    fmt = get_format("mp3")
    assert isinstance(fmt, FormatSpec)
    assert fmt.codec == "mp3"
    assert fmt.quality == "320"
    assert fmt.ext == "mp3"


def test_get_flac_is_lossless_without_quality():
    fmt = get_format("flac")
    assert fmt.codec == "flac"
    assert fmt.quality is None
    assert fmt.ext == "flac"


def test_unknown_format_raises_valueerror():
    with pytest.raises(ValueError, match="não suportado"):
        get_format("ogg")
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_formats.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'music_downloader.formats'`.

- [ ] **Step 3: Implementar `formats.py`**

Create `src/music_downloader/formats.py`:
```python
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
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_formats.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```powershell
git add src/music_downloader/formats.py tests/test_formats.py
git commit -m "feat: format registry for mp3 and flac"
```

---

## Task 2: Nomeação de arquivos (`naming.py`)

**Files:**
- Create: `src/music_downloader/naming.py`
- Test: `tests/test_naming.py`

- [ ] **Step 1: Escrever os testes que falham**

Create `tests/test_naming.py`:
```python
from music_downloader.naming import sanitize_filename, OUTPUT_TEMPLATE


def test_replaces_windows_invalid_chars():
    assert sanitize_filename('a/b:c*d?e"f<g>h|i\\j') == "a_b_c_d_e_f_g_h_i_j"


def test_collapses_whitespace_and_trims():
    assert sanitize_filename("  hello   world  ") == "hello world"


def test_strips_trailing_dots():
    assert sanitize_filename("name...") == "name"


def test_empty_becomes_untitled():
    assert sanitize_filename("   ") == "untitled"


def test_output_template_uses_artist_title_with_uploader_fallback():
    assert OUTPUT_TEMPLATE == "%(artist,uploader)s - %(title)s.%(ext)s"
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_naming.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'music_downloader.naming'`.

- [ ] **Step 3: Implementar `naming.py`**

Create `src/music_downloader/naming.py`:
```python
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
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_naming.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```powershell
git add src/music_downloader/naming.py tests/test_naming.py
git commit -m "feat: filename sanitization and output template"
```

---

## Task 3: Detecção de playlist (`core.is_playlist`)

**Files:**
- Create: `src/music_downloader/core.py`
- Test: `tests/test_core.py`

- [ ] **Step 1: Escrever os testes que falham**

Create `tests/test_core.py`:
```python
from music_downloader.core import is_playlist


def test_plain_video_url_is_not_playlist():
    assert is_playlist("https://www.youtube.com/watch?v=abc123") is False


def test_video_with_list_param_is_treated_as_single_video():
    # watch?v=...&list=... -> intenção é o vídeo; não baixa a playlist toda
    assert is_playlist("https://www.youtube.com/watch?v=abc123&list=PL999") is False


def test_playlist_url_is_playlist():
    assert is_playlist("https://www.youtube.com/playlist?list=PL999") is True


def test_youtu_be_short_link_is_not_playlist():
    assert is_playlist("https://youtu.be/abc123") is False
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_core.py -v`
Expected: FAIL com `ImportError: cannot import name 'is_playlist'`.

- [ ] **Step 3: Implementar `is_playlist` em `core.py`**

Create `src/music_downloader/core.py`:
```python
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
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_core.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```powershell
git add src/music_downloader/core.py tests/test_core.py
git commit -m "feat: playlist URL detection"
```

---

## Task 4: Opções do yt-dlp e localização do ffmpeg (`downloader.py`)

**Files:**
- Create: `src/music_downloader/downloader.py`
- Test: `tests/test_downloader.py`

- [ ] **Step 1: Escrever os testes que falham**

Create `tests/test_downloader.py`:
```python
from pathlib import Path

from music_downloader.downloader import build_ydl_options, find_ffmpeg
from music_downloader.formats import get_format


def _pp(opts, key):
    return next(p for p in opts["postprocessors"] if p["key"] == key)


def test_selects_best_audio_and_keeps_original():
    opts = build_ydl_options("out", get_format("mp3"), "C:/ffmpeg/ffmpeg.exe", noplaylist=True)
    assert opts["format"] == "bestaudio/best"
    assert opts["keepvideo"] is True          # mantém o original
    assert opts["writethumbnail"] is True
    assert opts["ignoreerrors"] is True
    assert opts["noplaylist"] is True


def test_outtmpl_points_into_output_dir_with_template():
    opts = build_ydl_options("mymusic", get_format("mp3"), "ff", noplaylist=True)
    assert opts["outtmpl"] == str(Path("mymusic") / "%(artist,uploader)s - %(title)s.%(ext)s")


def test_mp3_postprocessor_uses_320_quality():
    opts = build_ydl_options("out", get_format("mp3"), "ff", noplaylist=True)
    extract = _pp(opts, "FFmpegExtractAudio")
    assert extract["preferredcodec"] == "mp3"
    assert extract["preferredquality"] == "320"


def test_flac_postprocessor_omits_quality():
    opts = build_ydl_options("out", get_format("flac"), "ff", noplaylist=True)
    extract = _pp(opts, "FFmpegExtractAudio")
    assert extract["preferredcodec"] == "flac"
    assert "preferredquality" not in extract


def test_includes_metadata_and_thumbnail_postprocessors():
    opts = build_ydl_options("out", get_format("mp3"), "ff", noplaylist=True)
    keys = [p["key"] for p in opts["postprocessors"]]
    assert "FFmpegMetadata" in keys
    assert "EmbedThumbnail" in keys


def test_ffmpeg_location_is_passed():
    opts = build_ydl_options("out", get_format("mp3"), "C:/ffmpeg/ffmpeg.exe", noplaylist=True)
    assert opts["ffmpeg_location"] == "C:/ffmpeg/ffmpeg.exe"


def test_find_ffmpeg_returns_a_path(monkeypatch):
    monkeypatch.setattr("shutil.which", lambda name: None)
    assert find_ffmpeg() == r"C:\ffmpeg\ffmpeg.exe"
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_downloader.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'music_downloader.downloader'`.

- [ ] **Step 3: Implementar `downloader.py`**

Create `src/music_downloader/downloader.py`:
```python
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
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_downloader.py -v`
Expected: 7 passed.

- [ ] **Step 5: Commit**

```powershell
git add src/music_downloader/downloader.py tests/test_downloader.py
git commit -m "feat: yt-dlp options builder and ffmpeg discovery"
```

---

## Task 5: Orquestração do download e resumo (`core.download`, `DownloadSummary`)

**Files:**
- Modify: `src/music_downloader/core.py`
- Modify: `tests/test_core.py`

- [ ] **Step 1: Escrever os testes que falham (mock do yt-dlp)**

Append to `tests/test_core.py`:
```python
import music_downloader.core as core_mod
from music_downloader.core import DownloadSummary, download


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
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_core.py -v`
Expected: FAIL com `ImportError: cannot import name 'DownloadSummary'`.

- [ ] **Step 3: Implementar `download` e `DownloadSummary` em `core.py`**

Replace the full contents of `src/music_downloader/core.py` with:
```python
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
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_core.py -v`
Expected: 10 passed (4 de is_playlist + 6 novos).

- [ ] **Step 5: Commit**

```powershell
git add src/music_downloader/core.py tests/test_core.py
git commit -m "feat: download orchestration with playlist-aware summary"
```

---

## Task 6: Interface de linha de comando (`cli.py`)

**Files:**
- Create: `src/music_downloader/cli.py`
- Test: `tests/test_cli.py`

- [ ] **Step 1: Escrever os testes que falham**

Create `tests/test_cli.py`:
```python
import pytest

import music_downloader.cli as cli_mod
from music_downloader.cli import build_parser, main
from music_downloader.core import DownloadSummary


def test_defaults_are_mp3_and_downloads_dir():
    args = build_parser().parse_args(["https://youtu.be/abc"])
    assert args.url == "https://youtu.be/abc"
    assert args.format == "mp3"
    assert args.output == "downloads"


def test_accepts_flac_and_custom_output():
    args = build_parser().parse_args(["URL", "-f", "flac", "-o", "C:/Music"])
    assert args.format == "flac"
    assert args.output == "C:/Music"


def test_invalid_format_exits():
    with pytest.raises(SystemExit):
        build_parser().parse_args(["URL", "-f", "ogg"])


def test_main_returns_zero_on_success(monkeypatch, capsys):
    monkeypatch.setattr(
        cli_mod, "download",
        lambda url, output, fmt: DownloadSummary(succeeded=["Song"]),
    )
    code = main(["https://youtu.be/abc"])
    assert code == 0
    assert "Song" in capsys.readouterr().out


def test_main_returns_one_when_failures(monkeypatch):
    monkeypatch.setattr(
        cli_mod, "download",
        lambda url, output, fmt: DownloadSummary(succeeded=[], failed=["X"]),
    )
    assert main(["URL"]) == 1
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_cli.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'music_downloader.cli'`.

- [ ] **Step 3: Implementar `cli.py`**

Create `src/music_downloader/cli.py`:
```python
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
    summary = download(args.url, args.output, args.format)
    print(summary.report())
    return 0 if summary.ok else 1
```

- [ ] **Step 4: Rodar e ver passar**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_cli.py -v`
Expected: 5 passed.

- [ ] **Step 5: Rodar a suíte completa**

Run: `.\.venv\Scripts\python.exe -m pytest -v`
Expected: todos passam (formats 4, naming 5, core 10, downloader 7, cli 5).

- [ ] **Step 6: Commit**

```powershell
git add src/music_downloader/cli.py tests/test_cli.py
git commit -m "feat: CLI entry point with mp3/flac and output options"
```

---

## Task 7: Smoke test real, teste de integração opcional e README

**Files:**
- Create: `tests/test_integration.py`
- Create: `README.md` (sobrescreve o atual)

- [ ] **Step 1: Smoke test manual (download real)**

Run (PowerShell) — usa um vídeo Creative Commons curto:
```powershell
.\.venv\Scripts\python.exe -m music_downloader.cli "https://www.youtube.com/watch?v=aqz-KE-bpKQ" -o "downloads" -f mp3
```
Expected: imprime "Baixadas: 1" e a pasta `downloads/` contém o `.mp3` final **e** o arquivo original (`.webm`/`.m4a`). Abrir o `.mp3` e confirmar que toca e tem capa/tags.

Nota: o entry point `mdl` também funciona após `pip install -e .` (rode `.\.venv\Scripts\mdl.exe "<URL>"`).

- [ ] **Step 2: Escrever o teste de integração (marcado)**

Create `tests/test_integration.py`:
```python
from pathlib import Path

import pytest

from music_downloader.core import download


@pytest.mark.integration
def test_real_download_creates_mp3_and_keeps_original(tmp_path):
    summary = download(
        "https://www.youtube.com/watch?v=aqz-KE-bpKQ", str(tmp_path), "mp3"
    )
    assert summary.ok
    assert list(tmp_path.glob("*.mp3")), "deveria gerar um .mp3"
    originais = list(tmp_path.glob("*.webm")) + list(tmp_path.glob("*.m4a"))
    assert originais, "deveria guardar o arquivo original"
```

- [ ] **Step 3: Rodar o teste de integração sob demanda**

Run: `.\.venv\Scripts\python.exe -m pytest -m integration -v`
Expected: 1 passed (baixa de verdade; leva alguns segundos).

- [ ] **Step 4: Confirmar que a suíte normal continua ignorando integração**

Run: `.\.venv\Scripts\python.exe -m pytest -v`
Expected: integração NÃO roda (deselected); demais testes passam.

- [ ] **Step 5: Escrever o README**

Create `README.md`:
```markdown
# music-downloader

CLI que baixa o melhor áudio do YouTube e converte para MP3 ou FLAC,
guardando sempre o arquivo original (máxima fidelidade). Metadados e capa
são embutidos no arquivo final.

> O YouTube só serve áudio comprimido (lossy, ~160 kbps Opus no melhor caso).
> O original guardado é o teto de fidelidade. FLAC preserva esse áudio sem
> uma segunda perda; MP3 320 é a melhor opção para compatibilidade/tamanho.

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
# MP3 320 (padrão) na pasta downloads/
mdl "https://www.youtube.com/watch?v=VIDEO_ID"

# FLAC, em pasta específica
mdl "https://www.youtube.com/watch?v=VIDEO_ID" -f flac -o "C:/Users/User/Music"

# Playlist inteira
mdl "https://www.youtube.com/playlist?list=PLAYLIST_ID"
```

| Opção            | Descrição                                  | Padrão       |
|------------------|--------------------------------------------|--------------|
| `url`            | URL de vídeo ou playlist                    | (obrigatório)|
| `-f, --format`   | `mp3` ou `flac`                             | `mp3`        |
| `-o, --output`   | Pasta de destino                            | `downloads`  |

## Testes

```powershell
.\.venv\Scripts\python.exe -m pytest            # unitários (sem rede)
.\.venv\Scripts\python.exe -m pytest -m integration   # download real
```
```

- [ ] **Step 6: Commit**

```powershell
git add tests/test_integration.py README.md
git commit -m "test: optional integration test and usage docs"
```

---

## Resumo de cobertura (self-review)

- Stack Python + yt-dlp + ffmpeg → Task 0, 4.
- bestaudio + guardar original sempre → Task 4 (`format`, `keepvideo`), validado na Task 7.
- Conversão MP3 320 / FLAC selecionável → Task 1, 4, 6.
- URL de vídeo e playlist (autodetecção) → Task 3, 5.
- Metadados + capa embutidos → Task 4 (FFmpegMetadata, EmbedThumbnail), validado na Task 7.
- Saída via `-o` (padrão `downloads`) → Task 6.
- Tratamento de erro de playlist (continua + resumo) → Task 4 (`ignoreerrors`), Task 5 (`_collect`, summary).
- Testes unitários sem rede + integração opcional → Tasks 1-6, 7.
```
