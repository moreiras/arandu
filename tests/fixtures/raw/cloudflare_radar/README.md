# cloudflare_radar — respostas da API do Cloudflare Radar (SINTÉTICO)
Origem do formato: `https://api.cloudflare.com/client/v4/radar/` (entities/asns, http/summary/ip_version, http/top/ases, quality/speed/top/ases, bgp/leaks/events, bgp/hijacks/events,
traffic_anomalies, annotations/outages), conferido em 2026-11-09 com token de conta `Account → Radar → Read` (ver `core/radar.py`). Os `.json` desta pasta são **inventados**: ASNs de documentação
(RFC 5398, AS64496–AS64499), nomes fictícios, prefixos de documentação (RFC 5737) e números arbitrários; só a forma dos campos segue a API real (percentuais como string, `top_0`, `result_info`).
Cobrem: IPv6 com dado, 0 % e sem `IPv6` (resposta vazia), lista de ASNs em duas páginas, vazamento e sequestro com RPKI inválido, e quedas vazias. Nada da Cloudflare foi copiado. Licença dos dados reais:
CC BY-NC 4.0.
