# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Séries nacionais por snapshot com regra de comparabilidade (PT-28): roteamento (RPKI das rotas brasileiras) e segurança (prontidão, ROV e DNSSEC).

Reaproveita o que cada snapshot já publicou (`routing_analysis_resumo.json`, `prontidao/asns.json.gz`, `seguranca/asns.json.gz`): nada novo é coletado. Cada
ponto traz os metadados que a regra de `core/comparabilidade.py` usa (base, método, cobertura) e a resposta marca onde a série é cortada.

Snapshot sem o artefato entra como ponto sem valor (`ausente`), para a lacuna aparecer na série em vez de sumir. Os documentos de ASN são grandes: cada um é
lido, reduzido ao ponto e solto; o ponto fica em cache por data (snapshot publicado é imutável)."""
from __future__ import annotations

import gzip
import hashlib
import json
import re
from typing import Any, Callable, Optional

from core import comparabilidade as comp
from core import layout

FAMILIAS = ("roteamento", "seguranca")
_DATA = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_PONTOS: dict[tuple[str, str], dict[str, Any]] = {}
_LIMITE_CACHE = 400


class SerieErro(Exception):
    def __init__(self, status: int, mensagem: str):
        super().__init__(mensagem)
        self.status = status
        self.mensagem = mensagem


def _ler(store, data: str, rel: str) -> Optional[Any]:
    bruto = layout.ler_bytes(store._pub(data), rel)
    if bruto is None:
        return None
    try:
        return json.loads(gzip.decompress(bruto) if rel.endswith(".gz") else bruto)
    except Exception:
        return None


def _hash(texto: Any) -> str:
    return hashlib.sha256(str(texto).encode("utf-8")).hexdigest()[:10]


# ── roteamento: estado RPKI das rotas brasileiras (routing_analysis_resumo.json) ────────────────────────────────────────────────────
_ROT = {  # id: (rótulo, unidade, função que lê o resumo)
    "rpki_valido_pct_v6": ("Rotas IPv6 com origem RPKI válida", "%", lambda r: r["rpki"]["v6"]["pct"]["valid"]),
    "rpki_invalido_pct_v6": ("Rotas IPv6 com origem RPKI inválida", "%", lambda r: r["rpki"]["v6"]["pct"]["invalid"]),
    "rpki_sem_roa_pct_v6": ("Rotas IPv6 sem ROA", "%", lambda r: r["rpki"]["v6"]["pct"]["not_found"]),
    "rotas_br_v6": ("Rotas IPv6 brasileiras", "rotas", lambda r: r["rotas_br"]["v6"]["pbr_routes"]),
    "rpki_valido_pct_v4": ("Rotas IPv4 com origem RPKI válida", "%", lambda r: r["rpki"]["v4"]["pct"]["valid"]),
    "rpki_invalido_pct_v4": ("Rotas IPv4 com origem RPKI inválida", "%", lambda r: r["rpki"]["v4"]["pct"]["invalid"]),
    "rpki_sem_roa_pct_v4": ("Rotas IPv4 sem ROA", "%", lambda r: r["rpki"]["v4"]["pct"]["not_found"]),
    "rotas_br_v4": ("Rotas IPv4 brasileiras", "rotas", lambda r: r["rotas_br"]["v4"]["pbr_routes"]),
}
_ROT_FONTE = "RouteViews (tabela global) e VRPs do RPKI; estado de origem pela RFC 6811 (Proposed Standard)"
_SEG_FONTE = {"prontidao": "índice composto do site sobre CAIDA Spoofer, IRR, RPKI e APNIC Labs", "rov": "APNIC Labs (iROV)", "dnssec": "APNIC Labs"}
_SEG_SELO = {"prontidao_pronto_pct": "inferido", "prontidao_indice": "inferido"}


def _ponto_roteamento(store, data: str) -> dict:
    r = _ler(store, data, "routing_analysis_resumo.json")
    if not isinstance(r, dict):
        return {"date": data, "valores": {}, "meta": {}}
    valores = {}
    for k, (_, _, f) in _ROT.items():
        try:
            valores[k] = f(r)
        except (KeyError, TypeError):
            valores[k] = None
    # `definicao` é o texto da regra de "rota brasileira" (P_BR): mudou a definição, mudou o método (D4)
    meta = {"base": "rotas brasileiras (P_BR) na tabela global", "metodo": _hash(r.get("definicao")), "cobertura": {"vrps": r.get("vrps")}}
    return {"date": data, "valores": valores, "meta": meta}


# ── segurança: prontidão (pronto, índice), ROV e DNSSEC ─────────────────────────────────────────────────────────────────────────────
_SEG = {
    "prontidao_pronto_pct": ("ASNs na classe pronto (índice de prontidão)", "%"),
    "prontidao_indice": ("Índice de prontidão, média ponderada por usuários", "índice"),
    "rov_media_ponderada_pct": ("ROV, média ponderada pelas amostras do APNIC", "%"),
    "rov_mediana_pct": ("ROV, mediana das redes", "%"),
    "dnssec_media_ponderada_pct": ("DNSSEC, média ponderada pelas amostras do APNIC", "%"),
}


def _ponto_seguranca(store, data: str) -> dict:
    pr = _ler(store, data, "prontidao/asns.json.gz")
    sg = _ler(store, data, "seguranca/asns.json.gz")
    valores: dict[str, Any] = {}
    metas: dict[str, dict] = {}
    if isinstance(pr, dict) and isinstance(pr.get("brasil"), dict):
        b, regras = pr["brasil"], pr.get("regras") or {}
        total = b.get("asns") or 0
        valores["prontidao_pronto_pct"] = round(100 * (b.get("classes") or {}).get("pronto", 0) / total, 2) if total else None
        valores["prontidao_indice"] = b.get("media_ponderada_usuarios")
        cob = {f"pilar_{k}": v for k, v in (b.get("cobertura_pilares") or {}).items()}
        fontes = pr.get("fontes") or {}
        metodo = f"regras {regras.get('hash')}"
        for k in ("prontidao_pronto_pct", "prontidao_indice"):
            metas[k] = {"base": "ASNs brasileiros com índice de prontidão", "metodo": metodo, "cobertura": cob,
                        "fontes": {"spoofer": (fontes.get("spoofer") or {}).get("janela"), "irr": (fontes.get("irr") or {}).get("serial")}}
    if isinstance(sg, dict) and isinstance(sg.get("brasil"), dict):
        b = sg["brasil"]
        for k, bloco, campo in (("rov_media_ponderada_pct", "rov", "media_ponderada_pct"), ("rov_mediana_pct", "rov", "mediana_pct"),
                                ("dnssec_media_ponderada_pct", "dnssec", "media_ponderada_pct")):
            m = b.get(bloco) or {}
            valores[k] = m.get(campo)
            as_of = ((sg.get("fontes") or {}).get(bloco) or {}).get("as_of")
            metas[k] = {"base": f"ASNs brasileiros medidos pelo APNIC ({bloco})", "metodo": "apnic-labs", "cobertura": {f"{bloco}_asns": m.get("asns")}, "as_of": as_of}
    return {"date": data, "valores": valores, "metas": metas}


_FAMILIA: dict[str, tuple[dict, Callable]] = {"roteamento": (_ROT, _ponto_roteamento), "seguranca": (_SEG, _ponto_seguranca)}


def _ponto(store, familia: str, data: str) -> dict:
    chave = (familia, data)
    if chave not in _PONTOS:
        if len(_PONTOS) > _LIMITE_CACHE:
            _PONTOS.clear()
        _PONTOS[chave] = _FAMILIA[familia][1](store, data)
    return _PONTOS[chave]


def _meta(p: dict, metrica: str) -> dict:
    return (p.get("metas") or {}).get(metrica) or p.get("meta") or {}


def _limpa(meta: dict) -> dict:
    """Só o que a regra usa e o leitor entende; as fontes por ponto não vão para a resposta."""
    return {k: v for k, v in meta.items() if k in ("base", "metodo", "cobertura", "as_of") and v not in (None, {})}


def serie(store, familia: str, de: Optional[str] = None, ate: Optional[str] = None, datas: Optional[list[str]] = None) -> dict:
    """Série nacional de uma família, de `de` a `ate`, com as métricas (IPv6 antes de IPv4 nos ids e na ordem), a anotação de comparabilidade e a regra."""
    if familia not in _FAMILIA:
        raise SerieErro(400, f"`familia` deve ser uma de {', '.join(FAMILIAS)}; recebido {familia!r}")
    for nome, v in (("from", de), ("to", ate)):
        if v is not None and not _DATA.match(v):
            raise SerieErro(400, f"`{nome}` deve ser uma data AAAA-MM-DD; recebido {v!r}")
    todas = datas if datas is not None else store.list_snapshots()
    recorte = [d for d in todas if (de is None or d >= de) and (ate is None or d <= ate)]
    if not recorte:
        raise SerieErro(404, "Nenhum snapshot no período pedido.")
    metricas, _ = _FAMILIA[familia]
    pontos = [_ponto(store, familia, d) for d in recorte]
    out_m = []
    for mid, info in metricas.items():
        rotulo, unidade = info[0], info[1]
        pp = unidade == "%"
        selo = "fato" if familia == "roteamento" else _SEG_SELO.get(mid, "estimado")
        fonte = _ROT_FONTE if familia == "roteamento" else _SEG_FONTE[mid.split("_")[0]]
        serie_m = [{"date": p["date"], "valor": (p["valores"] or {}).get(mid), "meta": _meta(p, mid)} for p in pontos]
        if all(x["valor"] is None for x in serie_m):
            continue
        a = comp.anotar_serie(serie_m, mid, unidade="pp" if pp else "absoluta")
        out_m.append({
            "id": mid, "rotulo": rotulo, "unidade": unidade, "selo": selo, "fonte": fonte, "desenhar_linha": a["desenhar_linha"], "segmentos": a["segmentos"],
            **({"variacao": _var_publica(a["variacao"])} if "variacao" in a else {}), **({"nota": a["nota"]} if "nota" in a else {}),
            "pontos": [{"date": p["date"], "valor": p["valor"], "comparavel_com_anterior": p["comparavel_com_anterior"], "motivos": p["motivos"],
                        "detalhes": p.get("detalhes", []), "avisos": p["avisos"], "meta": _limpa(p["meta"])} for p in a["pontos"]],
        })
    return {"familia": familia, "total": len(recorte), "snapshots": recorte, "metricas": out_m, "regra": comp.regra()}


def _var_publica(v: dict) -> dict:
    return {"de": v["de"], "para": v["para"], "calculada": v["calculada"], "absoluta": v.get("absoluta"), "unidade": v.get("unidade"),
            "motivos": [m["codigo"] for m in v["motivos"]]}
