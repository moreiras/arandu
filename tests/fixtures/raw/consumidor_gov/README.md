# consumidor_gov — reclamações finalizadas do Consumidor.gov.br (SINTÉTICA)
`finalizadas_sintetico.zip` é **sintética**: linhas inventadas no leiaute do `finalizadas_AAAA-MM.zip` real do Consumidor.gov.br
(`https://consumidor.gov.br/pages/publicacao/externo/{codigo}/download`, leiaute conferido em 2026-11-07 com o arquivo de 2026-09): um CSV UTF-8 com BOM, separador `;`, CRLF e as 19 colunas
(`Região;UF;Cidade;Sexo;Faixa Etária;Data Finalização;Tempo Resposta;Nome Fantasia;Segmento de Mercado;Área;Assunto;Grupo Problema;Problema;Como Comprou Contratou;Procurou Empresa;Respondida;Situação;Avaliação Reclamação;Nota do Consumidor`).
O arquivo real tem uma linha por reclamação, com sexo e faixa etária de quem reclamou; nada disso é real aqui (empresas e cidades inventadas). Casos plantados: reclamação não respondida (tempo vazio),
não avaliada (sem nota), região com espaço no fim (`S `), cidade que não existe no IBGE, plano de saúde e aparelho de telefonia (outros segmentos, descartados) e linha truncada.
Os arquivos reais (4 a 16 MB o zip, ~120 MB o CSV) não entram no repositório.
