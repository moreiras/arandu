# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Sub-asignações de IPv4 (aluguel regulado, LAC-2025-5). Saída: `published/{date}/ipv4/subasignacoes.json.gz`.

Sem a bitácora oficial (até 2026-11-02 ela não existe), o artefato sai com `ativa: false`, o aviso "aguardando a publicação oficial" e o estado do vigia de diretórios, para a interface explicar o que
falta e para o dia em que o arquivo aparecer ser visível. Com a fonte ativada (`ARANDU_SUBASIGNACAO_URL`, `sources/ipv4_subasignacao`), cada registro recebe as validações de `core/ipv4_subasignacao.py`
(`True`, `False` ou `None` quando falta dado) e o indicador de anúncios de terceiros **com** e **sem** registro oficial sai do cruzamento com os sinais S1 e S3 de `products/ipv4_uso`.
Eventos `subasignacao_inicio` e `subasignacao_fim` vêm da diferença para o artefato do snapshot anterior.
"""
from __future__ import annotations

import datetime as dt
import gzip
import ipaddress
import json
from pathlib import Path
from typing import Optional

from core import ipv4_subasignacao as S
from core.common import normalized_path, now_iso, published_path
from core.jsonio import carregar_json_gz, gravar_json_gz
from products.ipv4.build import _documentos_asn
from products.ipv4_uso.build import Roas, Tabela, _intervalo

AVISO_AGUARDANDO = ("Aguardando a publicação oficial. A política LAC-2025-5 (sub-asignação, o aluguel regulado de IPv4) foi ratificada em 24/03/2026 e a produção está prevista até o fim de 2026; "
                    "a bitácora pública e o formato dos registros ainda não existem. Os diretórios do Registro.br e do LACNIC são vigiados todos os dias: quando surgir arquivo novo, ele aparece aqui.")
POLITICA = {"nome": "LAC-2025-5", "estado": "ratificada em 2026-03-24; produção prevista até o fim de 2026 (a confirmar)", "fonte_oficial": "ainda não publicada"}


def vigia_resumo(base: Path, date_str: str) -> dict:
    pasta = base / "ops" / "vigia" / "ipv4"
    arqs = sorted(p for p in pasta.glob("*.json") if p.stem <= date_str) if pasta.exists() else []
    if not arqs:
        return {"ultima_varredura": None, "alertas_30_dias": []}
    corte = (dt.date.fromisoformat(date_str) - dt.timedelta(days=30)).isoformat()
    alertas = []
    for p in arqs:
        if p.stem > corte:
            d = json.loads(p.read_text(encoding="utf-8"))
            alertas += [{"data": p.stem, **{k: v for k, v in a.items() if k in ("tipo", "url", "nome", "padrao")}} for a in d.get("alertas", [])]
    return {"ultima_varredura": arqs[-1].stem, "alertas_30_dias": alertas[-20:]}


def eventos(anterior: list[dict], atual: list[dict], data: str) -> list[dict]:
    a, b = {r["id"]: r for r in anterior}, {r["id"]: r for r in atual}
    ev = [{"tipo": "subasignacao_inicio", "data": data, "id": i, "bloco": r["bloco"], "receptor_asn": r["receptor_asn"]} for i, r in b.items() if i not in a]
    ev += [{"tipo": "subasignacao_fim", "data": data, "id": i, "bloco": r["bloco"], "receptor_asn": r["receptor_asn"]} for i, r in a.items() if i not in b or (b[i]["fim"] and not a[i]["fim"] and b[i]["fim"] <= data)]
    return ev


def _snapshot_anterior(base: Path, date_str: str) -> Optional[Path]:
    raiz = base / "published"
    antes = sorted(d.name for d in raiz.iterdir() if d.is_dir() and d.name < date_str and (d / "ipv4" / "subasignacoes.json.gz").exists()) if raiz.exists() else []
    return raiz / antes[-1] / "ipv4" / "subasignacoes.json.gz" if antes else None


def _ultimo_evento(r: dict, evs: list[dict], listas: dict) -> Optional[str]:
    net = ipaddress.ip_network(r["bloco"])
    datas = [e["data"] for e in evs if e["tipo"] in ("titularidade", "recuperacao") and e["data"] <= r["inicio"] and any(ipaddress.ip_network(b).overlaps(net) for b in e["blocos"])]
    datas += [t["data"] for t in listas.get("transferencias_registrobr", []) if t["data"] <= r["inicio"] and any(ipaddress.ip_network(b).overlaps(net) for b in t["blocos"] if ":" not in b)]
    return max(datas) if datas else None


def publicar_ipv4_subasig(base: Path, date_str: str, log) -> dict:
    norm = normalized_path(base, date_str, "summary")
    pub = published_path(base, date_str)
    fonte = carregar_json_gz(norm / "ipv4_subasignacoes.json.gz")
    regs = (fonte or {}).get("registros") or []
    meta = {"snapshot_date": date_str, "generated_at": now_iso(), "natureza": "observado" if fonte else "indisponivel", "politica": POLITICA, "validacoes": S.VALIDACOES, "esquema_hipotetico": True}
    doc = {**meta, "ativa": bool(fonte), "aguardando": not fonte, "aviso": None if fonte else AVISO_AGUARDANDO, "vigia": vigia_resumo(base, date_str), "subasignacoes": [], "eventos": [],
           "indicador_terceiros": {"com_registro": None, "sem_registro": None, "nota": "Sem a bitácora oficial não há como separar anúncios de terceiros com e sem registro."}}
    if fonte:
        origin = carregar_json_gz(norm / "origin-prefixes-v4.json.gz") or {}
        tab = Tabela((p, int(a)) for a, ps in origin.items() for p in ps)
        roas = Roas(carregar_json_gz(pub / "rpki" / "vrp_list.json.gz") or [])
        listas = carregar_json_gz(norm / "ipv4_listas.json.gz") or {}
        ipv6 = {int(asn): bool(d["has_ipv6"]) for asn, d in _documentos_asn(base, date_str) if "has_ipv6" in d}
        crit_arq = base / "raw" / date_str / "summary" / f"lacnic-critical-infra-{date_str}.gz"
        criticos = S.parse_infra_critica(gzip.decompress(crit_arq.read_bytes()).decode("utf-8", "replace")) if crit_arq.exists() else None
        from sources.ipv4_delegated.enrich import todos_eventos
        evs = [e for e in todos_eventos(base) if e["data"] <= date_str]
        itens = []
        for r in regs:
            net = ipaddress.ip_network(r["bloco"])
            ini, fim = int(net.network_address), int(net.broadcast_address)
            origens = tab.cobertura(ini, fim)[1] if origin else None
            val = S.validar(r, origens, roas.asns(ini, fim), ipv6.get(r["receptor_asn"]), _ultimo_evento(r, evs, listas), criticos)
            itens.append({**r, "validacoes": val, "em_conformidade": all(v is True for v in val.values()), "pendentes": [k for k, v in val.items() if v is None]})
        doc["subasignacoes"] = itens
        doc["ignoradas"] = fonte.get("ignoradas", 0)
        ant = _snapshot_anterior(base, date_str)
        doc["eventos"] = eventos((carregar_json_gz(ant) or {}).get("subasignacoes", []) if ant else [], itens, date_str)
        uso = carregar_json_gz(pub / "ipv4" / "uso_por_terceiros.json.gz") or {}
        receptores = receptores_por_bloco(itens)
        terc = [i for i in uso.get("itens", []) if any(s["id"] in ("S1", "S3") for s in i["sinais"])]
        com = [i for i in terc if any(set(i["origens"]) & rs for rs in receptores_do_bloco(receptores, i))]
        doc["indicador_terceiros"] = {"com_registro": len(com), "sem_registro": len(terc) - len(com), "nota": "Blocos com sinal S1 ou S3 cujo anunciante tem sub-asignação registrada para o bloco, e os demais. Hipótese, não acusação."}
    destino = pub / "ipv4"
    destino.mkdir(parents=True, exist_ok=True)
    gravar_json_gz(destino / "subasignacoes.json.gz", doc)
    log.info("ipv4_subasig written", ativa=doc["ativa"], registros=len(doc["subasignacoes"]), alertas_vigia=len(doc["vigia"]["alertas_30_dias"]))
    return {"ativa": doc["ativa"], "registros": len(doc["subasignacoes"]), "eventos": len(doc["eventos"])}


def receptores_por_bloco(itens: list[dict]) -> dict[str, set[int]]:
    out: dict[str, set[int]] = {}
    for i in itens:
        out.setdefault(i["bloco"], set()).add(i["receptor_asn"])
    return out


def receptores_do_bloco(receptores: dict[str, set[int]], item: dict) -> list[set[int]]:
    """Receptores registrados para algum bloco que se sobrepõe ao bloco do item."""
    ini = int(ipaddress.IPv4Address(item["inicio"]))
    fim = ini + item["quantidade"] - 1
    out = []
    for b, asns in receptores.items():
        n = ipaddress.ip_network(b)
        if int(n.network_address) <= fim and int(n.broadcast_address) >= ini:
            out.append(asns)
    return out
