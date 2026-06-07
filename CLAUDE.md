# CLAUDE.md

Guia para o Claude trabalhar neste repositório. (Leitura humana: ver
[README.md](README.md). Mergulho profundo: [docs/](docs/).)

## O que é

CLI em Python que baixa o melhor áudio de **YouTube**, **SoundCloud** ou **Spotify**,
converte para **MP3** ou **FLAC**, e embute metadados + capa. O usuário passa **só o
link**; o programa detecta a fonte automaticamente e sempre guarda o arquivo original.

Prioridade do projeto: **máxima qualidade de áudio** + **todos os metadados**.

## Como rodar (regra de ouro)

O `python` puro é um stub quebrado nesta máquina. **Sempre** use o interpretador do venv:

```powershell
.\.venv\Scripts\python.exe -m music_downloader.cli "<URL>" [-f mp3|flac] [-o PASTA]
```

Exemplos:
```powershell
.\.venv\Scripts\python.exe -m music_downloader.cli "https://www.youtube.com/watch?v=ID"
.\.venv\Scripts\python.exe -m music_downloader.cli "https://soundcloud.com/artista/faixa" -f flac
.\.venv\Scripts\python.exe -m music_downloader.cli "https://open.spotify.com/track/ID"
```

Para baixar música a pedido do usuário, **use a skill de projeto** `music-downloader`
(em `.claude/skills/music-downloader/`).

## Setup

- **ffmpeg**: `C:\ffmpeg\ffmpeg.exe` (ou no PATH) — obrigatório p/ conversão.
- **venv + deps**: `.\.venv\Scripts\python.exe -m pip install -e .` (instala
  `yt-dlp`, `mutagen`, `spotipy`).
- **Credenciais do Spotify**: `SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET`. O CLI
  carrega automaticamente um `.env` na raiz (gitignored; já existe neste repo).

## Arquitetura (mapa rápido)

```
src/music_downloader/
  cli.py         # argparse, flags, carrega .env, main(); entry point `mdl`
  core.py        # download(): roteia e orquestra; resumo (DownloadSummary)
  providers.py   # YouTube/SoundCloud (download direto) + detect_provider + AuthConfig
  spotify.py     # RESOLVER: metadados via spotipy (NÃO baixa áudio do Spotify)
  matching.py    # acha o vídeo do YouTube equivalente (match por duração)
  tagging.py     # embute metadados + capa do Spotify (mutagen)
  downloader.py  # monta as opções do yt-dlp (bestaudio, keepvideo, postprocessors)
  formats.py     # registro mp3/flac
  naming.py      # template de saída + sanitização
```

Fluxo: `cli → core.download → (Spotify? resolver: spotify+matching+yt-dlp+tagging) |
(YouTube/SoundCloud: detect_provider + yt-dlp)`. Detalhes:
[docs/architecture.md](docs/architecture.md).

## Conceitos que NÃO são óbvios (gotchas)

- **Spotify é DRM**: o áudio nunca vem do Spotify. Pega-se metadados do Spotify e
  baixa-se o áudio equivalente do YouTube (match por duração ±7s). Teto de qualidade =
  YouTube (~160 kbps Opus). Não prometa lossless via Spotify.
- **SoundCloud lossless** só com login (cookies do navegador, padrão Chrome). Chrome
  v127+ pode bloquear a leitura de cookies → o CLI avisa e segue na qualidade pública;
  fallback confiável: `--cookies cookies.txt`.
- **mutagen** é obrigatório p/ embutir capa em FLAC/M4A (no MP3 é o ffmpeg).
- O original (`.webm`/`.m4a`/`.opus`) é sempre guardado junto do convertido.

## Testes

```powershell
.\.venv\Scripts\python.exe -m pytest                 # unitários (sem rede)
.\.venv\Scripts\python.exe -m pytest -m integration  # downloads reais (precisa rede/creds)
```

TDD é o padrão do projeto. Specs e planos ficam em `docs/superpowers/`.

## Convenções

- Mensagens ao usuário em português; código/identificadores em inglês.
- Cada módulo tem uma responsabilidade única; mantenha assim.
- Novos provedores: adicionar uma classe em `providers.py` e registrar em `PROVIDERS`
  (ver [docs/architecture.md](docs/architecture.md)). Spotify-like (resolvers) seguem o
  padrão de `spotify.py` + `matching.py`.
- Nunca commitar `.env`, `.cache` (token do spotipy) ou `downloads/` (já gitignored).
