# receita_socios — dump CNPJ da Receita Federal (Socios*.zip)
Origem: https://arquivos.receitafederal.gov.br (compartilhamento Nextcloud, WebDAV), arquivos `Socios0.zip…`.
O dump real traz nomes de pessoas físicas; **esta amostra é SINTÉTICA** (nomes fictícios, CPFs mascarados à
maneira da RFB) e segue o layout documentado em cnpj-metadados.pdf: CSV `;`-delimitado, latin-1, sem cabeçalho,
11 colunas. Os CNPJs básicos 19438160, 17131007 e 18362941 são os das outorgas de `anatel_outorgas`.
Há 1 linha de empresa fora da base e 1 linha malformada para exercitar o filtro.
