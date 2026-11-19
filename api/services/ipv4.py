# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Mercado de IPv4: consultas sobre `ipv4/*.json.gz` e os eventos do `delegated`. Diferenças observadas, sem causa nem intenção; nome de pessoa física já vem omitido."""
from __future__ import annotations

import ipaddress
from typing import Optional

from core.ipv4_listas import faixa_para_cidrs

DIRECOES = ("br_br", "br_exterior", "exterior_br")
_META = ("natureza", "fonte", "limites", "snapshot_date")


class Ipv4Erro(Exception):
    def __init__(self, status: int, mensagem: str):
        super().__init__(mensagem)
        self.status, self.mensagem = status, mensagem


def _meta(doc: dict) -> dict:
    return {k: doc.get(k) for k in _META}


def _norm_prefixo(prefixo: str) -> ipaddress.IPv4Network:
    try:
        net = ipaddress.ip_network(prefixo.strip(), strict=False)
    except ValueError:
        raise Ipv4Erro(400, f"prefixo inválido: {prefixo!r}")
    if net.version != 4:
        raise Ipv4Erro(400, "só IPv4: o ciclo de vida do IPv6 não faz parte deste passo.")
    return net


def _sobrepoe(blocos: list[str], net: ipaddress.IPv4Network) -> bool:
    return any(ipaddress.ip_network(b).overlaps(net) for b in blocos if ":" not in b)


def transferencias(doc: dict, ano: Optional[str], direcao: Optional[str], q: Optional[str], asn: Optional[int], prefixo: Optional[str], limit: int, offset: int) -> dict:
    if direcao and direcao not in DIRECOES:
        raise Ipv4Erro(400, f"direcao inválida: use {', '.join(DIRECOES)}.")
    net = _norm_prefixo(prefixo) if prefixo else None
    ops = doc["operacoes"]
    if ano:
        ops = [o for o in ops if o["data"].startswith(ano)]
    if direcao:
        ops = [o for o in ops if o["direcao"] == direcao]
    if asn is not None:
        ops = [o for o in ops if (o.get("casamento") or {}).get("asn") == asn]
    if net is not None:
        ops = [o for o in ops if _sobrepoe(o["blocos"], net)]
    if q:
        t = q.strip().lower()
        ops = [o for o in ops if t in f"{o['origem']['nome']} {o['destino']['nome']} {(o.get('casamento') or {}).get('org') or ''}".lower()]
    return {**_meta(doc), "filtros": {"ano": ano, "direcao": direcao, "q": q, "asn": asn, "prefixo": prefixo}, "total": len(ops), "limit": limit, "offset": offset, "items": ops[offset:offset + limit]}


def resumo(doc: dict) -> dict:
    return {**_meta(doc), **{k: v for k, v in doc.items() if k not in ("snapshot_date", "generated_at", "natureza", "fonte", "limites")}}


def recuperacao(doc: dict) -> dict:
    return {**_meta(doc), **{k: v for k, v in doc.items() if k not in ("snapshot_date", "generated_at", "natureza", "fonte", "limites")}}


def _limpo(e: dict) -> dict:
    return {k: v for k, v in e.items() if not k.startswith("_")}


def ciclo_de_vida(prefixo: str, transf: Optional[dict], rec: Optional[dict], blocos: Optional[dict], eventos: list[dict], ate: str, espaco_doc: Optional[dict] = None, uso: Optional[dict] = None) -> dict:
    """Linha do tempo de um bloco IPv4: estado atual no `delegated`, eventos observados, transferências declaradas e recuperação, ordenados do mais recente ao mais antigo."""
    net = _norm_prefixo(prefixo)
    i0, i1 = int(net.network_address), int(net.broadcast_address)
    atual = []
    for r in (blocos or {}).get("blocos", []):
        ini = int(ipaddress.IPv4Address(r[0]))
        if ini <= i1 and ini + r[1] - 1 >= i0:
            atual.append(dict(zip((blocos or {})["colunas"], r)))
    ev = [_limpo(e) for e in eventos if e["data"] <= ate and e["_i0"] <= i1 and e["_i1"] >= i0]
    tr = [o for o in (transf or {}).get("operacoes", []) if o["data"] <= ate and _sobrepoe(o["blocos"], net)]
    rc = [r for r in ((rec or {}).get("em_recuperacao") or {}).get("itens", []) if r["tipo"] == "bloco" and ipaddress.ip_network(r["recurso"]).overlaps(net)]
    if not (atual or ev or tr or rc):
        raise Ipv4Erro(404, f"Nenhum registro do Brasil para o bloco {net}.")
    linha = [{"data": e["data"], "fonte": "delegated", "tipo": e["tipo"], "detalhe": _limpo(e)} for e in ev]
    linha += [{"data": o["data"], "fonte": "+".join(o["fontes"]), "tipo": "transferencia", "detalhe": {k: o[k] for k in ("id", "origem", "destino", "blocos", "enderecos", "direcao", "primeira_vez_visto",
                                                                                                                      "anterior_a_coleta", "casamento")}} for o in tr]
    linha += [{"data": r["inicio"], "fonte": "registrobr", "tipo": "em_recuperacao", "detalhe": r} for r in rc]
    linha.sort(key=lambda x: (x["data"], x["tipo"]), reverse=True)
    sem = [x for x in _linhas_espaco(espaco_doc) if _cruza(x["inicio"], x["quantidade"], i0, i1)] if espaco_doc else []
    sin = [x for x in (uso or {}).get("itens", []) if _cruza(x["inicio"], x["quantidade"], i0, i1)]
    return {**_meta(transf or blocos or rec or {}), "bloco": str(net), "atual": atual, "espaco": sem, "sinais_de_terceiros": sin, "linha_do_tempo": linha,
            "aviso": "Diferenças observadas entre fotos diárias do delegated e o que as listas declaram; sem causa nem intenção. 'Transferência' é a data declarada; 'titularidade' é a mudança de organização vista no delegated."}


