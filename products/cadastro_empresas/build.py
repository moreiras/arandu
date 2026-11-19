# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Cadastro das empresas de telecom: o CNPJ da Receita cruzado com o SICI.

Entrada:  normalized/{date}/summary/receita_cnpj.json.gz (fonte `receita_cnpj`), `sici_municipios.json.gz` e `sici_movel_municipios.json.gz` (publicados),
          `config/municipios-referencia.json` (IBGE por nome e UF) e as outorgas normalizadas (quem é operadora).
Saída:    published/{date}/empresas/cadastro.json.gz (mercado: entradas e baixas por ano, empresas ativas por UF e porte, resumo) e
          published/{date}/empresas/operadoras/{NN}.json.gz (uma por operadora, em arquivos de 100 faixas pelos 2 primeiros dígitos da raiz do CNPJ).

Por operadora (raiz de CNPJ de 8 dígitos, no SICI ou nas outorgas): matriz, número de estabelecimentos por situação, porte, Simples e MEI, e a PRESENÇA FÍSICA por município,
cruzando onde há estabelecimento ativo com onde a empresa declara acessos no SICI (fixo ou móvel). O cadastro é fato da Receita na data do dump mensal; o cruzamento com o
SICI é leitura de duas fontes diferentes, não prova que a empresa atende ou deixa de atender o município. Sem e-mail, telefone, rua nem CEP, e sem razão social nem nome
fantasia de empresário individual. O `cnpj_geo` (BrasilAPI) fica como está por um ciclo; este produto não o substitui ainda.

Uso:
    python -m products.cadastro_empresas.build --date 2026-11-07
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Optional

from core import receita_cnpj as rc
from core.common import configure_logging, data_dir, normalized_path, now_iso, published_path, today_str
from core.geoip import normaliza
from core.jsonio import carregar_json_gz, gravar_json_gz

_CONFIG = Path(__file__).resolve().parent.parent.parent / "config"
_OUTORGAS = ("anatel_scm.json.gz", "anatel_smp.json.gz", "anatel_stfc.json.gz", "anatel_seac.json.gz")
LIMITES = (
    "Cadastro da Receita Federal na data do dump mensal (não o de hoje): situação, datas e CNAE como a empresa declarou. A presença física compara onde há estabelecimento ativo com onde a empresa declara "
    "acessos no SICI; são duas fontes que medem coisas diferentes (sede e filiais × assinantes), então a diferença não prova que a empresa atende ou deixou de atender um município. "
    "O recorte é o de telecom (outorgas, SICI e CNAE 61): uma filial de outro CNAE de empresa fora desses conjuntos pode faltar. Município por nome e UF; o que não casa com o IBGE fica fora do mapa por município "
    "e é contado em `resumo.estabelecimentos_sem_ibge`. Sem e-mail, telefone, rua nem CEP; empresário individual sem razão social nem nome fantasia."
)


def _ref() -> dict[tuple[str, str], str]:
    ref = json.loads((_CONFIG / "municipios-referencia.json").read_text(encoding="utf-8"))
    return {(uf, normaliza(nome)): codigo for codigo, (nome, uf, _a) in ref.items()}


def _nomes() -> dict[str, tuple[str, str]]:
    ref = json.loads((_CONFIG / "municipios-referencia.json").read_text(encoding="utf-8"))
    return {codigo: (nome, uf) for codigo, (nome, uf, _a) in ref.items()}


def _ibge(est: dict, municipios_rfb: dict[str, str], por_nome: dict[tuple[str, str], str]) -> Optional[str]:
    nome = municipios_rfb.get(est.get("mu") or "")
    return por_nome.get((est.get("u") or "", normaliza(nome))) if nome else None


def _acessos_por_raiz_municipio(docs: list[tuple[str, dict]]) -> dict[str, dict[str, dict[str, int]]]:
    """{raiz: {ibge: {"fixo": n, "movel": n}}} a partir de `sici_municipios` (fixo) e `sici_movel_municipios` (móvel)."""
    out: dict[str, dict[str, dict[str, int]]] = defaultdict(lambda: defaultdict(lambda: {"fixo": 0, "movel": 0}))
    for tipo, doc in docs:
        for ibge, m in ((doc or {}).get("municipios") or {}).items():
            for op in m.get("operadores") or []:
                cnpj = op.get("cnpj") or ""
                if len(cnpj) == 14:
                    out[cnpj[:8]][ibge][tipo] += int(op.get("acessos") or 0)
    return out


