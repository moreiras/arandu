# ipv4_listas — listas de numeração e delegated (SINTÉTICAS) e sub-asignações (HIPOTÉTICO)
`registrobr-transferencias-diretas(-lacnic)`, `registrobr-recuperacao`, `registrobr-recuperados`, `lacnic-transfers.json` e os três `delegated-lacnic-extended-AAAAMMDD.gz` são **sintéticos** (gerados por
`gerar_listas_sinteticas.py`), no formato real medido em 2026-11-02 (Latin-1 e CIDR abreviado no Registro.br; JSON no LACNIC; `registro|cc|tipo|início|quantidade|data|status|opaque-id` no delegated, com
quantidade de IPv4 em endereços). Organizações e blocos inventados (198.18.0.0/15 e 203.0.113.0/24 são de documentação). Casos plantados: lote de blocos na mesma data e partes, CIDR abreviado, pessoa física,
saída para o exterior, registro do LACNIC sem endereço, e no delegated uma troca de titularidade, uma recuperação, uma liberação, bloco novo e removido, mudança de país. Sem dado pessoal real.

`subasignacoes_hipotetico.json` é **HIPOTÉTICO**: não existe bitácora oficial da LAC-2025-5 (aluguel regulado de IPv4) até 2026-11-02, então o esquema (bloco, ASN do receptor, início, fim, cedente, RIR) é suposto. Traz um registro válido
completo, um sem fim, um fora do tamanho permitido (/16), um bloco inválido e um com fim antes do início, para testar o adaptador desativado por padrão.
