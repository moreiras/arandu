# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Sessões BGP dos route servers do IX.br pela API do Alice-LG (níveis 0 e 1).

Fonte:       https://lg.ix.br/api/v1/{config,status,routeservers,routeservers/{id}/neighbors}
Normalizado: data/normalized/{date}/summary/rs_sessions.json.gz     {rs: [...], sessoes: [...]}
             data/normalized/{date}/summary/ixbr_communities.json.gz   dicionário de communities (a semântica pode mudar: um por snapshot)
Bruto:       não é guardado (derivados apenas): o `neighbors` de SP rs1 v4 sozinho pesa 5 MB e traz campos que não usamos.

Carga: o `robots.txt` do lg.ix.br pede `Crawl-delay: 1`; a pausa entre requisições é de 1 s por padrão (`ARANDU_ALICE_PAUSA_S`), com uma
requisição por vez e repetição com recuo. Uma rodada são ~170 requisições. Coordenar mudanças de taxa com a engenharia do IX.br.

O Alice fala com route servers BIRD e guarda dois caches por route server: o de **rotas** (é dele o `state` READY/BUSY/ERROR e o `updated_at` do `/status`; aqui
`estado_rotas` e `rotas_atualizadas_em`) e o de **vizinhos** (as sessões, do `neighbors`). Um não diz nada sobre o outro: o SP rs1 v4 aparece BUSY/ERROR nas rotas e tem
sessões com minutos de uptime. O frescor das sessões é o `cache_status.cached_at` da própria resposta do `neighbors` (`vizinhos_em`). RS cujo `neighbors` falhou fica com
`consultado: false`, `erro` e sem sessões, nunca com zero inventado.

Uso:
    python -m sources.ixbr_alice.collect --date 2026-10-31
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from typing import Callable, Optional

import httpx

from core.common import configure_logging, data_dir, normalized_path, now_iso, today_str, write_json_gz
from core.site import USER_AGENT

BASE = "https://lg.ix.br/api/v1"
HEADERS = {"User-Agent": USER_AGENT}
PAUSA_S = float(os.environ.get("ARANDU_ALICE_PAUSA_S", "1.0"))
TENTATIVAS = 3
MINIMO_RS = 100                                   # RS listados: bem menos que isso é resposta truncada (hoje 164)
MAX_FALHA = 0.2                                   # fração de RS sem `neighbors` acima da qual a coleta falha
CAMPOS_COMMUNITIES = ("reject_reasons", "noexport", "noexport_reasons", "reject_candidates", "rpki", "bgp_communities", "bgp_blackhole_communities")


def _get(client: httpx.Client, caminho: str, dormir: Callable[[float], None]) -> dict:
    ultimo: Optional[Exception] = None
    for tentativa in range(TENTATIVAS):
        try:
            r = client.get(f"{BASE}/{caminho}")
            r.raise_for_status()
            return r.json()
        except (httpx.HTTPError, ValueError) as e:
            ultimo = e
            dormir(PAUSA_S * (2 ** tentativa) * 2)
    raise RuntimeError(f"alice {caminho}: {ultimo}")


def _afi(rs_id: str) -> str:
    return rs_id.rsplit("-", 1)[-1]


def _ixp(rs_id: str) -> str:
    return rs_id.rsplit("-", 2)[0].lower()


def _numero_rs(rs_id: str) -> str:
    return rs_id.rsplit("-", 2)[1]


def normalizar_sessao(rs_id: str, n: dict) -> dict:
    d = n.get("details") or {}
    mudancas = d.get("route_changes") or {}
    imp = mudancas.get("import_updates") or {}
    return {
        "rs": rs_id, "ixp": _ixp(rs_id), "afi": _afi(rs_id), "neighbor_ip": n.get("address"), "asn": n.get("asn"),
        "descricao": n.get("description") or "", "estado": n.get("state"), "bgp_state": d.get("bgp_state"),
        "state_changed": d.get("state_changed"), "last_error": n.get("last_error") or "",
        "rotas": {"recebidas": n.get("routes_received"), "aceitas": n.get("routes_accepted"), "filtradas": n.get("routes_filtered"),
                  "exportadas": n.get("routes_exported")},
        "import_limit": d.get("import_limit"), "receive_limit": d.get("receive_limit"),
        "route_changes_import": {k: imp.get(k) for k in ("received", "accepted", "filtered", "rejected", "ignored") if k in imp},
    }


