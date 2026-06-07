# music-downloader

CLI que baixa o melhor áudio do **YouTube**, **SoundCloud** ou **Spotify** e
converte para MP3 ou FLAC, guardando sempre o arquivo original (máxima fidelidade).
Metadados e capa são embutidos no arquivo final. Você passa só o link — o programa
detecta a fonte automaticamente.

> **Qualidade & Spotify.** O áudio do Spotify é DRM e não pode ser baixado. Para
> links do Spotify, o programa usa os **metadados do Spotify** (título, artista,
> álbum, capa) e baixa o áudio equivalente do **YouTube** (match por duração) — o
> teto de qualidade é o do YouTube (~160 kbps Opus). YouTube/SoundCloud baixam
> direto; no SoundCloud o original do artista (potencialmente lossless) sai com login.

## Requisitos

- Python 3.12+
- ffmpeg (em `C:\ffmpeg\ffmpeg.exe` ou no PATH)
- Para Spotify: credenciais (veja abaixo)

## Instalação

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
```

## Uso

```powershell
# YouTube
mdl "https://www.youtube.com/watch?v=VIDEO_ID"

# SoundCloud (FLAC; cookies do Chrome por padrão p/ máxima qualidade)
mdl "https://soundcloud.com/artista/faixa" -f flac

# Spotify (faixa, álbum ou playlist)
mdl "https://open.spotify.com/track/TRACK_ID"
mdl "https://open.spotify.com/album/ALBUM_ID" -f flac
mdl "https://open.spotify.com/playlist/PLAYLIST_ID"
```

| Opção           | Descrição                                            | Padrão       |
|-----------------|------------------------------------------------------|--------------|
| `url`           | Link do YouTube, SoundCloud ou Spotify               | (obrigatório)|
| `-f, --format`  | `mp3` ou `flac`                                      | `mp3`        |
| `-o, --output`  | Pasta de destino                                     | `downloads`  |
| `--browser`     | Navegador p/ cookies do SoundCloud                   | `chrome`     |
| `--cookies`     | Caminho de um `cookies.txt` (fallback SoundCloud)    | —            |
| `--no-cookies`  | Não usar cookies (qualidade pública)                 | desligado    |

### Credenciais do Spotify

Para links do Spotify, crie um app gratuito em
<https://developer.spotify.com/dashboard>, pegue o **Client ID** e **Client Secret**
e defina as variáveis de ambiente:

```powershell
$env:SPOTIFY_CLIENT_ID = "seu_client_id"
$env:SPOTIFY_CLIENT_SECRET = "seu_client_secret"
```

(Para persistir, use as Variáveis de Ambiente do Windows.)

## Testes

```powershell
.\.venv\Scripts\python.exe -m pytest                  # unitários (sem rede)
.\.venv\Scripts\python.exe -m pytest -m integration   # downloads reais
```
