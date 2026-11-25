# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Resumo nacional da análise de roteamento (Panorama técnico): estado RPKI das rotas brasileiras e as
contagens de saúde da tabela, num arquivo de poucos KB.

O `routing_analysis.json` tem ~14 MB; o Panorama só precisa dos totais, e a API não deve carregar o documento inteiro
para servir meia dúzia de números (diretriz de memória da API). O estado RPKI por rota (válida, inválida, sem ROA)
não existia em nenhum agregado: só bloco a bloco na cobertura do Registro.br.

Rotas brasileiras = P_BR (prefixo contido em bloco alocado pelo Registro.br; a origem não define), a mesma definição da página
Tabela BGP. As rotas de ASN da lista do Registro.br em espaço de outro RIR saem contadas à parte (`asn_br_fora_de_bloco`).
O espaço é a união dos prefixos de cada estado; um bloco pode ter rotas em mais de um estado (um agregado válido e um
mais-específico inválido), por isso os espaços por estado não somam necessariamente o total.

Saída: published/{date}/routing_analysis_resumo.json. Também é chamado por `build.run` com os dados já carregados.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from ipaddress import collapse_addresses, ip_network
from pathlib import Path

from core.common import configure_logging, data_dir, normalized_path, now_iso, published_path, read_json_gz, today_str
from core.moas import MOTIVO as MOAS_MOTIVO
from products.routing_analysis.mais_especificos import _classify_pbr, separar_rota_br
from products.routing_analysis.rpki import _build_rpki_index, _rpki_status

ARQUIVO = "routing_analysis_resumo.json"
ESTADOS = ("valid", "invalid", "not_found")
# Unidade de espaço por família: /48 em IPv6 e /24 em IPv4, como no resto do site.
_UNIDADE = {"v6": ("/48", 128 - 48), "v4": ("/24", 32 - 24)}


def _espaco(prefixos: list[str], afi: str) -> int:
    """União dos prefixos em unidades da família (prefixos menores que a unidade contam a fração, arredondada no fim)."""
    redes = []
    for p in prefixos:
        try:
            redes.append(ip_network(p, strict=False))
        except ValueError:
            continue
    if not redes:
        return 0
    enderecos = sum(n.num_addresses for n in collapse_addresses(redes))
    return round(enderecos / (1 << _UNIDADE[afi][1]))


def estado_rpki(pbr: list[dict], rpki_index: dict, afi: str) -> dict:
    """Rotas P_BR por estado RPKI de origem (RFC 6811), com o espaço de cada estado e os ASNs de origem com rota inválida."""
    por_estado: dict[str, list[str]] = {e: [] for e in ESTADOS}
    asns_invalida: set[int] = set()
    for r in pbr:
        estado = _rpki_status(r["prefix"], r["origin_as"], rpki_index)
        por_estado[estado].append(r["prefix"])
        if estado == "invalid":
            asns_invalida.add(r["origin_as"])
    total = len(pbr)
    rotas = {e: len(por_estado[e]) for e in ESTADOS}
    return {
        "rotas": total,
        **rotas,
        "pct": {e: (round(rotas[e] / total * 100, 2) if total else None) for e in ESTADOS},
        "espaco": {
            "unidade": _UNIDADE[afi][0],
            "total": _espaco([r["prefix"] for r in pbr], afi),
            **{e: _espaco(por_estado[e], afi) for e in ESTADOS},
        },
        "asns_origem_com_invalida": len(asns_invalida),
    }


