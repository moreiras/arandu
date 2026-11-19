# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""PeeringDB completo: instalações (`fac`), redes por instalação (`netfac`), PTTs por instalação (`ixfac`), carriers
(`carrier`, `carrierfac`), campus e atributos de peering das redes do Brasil (`net`).

Escopo restrito: **Brasil** (`country=BR`) mais as instalações dos PTTs externos já cadastrados em
`config/peeringdb_ixps.yaml`. Nada de dump mundial. **Nenhum contato**: `fac`, `net` e `ix` trazem e-mail e telefone (`tech_email`, `sales_phone`…) e `notes`
em texto livre (com e-mails de NOC); o normalizador só leva os campos da lista branca abaixo, e o bruto NÃO é gravado (só o manifesto das requisições).

Requisições (≈ 29): ix (BR, só id/nome/cidade), fac, ixfac (BR e dos PTTs cadastrados), fac dos PTTs externos, netfac (BR), carrierfac, carrier, campus e `net` em lotes de 500 ASNs
(só os ASNs que o `peeringdb_networks` já achou no PeeringDB, com `fields=`). Uma por vez, pausa de 1,5 s, `Authorization: Api-Key` se houver `PEERINGDB_API_KEY`.
A velocidade das portas dos PTTs externos já vem do `peeringdb_ixps` (netixlan): não é coletada de novo.

Normalizado: data/normalized/{date}/summary/peeringdb_fac.json.gz
Manifesto:   data/raw/{date}/summary/peeringdb-fac-requisicoes-{date}.json (recurso, parâmetros sem chave, status, linhas, bytes, segundos)

Uso:
    python -m sources.peeringdb_fac.collect --date 2026-11-05
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from core.common import (
    configure_logging,
    data_dir,
    load_peeringdb_ixps_config,
    normalized_path,
    now_iso,
    raw_path,
    read_json_gz,
    today_str,
    write_json_gz,
)
from core.site import USER_AGENT

PDB_BASE = "https://www.peeringdb.com/api"
HEADERS = {"User-Agent": USER_AGENT}
ESPERA_S = 1.5
RETRY_S = 65
MAX_TENTATIVAS = 4
LOTE_IDS = 150            # ids por `id__in` (URL curta)
LOTE_ASNS = 500
MINIMO_FAC_BR = 100       # sanidade: o PeeringDB tem ~370 instalações no Brasil (2026-11-05)

CITACAO = "Dados do PeeringDB (https://www.peeringdb.com), cadastro autodeclarado por organizações; uso conforme o AUP (https://www.peeringdb.com/aup)."

# Lista branca: o que NÃO está aqui é descartado (contatos, notes, redes sociais, endereço de rua, CEP…).
_FAC = {"id": "id", "name": "nome", "aka": "aka", "name_long": "nome_longo", "org_id": "org_id", "org_name": "org_nome", "campus_id": "campus_id", "website": "site",
        "property": "propriedade", "net_count": "redes_declaradas", "ix_count": "ixps_declarados", "carrier_count": "carriers_declarados", "created": "criado",
        "updated": "atualizado", "city": "cidade", "state": "uf", "country": "pais", "latitude": "lat", "longitude": "lon"}
_NET = {"info_scope": "escopo", "info_ipv6": "ipv6", "info_multicast": "multicast", "info_unicast": "unicast",
        "info_never_via_route_servers": "nunca_via_route_server", "looking_glass": "looking_glass", "route_server": "route_server",
        "created": "criado", "updated": "atualizado", "netixlan_updated": "portas_atualizadas", "netfac_updated": "instalacoes_atualizadas",
        "ix_count": "ixps_declarados", "fac_count": "instalacoes_declaradas"}
_IX = {"id": "id", "name": "nome", "city": "cidade", "country": "pais"}
_CARRIER = {"id": "id", "name": "nome", "aka": "aka", "org_name": "org_nome", "website": "site", "fac_count": "instalacoes_declaradas", "created": "criado", "updated": "atualizado"}
_CAMPUS = {"id": "id", "name": "nome", "aka": "aka", "org_name": "org_nome", "website": "site", "city": "cidade", "state": "uf", "country": "pais", "created": "criado", "updated": "atualizado"}
CAMPOS_NET = ["asn", "status", *_NET]       # `fields=` do /net: só o que a lista branca usa (não pede notes, contatos nem política)


class LimiteError(RuntimeError):
    """O PeeringDB continuou limitando (429) ou sem responder depois de todas as tentativas."""


def url_publica(v) -> str | None:
    """URL http(s)/telnet/ssh (site, looking glass, route server) sem credencial embutida; o resto vira None (texto livre, e-mail, 'n/a')."""
    if not isinstance(v, str):
        return None
    v = v.strip()
    if not v or len(v) > 300 or " " in v:
        return None
    p = urlsplit(v)
    if p.scheme.lower() not in ("http", "https", "telnet", "ssh") or not p.hostname or p.username or p.password:
        return None
    return v