def calcular(rfb: dict, fixo: Optional[dict], movel: Optional[dict], operadoras: set[str], por_nome: dict, nomes: dict, snapshot_date: str) -> tuple[dict, dict[str, dict]]:
    """(documento de mercado, {raiz: documento da operadora}). Função pura: nada de rede nem disco."""
    mun_rfb = rfb.get("municipios_rfb") or {}
    cnaes = rfb.get("cnaes") or {}
    naturezas = rfb.get("naturezas") or {}
    acessos = _acessos_por_raiz_municipio([("fixo", fixo or {}), ("movel", movel or {})])
    entradas: dict[str, Counter] = defaultdict(Counter)
    baixas: dict[str, Counter] = defaultdict(Counter)
    ativas_uf: Counter = Counter()
    ativas_porte: Counter = Counter()
    sem_ibge = 0
    docs: dict[str, dict] = {}
    for basico, ests in (rfb.get("estabelecimentos") or {}).items():
        emp = (rfb.get("empresa") or {}).get(basico) or {}
        sim = (rfb.get("simples") or {}).get(basico) or {}
        matriz = next((e for e in ests if e.get("m") == 1), None)
        telecom = bool(matriz) and (matriz.get("p") or "").startswith(rc.TELECOM)
        if matriz and telecom:                        # mercado: uma contagem por empresa (a matriz), só CNAE 61 principal
            ano = (matriz.get("d") or "")[:4]
            if ano.isdigit():
                entradas[ano][matriz.get("u") or "?"] += 1
            if matriz.get("s") == "08" and (matriz.get("ds") or "")[:4].isdigit():
                baixas[matriz["ds"][:4]][matriz.get("u") or "?"] += 1
            if matriz.get("s") == "02":
                ativas_uf[matriz.get("u") or "?"] += 1
                ativas_porte[("mei" if sim.get("mei") else rc.PORTE.get(emp.get("porte") or "00", "nao_informado"))] += 1
        if basico not in operadoras:
            continue
        por_mun: dict[str, dict] = {}
        total: Counter = Counter()
        for e in ests:
            total["total"] += 1
            total["ativos" if e.get("s") == "02" else ("baixados" if e.get("s") == "08" else "outras")] += 1
            if e.get("m") == 2 and e.get("s") == "02":
                total["filiais_ativas"] += 1
            ibge = _ibge(e, mun_rfb, por_nome)
            if not ibge:
                sem_ibge += 1
                continue
            m = por_mun.setdefault(ibge, {"estabelecimentos": 0, "ativos": 0, "tem_matriz": False})
            m["estabelecimentos"] += 1
            m["ativos"] += 1 if e.get("s") == "02" else 0
            m["tem_matriz"] = m["tem_matriz"] or e.get("m") == 1
        ac = acessos.get(basico, {})
        presenca = []
        for ibge in sorted(set(por_mun) | set(ac)):
            nome, uf = nomes.get(ibge, ("", ""))
            m = por_mun.get(ibge) or {"estabelecimentos": 0, "ativos": 0, "tem_matriz": False}
            a = ac.get(ibge) or {"fixo": 0, "movel": 0}
            presenca.append({"ibge": ibge, "municipio": nome, "uf": uf, **m, "acessos_fixo": a["fixo"], "acessos_movel": a["movel"]})
        com_est = {p["ibge"] for p in presenca if p["ativos"] > 0}
        com_ac = {p["ibge"] for p in presenca if p["acessos_fixo"] + p["acessos_movel"] > 0}
        m_doc = None
        if matriz:
            ib = _ibge(matriz, mun_rfb, por_nome)
            m_doc = {"cnpj": matriz["c"], "uf": matriz.get("u"), "ibge": ib, "municipio": (nomes.get(ib) or (mun_rfb.get(matriz.get("mu") or ""), ""))[0] if ib else mun_rfb.get(matriz.get("mu") or ""),
                     "situacao": rc.SITUACAO.get(matriz.get("s") or "", matriz.get("s")), "inicio": matriz.get("d"), "cnae": matriz.get("p"), "cnae_descricao": cnaes.get(matriz.get("p") or "")}
        docs[basico] = {
            "raiz": basico, "razao_social": emp.get("razao"), "nome_fantasia": (matriz or {}).get("n"),
            "natureza_juridica": {"codigo": emp.get("nat"), "descricao": naturezas.get(emp.get("nat") or "")} if emp.get("nat") else None,
            "porte": rc.PORTE.get(emp.get("porte") or "", None), "capital_social": emp.get("capital"),
            "simples": bool(sim.get("simples")), "mei": bool(sim.get("mei")), "matriz": m_doc,
            "estabelecimentos": {"total": total["total"], "ativos": total["ativos"], "baixados": total["baixados"], "filiais_ativas": total["filiais_ativas"]},
            "presenca": presenca,
            "resumo_presenca": {"municipios_com_estabelecimento_ativo": len(com_est), "municipios_com_acessos": len(com_ac), "com_ambos": len(com_est & com_ac),
                                 "so_acessos": len(com_ac - com_est), "so_estabelecimento": len(com_est - com_ac)},
        }
    anos = sorted(set(entradas) | set(baixas))
    mercado = {
        "entradas_por_ano": [{"ano": int(a), "total": sum(entradas[a].values()), "por_uf": dict(sorted(entradas[a].items()))} for a in anos if a in entradas],
        "baixas_por_ano": [{"ano": int(a), "total": sum(baixas[a].values()), "por_uf": dict(sorted(baixas[a].items()))} for a in anos if a in baixas],
        "ativas_por_uf": dict(sorted(ativas_uf.items())), "ativas_por_porte": dict(sorted(ativas_porte.items())),
    }
    resumo = {"empresas_no_recorte": len(rfb.get("estabelecimentos") or {}), "operadoras_com_cadastro": len(docs), "operadoras_sem_cadastro": len(operadoras - set(docs)),
              "estabelecimentos_sem_ibge": sem_ibge, "empresas_ativas": sum(ativas_uf.values())}
    return {"mercado": mercado, "resumo": resumo}, docs