def montar(date_str: str, pbr_v4: list[dict], pbr_v6: list[dict], rpki_index: dict, *, summary: dict | None = None,
           more_specifics: dict | None = None, too_specific: dict | None = None, moas: list | None = None,
           moas_limite: int = 500, vrps: int | None = None, fora_de_bloco: dict | None = None) -> dict:
    saude: dict = {}
    for afi in ("v6", "v4"):
        ms = (more_specifics or {}).get(afi) or {}
        raiz, mais = ms.get("pbr_root"), ms.get("pbr_more_specific")
        saude[afi] = {
            "mais_especificos": mais,
            "mais_especificos_pct": round(mais / (raiz + mais) * 100, 1) if raiz is not None and mais is not None and (raiz + mais) else None,
            "filtraveis": len((too_specific or {}).get(afi) or []) if too_specific is not None else None,
        }
    return {
        "snapshot_date": date_str,
        "generated_at": now_iso(),
        "definicao": "Rotas brasileiras (P_BR): prefixo contido em bloco alocado pelo Registro.br, na tabela global (RouteViews); a origem do "
                     "anúncio não define. Rotas de ASN da lista do Registro.br em espaço de outro RIR ficam fora do total "
                     "(asn_br_fora_de_bloco). Estado RPKI de origem (RFC 6811) contra os VRPs do snapshot.",
        "vrps": vrps,
        "rotas_br": {afi: {**{k: (summary or {}).get(afi, {}).get(k) for k in ("pbr_routes", "pbr_pct", "br_origin_asns", "total_routes_global")},
                           "asn_br_fora_de_bloco": (fora_de_bloco or {}).get(afi)} for afi in ("v6", "v4")},
        "rpki": {"v6": estado_rpki(pbr_v6, rpki_index, "v6"), "v4": estado_rpki(pbr_v4, rpki_index, "v4")},
        "saude": {
            **saude,
            # Nulo, com o motivo: origin-prefixes-{afi} traz uma origem por prefixo e a contagem sairia 0 por limite da coleta, não por ausência de MOAS (core/moas.py).
            # `moas` e `moas_limite` ficam na assinatura para quem chama com a análise antiga; não entram no resultado.
            "moas": None,
            "moas_indisponivel": MOAS_MOTIVO,
        },
        "limites": "Um bloco pode ter rotas em mais de um estado, então os espaços por estado não somam o total. "
                   "Sem ROA (not_found) não é inválido: só não há ROA que cubra o prefixo.",
    }


def gravar(pub: Path, payload: dict) -> Path:
    """Escrita atômica (temporário + rename)."""
    pub.mkdir(parents=True, exist_ok=True)
    destino = pub / ARQUIVO
    tmp = destino.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    os.replace(tmp, destino)
    return destino


def run(date_str: str, base: Path, log) -> bool:
    """Gera só o resumo, para snapshots já publicados (aditivo): lê o normalizado, os VRPs e o routing_analysis.json publicado."""
    norm = normalized_path(base, date_str, "summary")
    pub = published_path(base, date_str)
    registro_br = read_json_gz(norm / "registro_br.json.gz") if (norm / "registro_br.json.gz").exists() else None
    if not registro_br:
        log.error("registro_br.json.gz não encontrado", date=date_str)
        return False
    op = {afi: read_json_gz(norm / f"origin-prefixes-{afi}.json.gz") if (norm / f"origin-prefixes-{afi}.json.gz").exists() else {} for afi in ("v4", "v6")}
    vrp_path = pub / "rpki" / "vrp_list.json.gz"
    if not vrp_path.exists():
        log.error("vrp_list.json.gz não encontrado", date=date_str)
        return False
    vrp_list = read_json_gz(vrp_path)
    todas_v4, todas_v6 = _classify_pbr(op["v4"], op["v6"], registro_br)
    (pbr_v4, fora_v4), (pbr_v6, fora_v6) = separar_rota_br(todas_v4), separar_rota_br(todas_v6)
    analise = json.loads((pub / "routing_analysis.json").read_text(encoding="utf-8")) if (pub / "routing_analysis.json").exists() else {}
    payload = montar(date_str, pbr_v4, pbr_v6, _build_rpki_index(vrp_list), summary=analise.get("summary"),
                     more_specifics=analise.get("more_specifics"), too_specific=analise.get("too_specific"),
                     moas=analise.get("moas"), vrps=len(vrp_list), fora_de_bloco={"v4": len(fora_v4), "v6": len(fora_v6)})
    destino = gravar(pub, payload)
    log.info("routing_analysis_resumo written", path=str(destino))
    return True


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Resumo nacional da análise de roteamento (estado RPKI das rotas BR e saúde da tabela)")
    p.add_argument("--date", default=today_str(), help="data do snapshot (YYYY-MM-DD)")
    p.add_argument("--force", action="store_true", help="regrava mesmo se o arquivo já existir")
    args = p.parse_args(argv)
    log = configure_logging()
    base = data_dir()
    if not args.force and (published_path(base, args.date) / ARQUIVO).exists():
        log.info("already exists, skipping", date=args.date)
        return 0
    return 0 if run(args.date, base, log) else 1


if __name__ == "__main__":
    sys.exit(main())
