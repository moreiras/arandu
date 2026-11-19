# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Contratos públicos de operadoras. Saída: `published/{date}/contratos/operadoras.json.gz`, `municipios.json.gz` e `resumo.json.gz`.

Entrada: `normalized/{date}/summary/siasg_contratos.json.gz` (resultados de itens da Lei 14.133 do PNCP, por raiz de CNPJ, em rodízio) e, só para o nome da empresa, `receita_cnpj.json.gz`
(que já não traz razão social de empresário individual).

Por raiz de CNPJ: itens e contratações (valor homologado, sem os itens cancelados, que são contados à parte), órgãos, UF, ano, esfera, modalidade e objeto resumido. Linguagem de evidência:
"resultado de item publicado no PNCP, consultado em <data>". Não é contrato assinado nem pagamento; sem adjetivo e sem ranking de fornecedor no resumo nacional. Ausência não é zero: a raiz
sem leitura não aparece, a lida sem resultado diz isso com a data, e esfera e município só existem para o que foi enriquecido (cobertura declarada).

Município = o do órgão comprador (detalhe da contratação; na falta, a unidade de compra da tabela UASG), não o local de entrega do serviço.
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from datetime import date as _date
from pathlib import Path
from typing import Optional

from core import siasg
from core.common import configure_logging, data_dir, normalized_path, now_iso, published_path, today_str
from core.jsonio import carregar_json_gz, gravar_json_gz

TOP_ORGAOS = 10
RECENTES = 20
TOP_FORNECEDORES_MUNICIPIO = 20
AVISO = ("Cada linha é um resultado de item de contratação publicado no PNCP (Lei 14.133) e espelhado no Compras.gov.br, consultado na data indicada para o CNPJ de matriz da empresa; não é, por si, "
         "contrato assinado nem pagamento. O valor é o homologado no resultado do item, sem correção. Itens cancelados ficam fora dos valores e são contados à parte.")
LIMITES = ("Só a Lei 14.133 (o legado do SIASG anterior a 2021 não entra); só o CNPJ de matriz da raiz (contrato em nome de filial não aparece); só órgão que publica no PNCP. A coleta é um rodízio de dias: "
           "cada raiz tem a data da sua leitura (faixa A, que declara acessos no SICI, até ~7 dias; faixa B até ~56) e raiz ainda não lida não tem número, o que não quer dizer zero. Esfera, município do órgão e objeto "
           "só existem para as contratações já detalhadas (`cobertura.contratacoes_com_detalhe`); o município é o do órgão comprador, não o do local de entrega. A esfera é a informada no PNCP e pode estar inconsistente.")


def _r2(v: float) -> float:
    return round(v, 2)


def _idade(lida_em: Optional[str], hoje: str) -> Optional[int]:
    return (_date.fromisoformat(hoje) - _date.fromisoformat(lida_em[:10])).days if lida_em else None


def _contratacoes(itens: list[dict], compras: dict[str, dict], uasg: dict[str, dict]) -> dict[str, dict]:
    """Itens não cancelados agrupados por contratação, com órgão, esfera, município e objeto quando o detalhe existe."""
    por: dict[str, dict] = {}
    for it in itens:
        c = por.setdefault(it.get("compra") or f"?{it['id']}", {"itens": 0, "valor": 0.0, "data": it.get("data"), "un": it.get("un"), "uf": it.get("uf"), "org": it.get("org")})
        c["itens"] += 1
        c["valor"] += it.get("valor") or 0.0
        if it.get("data") and (not c["data"] or it["data"] > c["data"]):
            c["data"] = it["data"]
    for numero, c in por.items():
        d = compras.get(numero) or {}
        u = uasg.get(c["un"] or "") or {}
        c.update({"detalhada": bool(d), "orgao": d.get("orgao"), "esfera": d.get("esfera"), "modalidade": d.get("modalidade"), "objeto": d.get("objeto"), "uf": c["uf"] or d.get("uf") or u.get("uf"),
                  "ibge": d.get("ibge") or u.get("ibge"), "municipio": d.get("municipio") or u.get("municipio"), "unidade": u.get("nome")})
    return por


def _soma(grupos: dict, chave) -> list[dict]:
    return [{**{"chave": k}, "itens": v["itens"], "contratacoes": v["contratacoes"], "valor": _r2(v["valor"])} for k, v in sorted(grupos.items(), key=chave)]


