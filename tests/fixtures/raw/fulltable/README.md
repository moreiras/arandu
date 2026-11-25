# fulltable — RouteViews/RIS RIB (MRT TABLE_DUMP_V2) — SINTÉTICO
Os dumps reais (`rib.AAAAMMDD.HHMM.bz2`, > 1 GB) não são retidos. Estas amostras são MRT TABLE_DUMP_V2 binários
válidos gerados por `cut_fixtures.py` (PEER_INDEX_TABLE + RIB_IPV4/IPV6_UNICAST) com prefixos de documentação
(RFC 5737/3849) e ASNs reservados (64496–64540): rota default (ignorada), prefixo com 2 caminhos, prepend, communities
padrão e um /8. É exatamente o formato que o `mrtparse` lê da fonte real.

`rib-{v4,v6}-moas-{a,b}.sample.mrt.bz2` (grupo `m`, sem dado real): dois coletores fictícios para a origem múltipla (MOAS).
No v4, `198.51.100.0/24` tem duas origens no mesmo dump (A: 64510 e 64512), `203.0.113.0/24` tem uma origem em cada coletor
(A: 64511, B: 64513) e `192.0.2.0/25` tem a mesma nos dois (64520, sem MOAS). No v6, `2001:db8::/32` diverge entre coletores
(A: 64510, B: 64515) e `2001:db8:1::/48` diverge dentro de A (64511 e 64514).
