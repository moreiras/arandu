# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Indicadores do SICI e outorgas sem declaração.

Saídas em `published/{date}/`:
  * `sici_indicadores.json.gz` — por operadora (CNPJ), UF e município: acessos, share, HHI, variação m/m e a/a, líder, ganho e perda,
    "em declínio contínuo" e "parou de declarar";
  * `sici_serie_municipio.json.gz` — série mensal (13 meses) de acessos, HHI e participação das 4 maiores operadoras por município;
  * `mercado_grupos.json.gz` — HHI por grupo ao lado do HHI por CNPJ (município e UF) e sobreposição de concorrentes por operadora;
  * `omissao_sici.json.gz` — outorgas SCM ativas sem acessos declarados no mês de referência, com a classe pelos usuários estimados
    (APNIC) dos ASNs do CNPJ, e o agregado por UF.

Tudo é descrição de dado declarado ou medido: "sem declaração no mês X; usuários APNIC estimados: Y". Nenhuma causa nem intenção.
As séries mensais por município vêm do cache normalizado do SICI (`normalized/sici_cache/months/`), que guarda todos os meses.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Optional

from core.common import now_iso, published_path
from core.jsonio import carregar_json_gz, gravar_json_gz
from core.nome_grupo import nome_do_grupo

FAIXAS_HHI = ((1500, "competitivo"), (2500, "moderado"))      # abaixo de 1.500 competitivo, até 2.500 moderado, acima concentrado (a mesma leitura que a interface já usa)
TOP_SOBREPOSICAO = 10        # concorrentes listados por operadora
MESES_SERIE = 13             # série de participação por município: o mês de referência e os 12 anteriores (compara com o ano anterior)
LIDERES_SERIE = 4            # só as maiores operadoras do mês de referência entram na série; o resto é "demais"
JANELA_DECLINIO = 6          # meses seguidos de queda para "em declínio contínuo"
JANELA_PAROU = 6             # meses sem declarar para "parou de declarar"
ANTIGUIDADE_MAX_PAROU = 36   # quem declarou pela última vez há mais que isso é inativo antigo: não entra
USUARIOS_MIN = 100           # abaixo disso a estimativa da APNIC é instável (mesmo limiar da divergência)


def somar_meses(mes: str, n: int) -> str:
    a, m = int(mes[:4]), int(mes[5:7])
    t = a * 12 + (m - 1) + n
    return f"{t // 12:04d}-{t % 12 + 1:02d}"


def _diff_meses(a: str, b: str) -> int:
    """Meses de `b` até `a` (a − b)."""
    return (int(a[:4]) - int(b[:4])) * 12 + int(a[5:7]) - int(b[5:7])


def _pct(novo: float, antigo: float) -> Optional[float]:
    return round(100 * (novo - antigo) / antigo, 2) if antigo else None


def _hhi_e_lider(acessos_por_cnpj: dict[str, int], nomes: dict[str, str]) -> dict:
    total = sum(acessos_por_cnpj.values())
    if not total:
        return {"acessos": 0, "n_operadoras": 0, "hhi": 0}
    lider = max(acessos_por_cnpj, key=lambda c: (acessos_por_cnpj[c], c))
    return {
        "acessos": total, "n_operadoras": len(acessos_por_cnpj),
        "hhi": round(sum((100 * a / total) ** 2 for a in acessos_por_cnpj.values())),
        "lider": {"cnpj": lider, "empresa": nomes.get(lider, ""), "share": round(100 * acessos_por_cnpj[lider] / total, 2)},
    }


def _por_municipio(mes_cnpjs: dict) -> tuple[dict[str, dict[str, int]], dict[str, tuple[str, str]]]:
    """{ibge: {cnpj: acessos}} e {ibge: (uf, nome)} de um mês do cache."""
    por: dict[str, dict[str, int]] = defaultdict(dict)
    info: dict[str, tuple[str, str]] = {}
    for cnpj, agg in mes_cnpjs.items():
        for ibge, m in (agg.get("por_municipio") or {}).items():
            if m.get("acessos"):
                por[ibge][cnpj] = por[ibge].get(cnpj, 0) + m["acessos"]
                info[ibge] = (m.get("uf", ""), m.get("nome", ""))
    return por, info


