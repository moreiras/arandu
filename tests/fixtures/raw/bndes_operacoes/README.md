# Amostra sintética: BNDES, operações de financiamento não automáticas

**Origem:** sintética, no formato original do recurso "Operações não automáticas" do conjunto `operacoes-financiamento` (dadosabertos.bndes.gov.br, ODbL): CSV latin-1, `;`, aspas,
cabeçalho de 35 colunas, conferido em 2026-11-08 contra o arquivo real (20 MB). **Nenhuma linha real foi copiada**; CNPJs e nomes são inventados.
**Recorte:** 4 operações: duas do mesmo CNPJ básico (11111111, matriz e filial, que entram), uma de empresa de outro ramo e uma de cliente com CNPJ mascarado (`*****222/0001-**`, como nas
operações indiretas), que não entram. `ckan_package_show.sample.json` reproduz o formato da resposta do CKAN (recursos e `metadata_modified`).
