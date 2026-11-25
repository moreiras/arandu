# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Contatos nunca saem em resposta pública nem no MCP (AGENTS.md, seção 3): só `contacts_available` (contagens) e a rota com login.

O cadastro da Receita (`geo_org`) traz `ddd_telefone_1/2`; o das outorgas, `telefone`/`email`. `sem_contatos` remove, em qualquer profundidade,
as chaves que são contato — defesa em profundidade para o MCP, que serve documentos do `Store` sem passar pelos modelos de resposta da REST.
"""
from __future__ import annotations

import re
from typing import Any

CHAVE_DE_CONTATO = re.compile(r"(e-?mail|correio|telefone|phone|fone|fax|whatsapp|celular)", re.I)


def e_chave_de_contato(chave: str) -> bool:
    return bool(CHAVE_DE_CONTATO.search(chave))


# Cadastro da Receita (`geo_org`) servido junto do prefixo e no documento do ASN: só identificação e classificação da PJ. Fora: telefone, e-mail,
# logradouro, número, complemento, bairro, CEP e as coordenadas geocodificadas do endereço. Lista de permitidos,
# não de proibidos: campo novo da coleta não sai sem decisão.
GEO_ORG_PUBLICO = frozenset({
    "cnpj", "name", "razao_social", "nome_fantasia", "natureza_juridica", "codigo_natureza_juridica", "porte", "codigo_porte",
    "cnae_fiscal", "cnae_fiscal_descricao", "cnaes_secundarios", "situacao_cadastral", "descricao_situacao_cadastral",
    "identificador_matriz_filial", "descricao_identificador_matriz_filial", "data_inicio_atividade",
    "city", "municipio", "codigo_municipio_ibge", "uf", "geo_confidence", "geo_source",
})


def geo_org_publico(geo_org: Any) -> Any:
    """Projeção pública do `geo_org` (lista de permitidos `GEO_ORG_PUBLICO`); `None`/não dicionário passa como está."""
    if not isinstance(geo_org, dict):
        return geo_org
    return {k: v for k, v in geo_org.items() if k in GEO_ORG_PUBLICO}


# Endereço da sede (decisão D1 do mantenedor, 2026-11-24): logradouro, número, complemento, bairro, CEP e a coordenada geocodificada do endereço
# não saem no MCP nem nos dados de outorga, para nenhum titular (PJ, EI ou MEI); município, UF e código IBGE ficam. A posição pode ser usada
# por dentro (filtro `near` do `query`), sem ser servida.
CAMPOS_DE_ENDERECO = frozenset({"descricao_tipo_de_logradouro", "tipo_logradouro", "logradouro", "numero", "complemento", "bairro", "cep",
                                "address", "endereco"})
CAMPOS_DE_COORDENADA = frozenset({"lat", "lon", "latitude", "longitude"})
CAMPOS_DA_SEDE = CAMPOS_DE_ENDERECO | CAMPOS_DE_COORDENADA


def sem_endereco(registro: Any) -> Any:
    """Cópia de um registro de cadastro (outorga, linha de operadora) sem endereço nem coordenada da sede; só o primeiro nível."""
    if not isinstance(registro, dict):
        return registro
    return {k: v for k, v in registro.items() if k not in CAMPOS_DA_SEDE}


def sem_contatos(valor: Any) -> Any:
    """Cópia de `valor` sem as chaves de contato (dicionários e listas, recursivamente). Não altera o original."""
    if isinstance(valor, dict):
        return {k: sem_contatos(v) for k, v in valor.items() if not (isinstance(k, str) and e_chave_de_contato(k))}
    if isinstance(valor, list):
        return [sem_contatos(v) for v in valor]
    return valor
