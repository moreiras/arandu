# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Mercado de IPv4 do Brasil. Saída: `published/{date}/ipv4/{transferencias,mercado,recuperacao,blocos_br}.json.gz`.

Junta as listas de transferência do Registro.br e o log do LACNIC (`ipv4_listas`), o `delegated` diário (`ipv4_delegated`, eventos em `data/ipv4/`) e o cadastro de ASNs do snapshot (casamento
bloco → ASN e organização). A unidade é a **operação**: o mesmo dia e o mesmo par de partes (um lote de 430 blocos é uma operação, não 430).

  * Transferência é o que as listas declaram, na data que declaram; o que o `delegated` mostra como mudança de titularidade é outro dado, cruzado em `ipv4_delegated.validacao_cruzada`.
  * `defasagem_dias` = primeira data de snapshot em que a lista mostrou a operação − data da operação; só para o que apareceu depois do início da nossa coleta.
  * Nome de pessoa física provável sai mascarado (`Pessoa física`); o casamento com ASN usa o cadastro do snapshot, que é público.
  * Sem causa nem intenção: "mudança de titularidade" é diferença observada, não aluguel nem venda.
"""
from __future__ import annotations

import datetime as dt
import ipaddress
import re
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median
from typing import Optional

from core.common import normalized_path, now_iso, published_path
from core.ipv4_listas import mascarar_nome, sem_acento, tipo_pessoa
from core.jsonio import carregar_json, carregar_json_gz, gravar_json_gz

LIMITES = (
    "Transferências são o que o Registro.br e o LACNIC declaram, na data que declaram; o histórico do Registro.br só existe desde o início da nossa coleta (junho de 2026), então "
    "'primeira vez visto' de registros antigos é a primeira data coletada. Uma operação reúne os blocos do mesmo dia e das mesmas partes. O casamento com o ASN usa os blocos que o "
    "Registro.br aloca ao ASN no snapshot (organização sem ASN fica sem casamento). Nome de pessoa física provável é omitido. Não se atribui causa nem intenção."
)
CLASSES = (("ate_24", 256), ("22_a_23", 1024), ("20_a_21", 4096))


def classe_tamanho(enderecos: int) -> str:
    for nome, lim in CLASSES:
        if enderecos <= lim:
            return nome
    return "19_ou_maior"


def direcao(pais_o: Optional[str], pais_d: Optional[str]) -> str:
    o, d = pais_o == "BR", pais_d == "BR"
    return "br_br" if o and d else "br_exterior" if o else "exterior_br" if d else "exterior"


def _documentos_asn(base: Path, date_str: str):
    """(asn, documento): do fragmento `base` quando o snapshot está sendo montado (os documentos ainda não existem) ou dos documentos publicados."""
    from core import compose
    if compose.fluxo_novo(base, date_str):
        yield from compose.iterar_documentos(base, date_str, ("base",))
        return
    pub = published_path(base, date_str)
    for a in carregar_json(pub / "asns" / "index.json", []) or []:
        if a.get("is_br") and a.get("rir_prefixes_v4_count"):
            d = carregar_json(pub / "asns" / f"{a['asn']}.json", None)
            if d:
                yield a["asn"], d


def indice_asn(base: Path, date_str: str) -> dict[str, dict]:
    """Blocos que o Registro.br aloca a cada ASN brasileiro do snapshot: {cidr: {asn, org, cnpj}} (para casar bloco → ASN e organização)."""
    out: dict[str, dict] = {}
    for asn, d in _documentos_asn(base, date_str):
        if not d.get("is_br"):
            continue
        for b in d.get("rir_prefixes_v4") or []:
            out.setdefault(b, {"asn": asn, "org": d.get("name"), "cnpj": d.get("cnpj")})
    return out


def casar(bloco: str, idx: dict[str, dict]) -> Optional[dict]:
    """Bloco igual ou contido num bloco alocado a um ASN."""
    net = ipaddress.ip_network(bloco)
    for p in range(net.prefixlen, 7, -1):
        hit = idx.get(str(net.supernet(new_prefix=p)))
        if hit:
            return hit
    return None


def _parte(nome: Optional[str], pais: Optional[str], rir: Optional[str]) -> dict:
    return {"nome": mascarar_nome(nome or "", pais) if nome else None, "pais": pais, "rir": rir, "pessoa": tipo_pessoa(nome or "", pais) if nome else None}


def _sobrepoe(a: list[str], b: list[str]) -> bool:
    return any(ipaddress.ip_network(x).overlaps(ipaddress.ip_network(y)) for x in a for y in b)


def operacoes(listas: dict, idx: dict[str, dict]) -> list[dict]:
    """Operações com o Brasil: Registro.br (nomes em português, blocos) + as do log do LACNIC que o Registro.br não tem."""
    grupos: dict[tuple, dict] = {}
    for t in listas.get("transferencias_registrobr", []):
        k = (t["data"], t["origem"], t["destino"])
        g = grupos.setdefault(k, {"data": t["data"], "origem": _parte(t["origem"], t["pais_origem"], t["rir_origem"]), "destino": _parte(t["destino"], t["pais_destino"], t["rir_destino"]),
                                  "blocos": [], "vistas": [], "fontes": ["registrobr"], "anterior": True})
        g["blocos"].extend(t["blocos"])
        g["vistas"].append(t.get("primeira_vez_visto"))
        g["anterior"] = g["anterior"] and bool(t.get("anterior_a_coleta"))
    ops = list(grupos.values())
    por_data: dict[str, list[dict]] = defaultdict(list)
    for o in ops:
        por_data[o["data"]].append(o)
    novas = []
    for t in listas.get("transferencias_lacnic", []):
        if "BR" not in (t.get("pais_origem"), t.get("pais_destino")) or not t.get("blocos"):
            continue
        data = dt.date.fromisoformat(t["data"])
        par = [o for dd in (data - dt.timedelta(days=1), data, data + dt.timedelta(days=1)) for o in por_data.get(dd.isoformat(), []) if _sobrepoe(o["blocos"], t["blocos"])]
        if par:
            for o in par:
                if "lacnic" not in o["fontes"]:
                    o["fontes"].append("lacnic")
            continue
        k = (t["data"], t["origem"], t["destino"])
        n = next((x for x in novas if x["_k"] == k), None)
        if n is None:
            n = {"_k": k, "data": t["data"], "origem": _parte(t["origem"], t["pais_origem"], t["rir_origem"]), "destino": _parte(t["destino"], t["pais_destino"], t["rir_destino"]),
                 "blocos": [], "vistas": [], "fontes": ["lacnic"], "anterior": True}
            novas.append(n)
        n["blocos"].extend(t["blocos"])
        n["vistas"].append(t.get("primeira_vez_visto"))
        n["anterior"] = n["anterior"] and bool(t.get("anterior_a_coleta"))
    out = []
    for o in ops + novas:
        o.pop("_k", None)
        blocos = sorted(set(o["blocos"]), key=lambda b: (ipaddress.ip_network(b).version, int(ipaddress.ip_network(b).network_address)))
        vistas = [v for v in o.pop("vistas") if v]
        visto = min(vistas) if vistas else None
        anterior = o.pop("anterior")
        enderecos = sum(ipaddress.ip_network(b).num_addresses for b in blocos if ":" not in b)
        o.update({"blocos": blocos, "n_blocos": len(blocos), "enderecos": enderecos, "tamanho": classe_tamanho(enderecos), "direcao": direcao(o["origem"]["pais"], o["destino"]["pais"]),
                  "primeira_vez_visto": visto, "anterior_a_coleta": anterior,
                  "defasagem_dias": None if anterior or not visto else (dt.date.fromisoformat(visto) - dt.date.fromisoformat(o["data"])).days})
        hit = next((c for c in (casar(b, idx) for b in blocos if ":" not in b) if c), None) if o["destino"]["pais"] == "BR" else None
        if hit:
            o["casamento"] = {"asn": hit["asn"], "org": mascarar_nome(hit["org"] or "", "BR") if hit.get("org") else None}
        o["id"] = _id(o)
        out.append(o)
    out.sort(key=lambda o: (o["data"], o["id"]), reverse=True)
    return out


def _id(o: dict) -> str:
    import hashlib
    return hashlib.sha1(f"{o['data']}|{','.join(o['blocos'][:5])}|{o['origem']['nome']}|{o['destino']['nome']}".encode()).hexdigest()[:12]


class _Partes:
    """Soma endereços por parte, juntando grafias do mesmo nome (maiúsculas, pontuação, acento: `TIM SA`, `TIM S.A.`, `Tim S/A`); mostra a grafia mais frequente."""

    def __init__(self) -> None:
        self.soma: Counter = Counter()
        self.grafias: dict[str, Counter] = defaultdict(Counter)

    def somar(self, nome: str, enderecos: int) -> None:
        k = re.sub(r"[^A-Z0-9]+", "", sem_acento(nome))
        self.soma[k] += enderecos
        self.grafias[k][nome] += 1

    def top(self, n: int) -> list[tuple[str, int]]:
        return [(self.grafias[k].most_common(1)[0][0], e) for k, e in self.soma.most_common(n)]


def mercado(ops: list[dict]) -> dict:
    por_ano: dict[str, dict] = {}
    for o in ops:
        a = por_ano.setdefault(o["data"][:4], {"operacoes": 0, "blocos": 0, "enderecos": 0, "por_direcao": defaultdict(lambda: {"operacoes": 0, "enderecos": 0})})
        a["operacoes"] += 1
        a["blocos"] += o["n_blocos"]
        a["enderecos"] += o["enderecos"]
        d = a["por_direcao"][o["direcao"]]
        d["operacoes"] += 1
        d["enderecos"] += o["enderecos"]
    for a in por_ano.values():
        a["por_direcao"] = dict(a["por_direcao"])
    tam = Counter(o["tamanho"] for o in ops)
    total_end = sum(o["enderecos"] for o in ops) or 1
    dest, orig = _Partes(), _Partes()
    for o in ops:
        if o["destino"]["nome"] and o["destino"]["pessoa"] == "pj":
            dest.somar(o["destino"]["nome"], o["enderecos"])
        if o["origem"]["nome"] and o["origem"]["pessoa"] == "pj":
            orig.somar(o["origem"]["nome"], o["enderecos"])
    maior = max(ops, key=lambda o: o["n_blocos"], default=None)
    defas = [o["defasagem_dias"] for o in ops if o["defasagem_dias"] is not None]
    br_dest = [o for o in ops if o["destino"]["pais"] == "BR" and o["direcao"] != "exterior"]
    return {"por_ano": dict(sorted(por_ano.items())), "por_tamanho": dict(tam), "operacoes": len(ops), "blocos": sum(o["n_blocos"] for o in ops), "enderecos": total_end if ops else 0,
            "concentracao": {"top_destinos": [{"nome": n, "enderecos": e, "pct": round(100 * e / total_end, 1)} for n, e in dest.top(10)],
                             "top_origens": [{"nome": n, "enderecos": e, "pct": round(100 * e / total_end, 1)} for n, e in orig.top(10)]},
            "maior_operacao": {"data": maior["data"], "blocos": maior["n_blocos"], "enderecos": maior["enderecos"]} if maior else None,
            "defasagem": {"operacoes_com_medida": len(defas), "mediana_dias": median(defas) if defas else None, "maximo_dias": max(defas) if defas else None},
            "casamento": {"destino_br": len(br_dest), "com_asn": sum(1 for o in br_dest if o.get("casamento")), "pct": round(100 * sum(1 for o in br_dest if o.get("casamento")) / len(br_dest), 1) if br_dest else None}}


def recuperacao(listas: dict, estado: Optional[dict], eventos_br: list[dict]) -> dict:
    """Recursos em recuperação (com a janela e, para bloco IPv4, o status atual no `delegated`) e recuperados; eventos de recuperação e liberação por mês."""
    blocos = (estado or {}).get("blocos") or {}
    por_net = {ipaddress.ip_network(f"{b['inicio']}/{32 - (b['quantidade'] - 1).bit_length()}"): b for b in blocos.values() if b["quantidade"] & (b["quantidade"] - 1) == 0}

    def status_atual(rec: str) -> Optional[str]:
        net = ipaddress.ip_network(rec)
        for p in range(net.prefixlen, 7, -1):
            b = por_net.get(net.supernet(new_prefix=p))
            if b:
                return b["status"]
        return None

    itens = []
    for r in listas.get("recuperacao", []):
        itens.append({"tipo": r["tipo"], "recurso": r["recurso"], "inicio": r["inicio"], "fim": r["fim"], "primeira_vez_visto": r.get("primeira_vez_visto"),
                      "status_delegated": status_atual(r["recurso"]) if r["tipo"] == "bloco" else None})
    mensal: dict[str, Counter] = defaultdict(Counter)
    for e in eventos_br:
        if e["tipo"] in ("recuperacao", "liberacao"):
            mensal[e["data"][:7]][e["tipo"]] += e["quantidade"]
    return {"em_recuperacao": {"total": len(itens), "por_tipo": dict(Counter(i["tipo"] for i in itens)), "janelas": sorted({(i["inicio"], i["fim"]) for i in itens}), "itens": itens},
            "recuperados": {"total": len(listas.get("recuperados", [])), "por_tipo": dict(Counter(r["tipo"] for r in listas.get("recuperados", [])))},
            "eventos_por_mes": {m: dict(c) for m, c in sorted(mensal.items())}}


def blocos_br(estado: Optional[dict], idx: dict[str, dict]) -> list[list]:
    """Blocos IPv4 do Brasil na última foto do `delegated`: [início, quantidade, status, data, opaque-id, ASN, organização]."""
    out = []
    for b in sorted(((estado or {}).get("blocos") or {}).values(), key=lambda b: int(ipaddress.IPv4Address(b["inicio"]))):
        if b.get("cc") != "BR":
            continue
        hit = None
        for c in faixa_cidrs(b):
            hit = casar(c, idx)
            if hit:
                break
        out.append([b["inicio"], b["quantidade"], b["status"], b.get("data"), b.get("opaque"), hit["asn"] if hit else None, mascarar_nome(hit["org"] or "", "BR") if hit and hit.get("org") else None])
    return out


def faixa_cidrs(b: dict) -> list[str]:
    from core.ipv4_listas import faixa_para_cidrs
    return faixa_para_cidrs(b["inicio"], b["quantidade"])


def eventos_br(base: Path, ate: str) -> list[dict]:
    from sources.ipv4_delegated.enrich import todos_eventos
    return [e for e in todos_eventos(base) if e["data"] <= ate and ((e.get("de") or {}).get("cc") == "BR" or (e.get("para") or {}).get("cc") == "BR")]


def publicar_ipv4(base: Path, date_str: str, log) -> dict:
    norm = normalized_path(base, date_str, "summary")
    pub = published_path(base, date_str)
    listas = carregar_json_gz(norm / "ipv4_listas.json.gz")
    if not listas:
        log.info("ipv4_listas ausente: mercado de IPv4 não gerado")
        return {}
    from sources.ipv4_delegated.enrich import carregar_estado
    estado = carregar_estado(base)
    idx = indice_asn(base, date_str)
    ops = operacoes(listas, idx)
    evs = eventos_br(base, date_str)
    destino = pub / "ipv4"
    destino.mkdir(parents=True, exist_ok=True)
    meta = {"snapshot_date": date_str, "generated_at": now_iso(), "natureza": "observado", "fonte": "Registro.br e LACNIC (listas de numeração e delegated-extended)", "limites": LIMITES}
    m = mercado(ops)
    gravar_json_gz(destino / "transferencias.json.gz", {**meta, "total": len(ops), "operacoes": ops})
    gravar_json_gz(destino / "mercado.json.gz", {**meta, "periodo": [min((o["data"] for o in ops), default=None), max((o["data"] for o in ops), default=None)], **m})
    gravar_json_gz(destino / "recuperacao.json.gz", {**meta, **recuperacao(listas, estado, evs)})
    gravar_json_gz(destino / "blocos_br.json.gz", {**meta, "ultima_foto": estado["dia"] if estado else None, "colunas": ["inicio", "quantidade", "status", "data_registro", "opaque_id", "asn", "organizacao"],
                                                   "blocos": blocos_br(estado, idx)})
    log.info("ipv4 written", operacoes=len(ops), eventos_br=len(evs), casamento_pct=m["casamento"]["pct"])
    return {"operacoes": len(ops), "eventos_br": len(evs), "casamento_pct": m["casamento"]["pct"]}