def _tendencia(serie: list, mes_ref: str) -> dict:
    """Da série [[mes, acessos, ...], ...] de um CNPJ: meses seguidos de queda até o último declarado e meses sem declarar."""
    if not serie:
        return {}
    pontos = sorted((p[0], p[1]) for p in serie)
    ultimo = pontos[-1][0]
    out: dict = {"ultimo_mes_declarado": ultimo, "meses_sem_declarar": max(0, _diff_meses(mes_ref, ultimo))}
    queda = 0
    for (m0, a0), (m1, a1) in zip(reversed(pontos[:-1]), reversed(pontos[1:])):
        if _diff_meses(m1, m0) == 1 and a1 < a0:
            queda += 1
        else:
            break
    out["meses_declinio"] = queda
    return out


def calcular_indicadores(mes_ref: str, meses: dict[str, dict], series: dict[str, list], nomes_extra: Optional[dict[str, str]] = None,
                         ufs_extra: Optional[dict[str, str]] = None) -> dict:
    """`meses`: {mes: cnpjs do cache} com `mes_ref`, o anterior e o de um ano antes (os dois últimos podem faltar).
    `series`: `serie_por_cnpj` do sici.json.gz. `nomes_extra`: razão social por CNPJ (cadastro SCM) para quem não está no mês.
    `ufs_extra`: UF da sede por CNPJ (cadastro SCM), gravada em `parou_de_declarar[].uf`."""
    atual = meses[mes_ref]
    ant, ano = meses.get(somar_meses(mes_ref, -1)), meses.get(somar_meses(mes_ref, -12))
    # nome de quem não declarou no mês (ganho e perda em 12 meses, MUN-E1): o do mês de um ano antes ou do anterior (como declarou ao
    # SICI) e, na falta, a razão social do cadastro SCM; nunca vazio quando alguma fonte tem o nome
    nomes = {c: a.get("empresa", "") for c, a in atual.items()}
    for m in (ano, ant):
        for c, a in (m or {}).items():
            if not nomes.get(c) and a.get("empresa"):
                nomes[c] = a["empresa"]
    for c, n in (nomes_extra or {}).items():
        if not nomes.get(c) and n:
            nomes[c] = n
    total_br = sum(a["acessos"] for a in atual.values()) or 1

    operadoras: dict[str, dict] = {}
    for cnpj, a in atual.items():
        reg = {
            "empresa": a.get("empresa", ""), "uf": a.get("uf", ""), "acessos": a["acessos"],
            "share_br": round(100 * a["acessos"] / total_br, 3),
            "ufs": {},
        }
        for m in (a.get("por_municipio") or {}).values():
            reg["ufs"][m.get("uf", "")] = reg["ufs"].get(m.get("uf", ""), 0) + m["acessos"]
        if ant is not None:
            reg["var_mm"] = {"abs": a["acessos"] - (ant.get(cnpj) or {}).get("acessos", 0), "pct": _pct(a["acessos"], (ant.get(cnpj) or {}).get("acessos", 0))}
        if ano is not None:
            reg["var_aa"] = {"abs": a["acessos"] - (ano.get(cnpj) or {}).get("acessos", 0), "pct": _pct(a["acessos"], (ano.get(cnpj) or {}).get("acessos", 0))}
        t = _tendencia(series.get(cnpj, []), mes_ref)
        reg["meses_declinio"] = t.get("meses_declinio", 0)
        reg["em_declinio"] = reg["meses_declinio"] >= JANELA_DECLINIO
        operadoras[cnpj] = reg
    for pos, cnpj in enumerate(sorted(operadoras, key=lambda c: (-operadoras[c]["acessos"], c)), 1):
        operadoras[cnpj]["posicao_br"] = pos

    parou: dict[str, dict] = {}
    for cnpj, serie in series.items():
        if cnpj in atual:
            continue
        t = _tendencia(serie, mes_ref)
        if JANELA_PAROU <= t.get("meses_sem_declarar", 0) <= ANTIGUIDADE_MAX_PAROU:
            ult = t["ultimo_mes_declarado"]
            ponto = next(p for p in serie if p[0] == ult)
            parou[cnpj] = {"empresa": (nomes_extra or {}).get(cnpj, ""), "ultimo_mes_declarado": ult, "meses_sem_declarar": t["meses_sem_declarar"], "acessos_no_ultimo_mes": ponto[1]}
            if ufs_extra is not None:                       # UF da sede no cadastro SCM: permite filtrar por UF (RANKINGS-E4)
                parou[cnpj]["uf"] = ufs_extra.get(cnpj, "")

    mun_a, info = _por_municipio(atual)
    mun_p, _ = _por_municipio(ant) if ant is not None else ({}, {})
    mun_y, _ = _por_municipio(ano) if ano is not None else ({}, {})
    municipios: dict[str, dict] = {}
    for ibge, ops in mun_a.items():
        e = {"uf": info[ibge][0], "nome": info[ibge][1], **_hhi_e_lider(ops, nomes)}
        if ant is not None:
            e["var_mm_pct"] = _pct(e["acessos"], sum(mun_p.get(ibge, {}).values()))
        if ano is not None:
            e["var_aa_pct"] = _pct(e["acessos"], sum(mun_y.get(ibge, {}).values()))
        base = mun_y.get(ibge) if ano is not None else None
        if base is not None:
            delta = {c: ops.get(c, 0) - base.get(c, 0) for c in set(ops) | set(base)}
            ganha = max(delta, key=lambda c: (delta[c], c))
            perde = min(delta, key=lambda c: (delta[c], c))
            if delta[ganha] > 0:
                e["ganho_aa"] = {"cnpj": ganha, "empresa": nomes.get(ganha, ""), "acessos": delta[ganha]}
            if delta[perde] < 0:
                e["perda_aa"] = {"cnpj": perde, "empresa": nomes.get(perde, ""), "acessos": delta[perde]}
        municipios[ibge] = e

    ufs: dict[str, dict] = {}
    por_uf: dict[str, dict[str, int]] = defaultdict(dict)
    for ibge, ops in mun_a.items():
        for c, ac in ops.items():
            u = info[ibge][0]
            por_uf[u][c] = por_uf[u].get(c, 0) + ac
    for u, ops in sorted(por_uf.items()):
        ufs[u] = _hhi_e_lider(ops, nomes)
        for chave, mm in (("var_mm_pct", mun_p), ("var_aa_pct", mun_y)):
            if (ant if chave == "var_mm_pct" else ano) is not None:
                antigo = sum(sum(v.values()) for i, v in mm.items() if info.get(i, ("",))[0] == u) if mm else 0
                ufs[u][chave] = _pct(ufs[u]["acessos"], antigo)

    brasil = _hhi_e_lider({c: a["acessos"] for c, a in atual.items()}, nomes)
    brasil.pop("lider", None)
    return {"operadoras": operadoras, "parou_de_declarar": parou, "ufs": ufs, "municipios": municipios, "brasil": brasil}


