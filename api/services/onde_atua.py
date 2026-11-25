# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Onde atua (PT-23): a parcela local, o número de declarantes e o HHI local de uma operadora ou de um grupo, município a município.

Só junta o que o snapshot já publica, sem coleta nova: os acessos por município e CNPJ do SICI (`sici_municipios`, com o total do município e o HHI por CNPJ)
e o cruzamento por grupo (`mercado_grupos`, com o HHI por grupo). Tudo sobre **acessos fixos declarados** no mês de referência do SICI, não sobre domicílios,
receita, preço nem escolha do cliente; o agrupamento por grupo é inferido do quadro societário. A parcela alta num município pequeno não é "domínio": o número
de declarantes e os acessos do município ficam ao lado. Funções puras: quem lê os documentos é a rota. Nenhum dado de pessoa física entra aqui.
"""
from __future__ import annotations

import unicodedata
from typing import Optional

from core.avisos_agregado import avisos

ORDENS = {
    "acessos": "acessos do conjunto no município",
    "parcela": "parcela do conjunto nos acessos do município",
    "hhi": "HHI local por grupo",
    "nome": "nome do município",
    "uf": "UF",
}

LIMITES = (
    "Acessos fixos declarados pelas empresas à Anatel no mês de referência do SICI (não é a data do snapshot). A parcela é os acessos do conjunto ÷ os acessos declarados por todas "
    "as empresas no município; o HHI local soma o quadrado da parcela de cada declarante. Medem acessos declarados, não domicílios, receita, preço nem escolha do cliente. "
    "Município com poucos acessos pode refletir declaração pontual; operadora de satélite declara em quase todos os municípios. O grupo é inferido do quadro societário e o HHI "
    "por grupo conta os CNPJs do mesmo grupo como um só; o HHI por CNPJ é o declarado."
)


class OndeAtuaErro(Exception):
    def __init__(self, status: int, mensagem: str):
        super().__init__(mensagem)
        self.status, self.mensagem = status, mensagem


def enriquecer_municipios_operadora(municipios: list[dict], sici_municipios: Optional[dict]) -> list[dict]:
    """Acrescenta a cada município da operadora o total do município, a parcela dela, o número de declarantes e o HHI por CNPJ.

    A parcela é nula quando o município não está no índice (snapshot sem `sici_municipios`): o mapa e a tabela mostram "—", nunca zero.
    Linhas novas; o documento do SICI não é alterado."""
    out = []
    for m in municipios:
        info = (sici_municipios or {}).get(m["ibge"]) or {}
        total = info.get("acessos") or 0
        out.append({**m,
                    "municipio_acessos": total or None,
                    "share": round(100 * m["acessos"] / total, 2) if total else None,
                    "municipio_operadores": info.get("operadores_count"),
                    "municipio_hhi": info.get("hhi"),
                    "avisos_hhi": avisos(info["operadores_count"], com_peso=False) if info.get("operadores_count") is not None else None})      # `poucos_casos`: nada é suprimido (D6)
    return out


def _sem_acento(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", texto.lower()) if unicodedata.category(c) != "Mn")


def linhas_do_grupo(cnpjs: list[str], cadastro: dict, sici_municipios: dict, mercado: Optional[dict]) -> list[dict]:
    """Uma linha por município onde algum CNPJ do conjunto declarou acessos: acessos do conjunto, parcela, declarantes e HHI local por grupo e por CNPJ.

    `cadastro`: `cnpjs` do SICI (com `por_municipio`); `mercado`: `mercado_grupos.json.gz` (None se não publicado: os HHI ficam nulos, não zero)."""
    por_mun: dict[str, dict] = {}
    for c in cnpjs:
        for ibge, m in ((cadastro.get(c) or {}).get("por_municipio") or {}).items():
            e = por_mun.setdefault(ibge, {"ibge": ibge, "nome": m.get("nome", ""), "uf": m.get("uf", ""), "acessos": 0, "cnpjs_do_conjunto": 0})
            e["acessos"] += m.get("acessos", 0)
            e["cnpjs_do_conjunto"] += 1
    muns_mg = (mercado or {}).get("municipios") or {}
    linhas = []
    for ibge, e in por_mun.items():
        info = sici_municipios.get(ibge) or {}
        mg = muns_mg.get(ibge) or {}
        total = info.get("acessos") or 0
        linhas.append({
            **e,
            "municipio_acessos": total or None,
            "parcela": round(100 * e["acessos"] / total, 2) if total else None,
            "declarantes": info.get("operadores_count"),
            "hhi_grupo": mg.get("hhi_grupo"), "faixa_grupo": mg.get("faixa_grupo"), "avisos_grupo": mg.get("avisos_grupo"),
            "hhi_cnpj": mg.get("hhi_cnpj") if mg else info.get("hhi"), "faixa_cnpj": mg.get("faixa_cnpj"),
        })
    return linhas


def resumo_do_grupo(linhas: list[dict]) -> dict:
    """Contagens sobre todos os municípios do conjunto (não só os da página): quantos têm mais da metade dos acessos e quantos têm um só declarante."""
    com_parcela = [l for l in linhas if l["parcela"] is not None]
    return {
        "municipios": len(linhas),
        "com_mais_da_metade": sum(1 for l in com_parcela if l["parcela"] > 50),
        "com_um_so_declarante": sum(1 for l in linhas if l["declarantes"] == 1),
        "acessos": sum(l["acessos"] for l in linhas),
        "ufs": len({l["uf"] for l in linhas}),
    }


_CHAVES = {
    "acessos": lambda l: (l["acessos"], l["ibge"]),
    "parcela": lambda l: (l["parcela"] if l["parcela"] is not None else -1, l["ibge"]),
    "hhi": lambda l: (l["hhi_grupo"] if l["hhi_grupo"] is not None else -1, l["ibge"]),
    "nome": lambda l: (_sem_acento(l["nome"]), l["ibge"]),
    "uf": lambda l: (l["uf"], _sem_acento(l["nome"]), l["ibge"]),
}


def pagina(linhas: list[dict], uf: Optional[str], q: Optional[str], ordem: str, desc: bool, limit: int, offset: int) -> dict:
    """Filtra por UF e por nome, ordena (empate pelo código IBGE: estável) e devolve a janela pedida com o total do filtro."""
    if ordem not in ORDENS:
        raise OndeAtuaErro(400, f"ordem inválida: {ordem}. Use: {', '.join(ORDENS)}")
    sel = linhas
    if uf:
        sel = [l for l in sel if l["uf"] == uf.upper()]
    if q:
        alvo = _sem_acento(q.strip())
        sel = [l for l in sel if alvo in _sem_acento(l["nome"])]
    sel = sorted(sel, key=_CHAVES[ordem], reverse=desc)
    return {"total": len(sel), "items": sel[offset:offset + limit]}
