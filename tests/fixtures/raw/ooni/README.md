# ooni — medições do OONI no bucket `ooni-data-eu-fra` (SINTÉTICO)
Origem do formato: `https://ooni-data-eu-fra.s3.amazonaws.com/raw/AAAAMMDD/HH/BR/<teste>/AAAAMMDDHH_BR_<teste>.<host>.<n>.jsonl.gz` (JSONL, uma medição por linha), conferido em 2026-11-07 e no `ooni/spec`
(df-000-base e ts-015/018/019/020/023/029/017). Os `.jsonl` desta pasta são **inventados**: ASNs de documentação (RFC 5398, AS64496–AS64498), nomes de rede, `report_id` e resolvedor fictícios, IP de sonda 127.0.0.1 (como o
OONI publica) e URL `exemplo.invalid`. Nenhuma medição real foi copiada. Cada arquivo cobre os casos de borda do teste: veredito de bloqueio por componente, sonda de outro país (descartada), ASN oculto (`AS0`, descartado),
signal com `test_version` <= 0.2.3 (descartado, falso positivo documentado) e webconnectivity com `blocking` falso, nulo e as quatro anomalias. O teste (`tests/sources/test_t1_ooni_bloqueios.py`) comprime os `.jsonl` na hora
e simula a listagem S3 (XML) com `respx`. Licença dos dados reais: CC BY-NC-SA 4.0; nada deles está aqui.
