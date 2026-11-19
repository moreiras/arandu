# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Dados abertos do CNPJ (Receita Federal): layout dos arquivos e regras de recorte.

Layout conferido em 2026-11-07 contra o arquivo real `Estabelecimentos1.zip` do mês 2026-10 (30 colunas, aspas, `;`, latin-1, sem cabeçalho) e
contra `https://www.gov.br/receitafederal/dados/cnpj-metadados.pdf`. O recorte é o universo de telecom: CNPJs das outorgas e do SICI e todo
estabelecimento com CNAE 61 (principal ou secundário). Não entram e-mail, telefone, logradouro, número, complemento, bairro nem CEP; sócios não passam
por aqui (ficam no `receita_socios`). Empresário individual (natureza 213-5) não leva razão social nem nome fantasia: o nome é o da pessoa.
"""
from __future__ import annotations

from typing import Optional

NATUREZA_EI = "2135"                     # Empresário (Individual): razão social = nome da pessoa física
TELECOM = "61"                           # divisão 61 da CNAE: telecomunicações
MAX_CNAES_SECUNDARIOS = 20
SITUACAO = {"01": "nula", "02": "ativa", "03": "suspensa", "04": "inapta", "08": "baixada"}
PORTE = {"00": "nao_informado", "01": "micro", "03": "pequeno", "05": "demais"}

# colunas de Estabelecimentos*.csv
E_BASICO, E_ORDEM, E_DV, E_MATRIZ, E_FANTASIA, E_SITUACAO, E_DATA_SITUACAO, E_INICIO, E_CNAE, E_CNAE_SEC, E_UF, E_MUNICIPIO = 0, 1, 2, 3, 4, 5, 6, 10, 11, 12, 19, 20
E_COLUNAS = 30


def dia(valor: str) -> Optional[str]:
    """AAAAMMDD → AAAA-MM-DD; a Receita usa 0 e 00000000 para "sem data"."""
    v = (valor or "").strip()
    if len(v) != 8 or not v.isdigit() or v == "00000000":
        return None
    return f"{v[:4]}-{v[4:6]}-{v[6:]}"


def cnaes_secundarios(valor: str) -> list[str]:
    return [c for c in (valor or "").replace(" ", "").split(",") if c][:MAX_CNAES_SECUNDARIOS]


def eh_telecom(cnae_principal: str, cnaes_sec: list[str]) -> bool:
    return (cnae_principal or "").startswith(TELECOM) or any(c.startswith(TELECOM) for c in cnaes_sec)


def estabelecimento(row: list[str]) -> dict:
    """Linha de Estabelecimentos → registro compacto, sem endereço de rua, contato nem CEP."""
    sec = cnaes_secundarios(row[E_CNAE_SEC])
    out = {"c": row[E_BASICO].strip() + row[E_ORDEM].strip() + row[E_DV].strip(),
           "m": 1 if row[E_MATRIZ].strip() == "1" else 2,
           "s": row[E_SITUACAO].strip(), "d": dia(row[E_INICIO]), "ds": dia(row[E_DATA_SITUACAO]),
           "u": row[E_UF].strip(), "mu": row[E_MUNICIPIO].strip(), "p": row[E_CNAE].strip(), "x": sec}
    fantasia = row[E_FANTASIA].strip()
    if fantasia:
        out["n"] = fantasia
    return out


def capital(valor: str) -> Optional[float]:
    try:
        return float((valor or "").strip().replace(".", "").replace(",", "."))
    except ValueError:
        return None


def empresa(row: list[str]) -> dict:
    """Linha de Empresas (7 colunas). Empresário individual: sem razão social."""
    natureza = row[2].strip()
    out = {"nat": natureza, "capital": capital(row[4]), "porte": row[5].strip()}
    if natureza != NATUREZA_EI:
        out["razao"] = row[1].strip()
    return out


def simples(row: list[str]) -> dict:
    """Linha de Simples (7 colunas): opção pelo Simples e pelo MEI, com as datas."""
    return {"simples": row[1].strip() == "S", "simples_in": dia(row[2]), "simples_out": dia(row[3]),
            "mei": row[4].strip() == "S", "mei_in": dia(row[5]), "mei_out": dia(row[6])}