def normalizar(config: dict, status: dict, servidores: dict, vizinhos: dict[str, Optional[list]], erros: dict[str, str], date_str: str,
               vizinhos_em: Optional[dict[str, Optional[str]]] = None) -> tuple[dict, dict]:
    """`vizinhos`: {rs_id: lista de neighbors, ou None se a consulta falhou}; `vizinhos_em`: {rs_id: `cache_status.cached_at` da resposta do `neighbors`}. Devolve (rs_sessions, ixbr_communities)."""
    vizinhos_em = vizinhos_em or {}
    estado_rs = {}
    for s in (status.get("routes") or {}).get("route_servers") or []:
        estado_rs[s.get("name")] = s
    rs, sessoes = [], []
    for r in sorted(servidores.get("routeservers") or [], key=lambda x: x["id"]):
        rid = r["id"]
        st = estado_rs.get(r.get("name")) or {}
        lista = vizinhos.get(rid)
        linhas = [normalizar_sessao(rid, n) for n in lista] if lista is not None else []
        linhas.sort(key=lambda x: (x["asn"] or 0, x["neighbor_ip"] or ""))
        sessoes.extend(linhas)
        rs.append({"rs": rid, "ixp": _ixp(rid), "numero": _numero_rs(rid), "afi": _afi(rid), "nome": r.get("name"), "grupo": r.get("group"),
                   "estado_rotas": st.get("state"), "rotas_atualizadas_em": st.get("updated_at"), "vizinhos_em": vizinhos_em.get(rid), "rotas_importadas": (st.get("routes") or {}).get("imported"),
                   "consultado": lista is not None, "erro": erros.get(rid), "sessoes": len(linhas),
                   "sessoes_up": sum(1 for x in linhas if x["estado"] == "up")})
    saida = {"snapshot_date": date_str, "generated_at": now_iso(), "fonte": "https://lg.ix.br (Alice-LG)", "versao_alice": status.get("version"),
             "total_rs": len(rs), "rs": rs, "sessoes": sessoes}
    comm = {"snapshot_date": date_str, "generated_at": now_iso(), "versao_alice": status.get("version"),
            **{k: config.get(k) for k in CAMPOS_COMMUNITIES}}
    return saida, comm


def coletar(client: httpx.Client, log, dormir: Callable[[float], None] = time.sleep) -> tuple[dict, dict, dict, dict, dict, dict]:
    config = _get(client, "config", dormir)
    dormir(PAUSA_S)
    status = _get(client, "status", dormir)
    dormir(PAUSA_S)
    servidores = _get(client, "routeservers", dormir)
    ids = [r["id"] for r in servidores.get("routeservers") or []]
    if len(ids) < MINIMO_RS:
        raise RuntimeError(f"ixbr_alice: {len(ids)} route servers (esperado ≥ {MINIMO_RS})")
    vizinhos: dict[str, Optional[list]] = {}
    erros: dict[str, str] = {}
    em: dict[str, Optional[str]] = {}
    for rid in ids:
        dormir(PAUSA_S)
        try:
            resp = _get(client, f"routeservers/{rid}/neighbors", dormir)
            vizinhos[rid] = resp.get("neighbors") or []
            em[rid] = ((resp.get("api") or {}).get("cache_status") or {}).get("cached_at")
        except RuntimeError as e:
            vizinhos[rid], erros[rid] = None, str(e)[:200]
            log.warning("neighbors falhou", rs=rid, erro=erros[rid])
    if len(erros) > MAX_FALHA * len(ids):
        raise RuntimeError(f"ixbr_alice: neighbors falhou em {len(erros)} de {len(ids)} route servers")
    return config, status, servidores, vizinhos, erros, em


def run(date_str: str, base: Path, log, client: Optional[httpx.Client] = None, dormir: Callable[[float], None] = time.sleep) -> dict:
    proprio = client is None
    client = client or httpx.Client(timeout=120, follow_redirects=True, headers=HEADERS)
    try:
        config, status, servidores, vizinhos, erros, em = coletar(client, log, dormir)
    finally:
        if proprio:
            client.close()
    sessoes, comm = normalizar(config, status, servidores, vizinhos, erros, date_str, em)
    destino = normalized_path(base, date_str, "summary")
    destino.mkdir(parents=True, exist_ok=True)
    write_json_gz(destino / "rs_sessions.json.gz", sessoes)
    write_json_gz(destino / "ixbr_communities.json.gz", comm)
    log.info("ixbr_alice written", rs=sessoes["total_rs"], sessoes=len(sessoes["sessoes"]), rs_com_erro=len(erros))
    return {"rs": sessoes["total_rs"], "sessoes": len(sessoes["sessoes"]), "rs_com_erro": len(erros)}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Sessões dos route servers do IX.br (Alice-LG, níveis 0 e 1)")
    p.add_argument("--date", default=today_str())
    p.add_argument("--force", action="store_true", help="aceito por compatibilidade com o executor; a coleta é sempre refeita")
    a = p.parse_args(argv)
    log = configure_logging()
    try:
        print(run(a.date, data_dir(), log))
    except Exception:
        log.exception("falha na coleta de ixbr_alice")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
