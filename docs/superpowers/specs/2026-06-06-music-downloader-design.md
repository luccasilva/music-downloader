# Design: music-downloader

**Data:** 2026-06-06
**Status:** Aprovado (design) — pronto para plano de implementação

## Visão geral

CLI em **Python** que baixa áudio do YouTube na melhor fonte disponível, guarda
o arquivo original (máxima fidelidade) e entrega também uma versão convertida no
formato escolhido. O MVP suporta conversão para **MP3 320 kbps** e **FLAC**, com
metadados e capa embutidos. Funciona com URL de vídeo único ou de playlist.

Prioridade central do produto: **máxima qualidade de áudio possível** (caso de uso
de produção musical), **escolha de formato** e **robustez** de download.

## Stack

- **Python** — linguagem do CLI (casa nativamente com o yt-dlp, usado como biblioteca).
- **yt-dlp** — motor de download (padrão-ouro, atualizado com frequência, controle
  fino de seleção de formato).
- **ffmpeg** — conversão/extração de áudio e embutição de metadados/capa.
  Já instalado em `C:\ffmpeg\ffmpeg.exe`; o caminho é passado explicitamente ao yt-dlp.

## Verdade sobre qualidade (premissa de design)

O YouTube só serve áudio **lossy**: no melhor caso **Opus ~160 kbps** (WebM) ou
**AAC ~128 kbps** (m4a). Esse é o teto — nenhuma ferramenta extrai mais do que existe.
Consequências de design:

- **Máxima fidelidade absoluta** = o arquivo **original** (Opus/m4a) sem reconversão.
  Por isso o original é **sempre guardado**.
- **FLAC** preserva o áudio decodificado bit a bit (sem segunda perda) → mais fiel
  que MP3 para produção. **MP3 320** re-codifica (lossy→lossy) → melhor para
  compatibilidade/tamanho.

## Interface (CLI)

```
mdl <URL> [-o PASTA] [-f {mp3,flac}]
```

- `<URL>` — link de vídeo **ou** playlist (detectado automaticamente).
- `-o, --output` — pasta de destino. Padrão: `./downloads` (criada se não existir).
- `-f, --format` — formato da cópia convertida. Padrão: `mp3`. MVP: `mp3`, `flac`.
- O **original** é sempre baixado e guardado, independentemente do `-f`.

### Comportamento de qualidade

- Seleção sempre `bestaudio`.
- `mp3` → 320 kbps.
- `flac` → lossless a partir da melhor fonte.
- Metadados completos: título, artista + **thumbnail como capa (album art)**.

## Arquitetura

Módulos isolados, cada um com responsabilidade única e testável de forma independente.

1. **`cli.py`** — parseia argumentos (`argparse`), valida entrada, chama o orquestrador.
2. **`downloader.py`** — encapsula o yt-dlp como biblioteca: seleção de formato
   (`bestaudio`), pós-processadores (extrair áudio, embutir metadados, embutir
   thumbnail), hooks de progresso. Recebe a config de formato do registro.
3. **`formats.py`** — registro de formatos: mapeia nome (`mp3`, `flac`) → parâmetros
   de codec/qualidade do ffmpeg. Adicionar formato no futuro = adicionar uma entrada.
4. **`naming.py`** — gera nome `Artista - Título.ext`; higieniza caracteres inválidos
   no Windows (`< > : " / \ | ? *`).
5. **`core.py`** — orquestrador: detecta vídeo único vs. playlist, agrega resultados
   e erros, monta o resumo final.

### Fluxo de dados

```
URL
 → cli.py (valida)
 → core.py (detecta playlist?)
 → downloader.py (yt-dlp baixa bestaudio → guarda original
                  → ffmpeg converte p/ formato escolhido
                  → embute tags + capa)
 → arquivos na pasta de saída
 → resumo no terminal
```

## Tratamento de erros

- URL inválida, vídeo privado/indisponível/com restrição de idade → mensagem clara.
- ffmpeg ausente → detectar e avisar (caminho passado explicitamente ao yt-dlp).
- **Playlist**: se uma música falhar, continua as demais e exibe resumo no fim
  (X baixadas, Y falharam, com os títulos que falharam).

## Testes

- **Unitários sem rede** (mock do yt-dlp):
  - parsing/validação de argumentos
  - mapeamento do registro de formatos
  - higienização de nome de arquivo
  - detecção vídeo vs. playlist
- **Integração opcional** (sob demanda, fora do fluxo normal de CI): baixa um vídeo
  curto Creative Commons e verifica que o original + a cópia convertida são gerados.

## Dependências a instalar

- Python (runtime) + ambiente virtual
- yt-dlp (pip)
- ffmpeg (já instalado)

## Fora de escopo (futuro)

- Busca por nome (`artista - música`) em vez de URL.
- Formatos adicionais (WAV, m4a/Opus por cópia direta).
- Configuração persistente (pasta/formato padrão salvos).
