# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Relações do grupo econômico: com que evidência as empresas do grupo estão ligadas.

Mostra a **estrutura entre empresas (PJ)**: o tipo da ligação (quadro de sócios idêntico, sócios em comum, controle parcial entre empresas) e **quantos** sócios
sustentam cada ligação. **Nunca** devolve nome nem CPF de sócio pessoa física (eles nem chegam à leitura: `core.cpf.sem_socios_pessoa_fisica`). As controladoras externas (PJ fora do universo de telecomunicações) saem só com razão social, CNPJ básico, situação e natureza jurídica.
"""
from __future__ import annotations

from typing import Callable, Optional

TIPOS = {
    "quadro_identico": "Quadro de sócios idêntico",
    "controle_parcial": "Uma empresa controla parte da outra (sócio pessoa jurídica)",
    "socios_em_comum": "Sócios em comum",
}
ORDEM = list(TIPOS)
LIMITE_FORA = 25


def relacoes_do_grupo(g: dict, socios: Optional[dict], nome: Callable[[str], str]) -> Optional[dict]:
    if not socios:
        return None
    by = socios.get("by_cnpj", {})
    membros = [c["cnpj"] for c in g["cnpjs"]]
    dentro = set(membros)
    pares: dict[tuple, dict] = {}
    fora: dict[str, dict] = {}
    holdings: dict[str, dict] = {}
    for cnpj in membros:
        row = by.get(cnpj) or {}
        for h in row.get("holdings_externas") or []:
            holdings.setdefault(h["cnpj_basico"], {"cnpj_basico": h["cnpj_basico"], "razao_social": h.get("razao_social"), "situacao_cadastral": h.get("situacao_cadastral"),
                                                   "natureza_juridica": h.get("natureza_juridica"), "controla": []})["controla"].append(cnpj)
        for lista in ("mesmo_grupo", "relacionadas_parcial"):
            for e in row.get(lista) or []:
                outro, t = e["cnpj"], e["tipo_relacao"]
                tipo = "controle_parcial" if t.startswith("controle_parcial") else t
                if tipo not in TIPOS:
                    continue
                if outro not in dentro:
                    f = fora.setdefault(outro, {"cnpj": outro, "tipo": tipo, "socios_em_comum": e.get("socios_em_comum"), "liga_a": []})
                    f["liga_a"].append(cnpj)
                    continue
                if t == "controle_parcial_exercido":
                    de, para = cnpj, outro
                elif t == "controle_parcial_recebido":
                    de, para = outro, cnpj
                else:
                    de, para = sorted((cnpj, outro))                      # ligação simétrica: uma linha por par
                chave = (tipo, de, para)
                p = pares.setdefault(chave, {"tipo": tipo, "de": de, "para": para, "socios": None})
                n = e.get("socios_em_comum") if tipo == "socios_em_comum" else e.get("total_socios_da_controlada") if tipo == "controle_parcial" else None
                if n is not None:
                    p["socios"] = n if p["socios"] is None else max(p["socios"], n)
    ligacoes = [{**p, "tipo_rotulo": TIPOS[p["tipo"]], "de_nome": nome(p["de"]), "para_nome": nome(p["para"])} for p in pares.values()]
    ligacoes.sort(key=lambda x: (ORDEM.index(x["tipo"]), x["de_nome"].lower(), x["para_nome"].lower()))
    fora_lista = sorted(({**f, "empresa": nome(f["cnpj"]), "tipo_rotulo": TIPOS[f["tipo"]], "liga_a": sorted(set(f["liga_a"]))} for f in fora.values()), key=lambda f: f["empresa"].lower())
    return {
        "grupo_id": g["grupo_id"], "classificacao": g.get("classificacao"), "empresas": len(membros), "referencia_receita": socios.get("receita_dump_reference"),
        "ligacoes": ligacoes, "tipos": TIPOS,
        "fora_do_grupo": {"total": len(fora_lista), "itens": fora_lista[:LIMITE_FORA]},
        "controladoras_externas": sorted(({**h, "controla": sorted(set(h["controla"]))} for h in holdings.values()), key=lambda h: (h["razao_social"] or "").lower()),
        "natureza": "inferido do quadro societário da Receita Federal: relações diretas entre pares; o grupo reúne as empresas ligadas por cadeia de relações",
        "limites": "Só a estrutura entre empresas (PJ) e a contagem de sócios que sustenta cada ligação; nome e CPF de sócio pessoa física não são mostrados. A ligação é um indício societário: "
                   "não prova que as empresas operam juntas nem que o controle é exercido. Ordem alfabética, sem ranking.",
    }
