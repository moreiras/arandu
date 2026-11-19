# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Shodan: constantes e classes de risco, compartilhadas pela coleta e pelo produto.

Só a API principal, só CONTAGENS: `GET https://api.shodan.io/shodan/host/count?key=...&query=asn:AS<N>&facets=port:20` devolve `{"total": N, "matches": [], "facets": {...}}`
sem listar hosts (nunca lista de IPs nem host individual). O `total` e as contagens das facetas são de SERVIÇOS observados (banners), não de IPs únicos: um host com
duas portas conta duas vezes no total. Para UMA porta, a contagem é a de hosts com a porta aberta (um banner por porta).

Layout da resposta conferido só na documentação pública (https://developer.shodan.io/api); a medição na conta real é a sondagem (`python -m sources.shodan_exposicao.collect --sondar`).
"""
from __future__ import annotations

from typing import Optional

BASE_URL = "https://api.shodan.io"
LICENCA = "Shodan (API principal): uso em produtos permitido com atribuição ao Shodan"
ATRIBUICAO = ("Dados: Shodan (https://www.shodan.io), API principal, contagens por ASN na data da consulta; agregados por UF e proporções são derivados pelo Arandurapé. "
              "Contagem observada pelo Shodan não é prova de vulnerabilidade nem inventário da rede.")

# Classes de risco por porta. Rótulo e portas são decisão do projeto, não do Shodan; o mantenedor pode ajustar.
# (porta -> rótulo do serviço). UDP e TCP dividem a mesma contagem por porta na faceta `port` do Shodan.
CLASSES_DE_RISCO: dict[str, dict[int, str]] = {
    "acesso_remoto": {23: "Telnet", 3389: "RDP", 5900: "VNC"},
    "gestao_de_equipamento": {7547: "TR-069 (CWMP)", 8291: "Winbox (MikroTik)", 8728: "API MikroTik", 161: "SNMP"},
    "banco_de_dados": {3306: "MySQL", 5432: "PostgreSQL", 1433: "SQL Server", 1521: "Oracle", 27017: "MongoDB", 6379: "Redis", 9200: "Elasticsearch", 11211: "Memcached"},
    "compartilhamento": {445: "SMB", 21: "FTP"},
}
ROTULO_CLASSE = {"acesso_remoto": "Acesso remoto", "gestao_de_equipamento": "Gestão de roteador/CPE", "banco_de_dados": "Banco de dados", "compartilhamento": "Compartilhamento de arquivos"}
PORTAS_DE_RISCO: dict[int, tuple[str, str]] = {p: (classe, nome) for classe, d in CLASSES_DE_RISCO.items() for p, nome in d.items()}

TOP_PORTAS = 20          # facetas `port:N` da consulta geral (as mais vistas do ASN)
TOP_VULNS = 20           # faceta `vuln:N`, só se o plano da conta permitir
CONSULTA_GERAL = "asn:AS{asn}"
CONSULTA_RISCO = "asn:AS{asn} port:" + ",".join(str(p) for p in sorted(PORTAS_DE_RISCO))


def numero(valor) -> Optional[int]:
    try:
        return None if valor is None else int(valor)
    except (TypeError, ValueError):
        return None


def faceta(resposta: Optional[dict], nome: str) -> list[dict]:
    """Lista [{value, count}] da faceta `nome`; vazia se a resposta não a trouxe."""
    return [x for x in (((resposta or {}).get("facets") or {}).get(nome) or []) if isinstance(x, dict) and x.get("count") is not None]