def _limpa(rec: dict, mapa: dict, urls: tuple[str, ...] = ()) -> dict:
    """Só os campos da lista branca, com nomes em português; vazio some, `False` fica (é informação); campo de URL só se for URL pública."""
    out = {}
    for k, nome in mapa.items():
        v = rec.get(k)
        if v is None or v == "":
            continue
        if nome in urls:
            v = url_publica(v)
            if v is None:
                continue
        out[nome] = v
    return out


def normaliza_fac(rec: dict) -> dict:
    return _limpa(rec, _FAC, ("site",))


def normaliza_net(rec: dict) -> dict:
    return _limpa(rec, _NET, ("looking_glass", "route_server"))


def normaliza_ix(rec: dict) -> dict:
    return _limpa(rec, _IX)


def normaliza_carrier(rec: dict) -> dict:
    return _limpa(rec, _CARRIER, ("site",))


def normaliza_campus(rec: dict) -> dict:
    return _limpa(rec, _CAMPUS, ("site",))


class Cliente:
    """Uma requisição por vez, pausa fixa, repetição em 429/erro de rede e manifesto do que foi pedido (sem a chave)."""

    def __init__(self, client: httpx.Client, espera_s: float = ESPERA_S, retry_s: float = RETRY_S, log=None):
        self.client, self.espera_s, self.retry_s, self.log = client, espera_s, retry_s, log
        self.manifesto: list[dict] = []

    def get(self, recurso: str, **params) -> list[dict]:
        ultimo = "429"
        for t in range(1, MAX_TENTATIVAS + 1):
            t0 = time.monotonic()
            try:
                r = self.client.get(f"{PDB_BASE}/{recurso}", params=params)
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                ultimo = type(exc).__name__
                if self.log:
                    self.log.warning("erro de rede", recurso=recurso, erro=ultimo, tentativa=t)
                time.sleep(self.retry_s * 0.25 * t)
                continue
            if r.status_code == 429:
                ultimo = "429"
                if self.log:
                    self.log.warning("rate limited", recurso=recurso, tentativa=t)
                time.sleep(int(r.headers.get("Retry-After", self.retry_s)))
                continue
            r.raise_for_status()
            dados = r.json().get("data", [])
            resumo = {k: (f"<{len(str(v).split(','))} ids>" if k.endswith("__in") else v) for k, v in params.items()}
            self.manifesto.append({"recurso": recurso, "params": resumo, "status": r.status_code, "linhas": len(dados), "bytes": len(r.content),
                                   "segundos": round(time.monotonic() - t0, 2)})
            time.sleep(self.espera_s)
            return dados
        raise LimiteError(f"PeeringDB sem resposta útil em {MAX_TENTATIVAS} tentativas ({recurso}; último: {ultimo})")


def _lotes(ids: list[int], n: int):
    for i in range(0, len(ids), n):
        yield ids[i:i + n]


def coletar(c: Cliente, ix_ids: list[int], asns_pdb: list[int]) -> dict:
    """Todas as consultas do passo; devolve o conteúdo normalizado (sem datas de snapshot)."""
    facs = {f["id"]: normaliza_fac(f) for f in c.get("fac", country="BR", status="ok", depth=0)}
    if len(facs) < MINIMO_FAC_BR:
        raise RuntimeError(f"peeringdb_fac: só {len(facs)} instalações no Brasil (mínimo {MINIMO_FAC_BR}) — coleta descartada")

    ixps = {x["id"]: normaliza_ix(x) for x in c.get("ix", country="BR", status="ok", depth=0)}      # só nome e cidade: o /ix traz e-mail e telefone
    ixfac = {(x["fac_id"], x["ix_id"]) for x in c.get("ixfac", country="BR", status="ok", depth=0)}
    for lote in _lotes(sorted(ix_ids), LOTE_IDS):
        ixfac |= {(x["fac_id"], x["ix_id"]) for x in c.get("ixfac", ix_id__in=",".join(map(str, lote)), status="ok", depth=0)}
    for lote in _lotes(sorted({i for _, i in ixfac} - set(ixps)), LOTE_IDS):          # PTT de uma instalação do Brasil que não é do Brasil ou não está no cadastro
        ixps.update({x["id"]: normaliza_ix(x) for x in c.get("ix", id__in=",".join(map(str, lote)), status="ok", depth=0)})
    for lote in _lotes(sorted({f for f, _ in ixfac} - set(facs)), LOTE_IDS):
        for f in c.get("fac", id__in=",".join(map(str, lote)), status="ok", depth=0):
            facs[f["id"]] = normaliza_fac(f)
    ixfac = {(f, i) for f, i in ixfac if f in facs}

    netfac = [[x["fac_id"], x["local_asn"], x.get("created"), x.get("updated")]
              for x in c.get("netfac", country="BR", status="ok", depth=0) if x["fac_id"] in facs and x.get("local_asn")]

    carrierfac, carrier_ids = set(), set()
    for lote in _lotes(sorted(facs), LOTE_IDS):
        for x in c.get("carrierfac", fac_id__in=",".join(map(str, lote)), status="ok", depth=0):
            carrierfac.add((x["carrier_id"], x["fac_id"]))
            carrier_ids.add(x["carrier_id"])
    carriers = {}
    for lote in _lotes(sorted(carrier_ids), LOTE_IDS):
        for x in c.get("carrier", id__in=",".join(map(str, lote)), status="ok", depth=0):
            carriers[x["id"]] = normaliza_carrier(x)

    campus_ids = {f["campus_id"] for f in facs.values() if f.get("campus_id")}
    campus = {}
    if campus_ids:                      # o filtro country= é ignorado em /campus (a lista inteira tem ~76 registros): filtra aqui
        for x in c.get("campus", status="ok", depth=0):
            if x["id"] in campus_ids:
                campus[x["id"]] = normaliza_campus(x)

    redes = {}
    for lote in _lotes(sorted(asns_pdb), LOTE_ASNS):
        for x in c.get("net", asn__in=",".join(map(str, lote)), status="ok", depth=0, fields=",".join(CAMPOS_NET)):
            if x.get("asn"):
                redes[str(x["asn"])] = normaliza_net(x)

    return {"facilities": {str(k): v for k, v in sorted(facs.items())}, "netfac": sorted(netfac), "ixfac": sorted([f, i] for f, i in ixfac), "ixps": {str(k): v for k, v in sorted(ixps.items())},
            "carriers": {str(k): v for k, v in sorted(carriers.items())}, "carrierfac": sorted([ca, f] for ca, f in carrierfac),
            "campus": {str(k): v for k, v in sorted(campus.items())}, "redes": dict(sorted(redes.items(), key=lambda kv: int(kv[0])))}