def operadora(raiz: str, reg: dict, faixa: Optional[str], compras: dict, uasg: dict, nome: Optional[str], hoje: str) -> tuple[dict, dict]:
    """(documento da raiz, contratações não canceladas com o detalhe resolvido)."""
    itens = reg.get("itens") or []
    base = {"raiz": raiz, "nome": nome, "cnpj_consultado": reg.get("cnpj"), "faixa": faixa, "lida_em": reg.get("lida_em"), "idade_dias": _idade(reg.get("lida_em"), hoje), "desde": reg.get("desde"),
            "incompleto": bool(reg.get("incompleto"))}
    if not itens:
        return {**base, "resultado": "sem_resultado_na_consulta", "itens": 0, "contratacoes": 0}, {}
    validos = [i for i in itens if i.get("sit") != siasg.CANCELADO]
    por = _contratacoes(validos, compras, uasg)
    ano, uf, esfera = (defaultdict(lambda: {"itens": 0, "contratacoes": 0, "valor": 0.0}) for _ in range(3))
    orgaos: dict[str, dict] = {}
    for numero, c in por.items():
        for grupo, k in ((ano, (c["data"] or "s/d")[:4]), (uf, c["uf"] or "s/d"), (esfera, c["esfera"] or "nao_detalhada")):
            grupo[k]["itens"] += c["itens"]
            grupo[k]["contratacoes"] += 1
            grupo[k]["valor"] += c["valor"]
        o = orgaos.setdefault(c["org"] or "s/d", {"org": c["org"], "orgao": None, "esfera": None, "uf": c["uf"], "itens": 0, "contratacoes": 0, "valor": 0.0})
        o["orgao"], o["esfera"] = o["orgao"] or c["orgao"], o["esfera"] or c["esfera"]
        o["itens"] += c["itens"]
        o["contratacoes"] += 1
        o["valor"] += c["valor"]
    datas = [i["data"] for i in validos if i.get("data")]
    recentes = sorted(por.items(), key=lambda kv: (kv[1]["data"] or "", kv[0]), reverse=True)[:RECENTES]
    return {**base, "resultado": "com_resultado", "itens": len(validos), "itens_cancelados": len(itens) - len(validos), "contratacoes": len(por), "orgaos": len(orgaos),
            "valor_homologado": _r2(sum(c["valor"] for c in por.values())), "primeiro_resultado": min(datas, default=None), "ultimo_resultado": max(datas, default=None),
            "contratacoes_detalhadas": sum(1 for c in por.values() if c["detalhada"]),
            "por_ano": [{"ano": x["chave"], **{k: x[k] for k in ("itens", "contratacoes", "valor")}} for x in _soma(ano, lambda kv: kv[0])],
            "por_uf": [{"uf": x["chave"], **{k: x[k] for k in ("itens", "contratacoes", "valor")}} for x in _soma(uf, lambda kv: (-kv[1]["valor"], kv[0]))],
            "por_esfera": [{"esfera": x["chave"], **{k: x[k] for k in ("itens", "contratacoes", "valor")}} for x in _soma(esfera, lambda kv: (-kv[1]["valor"], kv[0]))],
            "orgaos_principais": [{**o, "valor": _r2(o["valor"])} for o in sorted(orgaos.values(), key=lambda o: (-o["valor"], o["org"] or ""))[:TOP_ORGAOS]],
            "recentes": [{"contratacao": n, "data": c["data"], "orgao": c["orgao"] or c["unidade"], "orgao_detalhado": bool(c["orgao"]), "esfera": c["esfera"], "uf": c["uf"], "municipio": c["municipio"], "ibge": c["ibge"],
                          "modalidade": c["modalidade"], "objeto": c["objeto"], "itens": c["itens"], "valor": _r2(c["valor"])} for n, c in recentes]}, por


