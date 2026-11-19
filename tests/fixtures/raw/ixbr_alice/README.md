# ixbr_alice — API do Alice-LG do IX.br (RECONSTRUÍDOS)
Origem: `https://lg.ix.br/api/v1/{config,status,routeservers,routeservers/{id}/neighbors}` (Alice 6.1.0, medido em 2026-10-30). Formato real, recorte mínimo reconstruído à mão:
3 route servers (um READY, um BUSY, um ERROR), 3 sessões. ASNs de documentação (64496–64497), IPs 203.0.113.0/24 e nomes fictícios; nenhum dado real de membro.
Os `neighbors` trazem `api.cache_status.cached_at` (frescor do cache de vizinhos do Alice, independente do `state` do `/status`, que é o do cache de rotas). `neighbors_RR-rs1-v6` não existe de propósito: o teste simula a falha da consulta.