def make_client() -> httpx.Client:
    h = dict(HEADERS)
    chave = os.environ.get("PEERINGDB_API_KEY", "")
    if chave:
        h["Authorization"] = f"Api-Key {chave}"
    return httpx.Client(headers=h, timeout=60, follow_redirects=True)


def run(date_str: str, base: Path, log, client: httpx.Client | None = None, espera_s: float = ESPERA_S, retry_s: float = RETRY_S) -> dict:
    norm_dir = normalized_path(base, date_str, "summary")
    cfg = load_peeringdb_ixps_config()
    ix_ids = sorted({int(i["pdb_ix_id"]) for i in cfg["external"] + cfg["ixbr"] if i.get("pdb_ix_id")})
    redes_in = norm_dir / "peeringdb_networks.json.gz"
    asns_pdb = sorted(int(a) for a in read_json_gz(redes_in)["networks"]) if redes_in.exists() else []
    if not asns_pdb:
        raise RuntimeError("peeringdb_fac: peeringdb_networks.json.gz ausente ou vazio (a lista de ASNs vem de peeringdb_networks)")
    proprio = client is None
    client = client or make_client()
    try:
        c = Cliente(client, espera_s=espera_s, retry_s=retry_s, log=log)
        dados = coletar(c, ix_ids, asns_pdb)
    finally:
        if proprio:
            client.close()
    # o PeeringDB pode ter removido uns registros entre o `peeringdb_networks` e agora, mas não um quinto deles
    if len(dados["redes"]) < 0.8 * len(asns_pdb):
        raise RuntimeError(f"peeringdb_fac: {len(dados['redes'])} de {len(asns_pdb)} redes voltaram — coleta descartada")
    norm_dir.mkdir(parents=True, exist_ok=True)
    write_json_gz(norm_dir / "peeringdb_fac.json.gz", {
        "snapshot_date": date_str, "fetched_at": now_iso(), "fonte": PDB_BASE, "citacao": CITACAO, "requisicoes": len(c.manifesto),
        "escopo": "Brasil e instalações dos PTTs cadastrados em config/peeringdb_ixps.yaml", **dados})
    rd = raw_path(base, date_str, "summary")
    rd.mkdir(parents=True, exist_ok=True)
    (rd / f"peeringdb-fac-requisicoes-{date_str}.json").write_text(json.dumps(c.manifesto, ensure_ascii=False), encoding="utf-8")
    log.info("peeringdb_fac written", facilities=len(dados["facilities"]), netfac=len(dados["netfac"]), carriers=len(dados["carriers"]),
             redes=len(dados["redes"]), requisicoes=len(c.manifesto))
    return {"facilities": len(dados["facilities"]), "requisicoes": len(c.manifesto)}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="PeeringDB: instalações, carriers, campus e atributos das redes do Brasil")
    p.add_argument("--date", default=today_str())
    p.add_argument("--force", action="store_true", help="aceito por compatibilidade com o executor; a coleta é sempre refeita")
    a = p.parse_args(argv)
    log = configure_logging()
    try:
        run(a.date, data_dir(), log)
    except Exception:
        log.exception("falha na coleta de peeringdb_fac")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