def calcular(doc: dict, nomes: dict[str, str], hoje: str) -> tuple[dict, dict, dict]:
    """(operadoras, municípios, resumo). Função pura sobre o normalizado de `siasg_contratos`."""
    compras, uasg, faixas = doc.get("compras") or {}, doc.get("uasg") or {}, doc.get("faixas") or {}
    ops: dict[str, dict] = {}
    municipios: dict[str, dict] = {}
    nac_ano, nac_uf, nac_esfera = (defaultdict(lambda: {"itens": 0, "contratacoes": 0, "valor": 0.0}) for _ in range(3))
    itens_total = contratacoes_total = detalhadas = com_municipio = 0
    for raiz, reg in sorted((doc.get("fornecedores") or {}).items()):
        res, por = operadora(raiz, reg, faixas.get(raiz), compras, uasg, nomes.get(raiz), hoje)
        ops[raiz] = res
        for numero, c in por.items():
            itens_total += c["itens"]
            contratacoes_total += 1
            detalhadas += 1 if c["detalhada"] else 0
            for grupo, k in ((nac_ano, (c["data"] or "s/d")[:4]), (nac_uf, c["uf"] or "s/d"), (nac_esfera, c["esfera"] or "nao_detalhada")):
                grupo[k]["itens"] += c["itens"]
                grupo[k]["contratacoes"] += 1
                grupo[k]["valor"] += c["valor"]
            if c["ibge"]:
                com_municipio += 1
                m = municipios.setdefault(c["ibge"], {"municipio": c["municipio"], "uf": c["uf"], "itens": 0, "contratacoes": 0, "valor": 0.0, "fornecedores": {}})
                m["itens"] += c["itens"]
                m["contratacoes"] += 1
                m["valor"] += c["valor"]
                f = m["fornecedores"].setdefault(raiz, {"raiz": raiz, "cnpj": reg.get("cnpj"), "nome": nomes.get(raiz), "itens": 0, "contratacoes": 0, "valor": 0.0})
                f["itens"] += c["itens"]
                f["contratacoes"] += 1
                f["valor"] += c["valor"]
    for m in municipios.values():
        m["valor"] = _r2(m["valor"])
        m["fornecedores"] = [{**f, "valor": _r2(f["valor"])} for f in sorted(m["fornecedores"].values(), key=lambda f: (-f["valor"], f["raiz"]))[:TOP_FORNECEDORES_MUNICIPIO]]
    leituras = sorted(r["lida_em"] for r in ops.values() if r.get("lida_em"))
    universo = len(faixas)
    cobertura = {"raizes_no_universo": universo, "raizes_faixa_a": sum(1 for v in faixas.values() if v == "A"), "raizes_com_leitura": len(ops), "raizes_sem_leitura": max(universo - len(ops), 0),
                 "raizes_com_resultado": sum(1 for r in ops.values() if r["resultado"] == "com_resultado"), "raizes_incompletas": sum(1 for r in ops.values() if r["incompleto"]),
                 "leitura_mais_antiga": leituras[0] if leituras else None, "leitura_mais_recente": leituras[-1] if leituras else None, "janela_inicio": doc.get("janela_inicio"),
                 "itens": itens_total, "contratacoes": contratacoes_total, "contratacoes_com_detalhe": detalhadas, "contratacoes_com_municipio": com_municipio,
                 "municipios_com_contratacao": len(municipios)}
    fmt = lambda g, nome, chave: [{nome: k, **{x: (_r2(v[x]) if x == "valor" else v[x]) for x in ("itens", "contratacoes", "valor")}} for k, v in sorted(g.items(), key=chave)]      # noqa: E731
    resumo = {"cobertura": cobertura, "por_ano": fmt(nac_ano, "ano", lambda kv: kv[0]), "por_uf": fmt(nac_uf, "uf", lambda kv: kv[0]), "por_esfera": fmt(nac_esfera, "esfera", lambda kv: kv[0]),
              "valor_homologado": _r2(sum(v["valor"] for v in nac_ano.values()))}
    return ops, municipios, resumo


def _nomes(base: Path, date_str: str) -> dict[str, str]:
    rfb = carregar_json_gz(normalized_path(base, date_str, "summary") / "receita_cnpj.json.gz") or {}
    return {r: e["razao"] for r, e in (rfb.get("empresa") or {}).items() if e.get("razao")}


def publicar_contratos(base: Path, date_str: str, log) -> dict:
    doc = carregar_json_gz(normalized_path(base, date_str, "summary") / "siasg_contratos.json.gz")
    if not doc:
        log.info("siasg_contratos.json.gz ausente: contratos públicos não gerados")
        return {}
    ops, municipios, resumo = calcular(doc, _nomes(base, date_str), date_str)
    meta = {"snapshot_date": date_str, "generated_at": now_iso(), "coletado_em": doc.get("fetched_at"), "natureza": "fato_publicado",
            "fonte": {"nome": "Compras.gov.br (dados abertos), espelho do PNCP, Lei 14.133", "url": doc.get("fonte") or siasg.FONTE_URL, "api": doc.get("api"), "licenca": siasg.LICENCA,
                      "consultado_em": (doc.get("fetched_at") or "")[:10] or date_str},
            "licenca": siasg.LICENCA, "aviso": AVISO, "limites": LIMITES, "cobertura": resumo["cobertura"]}
    destino = published_path(base, date_str) / "contratos"
    destino.mkdir(parents=True, exist_ok=True)
    gravar_json_gz(destino / "operadoras.json.gz", {**meta, "operadoras": ops})
    gravar_json_gz(destino / "municipios.json.gz", {**meta, "criterio_municipio": "município do órgão comprador (detalhe da contratação ou unidade de compra), não o local de entrega", "municipios": municipios})
    gravar_json_gz(destino / "resumo.json.gz", {**meta, **{k: v for k, v in resumo.items() if k != "cobertura"}})
    log.info("contratos published", operadoras=len(ops), municipios=len(municipios), itens=resumo["cobertura"]["itens"])
    return {"operadoras": len(ops), "municipios": len(municipios), "itens": resumo["cobertura"]["itens"]}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Contratos públicos de operadoras")
    p.add_argument("--date", default=today_str())
    a = p.parse_args(argv)
    publicar_contratos(data_dir(), a.date, configure_logging())
    return 0


if __name__ == "__main__":
    sys.exit(main())
