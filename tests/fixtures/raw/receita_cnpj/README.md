# Amostra sintética: Receita Federal, dados abertos do CNPJ

**Origem:** sintética, no formato original dos arquivos mensais (`Estabelecimentos*`, `Empresas*`, `Simples`, `Municipios`, `Naturezas`, `Cnaes`), do compartilhamento oficial
em arquivos.receitafederal.gov.br. O layout (30 colunas de Estabelecimentos; 7 de Empresas e de Simples; aspas, `;`, latin-1, sem cabeçalho) foi conferido em 2026-11-07 contra
o arquivo real `Estabelecimentos1.zip` do mês 2026-10 e contra os metadados da Receita; **nenhuma linha real foi copiada**.
**Data:** 2026-11-07. **Recorte:** 7 estabelecimentos de 7 empresas fictícias (CNPJs inventados, sem dígito verificador válido) que cobrem: CNPJ no universo das outorgas; CNAE 61
principal; CNAE 61 só no secundário; falso positivo do pré-filtro (`"61` no CEP e no DDD de uma loja); empresário individual (natureza 2135) com nome fantasia; empresa de outro ramo fora do universo.
**Anonimizado:** tudo é inventado. O e-mail do primeiro estabelecimento existe só para provar que o coletor não o guarda.
