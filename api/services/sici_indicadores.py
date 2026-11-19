# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Rankings e omissão de declaração do SICI. Funções puras sobre os dois artefatos publicados.

Política editorial: os rankings são de dado declarado ou medido e mostram critério, valores e data, sem juízo; toda resposta
traz `criterio`, `mes_referencia` e o link da metodologia. A omissão é descrita como fato ("sem declaração no mês X; usuários estimados Y").
"""
from __future__ import annotations

from typing import Optional

METODOLOGIA = "/fontes"          # a página Fontes lista o produto; o texto de leitura está na página Rankings

ORDENS_OPERADORA = {
    "acessos": ("Acessos declarados", lambda r: r["acessos"]),
    "share": ("Parcela dos acessos declarados", lambda r: r["share"]),
    "var_aa_pct": ("Variação percentual em 12 meses", lambda r: r.get("var_aa_pct")),
    "var_aa_abs": ("Variação absoluta em 12 meses", lambda r: r.get("var_aa_abs")),
    "var_mm_pct": ("Variação percentual no mês", lambda r: r.get("var_mm_pct")),
    "declinio": ("Meses seguidos de queda", lambda r: r["meses_declinio"]),
}
ORDENS_MUNICIPIO = {
    "acessos": ("Acessos declarados", lambda r: r["acessos"]),
    "hhi": ("Concentração (HHI) sobre acessos declarados", lambda r: r["hhi"]),
    "n_operadoras": ("Número de operadoras declarantes", lambda r: r["n_operadoras"]),
    "var_aa_pct": ("Variação percentual em 12 meses", lambda r: r.get("var_aa_pct")),
}
CLASSES = ("com_usuarios_apnic", "sem_usuarios", "nao_comparavel")


class IndicadoresErro(Exception):
    def __init__(self, status: int, mensagem: str):
        super().__init__(mensagem)
        self.status, self.mensagem = status, mensagem


def _ordenar(linhas: list[dict], chave, asc: bool) -> list[dict]:
    com = [r for r in linhas if chave(r) is not None]
    com.sort(key=lambda r: (chave(r), r.get("cnpj") or r.get("ibge") or ""), reverse=not asc)
    return com


def _meta(ind: dict) -> dict:
    return {"snapshot_date": ind["snapshot_date"], "mes_referencia": ind["mes_referencia"], "fonte": ind["fonte"], "metodologia": METODOLOGIA}


def _paginar(linhas: list[dict], limit: int, offset: int) -> list[dict]:
    return [{"posicao": offset + i + 1, **r} for i, r in enumerate(linhas[offset:offset + limit])]


def ranking_operadoras(ind: dict, uf: Optional[str], ordem: str, asc: bool, limit: int, offset: int) -> dict:
    if ordem not in ORDENS_OPERADORA:
        raise IndicadoresErro(400, f"ordem inválida: {ordem}. Use: {', '.join(ORDENS_OPERADORA)}")
    uf = uf.upper() if uf else None
    if uf and uf not in ind["ufs"]:
        raise IndicadoresErro(404, f"UF {uf} sem acessos declarados.")
    total_uf = ind["ufs"][uf]["acessos"] if uf else None
    linhas = []
    for cnpj, o in ind["operadoras"].items():
        if uf:
            ac = o["ufs"].get(uf)
            if not ac:
                continue
        else:
            ac = o["acessos"]
        r = {"cnpj": cnpj, "empresa": o["empresa"], "uf_sede": o["uf"], "acessos": ac,
             "share": round(100 * ac / total_uf, 3) if uf else o["share_br"],
             "meses_declinio": o["meses_declinio"], "em_declinio": o["em_declinio"]}
        if not uf:                                         # a variação é da operadora no país: não se divide por UF
            for k in ("var_mm", "var_aa"):
                if k in o:
                    r[f"{k}_abs"], r[f"{k}_pct"] = o[k]["abs"], o[k]["pct"]
        linhas.append(r)
    rotulo, chave = ORDENS_OPERADORA[ordem]
    if uf and ordem != "acessos" and ordem != "share" and ordem != "declinio":
        raise IndicadoresErro(400, "dentro de uma UF só se ordena por acessos, share ou declinio (a variação é da operadora no país).")
    linhas = _ordenar(linhas, chave, asc)
    return {**_meta(ind), "escopo": {"uf": uf} if uf else {"pais": "BR"}, "criterio": rotulo + (" (crescente)" if asc else " (decrescente)"),
            "total": len(linhas), "items": _paginar(linhas, limit, offset)}


def ranking_municipios(ind: dict, uf: Optional[str], ordem: str, asc: bool, limit: int, offset: int) -> dict:
    if ordem not in ORDENS_MUNICIPIO:
        raise IndicadoresErro(400, f"ordem inválida: {ordem}. Use: {', '.join(ORDENS_MUNICIPIO)}")
    uf = uf.upper() if uf else None
    linhas = [{"ibge": i, **m} for i, m in ind["municipios"].items() if not uf or m["uf"] == uf]
    if uf and not linhas:
        raise IndicadoresErro(404, f"UF {uf} sem acessos declarados.")
    rotulo, chave = ORDENS_MUNICIPIO[ordem]
    linhas = _ordenar(linhas, chave, asc)
    return {**_meta(ind), "escopo": {"uf": uf} if uf else {"pais": "BR"}, "criterio": rotulo + (" (crescente)" if asc else " (decrescente)"),
            "total": len(linhas), "items": _paginar(linhas, limit, offset)}


def omissao(om: dict, ind: dict, tipo: str, uf: Optional[str], classe: Optional[str], grupo_declara: Optional[bool], limit: int, offset: int) -> dict:
    uf = uf.upper() if uf else None
    meta = {"snapshot_date": om["snapshot_date"], "mes_referencia": om["mes_referencia"], "fonte": om["fonte"], "metodologia": METODOLOGIA,
            "parametros": om["parametros"]}
    if tipo == "parou_de_declarar":
        linhas = [{"cnpj": c, **v} for c, v in ind["parou_de_declarar"].items()]
        linhas.sort(key=lambda r: (-r["acessos_no_ultimo_mes"], r["cnpj"]))
        return {**meta, "tipo": tipo, "criterio": "Acessos no último mês declarado (decrescente)", "total": len(linhas), "items": _paginar(linhas, limit, offset)}
    if tipo != "outorga_sem_declaracao":
        raise IndicadoresErro(400, "tipo inválido. Use: outorga_sem_declaracao | parou_de_declarar")
    if classe and classe not in CLASSES:
        raise IndicadoresErro(400, f"classe inválida: {classe}. Use: {', '.join(CLASSES)}")
    linhas = [{"cnpj": c, **v} for c, v in om["itens"].items()
              if (not uf or v["uf"] == uf) and (not classe or v["classe"] == classe)
              and (grupo_declara is None or bool(v.get("grupo_declara")) is grupo_declara)]
    linhas.sort(key=lambda r: (-(r["usuarios_apnic"] or 0), r["cnpj"]))
    por_uf = om["por_uf"] if not uf else {uf: om["por_uf"].get(uf, {})}
    return {**meta, "tipo": tipo, "escopo": {"uf": uf} if uf else {"pais": "BR"},
            "criterio": "Usuários estimados (APNIC) dos ASNs do CNPJ (decrescente)", "total": len(linhas), "por_uf": por_uf,
            "items": _paginar(linhas, limit, offset)}


def bloco_operadora(ind: Optional[dict], om: Optional[dict], cnpj: str) -> Optional[dict]:
    """Bloco `indicadores` do perfil da operadora: indicadores do mês e, se houver, o fato da ausência de declaração."""
    if not ind:
        return None
    out: dict = {"mes_referencia": ind["mes_referencia"], "metodologia": METODOLOGIA}
    if cnpj in ind["operadoras"]:
        out.update({k: v for k, v in ind["operadoras"][cnpj].items() if k != "ufs"})
    elif cnpj in ind["parou_de_declarar"]:
        out["parou_de_declarar"] = ind["parou_de_declarar"][cnpj]
    if om and cnpj in om["itens"]:
        out["sem_declaracao"] = om["itens"][cnpj]
    return out if len(out) > 2 else None


def bloco_municipio(ind: Optional[dict], ibge: str) -> Optional[dict]:
    if not ind or ibge not in ind["municipios"]:
        return None
    return {"mes_referencia": ind["mes_referencia"], "metodologia": METODOLOGIA, **ind["municipios"][ibge]}


def bloco_uf(ind: Optional[dict], om: Optional[dict], uf: str) -> Optional[dict]:
    if not ind or uf not in ind["ufs"]:
        return None
    out = {"mes_referencia": ind["mes_referencia"], "metodologia": METODOLOGIA, **ind["ufs"][uf]}
    if om:
        out["sem_declaracao"] = om["por_uf"].get(uf) or {"cnpjs_sem_declaracao": 0, "com_usuarios_apnic": 0, "sem_usuarios": 0, "nao_comparavel": 0, "usuarios_apnic": 0}
    return out


def _meta_mg(doc: dict) -> dict:
    return {"snapshot_date": doc["snapshot_date"], "mes_referencia": doc["mes_referencia"], "natureza": doc["natureza"], "fonte": doc["fonte"], "limites": doc["limites"], "faixas": doc["faixas"]}


def bloco_mercado_municipio(doc: Optional[dict], ibge: str) -> Optional[dict]:
    """HHI por CNPJ e por grupo do município; `None` sem o artefato ou sem o município."""
    if not doc or ibge not in doc["municipios"]:
        return None
    return {**_meta_mg(doc), **doc["municipios"][ibge]}


def bloco_mercado_uf(doc: Optional[dict], uf: str) -> Optional[dict]:
    """HHI por CNPJ e por grupo da UF e quantos de seus municípios mudam de faixa ao juntar os CNPJs do grupo."""
    if not doc or uf not in doc["ufs"]:
        return None
    muns = [m for m in doc["municipios"].values() if m["uf"] == uf]
    mudam = [m for m in muns if m["faixa_cnpj"] != m["faixa_grupo"]]
    return {**_meta_mg(doc), **doc["ufs"][uf], "municipios": len(muns), "municipios_mudam_de_faixa": len(mudam)}


def bloco_sobreposicao_operadora(doc: Optional[dict], cnpj: str) -> Optional[dict]:
    """As operadoras que mais aparecem nos mesmos municípios que a operadora; presença conjunta, não rivalidade."""
    if not doc or cnpj not in doc["sobreposicao"]:
        return None
    return {**_meta_mg(doc), "concorrentes": doc["sobreposicao"][cnpj]}


def resumo_mercado_grupos(doc: dict) -> dict:
    """O que o Panorama de mercado mostra: faixas, quantos municípios mudam de faixa e o HHI por UF (sem a lista de municípios)."""
    return {**_meta_mg(doc), "resumo": doc["resumo"], "ufs": doc["ufs"]}


def bloco_serie_municipio(doc: Optional[dict], ibge: str) -> Optional[dict]:
    """Série mensal do município: acessos, HHI e a participação das maiores operadoras; `None` se o município não tem série."""
    if not doc or ibge not in doc.get("municipios", {}):
        return None
    return {"snapshot_date": doc["snapshot_date"], "mes_referencia": doc["mes_referencia"], "meses": doc["meses"], "fonte": doc["fonte"], "parametros": doc["parametros"], **doc["municipios"][ibge]}


def maiores(dados: dict, grupos: list[dict], n_ops: int = 8, meses: int = 24, n_unidades: int = 20) -> dict:
    """Os maiores do mercado fixo: a **posição mês a mês** das `n_ops` maiores operadoras de hoje (bump chart) e as `n_unidades` maiores
    empresas-ou-grupos pelo acesso declarado (treemap). A posição é entre TODOS os CNPJs que declararam no mês, não só entre as exibidas. A unidade do
    treemap é o grupo econômico (inferido do quadro societário) quando o CNPJ pertence a um com mais de um CNPJ, senão o próprio CNPJ."""
    series = dados.get("serie_por_cnpj", {})
    cadastro = dados.get("cnpjs", {})
    todos = sorted({l[0] for v in series.values() for l in v})
    janela = todos[-meses:]
    por_mes = {m: {} for m in janela}
    for cnpj, linhas in series.items():
        for mes, acessos, *_ in linhas:
            if mes in por_mes and acessos:
                por_mes[mes][cnpj] = acessos
    ultimo = janela[-1] if janela else None
    maiores_hoje = sorted(por_mes.get(ultimo, {}), key=lambda c: -por_mes[ultimo][c])[:n_ops] if ultimo else []
    ranks = {}
    for m in janela:
        ordem = sorted(por_mes[m], key=lambda c: (-por_mes[m][c], c))
        ranks[m] = {c: i + 1 for i, c in enumerate(ordem)}
    operadoras = [{"cnpj": c, "empresa": (cadastro.get(c) or {}).get("empresa") or c,
                   "posicao": [ranks[m].get(c) for m in janela], "acessos": [por_mes[m].get(c) for m in janela]} for c in maiores_hoje]
    grupo_de, nome_de = {}, {}
    for g in grupos:
        if g.get("tamanho", len(g.get("cnpjs", []))) >= 2:
            maior = max(g["cnpjs"], key=lambda x: (cadastro.get(x["cnpj"]) or {}).get("acessos", 0), default=None)
            nome_de[g["grupo_id"]] = (cadastro.get((maior or {}).get("cnpj")) or {}).get("empresa") or (maior or {}).get("empresa") or g["grupo_id"]
            for x in g["cnpjs"]:
                grupo_de[x["cnpj"]] = g["grupo_id"]
    unidades: dict[str, dict] = {}
    total = 0
    for cnpj, v in cadastro.items():
        ac = v.get("acessos") or 0
        if not ac:
            continue
        total += ac
        chave = grupo_de.get(cnpj, cnpj)
        u = unidades.setdefault(chave, {"id": chave, "grupo": chave in nome_de, "nome": nome_de.get(chave) or v.get("empresa") or cnpj, "acessos": 0, "cnpjs": 0})
        u["acessos"] += ac
        u["cnpjs"] += 1
    top = sorted(unidades.values(), key=lambda u: -u["acessos"])[:n_unidades]
    soma = sum(u["acessos"] for u in top)
    for u in top:
        u["share"] = round(100 * u["acessos"] / total, 2) if total else None
    return {"mes_referencia": ultimo, "meses": janela, "operadoras": operadoras,
            "unidades": top, "demais": {"acessos": total - soma, "share": round(100 * (total - soma) / total, 2) if total else None, "unidades": len(unidades) - len(top)},
            "total_acessos": total,
            "natureza": "fato (acessos declarados ao SICI) com agrupamento inferido",
            "aviso": "Posição por acessos declarados do mês, entre todos os CNPJs que declararam; não mede receita nem qualidade. O grupo econômico é inferido do quadro societário (Receita Federal) e pode juntar CNPJs que operam separados."}