def classificar_omissao(usuarios: Optional[int], tem_asn: bool) -> str:
    if not tem_asn:
        return "nao_comparavel"
    return "com_usuarios_apnic" if (usuarios or 0) >= USUARIOS_MIN else "sem_usuarios"


def calcular_omissao(mes_ref: str, scms: list[dict], cnpjs_declarantes: set[str], usuarios_asn: dict[int, int],
                     grupos: Optional[list[dict]] = None) -> dict:
    """Outorgas SCM sem acessos declarados no mês de referência. Uma linha por CNPJ (um CNPJ pode ter várias outorgas).
    `grupos` (grupos_societarios): `grupo_declara` diz se OUTRO CNPJ do mesmo grupo declarou no mês, evidência para quem lê a linha."""
    grupo_de = {c: g for g in (grupos or []) for c in g.get("cnpjs", [])}
    por_cnpj: dict[str, dict] = {}
    for s in scms:
        cnpj = s.get("cnpj")
        if not cnpj or cnpj in cnpjs_declarantes:
            continue
        r = por_cnpj.setdefault(cnpj, {"razao_social": s.get("razao_social", ""), "uf": s.get("uf", ""), "n_outorgas": 0, "asns": s.get("asns") or [],
                                       "desde": None})
        r["n_outorgas"] += 1
        d = (s.get("data_outorga") or "")[-4:] + "-" + (s.get("data_outorga") or "")[3:5] if s.get("data_outorga") else None
        if d and (r["desde"] is None or d < r["desde"]):
            r["desde"] = d
    itens: dict[str, dict] = {}
    for cnpj, r in por_cnpj.items():
        usuarios = sum(usuarios_asn.get(a, 0) for a in r["asns"]) if r["asns"] else None
        itens[cnpj] = {**r, "usuarios_apnic": usuarios, "classe": classificar_omissao(usuarios, bool(r["asns"]))}
        g = grupo_de.get(cnpj)
        if g:
            itens[cnpj]["grupo_id"] = g.get("grupo_id")
            itens[cnpj]["grupo_declara"] = any(c in cnpjs_declarantes for c in g["cnpjs"] if c != cnpj)
    por_uf: dict[str, dict] = {}
    for r in itens.values():
        u = por_uf.setdefault(r["uf"] or "", {"cnpjs_sem_declaracao": 0, "com_usuarios_apnic": 0, "sem_usuarios": 0, "nao_comparavel": 0, "usuarios_apnic": 0})
        u["cnpjs_sem_declaracao"] += 1
        u[r["classe"]] += 1
        u["usuarios_apnic"] += r["usuarios_apnic"] or 0
    return {"mes_referencia": mes_ref, "itens": itens, "por_uf": dict(sorted(por_uf.items()))}


