# Uso e troubleshooting

Guia prático do music-downloader. Para a estrutura interna, ver
[architecture.md](architecture.md).

## Comando

```powershell
.\.venv\Scripts\python.exe -m music_downloader.cli "<URL>" [-f mp3|flac] [-o PASTA] [opções de cookies]
```

(Ou, após `pip install -e .`, o atalho `.\.venv\Scripts\mdl.exe "<URL>"`.)

> Use sempre o Python do venv (`.\.venv\Scripts\python.exe`). O `python` puro é um stub.

## Opções

| Opção | Descrição | Padrão |
|-------|-----------|--------|
| `url` (posicional) | Link do YouTube, SoundCloud ou Spotify | obrigatório |
| `-f, --format` | `mp3` (320 kbps) ou `flac` (lossless) | `mp3` |
| `-o, --output` | Pasta de destino | `downloads` |
| `--browser` | Navegador p/ ler cookies do SoundCloud (`chrome`/`firefox`/`edge`/`brave`) | `chrome` |
| `--cookies ARQ` | Caminho de um `cookies.txt` exportado (fallback SoundCloud; ignora `--browser`) | — |
| `--no-cookies` | Não usar cookies (só qualidade pública) | desligado |

## Exemplos

```powershell
# YouTube — MP3 320
.\.venv\Scripts\python.exe -m music_downloader.cli "https://www.youtube.com/watch?v=VIDEO_ID"

# YouTube — playlist inteira
.\.venv\Scripts\python.exe -m music_downloader.cli "https://www.youtube.com/playlist?list=PLAYLIST_ID"

# SoundCloud — FLAC (cookies do Chrome por padrão p/ pegar o original/lossless)
.\.venv\Scripts\python.exe -m music_downloader.cli "https://soundcloud.com/artista/faixa" -f flac

# SoundCloud — com cookies.txt exportado (mais confiável)
.\.venv\Scripts\python.exe -m music_downloader.cli "https://soundcloud.com/artista/faixa" -f flac --cookies "C:/caminho/cookies.txt"

# Spotify — faixa, álbum ou playlist (precisa de credenciais; ver abaixo)
.\.venv\Scripts\python.exe -m music_downloader.cli "https://open.spotify.com/track/TRACK_ID"
.\.venv\Scripts\python.exe -m music_downloader.cli "https://open.spotify.com/album/ALBUM_ID" -f flac
```

## Saída

Na pasta de destino você recebe:
- o **arquivo convertido** (mp3/flac) com **metadados + capa** embutidos;
- o **arquivo original** (`.webm`/`.m4a`/`.opus`) — máxima fidelidade da fonte.

O CLI imprime um resumo:
```
Baixadas: 1
  + Artista - Título
```
Em playlists/álbuns, falhas individuais aparecem em `Falharam:` e não interrompem o resto.

## Setup

### ffmpeg
Necessário para converter/embutir. Tenha `ffmpeg` no PATH ou em `C:\ffmpeg\ffmpeg.exe`.

### Ambiente Python
```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .   # instala yt-dlp, mutagen, spotipy
```

### Credenciais do Spotify
1. Crie um app gratuito em <https://developer.spotify.com/dashboard>.
2. Copie o **Client ID** e o **Client Secret**.
3. Crie um arquivo `.env` na raiz do repositório (já é gitignored):
   ```
   SPOTIFY_CLIENT_ID=seu_client_id
   SPOTIFY_CLIENT_SECRET=seu_client_secret
   ```
O CLI carrega o `.env` automaticamente. Variáveis de ambiente já definidas têm
precedência sobre o `.env`.

## Qualidade por fonte

| Fonte | Áudio | Observação |
|-------|-------|------------|
| YouTube | ~160 kbps Opus (teto) | melhor que o YouTube tem |
| SoundCloud | original do artista (pode ser lossless) **com login**; senão ~160k AAC | use cookies |
| Spotify | = YouTube (~160 kbps) | DRM: áudio vem do YouTube, metadados do Spotify |

## Troubleshooting

| Mensagem | O que significa / como resolver |
|----------|--------------------------------|
| `Erro: Provedor não suportado: ...` | O link não é YouTube/SoundCloud/Spotify. |
| `Erro: Credenciais do Spotify ausentes...` | Crie o `.env` com `SPOTIFY_CLIENT_ID` e `SPOTIFY_CLIENT_SECRET`. |
| `Erro: ffmpeg não encontrado em ...` | Instale o ffmpeg ou coloque em `C:\ffmpeg\ffmpeg.exe`. |
| `sem match confiável no YouTube` (Spotify) | Nenhum vídeo dentro de ±7s da duração da faixa; ela é pulada. |
| `Aviso: não consegui ler cookies do navegador (...)` | O Chrome bloqueou a leitura (App-Bound Encryption). Exporte um `cookies.txt` e use `--cookies`. O download segue na qualidade pública. |
| `Aviso: baixei mas não consegui aplicar metadados de ...` | O áudio foi baixado; só a etapa de tags/capa falhou (ex.: capa indisponível). |

## Testes

```powershell
.\.venv\Scripts\python.exe -m pytest                 # unitários (sem rede)
.\.venv\Scripts\python.exe -m pytest -m integration  # downloads reais (rede; Spotify precisa de creds)
```
