# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""IRR (TC e RADB): objetos `route`/`route6` dos ASNs brasileiros.

Fontes:      TC IRR   https://ftp.bgp.net.br/tc.db.gz (serial em TC.CURRENTSERIAL); termos em https://bgp.net.br/terms.html (uso para operação, segurança, auditoria e pesquisa; sem automação agressiva)
             RADB     ftp://ftp.radb.net/radb/dbase/radb.db.gz (serial em RADB.CURRENTSERIAL); dump público, sem assinatura. Termos lidos em cópia arquivada do ToS (2026-11-02); ver o catálogo.
Bruto:       data/raw/{date}/summary/irr-tc-{date}.db.gz e irr-radb-{date}.db.gz (cópias locais; nunca redistribuídas)
Normalizado: data/normalized/{date}/summary/irr_route_objects.json.gz   {fontes: {TC, RADB: {serial, ...}}, rotas: {TC: {asn: [prefixos]}, RADB: {...}}, aut_num: {...},
             politicas: {TC: {asn: [[sentido, asn_do_par, classe]]}, RADB: {...}}}  (só a classe do filtro, nunca o texto)
Só entram objetos cuja origem é ASN brasileiro (Registro.br); só o par prefixo/origem e, dos `aut-num` brasileiros, a classe do filtro de cada `import`/`export` com par ASN explícito (any, proprio, par, as_set, outro). A coleta é mensal e confere o serial: se não mudou, reaproveita o normalizado anterior e não baixa de novo.

Uso:
    python -m sources.irr_route_objects.collect --date 2026-11-02
