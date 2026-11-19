<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Quadro societário (dados abertos do CNPJ — Receita Federal)

`receita_socios` · tipo **bruta** · ativa

Lê, em streaming e arquivo a arquivo, as partes de Sócios do dump mensal do CNPJ e guarda só os sócios dos CNPJs já presentes na base (SCM/SMP/STFC/SeAC). Não guarda o dump (vários GB).

## Resumo

| | |
|---|---|
| Módulo / arquivo | `sources.receita_socios.collect` |
| Publicável | sim (exposição: aberta) |
| Política de falha | usar_ultima_valida |
| Cadência (origem atualiza) | mensal |
| Coleta hoje → alvo | mensal → mensal |
| Frescor máximo | 45d |
| Chaves | `cnpj` |
| Entradas | — |
| Amostra de teste | `tests/fixtures/raw/receita_socios/` |

## Origem e licença

- **URL:** https://arquivos.receitafederal.gov.br/index.php/s/YggdBLfdninEJX9
- **Formato:** zip/csv (;-delimitado, latin-1, sem cabeçalho) via WebDAV Nextcloud
- **Licença:** nao_verificado
- **Uso comercial:** `nao_verificado`
- **Termos:** https://www.gov.br/receitafederal/pt-br/acesso-a-informacao/dados-abertos/cadastros/cnpj
- **Evidência / ressalvas:** Dados abertos do CNPJ da Receita (Decreto 8.777/2016). A página oficial exige JavaScript e não foi lida em 2026-10-13; o domínio antigo dadosabertos.rfb.gov.br saiu do ar (confirmado em 2026-09). Contém pessoa física (CPF parcialmente mascarado): LGPD.

## Saídas

- **Normalizado (normalized/):** `summary/receita_socios.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `by_cnpj_basico[cnpj8][].nome_socio` ⚠️ dado pessoal/contato | str | Nome do sócio (PF) ou razão social (PJ). | PF: dado pessoal (LGPD); só entra em produto agregado. | grupos_societarios → grupos_societarios.json.gz#by_cnpj |
| `by_cnpj_basico[cnpj8][].cnpj_cpf_socio` ⚠️ dado pessoal/contato | str | Para PJ: 8 dígitos do CNPJ básico do sócio; para PF: CPF com 3 primeiros e 2 últimos dígitos ocultos. | CPF mascarado pela Receita; colisões possíveis (falso positivo). | — |
| `by_cnpj_basico[cnpj8][].identificador_socio` | str | 1=Pessoa Jurídica, 2=Pessoa Física, 3=Estrangeiro. | — | — |
| `by_cnpj_basico[cnpj8][].qualificacao_socio` | str | Código de qualificação do sócio (administrador, sócio, etc.). | — | — |
| `by_cnpj_basico[cnpj8][].data_entrada_sociedade` | str | Data de entrada do sócio na sociedade. | — | — |
| `by_cnpj_basico[cnpj8][].faixa_etaria` ⚠️ dado pessoal/contato | str | Código da faixa etária do sócio PF (1=0–12 … 9=80+; 0=não se aplica). | — | — |
| `dump_reference` | str | Mês de referência (AAAA-MM) do dump da Receita usado. | — | — |

## Limites

Sócio PJ só traz o CNPJ básico (8 dígitos). Sócio oculto/indireto não aparece. Cadência efetiva: download no máximo a cada 30 dias (marcador em data/receita_socios_last_run.json).

## Retenção

- **normalizado:** 2 versões (dado pessoal)

## Quem usa

- **Fontes derivadas:** `socios_grupos`

## Pendências (nao_verificado)

- Licença/termos do conjunto CNPJ não lidos (página exige JavaScript).
- Revisão jurídica do uso de nome/CPF mascarado de PF.