def serie_municipios(mes_ref: str, meses: list[str], leitor, nomes_extra: Optional[dict[str, str]] = None) -> dict:
    """Série mensal por município: acessos, HHI e a participação das `LIDERES_SERIE` maiores operadoras do mês de referência.

    `meses`: os meses da janela em ordem crescente (o último é `mes_ref`); `leitor(mes)` devolve os `cnpjs` do cache do mês ou `None` (mês ausente: ponto
    vazio, nunca zero). Um mês de cada vez na memória. Participação é sobre acessos declarados, não sobre receita."""
    por_mes: dict[str, dict[str, dict[str, int]]] = {}
    declarantes: dict[str, set[str]] = {}
    nomes: dict[str, str] = dict(nomes_extra or {})
    for m in meses:
        cn = leitor(m)
        if cn is None:
            continue
        por, _ = _por_municipio(cn)
        por_mes[m] = por
        declarantes[m] = set(cn)
        for c, a in cn.items():
            if a.get("empresa"):
                nomes[c] = a["empresa"]
    if mes_ref not in por_mes:
        return {}
    out: dict[str, dict] = {}
    for ibge, ops_ref in por_mes[mes_ref].items():
        lideres = sorted(ops_ref, key=lambda c: (-ops_ref[c], c))[:LIDERES_SERIE]
        acessos, hhi = [], []
        for m in meses:
            ops = (por_mes.get(m) or {}).get(ibge)
            tot = sum(ops.values()) if ops else 0
            acessos.append(tot if ops else None)
            hhi.append(round(sum((100 * a / tot) ** 2 for a in ops.values())) if tot else None)
        out[ibge] = {"acessos": acessos, "hhi": hhi, "lideres": [
            {"cnpj": c, "empresa": nomes.get(c, ""),
             # sem ponto (None) quando o CNPJ não declarou no mês, em nenhum município: zero só se declarou e não tinha acesso aqui (MUN-E2)
             "share": [round(100 * ops.get(c, 0) / sum(ops.values()), 2)
                       if c in declarantes.get(m, ()) and (ops := (por_mes.get(m) or {}).get(ibge)) and sum(ops.values()) else None
                       for m in meses]}
            for c in lideres]}
    return out


