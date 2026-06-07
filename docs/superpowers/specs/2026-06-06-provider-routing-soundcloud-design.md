# Design: roteamento por provedor + SoundCloud

**Data:** 2026-06-06
**Status:** Aprovado (design) — pronto para plano de implementação

## Visão geral

Estender o music-downloader para baixar de **SoundCloud** além do YouTube, com
**roteamento automático pelo link**: o usuário passa só a URL e o programa detecta
o provedor e aplica o fluxo correto. A arquitetura fica extensível para mais
provedores depois (Spotify, etc.).

Prioridade central (inalterada): **máxima qualidade de áudio** + **todos os
metadados disponíveis**. No SoundCloud isso depende de autenticação — ver abaixo.

## Premissa técnica (validada)

O `yt-dlp` já suporta SoundCloud nativamente (track, set/playlist, user, search),
usando o **mesmo motor** do YouTube. Logo, a extensão é principalmente um
**roteador de provedores**, não um segundo motor de download.

Validação prática numa faixa pública: sem login, os formatos disponíveis vão até
**AAC 160 kbps** / MP3 128 kbps. O **arquivo original** que o artista subiu
(potencialmente WAV/FLAC/MP3 alto — a verdadeira máxima qualidade) só é liberado
para **usuários autenticados** (yt-dlp: "Original download format is only available
for registered users").

⚠️ **Caveat do Chrome:** o Chrome v127+ usa "App-Bound Encryption" de cookies no
Windows, o que frequentemente quebra a leitura automática pelo yt-dlp (erro DPAPI).
Por isso o design prevê dois caminhos de cookies: automático (do navegador) e
fallback manual confiável (`cookies.txt` exportado).

## Decisões

- **Autenticação SoundCloud:** cookies do navegador, padrão **Chrome**
  (`cookies-from-browser=chrome`).
- **Fallback de cookies:** opção `--cookies CAMINHO` para usar um `cookies.txt`
  exportado, que ignora `--browser`.
- **Se a leitura de cookies falhar:** avisar de forma clara (com instrução do
  fallback) e **continuar** na melhor qualidade pública — não travar o download.
- **Seleção de formato:** `bestaudio/best` para ambos os provedores; autenticado, o
  yt-dlp ranqueia o original do SoundCloud no topo.
- **Guardar o original sempre** (igual ao YouTube; ainda mais valioso no SoundCloud).
- **Conversão:** mesma convenção `-f mp3|flac` (padrão `mp3`).
- **Metadados "tudo":** manter `FFmpegMetadata` (título, artista, gênero, data,
  descrição etc. fornecidos pelo provedor) + `EmbedThumbnail` na maior capa.
- **Provedor desconhecido:** erro claro listando os suportados.

## Arquitetura

Novo módulo `providers.py` com um contrato simples (Protocol/ABC). Cada provider:

- `name: str`
- `matches(url) -> bool` — detecção por domínio.
- `is_playlist(url) -> bool` — regra de playlist do provedor.
- `ydl_overrides(auth: AuthConfig) -> dict` — ajustes do yt-dlp específicos
  (SoundCloud injeta cookies conforme a config de autenticação).

Providers registrados: `YouTubeProvider`, `SoundCloudProvider`.

`detect_provider(url) -> Provider` percorre os providers e retorna o que casa;
se nenhum casar, levanta erro claro ("provedor não suportado: <url>. Suportados:
YouTube, SoundCloud").

### Detecção e playlist por provedor

- **YouTube**: `matches` = host em `youtube.com`/`youtu.be`/`music.youtube.com`.
  `is_playlist` = regra atual (precisa de `list` E (`/playlist` OU sem `v`)).
- **SoundCloud**: `matches` = host em `soundcloud.com`/`on.soundcloud.com`.
  `is_playlist` = caminho contém `/sets/`.

### Autenticação (config)

Uma estrutura simples carrega a intenção de auth do CLI:
- modo `browser` (padrão) + nome do navegador, OU
- modo `cookiefile` + caminho, OU
- `none` (desligado).

`SoundCloudProvider.ydl_overrides(auth)` traduz isso em opções do yt-dlp:
- browser → `{"cookiesfrombrowser": (nome_browser,)}`
- cookiefile → `{"cookiefile": caminho}`
- none → `{}`

`YouTubeProvider.ydl_overrides(auth)` → `{}` (não usa cookies).

## Fluxo de dados

```
URL
 → cli.py (parse; monta AuthConfig a partir de --browser/--cookies/--no-cookies)
 → core.download
     → detect_provider(url)               # YouTube | SoundCloud | erro
     → build_ydl_options(base) + provider.ydl_overrides(auth)
     → provider.is_playlist(url) -> noplaylist
     → yt-dlp baixa bestaudio (original quando autenticado)
        → guarda original → ffmpeg converte → embute metadados + capa
 → arquivos na pasta de saída
 → resumo no terminal
```

## Refatoração do código existente

- **Novo** `src/music_downloader/providers.py`: contrato + YouTubeProvider +
  SoundCloudProvider + detect_provider + AuthConfig.
- **Modificado** `core.py`: `download()` usa `detect_provider` e
  `provider.is_playlist`; recebe um `AuthConfig`. A função `is_playlist` é
  **removida** de core (migra para YouTubeProvider). Mantém DownloadSummary,
  _collect, _ensure_ffmpeg, tratamento de DownloadError.
- **Modificado** `downloader.py`: `build_ydl_options` aceita um dict de
  `overrides` e o mescla nas opções (chaves do provider têm precedência).
- **Modificado** `cli.py`: novas flags `--browser` (choices, padrão chrome),
  `--cookies CAMINHO`, `--no-cookies`; monta `AuthConfig` e repassa ao `download`.

## Tratamento de erros

- Provedor não suportado → `ValueError`/mensagem clara com a lista de suportados;
  CLI imprime e retorna 1.
- Falha ao ler cookies do navegador → o yt-dlp emite o erro; capturar/avisar de
  forma clara com instrução do fallback `--cookies cookies.txt` e seguir na melhor
  qualidade pública (não abortar).
- Faixa privada/indisponível, erro de playlist → comportamento atual mantido
  (DownloadError vira item "falhou"; playlist continua com resumo).

## Testes

- **Unitários sem rede:**
  - `detect_provider`: URLs de YouTube → YouTubeProvider; de SoundCloud →
    SoundCloudProvider; desconhecida → erro.
  - `is_playlist` de cada provider (YouTube: `watch?v=&list=` é single, `/playlist`
    é playlist; SoundCloud: `/sets/` é playlist, faixa simples não).
  - `SoundCloudProvider.ydl_overrides`: modo browser → `cookiesfrombrowser`;
    cookiefile → `cookiefile`; none → vazio. YouTube → vazio.
  - `build_ydl_options` mescla overrides (override do provider entra nas opções).
  - CLI: flags `--browser`/`--cookies`/`--no-cookies` produzem o AuthConfig certo.
- **Integração opcional** (marcada, sob demanda): baixa uma faixa pública CC do
  SoundCloud e verifica que gera o convertido + guarda o original + tem metadados.

## Fora de escopo (futuro)

- Outros provedores (Spotify, Bandcamp, etc.).
- Login por usuário/senha (ficou decidido usar cookies).
- Config persistente do navegador/cookies padrão.
