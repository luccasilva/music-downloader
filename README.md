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