def faixa_hhi(hhi: Optional[int]) -> Optional[str]:
    if hhi is None:
        return None
    for limite, nome in FAIXAS_HHI:
        if hhi < limite:
            return nome
    return "concentrado"


def _hhi(acessos: dict[str, int]) -> Optional[int]:
    tot = sum(acessos.values())
    return round(sum((100 * a / tot) ** 2 for a in acessos.values())) if tot else None


def calcular_mercado_grupos(municipios: dict[str, dict], grupos: list[dict], curada: Optional[dict] = None) -> dict:
    """Cruzamentos de mercado sobre `sici_municipios` (acessos por município e CNPJ) e os grupos societários.

    * HHI por **grupo** ao lado do HHI por CNPJ, por município e UF: CNPJs do mesmo grupo (quadro societário em comum, inferência) contam como um só.
      Só entram `grupos[].cnpjs` e o `grupo_id`; nenhum dado de sócio é lido.
    * Sobreposição de concorrentes: por operadora, as que mais aparecem nos mesmos municípios (contagem de municípios e acessos delas ali).
    Tudo sobre acessos declarados, não sobre receita; o grupo é INFERIDO."""
    grupo_de = {c: g["grupo_id"] for g in grupos if g.get("classificacao") != "individual" for c in g.get("cnpjs", [])}
    nomes: dict[str, str] = {}
    por_mun: dict[str, dict[str, int]] = {}
    info: dict[str, tuple[str, str]] = {}
    for ibge, m in municipios.items():
        ops = {}
        for o in m.get("operadores", []):
            if o.get("acessos"):
                ops[o["cnpj"]] = ops.get(o["cnpj"], 0) + o["acessos"]
                nomes[o["cnpj"]] = o.get("empresa", "") or nomes.get(o["cnpj"], "")
        if ops:
            por_mun[ibge] = ops
            info[ibge] = (m.get("uf", ""), m.get("nome", ""))
    entidade = lambda c: grupo_de.get(c, c)  # noqa: E731

    cnpjs_do_grupo = {g["grupo_id"]: g.get("cnpjs", []) for g in grupos if g.get("classificacao") != "individual"}
    acessos_cnpj: dict[str, int] = defaultdict(int)
    for ops in por_mun.values():
        for c, a in ops.items():
            acessos_cnpj[c] += a

    def nome_grupo(e: str) -> dict:
        """Nome do grupo pela regra única (`core.nome_grupo`): marca curada, senão o CNPJ com mais acessos. Entidade que não é grupo é o próprio CNPJ."""
        membros = cnpjs_do_grupo.get(e)
        if not membros:
            return {"nome": nomes.get(e, "") or e, "nome_regra": None}
        r = nome_do_grupo(membros, acessos_cnpj, lambda c: nomes.get(c, ""), curada)
        return {"nome": r["nome"], "nome_regra": r["nome_regra"]}

    muns: dict[str, dict] = {}
    uf_cnpj: dict[str, dict[str, int]] = defaultdict(dict)
    uf_grupo: dict[str, dict[str, int]] = defaultdict(dict)
    transicoes: dict[str, int] = defaultdict(int)
    for ibge, ops in por_mun.items():
        gr: dict[str, int] = defaultdict(int)
        for c, a in ops.items():
            gr[entidade(c)] += a
            uf = info[ibge][0]
            uf_cnpj[uf][c] = uf_cnpj[uf].get(c, 0) + a
            uf_grupo[uf][entidade(c)] = uf_grupo[uf].get(entidade(c), 0) + a
        tot = sum(gr.values())
        h_c, h_g = _hhi(ops), _hhi(gr)
        lider = max(gr, key=lambda e: (gr[e], e))
        muns[ibge] = {"uf": info[ibge][0], "hhi_cnpj": h_c, "hhi_grupo": h_g, "n_cnpjs": len(ops), "n_grupos": len(gr), "faixa_cnpj": faixa_hhi(h_c), "faixa_grupo": faixa_hhi(h_g),
                      "lider_grupo": {"id": lider, **{("empresa" if k == "nome" else k): v for k, v in nome_grupo(lider).items()}, "share": round(100 * gr[lider] / tot, 2), "e_grupo": lider in set(grupo_de.values())}}
        if muns[ibge]["faixa_cnpj"] != muns[ibge]["faixa_grupo"]:
            transicoes[f"{muns[ibge]['faixa_cnpj']} → {muns[ibge]['faixa_grupo']}"] += 1
    ufs = {u: {"hhi_cnpj": _hhi(uf_cnpj[u]), "hhi_grupo": _hhi(uf_grupo[u]), "faixa_cnpj": faixa_hhi(_hhi(uf_cnpj[u])), "faixa_grupo": faixa_hhi(_hhi(uf_grupo[u]))} for u in sorted(uf_cnpj)}

    # sobreposição: um concorrente por vez, sem guardar todos os pares (memória O(operadoras))
    muns_de: dict[str, set[str]] = defaultdict(set)
    for ibge, ops in por_mun.items():
        for c in ops:
            muns_de[c].add(ibge)
    sobre: dict[str, list[dict]] = {}
    for a, mas in muns_de.items():
        cont: dict[str, list[int]] = {}
        for ibge in mas:
            for b, ab in por_mun[ibge].items():
                if b != a:
                    e = cont.setdefault(b, [0, 0, 0])
                    e[0] += 1
                    e[1] += ab
                    e[2] += por_mun[ibge][a]
        top = sorted(cont.items(), key=lambda kv: (-kv[1][0], -kv[1][1], kv[0]))[:TOP_SOBREPOSICAO]
        sobre[a] = [{"cnpj": b, "empresa": nomes.get(b, ""), "municipios_em_comum": v[0], "acessos_dele_nos_comuns": v[1], "acessos_dela_nos_comuns": v[2],
                     "mesmo_grupo": grupo_de.get(a) is not None and grupo_de.get(a) == grupo_de.get(b)} for b, v in top]
    mudam = sum(transicoes.values())
    return {"faixas": {"competitivo": f"HHI < {FAIXAS_HHI[0][0]}", "moderado": f"{FAIXAS_HHI[0][0]} a {FAIXAS_HHI[1][0] - 1}", "concentrado": f"HHI ≥ {FAIXAS_HHI[1][0]}"},
            "resumo": {"municipios": len(muns), "mudam_de_faixa": mudam, "transicoes": dict(sorted(transicoes.items())), "grupos_com_mais_de_um_cnpj_no_mercado": sum(1 for g in grupos if g.get("classificacao") != "individual" and sum(1 for c in g.get("cnpjs", []) if c in nomes) > 1)},
            "municipios": muns, "ufs": ufs, "sobreposicao": sobre}


