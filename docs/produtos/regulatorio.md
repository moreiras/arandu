<!-- Gerado por scripts/gen_docs.py a partir de catalog/. Não edite; altere o catálogo e regenere. -->

# Regulatório complementar

`regulatorio` · produto

Compromissos do FUST por município, UF, programa e edital; multas constituídas por empresa (SCM, SMP, STFC e SeAC); quadro de faixas de frequência (PDFF) e satélites com direito de exploração, a partir dos dados abertos da Anatel. Cadastro regulatório, não desembolso nem licença; o FUST não tem operadora.

## Resumo

| | |
|---|---|
| Módulo (hoje) | `products.regulatorio.build` |
| Chaves de junção | `ibge`, `cnpj` |
| Cenários de teste (dataset sintético) | — |

## Entradas

- fonte [anatel_fust](../fontes/anatel_fust.md) — uso comercial: `permitido`
- fonte [anatel_multas](../fontes/anatel_multas.md) — uso comercial: `permitido`
- fonte [anatel_pdff](../fontes/anatel_pdff.md) — uso comercial: `permitido`
- fonte [anatel_satelites](../fontes/anatel_satelites.md) — uso comercial: `permitido`
- fonte [ibge_censo_pnad](../fontes/ibge_censo_pnad.md) — uso comercial: `nao_verificado`

## Saídas

- **Publicado:** `regulatorio/fust.json.gz`, `regulatorio/multas.json.gz`, `regulatorio/faixas.json.gz`, `regulatorio/satelites.json.gz`

## Dicionário de campos

| Campo | Tipo | Significado | Tratamento | Publicado em |
|---|---|---|---|---|
| `fust.municipios[ibge]` | dict | Compromissos do FUST no município (total, atendidos, a vencer, em apuração), investimento previsto, compromissos por programa e por tipo, por 10 mil habitantes. | Cadastro da Anatel; investimento é o previsto, não o desembolsado. Município sem compromisso não aparece. | regulatorio → regulatorio/fust.json.gz#municipios |
| `fust.ufs[uf] / brasil` | dict | Totais da UF e do país (compromissos, situação, investimento, municípios com compromisso). | — | regulatorio → regulatorio/fust.json.gz#ufs; regulatorio → regulatorio/fust.json.gz#brasil |
| `fust.programas[] / editais[]` | lista | Totais por programa (código e nome) e por edital ou projeto de origem. | — | regulatorio → regulatorio/fust.json.gz#programas; regulatorio → regulatorio/fust.json.gz#editais |
| `fust.casamento / limites / natureza / fonte / data_arquivo` | dict | Compromissos com município no IBGE (e por malha 2010 ou 2022), sem investimento, o que o dado é e não é e a data do arquivo na Anatel. | — | regulatorio → regulatorio/fust.json.gz#casamento; regulatorio → regulatorio/fust.json.gz#limites; regulatorio → regulatorio/fust.json.gz#natureza; regulatorio → regulatorio/fust.json.gz#fonte; regulatorio → regulatorio/fust.json.gz#data_arquivo |
| `multas.empresas[]` | lista | Por empresa (raiz do CNPJ) e grupo de serviço (SCM, SMP, STFC, SeAC), multas constituídas, valor original, pago e saldo devedor atualizado, situações, anos e CNPJ da matriz. | Só pessoa jurídica. Multa constituída não é condenação definitiva (pode estar em recurso, parcelada ou suspensa). | regulatorio → regulatorio/multas.json.gz#empresas |
| `multas.brasil / por_grupo / por_ano` | dict | Totais do país, por grupo de serviço e multas por ano de aplicação e grupo. | — | regulatorio → regulatorio/multas.json.gz#brasil; regulatorio → regulatorio/multas.json.gz#por_grupo; regulatorio → regulatorio/multas.json.gz#por_ano |
| `multas.limites / natureza / fonte / data_arquivo / leitura` | str | O que o dado é e não é, o que ficou de fora (pessoa física, outros serviços) e a data do arquivo na Anatel. | — | regulatorio → regulatorio/multas.json.gz#limites; regulatorio → regulatorio/multas.json.gz#natureza; regulatorio → regulatorio/multas.json.gz#fonte; regulatorio → regulatorio/multas.json.gz#data_arquivo; regulatorio → regulatorio/multas.json.gz#leitura |
| `faixas.faixas[] / referencias[]` | lista | Faixas de frequência em MHz com os serviços destinados e atribuídos no Brasil (caráter primário ou secundário) e as faixas de interesse para a Internet (700 MHz, 3,5 GHz, Wi-Fi 6 GHz...). | É o quadro normativo, não licença. Os nomes das faixas de interesse são referência do Arandurapé. | regulatorio → regulatorio/faixas.json.gz#faixas; regulatorio → regulatorio/faixas.json.gz#referencias |
| `faixas.resumo / limites / natureza / fonte / data_arquivo` | dict | Faixas lidas, com destinação e com atribuição; o que o dado é e não é; a data do arquivo na Anatel. | — | regulatorio → regulatorio/faixas.json.gz#resumo; regulatorio → regulatorio/faixas.json.gz#limites; regulatorio → regulatorio/faixas.json.gz#natureza; regulatorio → regulatorio/faixas.json.gz#fonte; regulatorio → regulatorio/faixas.json.gz#data_arquivo |
| `satelites.direitos[] / ngeo[] / operando[]` | lista | Direitos de exploração de satélite (operadora, satélite, posição, banda, tipo, status, validade), constelações NGEO e satélites em operação comercial. | Direito concedido não é capacidade em uso. Muitas operadoras são estrangeiras e não cruzam com o SICI. | regulatorio → regulatorio/satelites.json.gz#direitos; regulatorio → regulatorio/satelites.json.gz#ngeo; regulatorio → regulatorio/satelites.json.gz#operando |
| `satelites.resumo / limites / natureza / fonte / data_arquivo` | dict | Totais por tipo, status e órbita; direitos vencidos na data do snapshot; o que o dado é e não é; a data do arquivo na Anatel. | — | regulatorio → regulatorio/satelites.json.gz#resumo; regulatorio → regulatorio/satelites.json.gz#limites; regulatorio → regulatorio/satelites.json.gz#natureza; regulatorio → regulatorio/satelites.json.gz#fonte; regulatorio → regulatorio/satelites.json.gz#data_arquivo |
| `snapshot_date / generated_at` | str | Data do snapshot e instante em que o arquivo foi gerado. | — | regulatorio → regulatorio/fust.json.gz#snapshot_date; regulatorio → regulatorio/fust.json.gz#generated_at; regulatorio → regulatorio/multas.json.gz#snapshot_date; regulatorio → regulatorio/multas.json.gz#generated_at; regulatorio → regulatorio/faixas.json.gz#snapshot_date; regulatorio → regulatorio/faixas.json.gz#generated_at; regulatorio → regulatorio/satelites.json.gz#snapshot_date; regulatorio → regulatorio/satelites.json.gz#generated_at |
