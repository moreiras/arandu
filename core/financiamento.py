# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Dados abertos de financiamento (BNDES) e de sanções (CGU: CEIS e CNEP): regras de leitura e de recorte.

Layouts conferidos em 2026-11-08 contra os arquivos reais (BNDES "Operações não automáticas", CSV latin-1 com `;` e aspas, 35 colunas, cabeçalho; CEIS e CNEP, ZIP com um CSV latin-1,
`;`, aspas, cabeçalho). Só pessoa jurídica entra: a linha de pessoa física (CEIS/CNEP "TIPO DE PESSOA" = F, CPF) é descartada na leitura e nunca chega ao disco."""
from __future__ import annotations

import re
from typing import Optional

MAX_TEXTO = 160


def digitos(valor: str) -> str:
    return re.sub(r"\D", "", valor or "")


def numero(valor: str) -> Optional[float]:
    """"9090000,0" → 9090000.0 (decimal com vírgula, sem separador de milhar)."""
    try:
        return float((valor or "").strip().replace(".", "").replace(",", "."))
    except ValueError:
        return None


def data_iso(valor: str) -> Optional[str]:
    """DD/MM/AAAA (CEIS/CNEP) ou AAAA-MM-DD (BNDES) → AAAA-MM-DD."""
    v = (valor or "").strip()
    m = re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", v)
    if m:
        return f"{m[3]}-{m[2]}-{m[1]}"
    return v if re.fullmatch(r"\d{4}-\d{2}-\d{2}", v) else None


def texto(valor: str, limite: int = MAX_TEXTO) -> str:
    v = re.sub(r"\s+", " ", (valor or "").strip())
    return v if len(v) <= limite else v[: limite - 1].rstrip() + "…"


def operacao_bndes(r: dict[str, str]) -> dict:
    """Linha das operações não automáticas do BNDES → registro compacto (sem o texto livre longo do projeto)."""
    return {"contrato": (r.get("numero_do_contrato") or "").strip(), "data": data_iso(r.get("data_da_contratacao", "")),
            "contratado": numero(r.get("valor_contratado_reais", "")), "desembolsado": numero(r.get("valor_desembolsado_reais", "")),
            "produto": texto(r.get("produto", ""), 60), "instrumento": texto(r.get("instrumento_financeiro", ""), 60), "forma": texto(r.get("forma_de_apoio", ""), 30),
            "uf": (r.get("uf") or "").strip(), "ibge": (r.get("municipio_codigo") or "").strip(), "cnae": (r.get("subsetor_cnae_codigo") or "").strip(),
            "porte": texto(r.get("porte_do_cliente", ""), 30), "situacao": texto(r.get("situacao_do_contrato", ""), 30), "projeto": texto(r.get("descricao_do_projeto", ""))}


def sancao(r: dict[str, str], cadastro: str) -> dict:
    """Linha do CEIS/CNEP (pessoa jurídica) → registro compacto. `valor_multa` só existe no CNEP."""
    out = {"cadastro": cadastro, "codigo": (r.get("CÓDIGO DA SANÇÃO") or "").strip(), "categoria": texto(r.get("CATEGORIA DA SANÇÃO", ""), 100),
           "inicio": data_iso(r.get("DATA INÍCIO SANÇÃO", "")), "fim": data_iso(r.get("DATA FINAL SANÇÃO", "")), "publicacao": data_iso(r.get("DATA PUBLICAÇÃO", "")),
           "abrangencia": texto(r.get("ABRAGÊNCIA DA SANÇÃO", ""), 100), "orgao": texto(r.get("ÓRGÃO SANCIONADOR", ""), 100), "uf_orgao": (r.get("UF ÓRGÃO SANCIONADOR") or "").strip(),
           "esfera": (r.get("ESFERA ÓRGÃO SANCIONADOR") or "").strip(), "fundamento": texto(r.get("FUNDAMENTAÇÃO LEGAL", "")), "processo": (r.get("NÚMERO DO PROCESSO") or "").strip()}
    multa = numero(r.get("VALOR DA MULTA", ""))
    if multa is not None:
        out["multa"] = multa
    return out