def _cruza(inicio: str, qtd: int, i0: int, i1: int) -> bool:
    a = int(ipaddress.IPv4Address(inicio))
    return a <= i1 and a + qtd - 1 >= i0


def linhas_transferencias(doc: Optional[dict]) -> list[dict]:
    """Uma linha por operação (coleção `transferencias_ipv4` do `/query`)."""
    out = []
    for o in (doc or {}).get("operacoes", []):
        c = o.get("casamento") or {}
        out.append({"id": o["id"], "data": o["data"], "direcao": o["direcao"], "tamanho": o["tamanho"], "origem_nome": o["origem"]["nome"], "origem_pais": o["origem"]["pais"],
                    "origem_rir": o["origem"]["rir"], "destino_nome": o["destino"]["nome"], "destino_pais": o["destino"]["pais"], "destino_rir": o["destino"]["rir"], "n_blocos": o["n_blocos"],
                    "enderecos": o["enderecos"], "blocos": o["blocos"], "fontes": o["fontes"], "primeira_vez_visto": o["primeira_vez_visto"], "anterior_a_coleta": o["anterior_a_coleta"],
                    "defasagem_dias": o["defasagem_dias"], "asn_destino": c.get("asn"), "org_destino": c.get("org")})
    return out


def linhas_recuperacao(doc: Optional[dict]) -> list[dict]:
    return [dict(i) for i in ((doc or {}).get("em_recuperacao") or {}).get("itens", [])]


def linhas_eventos(eventos: list[dict], ate: str) -> list[dict]:
    """Uma linha por evento do `delegated` do Brasil (coleção `eventos_bloco`)."""
    out = []
    for e in eventos:
        if e["data"] > ate:
            continue
        de, para = e.get("de") or {}, e.get("para") or {}
        out.append({"id": e["id"], "data": e["data"], "tipo": e["tipo"], "inicio": e["inicio"], "quantidade": e["quantidade"], "blocos": e["blocos"], "de_status": de.get("status"),
                    "de_cc": de.get("cc"), "de_opaque": de.get("opaque"), "para_status": para.get("status"), "para_cc": para.get("cc"), "para_opaque": para.get("opaque"),
                    "visto_entre": e.get("visto_entre")})
    return out


CLASSES = ("nao_anunciado", "roa_sem_anuncio", "parcial", "em_recuperacao")
SINAIS_IDS = ("S1", "S2", "S3", "S4")


def _linhas_espaco(doc: dict) -> list[dict]:
    cols = doc["colunas"]
    return [dict(zip(cols, r)) for r in doc["blocos"]]


def espaco(doc: dict, classe: Optional[str], asn: Optional[int], cnpj: Optional[str], uf: Optional[str], limit: int, offset: int) -> dict:
    """Blocos IPv4 do Brasil que não estão plenamente anunciados, com o resumo geral. Não anunciado não é sem uso."""
    if classe and classe not in CLASSES:
        raise Ipv4Erro(400, f"classe inválida: use {', '.join(CLASSES)}.")
    ls = _linhas_espaco(doc)
    if classe:
        ls = [x for x in ls if x["classe"] == classe]
    if asn is not None:
        ls = [x for x in ls if x["asn"] == asn]
    if cnpj:
        ls = [x for x in ls if x["cnpj"] == "".join(c for c in cnpj if c.isdigit())]
    if uf:
        ls = [x for x in ls if x["uf"] == uf.upper()]
    ls.sort(key=lambda x: (-(x["quantidade"] or 0), x["inicio"]))
    return {**_meta(doc), "ultima_foto": doc.get("ultima_foto"), "resumo": doc["resumo"], "duracao": doc["duracao"], "filtros": {"classe": classe, "asn": asn, "cnpj": cnpj, "uf": uf},
            "total": len(ls), "limit": limit, "offset": offset, "items": ls[offset:offset + limit]}


