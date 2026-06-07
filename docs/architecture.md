# Arquitetura

Referência técnica do music-downloader. Para uso prático, ver [usage.md](usage.md).

## Visão geral

O programa recebe um link e entrega áudio convertido com metadados. Dois tipos de fonte:

- **Providers (download direto):** YouTube e SoundCloud — o yt-dlp baixa o áudio
  diretamente da URL.
- **Resolver (Spotify):** o áudio do Spotify é DRM e não pode ser baixado; em vez disso
  resolvemos os metadados no Spotify e baixamos o áudio equivalente do YouTube.

## Módulos

| Módulo | Responsabilidade |
|--------|------------------|
| `cli.py` | Parseia argumentos, carrega `.env`, monta `AuthConfig`, chama `core.download`, imprime o resumo. Entry point `mdl` e `python -m music_downloader.cli`. |
| `core.py` | `download()` — roteia (Spotify vs provider), executa o yt-dlp (com retry de cookies), agrega `DownloadSummary`. Helpers: `_run_download`, `_final_filepath`, `_download_spotify`. |
| `providers.py` | `Provider` (protocolo), `YouTubeProvider`, `SoundCloudProvider`, `detect_provider`, `AuthConfig`. Cada provider sabe `matches`, `is_playlist` e `ydl_overrides`. |
| `spotify.py` | `is_spotify_url`, `SpotifyTrack`, `SpotifyClient` (spotipy, credenciais por env), `resolve` (track/album/playlist), `MissingCredentialsError`. |
| `matching.py` | `Candidate`, `best_match` (puro, por proximidade de duração ±7s), `search_youtube` (ytsearch), `find_youtube`. |
| `tagging.py` | `apply` — grava metadados do Spotify e embute a capa (mutagen) em mp3/flac, inclui ISRC. |
| `downloader.py` | `build_ydl_options` (bestaudio, keepvideo, postprocessors: extrair áudio + metadados + thumbnail; mescla overrides do provider), `find_ffmpeg`. |
| `formats.py` | `FormatSpec`, `FORMATS` (mp3=320, flac=lossless), `get_format`, `supported_formats`. |
| `naming.py` | `OUTPUT_TEMPLATE` (`%(artist,uploader)s - %(title)s.%(ext)s`), `sanitize_filename`. |

## Fluxo de dados

### YouTube / SoundCloud (provider direto)
```
URL → cli → core.download
  → _ensure_ffmpeg
  → detect_provider(url)              # YouTube | SoundCloud | ValueError
  → build_ydl_options(... overrides=provider.ydl_overrides(auth),
                       noplaylist=not provider.is_playlist(url))
  → _run_download (yt-dlp; retry sem cookies se a leitura falhar)
  → _collect → DownloadSummary
```

### Spotify (resolver)
```
URL → cli → core.download → is_spotify_url? sim → _download_spotify
  → SpotifyClient.from_env().resolve(url)   # [SpotifyTrack...]
  → para cada faixa:
      find_youtube(track)                   # ytsearch + best_match(±7s)
      → build_ydl_options + _run_download    # baixa o vídeo do YouTube
      → _final_filepath(info)                # caminho do arquivo convertido
      → tagging.apply(track, [path])         # metadados + capa do Spotify
  → DownloadSummary
```

## Decisões de design

- **Qualidade**: sempre `bestaudio`; o arquivo original é mantido (`keepvideo=True`).
  FLAC preserva sem segunda perda; MP3 320 é a opção compatível. Spotify herda o teto
  do YouTube.
- **Metadados**: `FFmpegMetadata` + `EmbedThumbnail` no fluxo direto; no Spotify, as tags
  são sobrescritas com os dados do Spotify (incl. ISRC) e a capa do Spotify é embutida.
- **Resiliência**: em playlists/álbuns, a falha de um item não interrompe os demais
  (resumo no fim). Falha de cookies do navegador → aviso + retry sem cookies. Falha de
  tagging → aviso, sem abortar o lote.
- **Match do Spotify**: por proximidade de duração (±7s) entre os candidatos do YouTube,
  para evitar remixes/lives/versões aceleradas.

## Como adicionar um provedor

### Provider de download direto (estilo YouTube/SoundCloud)
1. Em `providers.py`, criar uma classe com `name`, `matches(url)` (por host),
   `is_playlist(url)` e `ydl_overrides(auth)`.
2. Registrar a instância em `PROVIDERS`.
3. Testar detecção, regra de playlist e overrides em `tests/test_providers.py`.

### Resolver (estilo Spotify, fonte sem download direto)
1. Criar um módulo que resolve a URL em metadados + uma estratégia de busca de áudio.
2. Adicionar um desvio em `core.download` (como `is_spotify_url`).
3. Reaproveitar `matching`/`tagging` ou criar equivalentes.

## Testes

- Unitários (sem rede), mockando o yt-dlp/spotipy: `tests/test_*.py`.
- Integração (marcada `@pytest.mark.integration`, opt-in): downloads reais; o teste do
  Spotify pula sem credenciais.

## Limitações conhecidas

- Spotify: teto de qualidade do YouTube; sem áudio lossless do Spotify (DRM).
- `spotify.link` (short links) não é resolvido ainda.
- Nome de arquivo de downloads do Spotify herda o título do YouTube (as **tags** são as
  do Spotify, corretas); renomear pelo `Artista - Título` do Spotify é um aprimoramento
  futuro.