def _operadoras(norm: Path, fixo: Optional[dict], movel: Optional[dict]) -> set[str]:
    """Raízes de CNPJ de operadora: as das outorgas (SCM, SMP, STFC, SeAC) e as que declaram acessos no SICI."""
    raizes: set[str] = set()
    for nome in _OUTORGAS:
        raizes.update(c[:8] for c in ((carregar_json_gz(norm / nome) or {}).get("by_cnpj") or {}) if len(c) == 14)
    for doc in (fixo, movel):
        for m in ((doc or {}).get("municipios") or {}).values():
            raizes.update(op["cnpj"][:8] for op in m.get("operadores") or [] if len(op.get("cnpj") or "") == 14)
    return raizes


def publicar_cadastro_empresas(base: Path, date_str: str, log) -> dict:
    norm = normalized_path(base, date_str, "summary")
    rfb = carregar_json_gz(norm / "receita_cnpj.json.gz")
    if not rfb:
        log.info("receita_cnpj ausente: cadastro das empresas não gerado")
        return {}
    pub = published_path(base, date_str)
    fixo = carregar_json_gz(pub / "sici_municipios.json.gz")
    movel = carregar_json_gz(pub / "sici_movel_municipios.json.gz")
    geral, docs = calcular(rfb, fixo, movel, _operadoras(norm, fixo, movel), _ref(), _nomes(), date_str)
    meta = {"snapshot_date": date_str, "generated_at": now_iso(), "natureza": "fato_cadastral", "fonte": "Receita Federal, dados abertos do CNPJ", "dump_reference": rfb.get("dump_reference"),
            "mes_referencia_sici": (fixo or {}).get("mes_referencia")}
    destino = pub / "empresas"
    (destino / "operadoras").mkdir(parents=True, exist_ok=True)
    gravar_json_gz(destino / "cadastro.json.gz", {**meta, "limites": LIMITES, **geral})
    faixas: dict[str, dict] = defaultdict(dict)
    for raiz, d in docs.items():
        faixas[raiz[:2]][raiz] = d
    for faixa, por_raiz in faixas.items():
        gravar_json_gz(destino / "operadoras" / f"{faixa}.json.gz", {**meta, "faixa": faixa, "operadoras": por_raiz})
    log.info("empresas/cadastro written", operadoras=len(docs), faixas=len(faixas), **geral["resumo"])
    return {**geral["resumo"], "faixas": len(faixas)}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Cadastro das empresas de telecom")
    p.add_argument("--date", default=today_str())
    a = p.parse_args(argv)
    publicar_cadastro_empresas(data_dir(), a.date, configure_logging())
    return 0


if __name__ == "__main__":
    sys.exit(main())
