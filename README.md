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