def uso_por_terceiros(doc: dict, sinal: Optional[str], confianca: Optional[str], asn: Optional[int], cnpj: Optional[str], limit: int, offset: int) -> dict:
    """Blocos com sinais de uso por terceiros: HIPÓTESE, com falsos positivos conhecidos; nunca aluguel."""
    if sinal and sinal not in doc["sinais"]:
        raise Ipv4Erro(400, f"sinal inválido: use {', '.join(doc['sinais'])}.")
    if confianca and confianca not in ("baixa", "media", "alta"):
        raise Ipv4Erro(400, "confianca inválida: use baixa, media ou alta.")
    it = doc["itens"]
    if sinal:
        it = [x for x in it if any(s["id"] == sinal for s in x["sinais"])]
    if confianca:
        it = [x for x in it if x["confianca"] == confianca]
    if asn is not None:
        it = [x for x in it if (x["titular"] or {}).get("asn") == asn or asn in x["origens"]]
    if cnpj:
        c = "".join(ch for ch in cnpj if ch.isdigit())
        it = [x for x in it if (x["titular"] or {}).get("cnpj") == c]
    return {**_meta(doc), "rotulo": doc["rotulo"], "sinais": doc["sinais"], "por_sinal": doc["por_sinal"], "por_confianca": doc["por_confianca"], "blocos_avaliados": doc["blocos_avaliados"],
            "filtros": {"sinal": sinal, "confianca": confianca, "asn": asn, "cnpj": cnpj}, "total": len(it), "limit": limit, "offset": offset, "items": it[offset:offset + limit]}


def recursos_do_asn(asn: int, blocos: Optional[dict], espaco_doc: Optional[dict], uso: Optional[dict]) -> Optional[dict]:
    """O que o ASN tem de IPv4: blocos alocados a ele (delegated), os não plenamente anunciados e os sinais de terceiros (como titular e como origem de bloco alheio). `None` se não há nada."""
    cols = (blocos or {}).get("colunas") or []
    meus = [dict(zip(cols, r)) for r in (blocos or {}).get("blocos", []) if r[cols.index("asn")] == asn] if cols else []
    sem = [x for x in _linhas_espaco(espaco_doc) if x["asn"] == asn] if espaco_doc else []
    como_titular = [x for x in (uso or {}).get("itens", []) if (x["titular"] or {}).get("asn") == asn]
    como_origem = [x for x in (uso or {}).get("itens", []) if asn in x["origens"] and (x["titular"] or {}).get("asn") != asn]
    if not (meus or sem or como_titular or como_origem):
        return None
    base = espaco_doc or uso or blocos or {}
    return {**_meta(base), "asn": asn, "blocos": len(meus), "enderecos": sum(m["quantidade"] for m in meus), "nao_plenamente_anunciados": sem, "sinais_como_titular": como_titular,
            "sinais_como_origem": como_origem, "aviso": "Não anunciado não é sem uso; sinal de terceiros é hipótese, com falsos positivos conhecidos (provedor que anuncia o bloco do cliente)."}


def subasignacoes(doc: dict, asn: Optional[int], conforme: Optional[bool], limit: int, offset: int) -> dict:
    """Sub-asignações (aluguel regulado, LAC-2025-5): `ativa: false` enquanto a bitácora oficial não existe (então `aviso` explica e `subasignacoes` fica vazio)."""
    itens = doc["subasignacoes"]
    if asn is not None:
        itens = [x for x in itens if x["receptor_asn"] == asn]
    if conforme is not None:
        itens = [x for x in itens if x["em_conformidade"] is conforme]
    return {**_meta(doc), **{k: doc[k] for k in ("ativa", "aguardando", "aviso", "politica", "validacoes", "esquema_hipotetico", "vigia", "indicador_terceiros", "eventos")},
            "filtros": {"asn": asn, "conforme": conforme}, "total": len(itens), "limit": limit, "offset": offset, "items": itens[offset:offset + limit]}


def linhas_subasignacoes(doc: Optional[dict]) -> list[dict]:
    return [{"id": x["id"], "bloco": x["bloco"], "receptor_asn": x["receptor_asn"], "cedente_asn": x.get("cedente_asn"), "inicio": x["inicio"], "fim": x["fim"], "em_conformidade": x["em_conformidade"],
             "pendentes": x["pendentes"], **{f"valida_{k}": v for k, v in x["validacoes"].items()}} for x in (doc or {}).get("subasignacoes", [])]


def linhas_espaco(doc: Optional[dict]) -> list[dict]:
    return _linhas_espaco(doc) if doc else []


def linhas_uso(doc: Optional[dict]) -> list[dict]:
    """Uma linha por bloco com sinal (coleção `uso_por_terceiros_ipv4`)."""
    out = []
    for x in (doc or {}).get("itens", []):
        t = x["titular"] or {}
        out.append({"inicio": x["inicio"], "quantidade": x["quantidade"], "classe": x["classe"], "anunciado_pct": x["anunciado_pct"], "asn_titular": t.get("asn"), "org_titular": t.get("org"),
                    "origens": x["origens"], "roa_asns": x["roa_asns"], "sinais": [s["id"] for s in x["sinais"]], "confianca": x["confianca"], "evidencias": [s["evidencia"] for s in x["sinais"]]})
    return out


__all__ = ["faixa_para_cidrs"]
