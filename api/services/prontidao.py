# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Prontidão em segurança de roteamento: bloco do ASN, da UF e da operadora, resumo agregado e tabela do `/query`. Funções puras sobre `prontidao/asns.json.gz`.

O índice é um conjunto de medições e fatos de terceiros somados com pesos públicos (`regras`); a resposta sempre traz as regras, as fontes e os limites (política editorial). **A lista nominal de ASNs é
pública** (`lista_nominal_habilitada()`, decisão do mantenedor), com salvaguardas: pilar sem dado é "não medido" e fica fora do índice e da classe; a classe informa quantos pilares foram medidos; a ordem padrão é
por ASN, nunca do pior índice para o melhor; o aviso de método (`AVISO_METODO`) acompanha a lista. O índice de um ASN também aparece no perfil dele; da operadora e da UF, só o agregado do próprio recorte; o resumo
traz país, UFs e faixas de porte.
"""
from __future__ import annotations

import os
from typing import Optional

UFS = frozenset("AC AL AP AM BA CE DF ES GO MA MT MS MG PA PB PR PE PI RJ RN RS RO RR SC SP SE TO".split())


class ProntidaoErro(Exception):
    def __init__(self, status: int, mensagem: str):
        super().__init__(mensagem)
        self.status, self.mensagem = status, mensagem


def lista_nominal_habilitada() -> bool:
    """Lista/ordenação/filtro por ASN do índice. Ligada e pública por padrão (decisão do mantenedor, com as salvaguardas do módulo);
    `PRONTIDAO_LISTA_NOMINAL=0` a desliga e então a rota e a coleção `prontidao_asn` respondem 404."""
    return os.environ.get("PRONTIDAO_LISTA_NOMINAL", "1").strip().lower() in ("1", "true", "sim", "on")


AVISO_METODO = (
    "Índice de prontidão: soma ponderada de medições de terceiros (ROV e anti-spoofing do APNIC e do CAIDA Spoofer, objetos do IRR, PeeringDB, ROA e ASPA do RPKI) com regras públicas e versionadas, "
    "e não um veredito sobre a empresa. Pilar sem dado aparece como \"não medido\" e fica fora do índice e da classe; `pilares_medidos` diz em quantos dos quatro pilares o índice se apoia "
    "(o anti-spoofing só existe para cerca de 2% dos ASNs e o ROV depende de amostra mínima do APNIC). A ordem padrão é por ASN, sem relação com o índice. Cite a data do snapshot e a versão das regras."
)
PILARES = ("filtragem", "anti_spoofing", "coordenacao", "validacao_global")


def _meta(doc: dict) -> dict:
    return {"snapshot_date": doc["snapshot_date"], "natureza": doc["natureza"], "regras": doc["regras"], "fontes": doc["fontes"], "limites": doc["limites"]}


def bloco_asn(doc: Optional[dict], asn: int) -> Optional[dict]:
    """Bloco `prontidao` do perfil do ASN (`include=prontidao`); None se o produto não foi publicado ou o ASN não é do Brasil."""
    if not doc or str(asn) not in doc["asns"]:
        return None
    a = doc["asns"][str(asn)]
    return {**_meta(doc), "total": a["total"], "classe": a["classe"], "pilares": a["pilares"], "pilares_sem_dado": a["pilares_sem_dado"], "usuarios": a["usuarios"],
            "faixa_porte": a.get("faixa_porte"), "faixa_acessos_sici": a.get("faixa_acessos_sici"),
            "comparacao_uf": doc["por_uf"].get(a["uf"] or ""), "brasil": doc["brasil"]}


def bloco_uf(doc: Optional[dict], uf: str) -> Optional[dict]:
    if not doc or uf not in doc["por_uf"]:
        return None
    return {**_meta(doc), "uf": uf, "agregado": doc["por_uf"][uf], "brasil": doc["brasil"]}


def bloco_operadora(doc: Optional[dict], cnpj: str) -> Optional[dict]:
    """Agregado dos ASNs da operadora (raiz do CNPJ) no perfil dela; `None` se nenhum ASN do CNPJ está no índice."""
    if not doc or cnpj[:8] not in doc["por_operadora"]:
        return None
    return {**_meta(doc), "raiz": cnpj[:8], "agregado": doc["por_operadora"][cnpj[:8]], "brasil": doc["brasil"]}


def resumo(doc: dict, uf: Optional[str]) -> dict:
    if uf:
        u = uf.upper()
        if u not in UFS:
            raise ProntidaoErro(404, f"UF '{uf}' desconhecida.")
        return {**_meta(doc), "lista_nominal": lista_nominal_habilitada(), "escopo": {"uf": u}, "agregado": doc["por_uf"].get(u) or {"asns": 0}, "brasil": doc["brasil"]}
    return {**_meta(doc), "lista_nominal": lista_nominal_habilitada(), "escopo": {"pais": "BR"}, "agregado": doc["brasil"], "por_uf": doc["por_uf"], "por_faixa_porte": doc["por_faixa_porte"]}


def linhas(doc: Optional[dict]) -> list[dict]:
    """Uma linha por recorte agregado (coleção `prontidao_agregado` do `/query`): país, UFs e faixas de porte. Sem ASN nem operadora nominais."""
    if not doc:
        return []
    out = []
    for tipo, recorte in (("brasil", {"BR": doc["brasil"]}), ("uf", doc["por_uf"]), ("porte", doc["por_faixa_porte"])):
        for nome, a in recorte.items():
            out.append({"tipo": tipo, "recorte": nome, "asns": a["asns"], "asns_com_indice": a["asns_com_indice"], "media_ponderada_usuarios": a["media_ponderada_usuarios"], "mediana": a["mediana"],
                        "usuarios": a["usuarios"], **{f"classe_{c}": n for c, n in a["classes"].items()}, **{f"cobertura_{p}": n for p, n in a["cobertura_pilares"].items()},
                        **{f"{k}_{c}": m[k] for c, m in (a.get("medicoes") or {}).items() for k in ("asns", "media", "media_ponderada_usuarios")}})
    return out


CLASSES = ("pronto", "em_progresso", "atrasado", "sem_dados")
PORTES = ("sem_usuarios", "ate_1000", "de_1000_a_10000", "de_10000_a_100000", "de_100000_a_1000000", "acima_de_1000000")
ORDENACOES = {"indice": "total", "usuarios": "usuarios", "asn": "asn"}
ORDEM_PADRAO = "asn"


def linhas_asn(doc: Optional[dict], nomes: Optional[dict] = None) -> list[dict]:
    """Uma linha por ASN do Brasil (coleção `prontidao_asn` e rota `/prontidao/asns`), em ordem de ASN: índice, classe, nota de cada pilar (nulo = não medido), quantos pilares foram medidos, porte e UF.
    Só com `PRONTIDAO_LISTA_NOMINAL` ligada."""
    if not doc:
        return []
    nomes = nomes or {}
    out = []
    for n, a in sorted(doc["asns"].items(), key=lambda kv: int(kv[0])):
        pil = a.get("pilares") or {}
        out.append({"asn": int(n), "nome": nomes.get(n), "uf": a.get("uf"), "indice": a["total"], "classe": a["classe"], "pilares_medidos": len(pil), "pilares_total": len(PILARES), "usuarios": a["usuarios"],
                    "faixa_porte": a.get("faixa_porte"), "faixa_acessos_sici": a.get("faixa_acessos_sici"),
                    **{f"pilar_{k}": (pil.get(k) or {}).get("score") for k in ("filtragem", "anti_spoofing", "coordenacao", "validacao_global")},
                    "pilares_sem_dado": a.get("pilares_sem_dado") or []})
    return out


def lista_asns(doc: dict, nomes: Optional[dict], uf: Optional[str], classe: Optional[str], porte: Optional[str], minimo: Optional[float], maximo: Optional[float],
               ordem: str, desc: bool, pagina: int, limite: int) -> dict:
    """Lista paginada de ASNs, por padrão em ordem de ASN. `ordem=indice` e `usuarios` são escolha de quem consulta. Sem valor na chave de ordem (índice nulo) vai sempre ao fim."""
    if uf and uf.upper() not in UFS:
        raise ProntidaoErro(404, f"UF '{uf}' desconhecida.")
    if classe and classe not in CLASSES:
        raise ProntidaoErro(400, f"classe inválida; válidas: {', '.join(CLASSES)}")
    if porte and porte not in PORTES:
        raise ProntidaoErro(400, f"porte inválido; válidos: {', '.join(PORTES)}")
    if ordem not in ORDENACOES:
        raise ProntidaoErro(400, f"ordem inválida; válidas: {', '.join(ORDENACOES)}")
    rows = linhas_asn(doc, nomes)
    if uf:
        rows = [r for r in rows if r["uf"] == uf.upper()]
    if classe:
        rows = [r for r in rows if r["classe"] == classe]
    if porte:
        rows = [r for r in rows if r["faixa_porte"] == porte]
    if minimo is not None:
        rows = [r for r in rows if r["indice"] is not None and r["indice"] >= minimo]
    if maximo is not None:
        rows = [r for r in rows if r["indice"] is not None and r["indice"] <= maximo]
    chave = {"indice": "indice", "usuarios": "usuarios", "asn": "asn"}[ordem]
    com = [r for r in rows if r[chave] is not None]
    sem = [r for r in rows if r[chave] is None]
    com.sort(key=lambda r: (r[chave], r["asn"]), reverse=desc)
    rows = com + sem
    ini = (pagina - 1) * limite
    return {**_meta(doc), "aviso_metodo": AVISO_METODO, "ordem": ordem, "desc": desc,
            "filtros": {"uf": uf.upper() if uf else None, "classe": classe, "porte": porte, "min": minimo, "max": maximo}, "total": len(rows), "page": pagina, "limit": limite,
            "pages": (len(rows) + limite - 1) // limite if rows else 0, "items": rows[ini:ini + limite]}


def indice_por_asn(doc: Optional[dict]) -> dict[int, dict]:
    """{asn: {indice, classe}} para a coluna da lista de ASNs (`/asns?include=prontidao`)."""
    if not doc:
        return {}
    return {int(n): {"prontidao_indice": a["total"], "prontidao_classe": a["classe"], "prontidao_pilares_medidos": len(a.get("pilares") or {})} for n, a in doc["asns"].items()}
