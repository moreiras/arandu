# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Fatos cadastrais e de numeração do ASN (PT-26, ASN 5.3): situação do CNPJ na Receita e ASN em recuperação pelo Registro.br.

Só fato com fonte e data. Nenhum endereço, coordenada nem contato: a lista de campos é explícita (`CAMPOS_CADASTRO`) e o registro leva `cnpj`
e `razao_social`, para a regra de pessoa natural (`core.pessoa_natural`) alcançar o nome do titular na saída. Situação cadastral diferente de ATIVA
e ASN em recuperação não provam que o AS está sem uso nem irregular: a tela diz o fato, a fonte e a data, sem causa.
"""
from __future__ import annotations

from typing import Any, Optional

#: campos do cadastro da Receita que saem no bloco (identificação, classificação, situação e município); nunca endereço, coordenada nem contato
CAMPOS_CADASTRO = ("cnpj", "razao_social", "nome_fantasia", "natureza_juridica", "porte", "cnae_fiscal", "cnae_fiscal_descricao",
                   "situacao_cadastral", "descricao_situacao_cadastral", "descricao_motivo_situacao_cadastral",
                   "municipio", "uf", "codigo_municipio_ibge")


def bloco_cadastro(geo_org: Optional[dict], cnpj_doc: Optional[str] = None) -> Optional[dict]:
    """Cadastro público do CNPJ do ASN com a data da leitura (`lido_em`, do cache da coleta). `None` sem cadastro."""
    if not isinstance(geo_org, dict) or not (geo_org.get("cnpj") or cnpj_doc):
        return None
    out: dict[str, Any] = {k: geo_org.get(k) for k in CAMPOS_CADASTRO if geo_org.get(k) not in (None, "")}
    out.setdefault("cnpj", geo_org.get("cnpj") or cnpj_doc)
    out["lido_em"] = geo_org.get("cached_at")
    out["fonte"] = "Receita Federal (cadastro de CNPJ, via BrasilAPI)"
    out["selo"] = "fato"
    return out


def bloco_recuperacao(doc: Optional[dict], asn: int) -> Optional[dict]:
    """ASN na lista de recursos em recuperação do Registro.br: a janela e a data em que o OBINT o viu pela primeira vez. A lista não informa o motivo."""
    for i in ((doc or {}).get("em_recuperacao") or {}).get("itens", []):
        if i.get("tipo") == "asn" and str(i.get("recurso")) == str(asn):
            return {"asn": asn, "inicio": i.get("inicio"), "fim": i.get("fim"), "primeira_vez_visto": i.get("primeira_vez_visto"),
                    "fonte": "Registro.br (lista de recursos em recuperação)", "selo": "fato"}
    return None