def publicar_sici_indicadores(base: Path, date_str: str, log) -> dict:
    pub = published_path(base, date_str)
    sici = carregar_json_gz(pub / "sici.json.gz")
    scm = carregar_json_gz(pub / "scm.json.gz")
    if not sici or not scm:
        log.info("sici.json.gz ou scm.json.gz ausente: indicadores do SICI não gerados")
        return {}
    mes_ref = sici["mes_referencia"]
    cache = base / "normalized" / "sici_cache" / "months"
    meses: dict[str, dict] = {}
    for m in (mes_ref, somar_meses(mes_ref, -1), somar_meses(mes_ref, -12)):
        d = carregar_json_gz(cache / f"{m}.json.gz")
        if d:
            meses[m] = d["cnpjs"]
    if mes_ref not in meses:
        log.warning("mês de referência %s fora do cache do SICI: indicadores não gerados", mes_ref)
        return {}
    nomes_scm = {s["cnpj"]: s.get("razao_social", "") for s in scm.get("scms", []) if s.get("cnpj")}
    ufs_scm: dict[str, str] = {}
    for s in scm.get("scms", []):
        if s.get("cnpj") and s.get("uf") and not ufs_scm.get(s["cnpj"]):
            ufs_scm[s["cnpj"]] = s["uf"]
    ind = calcular_indicadores(mes_ref, meses, sici.get("serie_por_cnpj", {}), nomes_scm, ufs_scm)
    meta = {
        "snapshot_date": date_str, "generated_at": now_iso(), "mes_referencia": mes_ref,
        "mes_anterior": somar_meses(mes_ref, -1) if somar_meses(mes_ref, -1) in meses else None,
        "mes_ano_anterior": somar_meses(mes_ref, -12) if somar_meses(mes_ref, -12) in meses else None,
        "fonte": "Anatel/SICI (acessos declarados); HHI sobre acessos, não sobre receita",
        "parametros": {"janela_declinio_meses": JANELA_DECLINIO, "janela_parou_meses": JANELA_PAROU, "antiguidade_max_parou_meses": ANTIGUIDADE_MAX_PAROU},
    }
    gravar_json_gz(pub / "sici_indicadores.json.gz", {**meta, **ind})

    janela = [somar_meses(mes_ref, -k) for k in range(MESES_SERIE - 1, -1, -1)]
    serie = serie_municipios(mes_ref, janela, lambda m: (carregar_json_gz(cache / f"{m}.json.gz") or {}).get("cnpjs"), nomes_scm)
    if serie:
        gravar_json_gz(pub / "sici_serie_municipio.json.gz", {
            "snapshot_date": date_str, "generated_at": meta["generated_at"], "mes_referencia": mes_ref, "meses": janela,
            "fonte": "Anatel/SICI (acessos declarados); participação e HHI sobre acessos, não sobre receita",
            "parametros": {"meses": MESES_SERIE, "lideres": LIDERES_SERIE}, "municipios": serie})

    munis = (carregar_json_gz(pub / "sici_municipios.json.gz") or {}).get("municipios")
    grupos_doc = carregar_json_gz(pub / "grupos_societarios.json.gz")
    if munis and grupos_doc:
        try:
            from core.marcas import carregar_curada
            curada = carregar_curada()
        except Exception:
            curada = None            # sem a tabela curada o nome cai no CNPJ com mais acessos
        mg = calcular_mercado_grupos(munis, grupos_doc.get("grupos", []), curada)
        gravar_json_gz(pub / "mercado_grupos.json.gz", {
            "snapshot_date": date_str, "generated_at": meta["generated_at"], "mes_referencia": mes_ref, "natureza": "inferido",
            "fonte": "Anatel/SICI (acessos declarados) × grupos societários (quadro societário da Receita, inferência); HHI sobre acessos, não sobre receita",
            "limites": "O grupo é uma inferência a partir do quadro societário em comum e pode juntar empresas independentes ou separar empresas do mesmo controle; sobreposição de concorrentes é presença nos mesmos municípios, não rivalidade.",
            **mg})

    ip = pub / "asns" / "index.json"
    usuarios = {}
    if ip.exists():
        usuarios = {a["asn"]: a["apnic_users"] for a in json.loads(ip.read_text(encoding="utf-8")) if a.get("is_br") and a.get("apnic_users")}
    grupos = (carregar_json_gz(pub / "grupos_societarios.json.gz") or {}).get("grupos", [])
    om = calcular_omissao(mes_ref, scm.get("scms", []), set(ind["operadoras"]), usuarios, grupos)
    gravar_json_gz(pub / "omissao_sici.json.gz", {
        "snapshot_date": date_str, "generated_at": meta["generated_at"], "fonte": "Anatel (outorgas SCM) × SICI × APNIC (usuários estimados)",
        "parametros": {"usuarios_min": USUARIOS_MIN}, **om})
    return {"operadoras": len(ind["operadoras"]), "municipios": len(ind["municipios"]), "omissao": len(om["itens"])}
