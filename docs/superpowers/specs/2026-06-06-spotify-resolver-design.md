# Design: Spotify como resolver (metadados Spotify + áudio YouTube)

**Data:** 2026-06-06
**Status:** Aprovado (design) — pronto para plano de implementação

## Visão geral

Adicionar "suporte a Spotify" ao music-downloader. O usuário passa um link do
Spotify (faixa, playlist ou álbum) e recebe o áudio baixado, convertido e com os
metadados do Spotify embutidos.

## Premissa técnica (validada)

O áudio do Spotify é **DRM (criptografado)** e não pode ser extraído por nenhuma
ferramenta sem quebrar DRM. O yt-dlp **não tem extractor de Spotify** (confirmado).
Portanto "baixar do Spotify" significa, no mundo real:

1. Obter a **identidade/metadados** da faixa via Spotify;
2. Achar a **mesma música no YouTube**;
3. Baixar do YouTube e **aplicar os metadados do Spotify**.

**Consequência de qualidade:** o áudio vem do YouTube → teto ~160 kbps Opus, o
mesmo do fluxo YouTube. O Spotify agrega **identidade correta + metadados ricos**,
não qualidade de áudio. Não existe "original/lossless via Spotify".

## Conceito de arquitetura: resolver, não provider

Diferente de YouTube/SoundCloud (`Provider`s que baixam direto), o Spotify é um
**resolver**: converte o link em (metadados + busca no YouTube) e **delega o
download ao `YouTubeProvider` existente**, re-taggeando o resultado com os dados do
Spotify. Por isso ele NÃO entra na lista `PROVIDERS`; o roteamento o trata à parte.

## Decisões

- **Fonte de metadados:** Web API do Spotify via `spotipy` (fluxo client-credentials).
- **Credenciais:** variáveis de ambiente `SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET`
  (fora do git). Faltando → erro claro com instruções.
- **Match com YouTube:** busca `ytsearch` (top N) e escolhe o candidato pela
  **proximidade de duração**; fora da tolerância → "sem match confiável" (não baixa
  versão errada silenciosamente).
- **Áudio:** YouTube `bestaudio`, **guarda o original**, converte `-f mp3|flac`.
- **Metadados:** do Spotify (título, artistas, álbum, data, nº/total de faixas,
  ISRC) + **capa do Spotify em alta**, sobrescrevendo os do YouTube.
- **Escopo de URL:** faixa, playlist e álbum (+ `spotify:` URI e `spotify.link`).
- **YouTube/SoundCloud:** inalterados.
- **Aprimoramento futuro (fora de escopo):** sourcing alternativo (ex.: SoundCloud
  lossless) quando a faixa existir lá.

## Módulos

- **`spotify.py`** (novo):
  - `is_spotify_url(url) -> bool` — detecta track/album/playlist, `open.spotify.com`,
    `spotify:` URI, `spotify.link`.
  - `SpotifyTrack` (dataclass): `title`, `artists` (list), `album`, `release_date`,
    `track_number`, `total_tracks`, `disc_number`, `duration_ms`, `isrc`, `cover_url`.
  - `SpotifyClient`: monta o spotipy com credenciais do env; `resolve(url) ->
    list[SpotifyTrack]` (faixa→1; álbum/playlist→N, paginando).
  - `MissingCredentialsError` (erro claro quando faltam env vars).
- **`matching.py`** (novo):
  - `best_match(track, candidates) -> Candidate | None` — função **pura**: escolhe o
    candidato com menor diferença de duração dentro da tolerância (ex.: ±7 s);
    `None` se nenhum dentro da tolerância.
  - `find_youtube(track, ydl) -> str | None` — roda `ytsearchN:"artistas título"`
    (download=False), monta candidatos (id/url/duração), aplica `best_match`, retorna
    a URL do YouTube escolhida (ou `None`).
- **`tagging.py`** (novo):
  - `apply(track, filepaths)` — grava os metadados do Spotify e embute a capa do
    Spotify (baixada de `cover_url`) nos arquivos via `mutagen` (mp3 e flac).

## Integração no core

- `core.download` ganha um desvio no topo: `if is_spotify_url(url): return
  _download_spotify(...)` senão segue o fluxo de providers atual.
- Extrair um helper compartilhado `_download_one(url, output_dir, fmt, ffmpeg,
  overrides, noplaylist) -> (titulo, filepaths)` que executa o yt-dlp e **retorna o(s)
  caminho(s) do arquivo gerado** (lendo `info['requested_downloads'][*]['filepath']`
  e o original guardado). O fluxo de providers e o de Spotify usam esse helper.
- `_download_spotify`: resolve as faixas; para cada uma: `find_youtube` →
  `_download_one` (com `YouTubeProvider`) → `tagging.apply` → registra no
  `DownloadSummary`. Item sem match/erro → falha registrada, segue o lote.

## Fluxo de dados

```
URL Spotify
 → core: is_spotify_url? sim
 → SpotifyClient.resolve(url) -> [SpotifyTrack...]
 → para cada faixa:
     matching.find_youtube(track) -> url do YouTube (ou None -> falha)
     → _download_one(url YouTube, fmt) -> arquivos (convertido + original)
     → tagging.apply(track, arquivos)   # metadados + capa do Spotify
 → DownloadSummary (X baixadas, Y falharam)
```

## Tratamento de erros

- Credenciais ausentes/inválidas → `MissingCredentialsError`/mensagem clara com
  como criar o app e setar as env vars; CLI imprime e retorna 1.
- Faixa sem match confiável (duração fora da tolerância / busca vazia) → registra
  falha com o nome da faixa, continua o lote.
- URL Spotify inválida ou erro da API → mensagem clara.
- Playlist/álbum: falha de um item não interrompe os demais; resumo no fim.

## Testes

- **Unit (sem rede):**
  - `is_spotify_url`: track/album/playlist/URI/short vs. não-Spotify.
  - Credenciais: monta cliente a partir do env; falta → `MissingCredentialsError`.
  - `best_match`: dada lista de candidatos com durações, escolhe o mais próximo;
    retorna `None` fora da tolerância. (função pura)
  - `resolve`: parseia respostas mockadas do spotipy (track/album/playlist) em
    `SpotifyTrack`s corretos.
  - `tagging.apply`: grava título/artista/álbum e embute capa (mock do download da
    capa; verifica via mutagen num arquivo de teste).
- **Integração (opt-in, precisa creds + rede, marcada):** resolve uma faixa
  conhecida → match → download → confere arquivo gerado + tags do Spotify + capa.

## Arquivos

- **Novos:** `spotify.py`, `matching.py`, `tagging.py` + testes.
- **Modificados:** `core.py` (desvio Spotify + helper `_download_one` que retorna
  caminhos), `cli.py` (erro de credenciais claro), `pyproject.toml` (dep `spotipy`),
  `README.md`.
- **Inalterados:** `providers.py`, `downloader.py`, `formats.py`, `naming.py`.

## Fora de escopo (futuro)

- Sourcing alternativo de áudio (SoundCloud lossless) para faixas que existam lá.
- Cache de credenciais/config persistente.
- Matching avançado por ISRC além da duração.
