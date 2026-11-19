# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Eventos do ciclo de vida do IPv4 a partir do `delegated-lacnic-extended` diário. Fonte derivada: lê o histórico (`data/historico/lacnic/`, backfill de `lacnic_historico`) e o bruto diário.

Entrada:     data/historico/lacnic/delegated-extended/AAAA/delegated-lacnic-extended-AAAAMMDD.gz e data/raw/*/summary/delegated-lacnic-extended-{dia}.txt.gz
Estado:      data/ipv4/delegated_estado.json.gz        última foto processada (derivado e reconstruível; fora de raw/ e de normalized/)
Eventos:     data/ipv4/eventos/AAAA-MM.jsonl.gz        um evento por linha (`core/ipv4_eventos.py`), de todos os registros do LACNIC; o produto filtra o Brasil
Normalizado: data/normalized/{date}/summary/ipv4_delegated.json.gz   resumo do dia (blocos por status, Brasil), eventos recentes, lacunas e a validação cruzada com as transferências

Idempotente e retomável: processa os dias entre a última foto e `--date`; dia sem arquivo é pulado e registrado em `lacunas` (o evento seguinte leva `visto_entre`). Sem estado, a primeira foto
do intervalo é só a linha de base (nenhum evento). `--backfill-desde AAAA-MM-DD` reprocessa do zero a partir dessa data.

Uso:
    python -m sources.ipv4_delegated.enrich --date 2026-11-02
    python -m sources.ipv4_delegated.enrich --date 2026-11-02 --backfill-desde 2020-01-01
"""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import json
import sys
from pathlib import Path
from typing import Optional

from core import ipv4_eventos as E
from core import ipv4_listas as L
from core.common import configure_logging, data_dir, normalized_path, now_iso, today_str, write_json_gz

DESDE_PADRAO = "2020-01-01"                         # pós-esgotamento do IPv4; o histórico de `lacnic_historico` começa aqui
MINIMO_BLOCOS = 10000                               # o LACNIC tem ~20 mil registros IPv4; bem menos que isso é arquivo truncado
RECENTES_DIAS = 30


def pasta(base: Path) -> Path:
    return base / "ipv4"


def arquivo_do_dia(base: Path, dia: str) -> Optional[Path]:
    ano, comp = dia[:4], dia.replace("-", "")
    h = base / "historico" / "lacnic" / "delegated-extended" / ano / f"delegated-lacnic-extended-{comp}.gz"
    if h.exists():
        return h
    raiz = base / "raw"
    if raiz.exists():
        for d in sorted(raiz.iterdir()):
            for nome in (f"delegated-lacnic-extended-{dia}.txt.gz", f"delegated-lacnic-extended-{dia}.txt"):
                p = d / "summary" / nome
                if p.exists():
                    return p
    return None


def _ler(p: Path) -> str:
    return (gzip.decompress(p.read_bytes()) if p.suffix == ".gz" else p.read_bytes()).decode("utf-8", "replace")


def _estado_path(base: Path) -> Path:
    return pasta(base) / "delegated_estado.json.gz"


def carregar_estado(base: Path) -> Optional[dict]:
    p = _estado_path(base)
    return json.loads(gzip.decompress(p.read_bytes())) if p.exists() else None


def _eventos_path(base: Path, mes: str) -> Path:
    return pasta(base) / "eventos" / f"{mes}.jsonl.gz"


def ler_eventos_mes(base: Path, mes: str) -> list[dict]:
    p = _eventos_path(base, mes)
    return [json.loads(x) for x in gzip.decompress(p.read_bytes()).decode().splitlines() if x] if p.exists() else []


def _gravar_mes(base: Path, mes: str, eventos: list[dict]) -> None:
    p = _eventos_path(base, mes)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_bytes(gzip.compress("\n".join(json.dumps(e, ensure_ascii=False, separators=(",", ":")) for e in sorted(eventos, key=lambda x: (x["data"], x["id"]))).encode(), mtime=0))
    tmp.replace(p)


def todos_eventos(base: Path) -> list[dict]:
    d = pasta(base) / "eventos"
    return [e for f in sorted(d.glob("*.jsonl.gz")) for e in ler_eventos_mes(base, f.name[:7])] if d.exists() else []


def processar(base: Path, ate: str, log, desde: str = DESDE_PADRAO, zerar: bool = False) -> dict:
    estado = None if zerar else carregar_estado(base)
    if estado is None:
        for f in (pasta(base) / "eventos").glob("*.jsonl.gz") if zerar and (pasta(base) / "eventos").exists() else []:
            f.unlink()
    dia = dt.date.fromisoformat(desde if estado is None else estado["dia"])
    fim = dt.date.fromisoformat(ate)
    ant = {k: v for k, v in estado["blocos"].items()} if estado else None
    ultima = estado["dia"] if estado else None
    lacunas, novos_ev, por_mes, fotos = [], 0, {}, 0
    cont_total = {"iguais": 0, "reorganizacoes": 0}
    d = dia if estado is None else dia + dt.timedelta(days=1)
    while d <= fim:
        s = d.isoformat()
        arq = arquivo_do_dia(base, s)
        if arq is None:
            lacunas.append(s)
            d += dt.timedelta(days=1)
            continue
        blocos, ign = L.parse_delegated_ipv4(_ler(arq))
        if len(blocos) < MINIMO_BLOCOS:
            raise RuntimeError(f"ipv4_delegated: {s} tem só {len(blocos)} blocos IPv4 (esperado ≥ {MINIMO_BLOCOS})")
        if ign:
            log.warning("ipv4_delegated: linhas ignoradas", dia=s, n=len(ign), exemplo=ign[0][:120])
        fotos += 1
        if ant is not None:
            ev, cont = E.diff(ant, blocos, s)
            if ultima and (dt.date.fromisoformat(s) - dt.date.fromisoformat(ultima)).days > 1:
                for e in ev:
                    e["visto_entre"] = [ultima, s]
            mes = s[:7]
            if mes not in por_mes:
                por_mes[mes] = ler_eventos_mes(base, mes)
            por_mes[mes] = [e for e in por_mes[mes] if e["data"] != s] + ev
            novos_ev += len(ev)
            for k in cont_total:
                cont_total[k] += cont[k]
        ant, ultima = blocos, s
        d += dt.timedelta(days=1)
    for mes, evs in por_mes.items():
        _gravar_mes(base, mes, evs)
    if ant is not None and ultima:
        pasta(base).mkdir(parents=True, exist_ok=True)
        tmp = _estado_path(base).with_suffix(".tmp")
        tmp.write_bytes(gzip.compress(json.dumps({"dia": ultima, "blocos": ant}, separators=(",", ":")).encode(), mtime=0))
        tmp.replace(_estado_path(base))
    return {"fotos": fotos, "eventos": novos_ev, "lacunas": lacunas, "ultima_foto": ultima, **cont_total}


def resumo_do_dia(base: Path, date_str: str, proc: dict) -> dict:
    estado = carregar_estado(base)
    blocos = estado["blocos"] if estado else {}
    por_status: dict[str, dict] = {}
    for b in blocos.values():
        k = b["status"]
        x = por_status.setdefault(k, {"blocos": 0, "enderecos": 0, "br_blocos": 0, "br_enderecos": 0})
        x["blocos"] += 1
        x["enderecos"] += b["quantidade"]
        if b["cc"] == "BR":
            x["br_blocos"] += 1
            x["br_enderecos"] += b["quantidade"]
    corte = (dt.date.fromisoformat(date_str) - dt.timedelta(days=RECENTES_DIAS)).isoformat()
    eventos = [e for e in todos_eventos(base) if e["data"] > corte]
    por_tipo: dict[str, int] = {}
    for e in eventos:
        por_tipo[e["tipo"]] = por_tipo.get(e["tipo"], 0) + 1
    return {"snapshot_date": date_str, "generated_at": now_iso(), "ultima_foto": estado["dia"] if estado else None, "por_status": por_status, "eventos_ultimos_dias": RECENTES_DIAS,
            "eventos_por_tipo": por_tipo, "processamento": proc}


def validacao_cruzada(base: Path, date_str: str) -> Optional[dict]:
    """Das transferências diretas BR → BR do Registro.br, quantas aparecem como `titularidade` no `delegated` (mesmo bloco, de −3 a +45 dias da data da transferência)."""
    from core.jsonio import carregar_json_gz
    listas = carregar_json_gz(normalized_path(base, date_str, "summary") / "ipv4_listas.json.gz")
    if not listas:
        return None
    import ipaddress
    por_bloco: dict[str, list[dict]] = {}
    for e in todos_eventos(base):
        if e["tipo"] in ("titularidade", "novo"):
            for b in e["blocos"]:
                por_bloco.setdefault(b, []).append(e)
    total = com_evento = 0
    for t in listas["transferencias_registrobr"]:
        if t["pais_origem"] != "BR" or t["pais_destino"] != "BR" or t["data"] < "2020-01-01":
            continue
        total += 1
        d0 = dt.date.fromisoformat(t["data"])
        achou = False
        for b in t["blocos"]:
            net = ipaddress.ip_network(b)
            for k, evs in por_bloco.items():
                kn = ipaddress.ip_network(k)
                if kn.version == 4 and (kn.overlaps(net)) and any(-3 <= (dt.date.fromisoformat(e["data"]) - d0).days <= 45 for e in evs):
                    achou = True
                    break
            if achou:
                break
        com_evento += achou
    return {"transferencias_br_br_desde_2020": total, "com_titularidade_no_delegated": com_evento, "pct": round(100 * com_evento / total, 1) if total else None, "janela_dias": [-3, 45]}


def run(date_str: str, base: Path, log, desde: str = DESDE_PADRAO, zerar: bool = False, validar: bool = True) -> dict:
    proc = processar(base, date_str, log, desde, zerar)
    doc = resumo_do_dia(base, date_str, proc)
    if validar:
        doc["validacao_cruzada"] = validacao_cruzada(base, date_str)
    destino = normalized_path(base, date_str, "summary")
    destino.mkdir(parents=True, exist_ok=True)
    write_json_gz(destino / "ipv4_delegated.json.gz", doc)
    log.info("ipv4_delegated written", fotos=proc["fotos"], eventos=proc["eventos"], lacunas=len(proc["lacunas"]), ultima_foto=proc["ultima_foto"])
    return {**{k: v for k, v in proc.items() if k != "lacunas"}, "lacunas": len(proc["lacunas"]), "validacao": doc.get("validacao_cruzada")}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Eventos do ciclo de vida do IPv4 a partir do delegated do LACNIC")
    p.add_argument("--date", default=today_str())
    p.add_argument("--backfill-desde", default=None, help="reprocessa do zero a partir desta data (padrão: continua do estado)")
    p.add_argument("--force", action="store_true", help="aceito por compatibilidade com o executor")
    a = p.parse_args(argv)
    log = configure_logging()
    try:
        print(run(a.date, data_dir(), log, a.backfill_desde or DESDE_PADRAO, zerar=bool(a.backfill_desde)))
    except Exception:
        log.exception("falha em ipv4_delegated")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
