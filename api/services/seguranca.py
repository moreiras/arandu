# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Segurança de roteamento por ASN, parte A: bloco do ASN, resumo agregado e tabela do `/query`. Funções puras sobre `seguranca/asns.json.gz`.

ROV e DNSSEC são medições do APNIC por amostragem (não declarações da rede); o AS Rank é inferência do CAIDA; bogon é fato verificável contra as listas citadas.
Toda resposta traz as fontes com a data e as limitações (política editorial). Sem lista de reputação.
"""
from __future__ import annotations

from typing import Optional

UFS = frozenset("AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split())


class SegurancaErro(Exception):
    def __init__(self, status: int, mensagem: str):
        super().__init__(mensagem)
        self.status, self.mensagem = status, mensagem


def _meta(doc: dict) -> dict:
    return {"snapshot_date": doc["snapshot_date"], "fontes": doc["fontes"], "parametros": doc["parametros"], "limites": doc["limites"]}


def bloco_asn(doc: Optional[dict], asn: int) -> Optional[dict]:
    """Bloco `seguranca` do perfil do ASN (`include=seguranca`); None se o produto não foi publicado ou o ASN não tem nenhum sinal."""
    if not doc or str(asn) not in doc["asns"]:
        return None
    s = {k: v for k, v in doc["asns"][str(asn)].items() if k not in ("uf", "faixa_porte", "faixa_acessos_sici")}
    return {**_meta(doc), **s}


def resumo(doc: dict, uf: Optional[str]) -> dict:
    if uf:
        u = uf.upper()
        if u not in UFS:
            raise SegurancaErro(404, f"UF '{uf}' desconhecida.")
        return {**_meta(doc), "escopo": {"uf": u}, "agregado": doc["por_uf"].get(u) or {"asns": 0}, "brasil": doc["brasil"]}
    return {**_meta(doc), "escopo": {"pais": "BR"}, "agregado": doc["brasil"], "por_uf": doc["por_uf"], "por_faixa_porte": doc["por_faixa_porte"]}


def linhas(doc: Optional[dict]) -> list[dict]:
    """Uma linha por ASN (coleção `seguranca_asn` do `/query`), achatando os sinais."""
    if not doc:
        return []
    out = []
    for a, s in doc["asns"].items():
        ln: dict = {"asn": int(a), "uf": s.get("uf"), "faixa_porte": s.get("faixa_porte"), "faixa_acessos_sici": s.get("faixa_acessos_sici")}
        if "rov" in s:
            ln["rov_validates_pct"], ln["rov_amostras"] = s["rov"]["validates_pct"], s["rov"]["amostras"]
        if "dnssec" in s:
            ln["dnssec_validates_pct"], ln["dnssec_parcial_pct"], ln["dnssec_amostras"] = s["dnssec"]["validates_pct"], s["dnssec"]["parcial_pct"], s["dnssec"]["amostras"]
        if "asrank" in s:
            r = s["asrank"]
            ln.update({"asrank_rank": r.get("rank"), "cone_asns": (r.get("cone") or {}).get("asns"),
                       "cone_prefixos": (r.get("cone") or {}).get("prefixos"), "grau_cliente": (r.get("grau") or {}).get("cliente"),
                       "grau_par": (r.get("grau") or {}).get("par"), "grau_provedor": (r.get("grau") or {}).get("provedor")})
        ln["n_prefixos_bogon"] = s.get("n_prefixos_bogon", 0)
        if "asn_reservado" in s:
            ln["asn_reservado"] = s["asn_reservado"]
        out.append({k: v for k, v in ln.items() if v is not None})
    out.sort(key=lambda x: x["asn"])
    return out