"""
from __future__ import annotations

import argparse
import hashlib
import sys
import urllib.request
from pathlib import Path

from core import irr
from core.common import configure_logging, data_dir, normalized_path, now_iso, raw_path, read_json_gz, today_str
from core.jsonio import carregar_json_gz, gravar_json_gz
from core.site import USER_AGENT

IRRS = {
    "TC": {"dump": "https://ftp.bgp.net.br/tc.db.gz", "serial": "https://ftp.bgp.net.br/TC.CURRENTSERIAL", "minimo_objetos": 10_000, "minimo_asns_br": 1_000,
           "termos": "https://bgp.net.br/terms.html"},
    "RADB": {"dump": "ftp://ftp.radb.net/radb/dbase/radb.db.gz", "serial": "ftp://ftp.radb.net/radb/dbase/RADB.CURRENTSERIAL", "minimo_objetos": 500_000, "minimo_asns_br": 3_000,
             "termos": "https://www.radb.net/terms-of-service"},
}
CITACAO = "TC Internet Routing Registry (bgp.net.br) e RADb, Merit Network (radb.net): objetos route/route6 publicados nos dumps abertos; o objeto declara política ou intenção de roteamento"


def _abrir(url: str):
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": USER_AGENT}), timeout=300)


def ler_serial(url: str) -> str | None:
    try:
        with _abrir(url) as r:
            return r.read(64).decode("ascii", "replace").strip() or None
    except Exception:
        return None


def baixar(url: str, destino: Path) -> dict:
    h = hashlib.sha256()
    n = 0
    tmp = destino.with_suffix(destino.suffix + ".tmp")
    with _abrir(url) as r, open(tmp, "wb") as f:
        while pedaco := r.read(1 << 20):
            f.write(pedaco)
            h.update(pedaco)
            n += len(pedaco)
    tmp.replace(destino)
    return {"bytes": n, "sha256": h.hexdigest()}


def asns_br(base: Path, date_str: str, log) -> set[int]:
    """ASNs do Registro.br do dia ou, na falta, do snapshot anterior mais recente."""
    candidatos = [normalized_path(base, date_str, "summary") / "registro_br.json.gz"]
    raiz = base / "normalized"
    if raiz.exists():
        candidatos += [d / "summary" / "registro_br.json.gz" for d in sorted(raiz.iterdir(), reverse=True) if d.is_dir() and d.name < date_str][:3]
    for c in candidatos:
        if c.exists():
            asns = {a["asn"] for a in read_json_gz(c).get("asns", [])}
            log.info("irr: asns_br", fonte=str(c), n=len(asns))
            return asns
    raise RuntimeError("irr_route_objects: lista de ASNs do Registro.br ausente (registro_br.json.gz)")


def _anterior(base: Path, date_str: str) -> dict | None:
    raiz = base / "normalized"
    for d in sorted((p for p in raiz.iterdir() if p.is_dir() and p.name < date_str), reverse=True) if raiz.exists() else []:
        doc = carregar_json_gz(d / "summary" / "irr_route_objects.json.gz")
        if doc:
            return doc
    return None


def run(date_str: str, base: Path, log, forcar: bool = False) -> dict:
    br = asns_br(base, date_str, log)
    anterior = _anterior(base, date_str)
    fontes: dict[str, dict] = {}
    rotas: dict[str, dict] = {}
    aut_num: dict[str, list] = {}
    politicas: dict[str, dict] = {}
    for nome, cfg in IRRS.items():
        serial = ler_serial(cfg["serial"])
        ant = (anterior or {}).get("fontes", {}).get(nome)
        if not forcar and serial and ant and ant.get("serial") == serial and nome in (anterior or {}).get("rotas", {}) and nome in (anterior or {}).get("politicas", {}):
            fontes[nome] = {**ant, "reaproveitado_de": anterior["snapshot_date"]}
            rotas[nome], aut_num[nome] = anterior["rotas"][nome], anterior["aut_num"][nome]
            politicas[nome] = anterior["politicas"][nome]
            log.info("irr: serial igual, reaproveitado", irr=nome, serial=serial)
            continue
        bruto = raw_path(base, date_str, "summary")
        bruto.mkdir(parents=True, exist_ok=True)
        destino = bruto / f"irr-{nome.lower()}-{date_str}.db.gz"
        meta = baixar(cfg["dump"], destino)
        r, aut, contagem, pol = irr.ler_dump_completo(destino, br)
        n_objetos = contagem.get("route", 0) + contagem.get("route6", 0)
        if n_objetos < cfg["minimo_objetos"] or len(r) < cfg["minimo_asns_br"]:
            raise RuntimeError(f"irr_route_objects: {nome} com {n_objetos} objetos route e {len(r)} ASNs brasileiros (esperado ≥ {cfg['minimo_objetos']} e ≥ {cfg['minimo_asns_br']}); dump truncado?")
        rotas[nome] = {str(a): sorted(p) for a, p in sorted(r.items())}
        aut_num[nome] = sorted(aut)
        politicas[nome] = {str(a): [list(x) for x in v] for a, v in sorted(pol.items())}
        fontes[nome] = {"url": cfg["dump"], "serial": serial, "termos": cfg["termos"], **meta, "objetos": contagem, "asns_br_com_route": len(r), "prefixos_br": sum(len(p) for p in r.values()),
                        "asns_br_com_aut_num": len(aut), "asns_br_com_politica": len(pol)}
        log.info("irr: lido", irr=nome, serial=serial, objetos=n_objetos, asns_br=len(r))
    destino_n = normalized_path(base, date_str, "summary")
    destino_n.mkdir(parents=True, exist_ok=True)
    gravar_json_gz(destino_n / "irr_route_objects.json.gz", {
        "snapshot_date": date_str, "fetched_at": now_iso(), "citacao": CITACAO, "asns_br_consultados": len(br), "fontes": fontes, "rotas": rotas, "aut_num": aut_num,
        "politicas": politicas})
    return {n: {k: v for k, v in f.items() if k in ("serial", "asns_br_com_route", "prefixos_br", "asns_br_com_aut_num", "reaproveitado_de")} for n, f in fontes.items()}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="IRR (TC e RADB): route/route6 dos ASNs brasileiros")
    p.add_argument("--date", default=today_str())
    p.add_argument("--force", action="store_true", help="baixa de novo mesmo com o serial igual ao anterior")
    a = p.parse_args(argv)
    log = configure_logging()
    try:
        print(run(a.date, data_dir(), log, forcar=a.force))
    except Exception:
        log.exception("falha na coleta de irr_route_objects")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
