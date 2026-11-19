# fulltable — RouteViews/RIS RIB (MRT TABLE_DUMP_V2) — SINTÉTICO
Os dumps reais (`rib.AAAAMMDD.HHMM.bz2`, > 1 GB) não são retidos. Estas amostras são MRT TABLE_DUMP_V2 binários
válidos gerados por `cut_fixtures.py` (PEER_INDEX_TABLE + RIB_IPV4/IPV6_UNICAST) com prefixos de documentação
(RFC 5737/3849) e ASNs reservados (64496–64540): rota default (ignorada), prefixo com 2 caminhos, prepend, communities
padrão e um /8. É exatamente o formato que o `mrtparse` lê da fonte real.
