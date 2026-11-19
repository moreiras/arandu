# siasg_contratos — respostas da API de dados abertos do Compras.gov.br (SINTÉTICO)
Origem do formato: `https://dadosabertos.compras.gov.br` (`/modulo-contratacoes/3_consultarResultadoItensContratacoes_PNCP_14133`, `/modulo-contratacoes/1.1_consultarContratacoes_PNCP_14133_Id` e
`/modulo-uasg/1_consultarUasg`), conferido em 2026-11-10 (documento OpenAPI `/v3/api-docs` e respostas reais lidas só para conferir nomes e tipos dos campos). Os `.json` desta pasta são **inventados**:
CNPJs fictícios (raízes 11222333, 44555666 e 77888999, com dígitos verificadores válidos), órgãos, unidades, valores e objetos arbitrários; só a forma dos campos segue a API real (paginação com
`totalRegistros`/`totalPaginas`, valores numéricos, data com hora, `situacaoCompraItemResultadoNome` Informado/Cancelado). Cobrem: duas páginas de resultados com um item cancelado e um fornecedor
pessoa física (CPF fictício, que nunca entra), fornecedor sem resultado, detalhe de contratação com as esferas F/E/M e objeto longo, e a tabela de unidades em duas páginas.
Nada do portal foi copiado. Licença dos dados reais: a avaliação está em `catalog/sources/siasg_contratos.yaml` (`licenca` e `nota`).
