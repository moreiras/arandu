# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Contratos públicos: constantes e funções puras sobre a API de dados abertos do Compras.gov.br (espelho do PNCP, Lei 14.133).

Só pessoa jurídica entra: o `niFornecedor` de 14 dígitos. Fornecedor pessoa física (CPF), servidor e representante ficam de fora por construção
(`item_compacto` devolve None). Cada item é um RESULTADO de item de contratação publicado no PNCP; não é, por si, um contrato assinado nem um pagamento.
"""
from __future__ import annotations

import datetime as _dt
import re
from typing import Optional

BASE_URL = "https://dadosabertos.compras.gov.br"
ENDPOINT_RESULTADOS = "/modulo-contratacoes/3_consultarResultadoItensContratacoes_PNCP_14133"
ENDPOINT_COMPRA = "/modulo-contratacoes/1.1_consultarContratacoes_PNCP_14133_Id"
TAMANHO_PAGINA = 500                                  # máximo aceito pela API
JANELA_INICIO = "2021-04-01"                          # Lei 14.133 (1º/4/2021): nada do PNCP em 14.133 é anterior
PERIODO_MAX_DIAS = 360                                # a API recusa período maior que 365 dias (HTTP 400 "Período inicial e final maior que 365 dias", medido em 2026-11-10)
JANELAS_INICIAIS = 1                                  # a primeira leitura de uma raiz é só a janela mais recente (360 dias); o histórico entra depois, uma janela por visita (`aprofundar_fornecedor`); `SIASG_JANELAS_INICIAIS` muda
SOBREPOSICAO_DIAS = 45                                # releitura incremental: o resultado pode ser incluído no PNCP dias depois da data dele
FONTE_URL = "https://dadosabertos.compras.gov.br"
OBJETO_MAX = 300
ESFERAS = {"F": "federal", "E": "estadual", "M": "municipal", "D": "distrital"}
CANCELADO = "Cancelado"
LICENCA = "dados abertos (Lei 12.527/2011, LAI; PNCP, Lei 14.133/2021, art. 174); sem licença nominal publicada"   # nenhuma política acessível no portal; informação pública é regra e sigilo é exceção (LAI)


def digitos(v: object) -> str:
    return re.sub(r"\D", "", str(v or ""))


def _dv(base: str) -> str:
    """Dígitos verificadores do CNPJ para os 12 primeiros dígitos."""
    pesos = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    out = base
    for p in (pesos[1:], pesos):
        r = sum(int(d) * w for d, w in zip(out, p)) % 11
        out += "0" if r < 2 else str(11 - r)
    return out[12:]


def cnpj_matriz(raiz: str) -> str:
    """CNPJ completo da matriz (ordem 0001) de uma raiz de 8 dígitos."""
    base = digitos(raiz)
    if len(base) != 8:
        raise ValueError(f"raiz de CNPJ inválida: {raiz!r}")
    return base + "0001" + _dv(base + "0001")


def numero(v: object) -> Optional[float]:
    try:
        return None if v is None else float(v)
    except (TypeError, ValueError):
        return None


def item_compacto(r: dict) -> Optional[dict]:
    """Resultado de item reduzido ao necessário. None se o fornecedor não é pessoa jurídica (CNPJ de 14 dígitos) ou falta a chave do item."""
    cnpj = digitos(r.get("niFornecedor"))
    if len(cnpj) != 14 or (r.get("tipoPessoa") or "PJ") != "PJ" or not r.get("idCompraItem"):
        return None
    return {"id": r["idCompraItem"], "seq": r.get("sequencialResultado") or 1, "compra": r.get("numeroControlePNCPCompra") or r.get("idContratacaoPNCP"),
            "un": str(r.get("unidadeOrgaoCodigoUnidade") or ""), "uf": r.get("unidadeOrgaoUfSigla"), "org": digitos(r.get("orgaoEntidadeCnpj")) or None, "cnpj": cnpj,
            "qtd": numero(r.get("quantidadeHomologada")), "valor": numero(r.get("valorTotalHomologado")), "sit": r.get("situacaoCompraItemResultadoNome"),
            "data": (r.get("dataResultadoPncp") or "")[:10] or None}


def chave_item(it: dict) -> str:
    return f"{it['id']}#{it['seq']}"


def compra_compacta(d: dict, lida_em: str) -> dict:
    """Detalhe da contratação (órgão, esfera, município, modalidade, objeto resumido). Só dado do órgão e da compra: nada de pessoa."""
    objeto = " ".join((d.get("objetoCompra") or "").split())
    return {"orgao": d.get("orgaoEntidadeRazaoSocial"), "org": digitos(d.get("orgaoEntidadeCnpj")) or None, "esfera": ESFERAS.get((d.get("orgaoEntidadeEsferaId") or "").upper()),
            "uf": d.get("unidadeOrgaoUfSigla"), "ibge": str(d["unidadeOrgaoCodigoIbge"]) if d.get("unidadeOrgaoCodigoIbge") else None, "municipio": d.get("unidadeOrgaoMunicipioNome"),
            "modalidade": d.get("modalidadeNome"), "objeto": objeto[:OBJETO_MAX] + ("…" if len(objeto) > OBJETO_MAX else ""), "ano": d.get("anoCompraPncp"), "em": lida_em}


def inicio_primeira_leitura(hoje: str, janelas: Optional[int] = None) -> str:
    """Primeira leitura de uma raiz: `janelas` períodos de `PERIODO_MAX_DIAS` para trás, nunca antes da Lei 14.133."""
    import os
    n = janelas if janelas is not None else int(os.environ.get("SIASG_JANELAS_INICIAIS") or JANELAS_INICIAIS)
    ini = (_dt.date.fromisoformat(hoje) - _dt.timedelta(days=n * PERIODO_MAX_DIAS - 1)).isoformat()
    return max(ini, JANELA_INICIO)


def janelas(inicio: str, fim: str, max_dias: int = PERIODO_MAX_DIAS) -> list[tuple[str, str]]:
    """Períodos consecutivos, sem sobreposição, de no máximo `max_dias` dias (a API não aceita período maior que 365)."""
    a, z = _dt.date.fromisoformat(inicio), _dt.date.fromisoformat(fim)
    out: list[tuple[str, str]] = []
    while a <= z:
        b = min(a + _dt.timedelta(days=max_dias - 1), z)
        out.append((a.isoformat(), b.isoformat()))
        a = b + _dt.timedelta(days=1)
    return out
