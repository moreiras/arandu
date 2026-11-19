<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Vigia dos diretórios de numeração (Registro.br e LACNIC)

`ipv4_vigia` · tipo **bruta** · ativa

Varre diariamente as listagens de ftp.registro.br/pub/{numeracao, origin, geoip, geofeed} e ftp.lacnic.net/pub/stats/lacnic{, transfers, critical_infra} e o cabeçalho dos arquivos-chave, e alerta quando surge um padrão de arquivo novo, um arquivo sem data novo ou uma mudança de formato. É o que detecta a bitácora pública da política LAC-2025-5 (aluguel de IPv4) no dia em que for publicada e qualquer mudança nas listas que o Arandurapé lê. Não publica dado: grava a varredura e os alertas em data/ops/vigia/ipv4/.

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.ipv4_vigia.collect` |
| Publicável | não (exposição: nenhuma) |
| Política de falha | opcional |
| Cadência (origem atualiza) | diaria |
| Coleta hoje → alvo | diaria → diaria |
| Frescor máximo | 3d |
| Chaves | — |
| Entradas | — |
| Amostra de teste | `tests/fixtures/raw/ipv4_listas/` |

## Origem e licença

- **URL:** https://ftp.registro.br/pub/ e https://ftp.lacnic.net/pub/stats/lacnic/
- **Formato:** índice HTML do Apache e as primeiras linhas dos arquivos
- **Licença:** nao_verificado
- **Uso comercial:** `nao_verificado`
- **Evidência / ressalvas:** Só listagens e 4 KB de cabeçalho por arquivo (15 requisições por dia, com pausa e User-Agent identificado).

## Saídas


## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `alertas[]` | lista | Novidades desde a varredura anterior: `padrao_novo`, `arquivo_novo`, `padrao_removido`, `cabecalho_mudou`, `diretorio_novo`. | Alerta não é falha da coleta; vai para o log (aviso) e para o arquivo da varredura. Arquivo diário com data nova não é novidade. | — |

## Limites

Só vê o que a listagem do Apache mostra; formato novo dentro de um arquivo já conhecido só aparece se mudar o cabeçalho (comentários e número de colunas).

## Retenção

- **normalizado:** 52 semanas

## Pendências (nao_verificado)

- Termos de uso dos diretórios não declarados; a coleta é só de listagens e cabeçalhos (15 requisições por dia).
