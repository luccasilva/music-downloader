---
name: music-downloader
description: Use when the user asks to download a song/track/audio (or a playlist/album) from a YouTube, SoundCloud, or Spotify link in this repo — e.g. "baixa essa música", "download this track", "pega o áudio desse link".
---

# music-downloader

CLI que baixa o melhor áudio de **YouTube**, **SoundCloud** ou **Spotify** e converte
para MP3/FLAC, embutindo metadados + capa. Você passa **só o link** — o programa
detecta a fonte automaticamente. O arquivo original também é sempre guardado.

## Regra de ouro

Sempre invoque o Python pelo venv (o `python` puro é um stub quebrado nesta máquina):

```powershell
.\.venv\Scripts\python.exe -m music_downloader.cli "<URL>" [-f mp3|flac] [-o PASTA]
```

Não tente baixar com `yt-dlp` direto nem reimplementar nada — use sempre o CLI acima.

## Quick reference

| Fonte | Exemplo |
|-------|---------|
| YouTube (vídeo/playlist) | `... -m music_downloader.cli "https://www.youtube.com/watch?v=ID"` |
| SoundCloud (faixa/set) | `... -m music_downloader.cli "https://soundcloud.com/artista/faixa" -f flac` |
| Spotify (track/album/playlist) | `... -m music_downloader.cli "https://open.spotify.com/track/ID"` |

| Flag | Efeito | Padrão |
|------|--------|--------|
| `-f, --format` | `mp3` (320) ou `flac` (lossless) | `mp3` |
| `-o, --output` | pasta de destino | `downloads/` |
| `--browser` | navegador p/ cookies do SoundCloud (chrome/firefox/edge/brave) | `chrome` |
| `--cookies ARQ` | usar um `cookies.txt` (fallback SoundCloud) | — |
| `--no-cookies` | não usar cookies | desligado |

Saída esperada na pasta: o arquivo convertido (mp3/flac, com tags + capa) **e** o
arquivo original (`.webm`/`.m4a`/`.opus`). O CLI imprime `Baixadas: N` + os títulos.

## Pré-requisitos (já configurados neste repo)

- **ffmpeg**: em `C:\ffmpeg\ffmpeg.exe` (ou no PATH). Necessário pra conversão.
- **Spotify**: precisa de `SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET`. O CLI carrega
  automaticamente um arquivo **`.env`** na raiz do repo (já existe aqui, fora do git).
  Sem credenciais, links do Spotify falham com `MissingCredentialsError`.
- Dependências (`yt-dlp`, `mutagen`, `spotipy`) já instaladas no `.venv`. Setup do zero:
  `.\.venv\Scripts\python.exe -m pip install -e .`

## Como cada fonte funciona (gotchas importantes)

- **Spotify é DRM — o áudio NÃO vem do Spotify.** O programa pega os **metadados** do
  Spotify (título, artista, álbum, capa, ISRC, duração) e baixa o áudio equivalente do
  **YouTube**, casando pela duração (±7s). Teto de qualidade = YouTube (~160 kbps Opus).
  Se não houver match confiável, a faixa é reportada como falha (e o lote continua).
- **SoundCloud**: o arquivo **original** do artista (potencialmente lossless) só sai
  **com login**. O CLI usa cookies do Chrome por padrão; se o Chrome bloquear a leitura
  (App-Bound Encryption v127+), ele **avisa e segue** na qualidade pública — aí use
  `--cookies cookies.txt` exportado.
- **YouTube**: baixa direto; máximo ~160 kbps Opus.
- `mutagen` é o que embute capa/metadados em FLAC/M4A (no MP3 é o ffmpeg). Já é dependência.

## Erros comuns

| Sintoma | Causa / correção |
|---------|------------------|
| `Erro: Provedor não suportado` | Link não é YouTube/SoundCloud/Spotify. |
| `Erro: Credenciais do Spotify ausentes` | Falta `.env` com `SPOTIFY_CLIENT_ID/SECRET`. |
| `Erro: ffmpeg não encontrado` | Instale o ffmpeg ou ponha em `C:\ffmpeg\ffmpeg.exe`. |
| `sem match confiável no YouTube` (Spotify) | Nenhum vídeo dentro de ±7s da duração; faixa pulada. |
| `Aviso: não consegui ler cookies do navegador` | Chrome bloqueou os cookies; use `--cookies cookies.txt` p/ máxima qualidade no SoundCloud. |

## Detalhes / referência profunda

Arquitetura por módulo, fluxo de dados e troubleshooting completo: ver
[docs/architecture.md](../../../docs/architecture.md) e [docs/usage.md](../../../docs/usage.md).
