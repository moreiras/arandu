# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Esquemas dos artefatos de histórico. Campo ausente numa linha = sem dado (nunca zero inventado)."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict

HISTORY_SCHEMA_VERSION = 1


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LinhaAsn(_Base):
    """Uma linha por ASN e snapshot (weekly/{date}/asn.jsonl.gz)."""
    asn: int
    is_br: bool
    cnpj: Optional[str] = None           # CNPJ da organização (ASN BR com cadastro); chave das séries por operadora
    uf: Optional[str] = None             # UF da sede da organização (não é a UF dos usuários)
    users: Optional[int] = None          # usuários estimados pela APNIC no snapshot (a média móvel de 4 semanas é da série agregada)
    v6users: Optional[int] = None
    p4: int = 0                          # prefixos IPv4 na tabela global
    p6: int = 0
    n_ixd: int = 0                       # PTTs onde o ASN é par direto (observado)
    n_ixm: int = 0                       # PTTs onde é membro cadastrado
    n_provedores: Optional[int] = None   # provedores confirmado+ (ARC); ausente = snapshot sem o bloco de relações
    n_roa: int = 0
    n_aspa: int = 0                      # objetos ASPA publicados pelo próprio AS
    rpki_valid: int = 0
    rpki_invalid: int = 0
    rpki_not_found: int = 0
    n_alertas: Optional[int] = None      # só ASN BR tem alertas
    hash_alertas: Optional[str] = None   # hash dos ids de alerta (compara conjuntos sem guardá-los)
    hash_relacoes: Optional[str] = None  # hash dos provedores confirmado+
    hash_ixd: Optional[str] = None       # hash dos PTTs diretos
    hash_ixm: Optional[str] = None       # hash dos PTTs membros cadastrados
    hash_pfx: Optional[str] = None       # hash dos prefixos globais (aponta quem pode ter trocado de origem)


class LinhaIxp(_Base):
    """Uma linha por PTT e snapshot (weekly/{date}/ixp.jsonl.gz). `status` vem da coleta (ok, partial, missing, failed)."""
    ixp: str
    status: Optional[str] = None
    n_direct: Optional[int] = None       # ASNs pares diretos (união v4 e v6)
    n_br_direct: Optional[int] = None
    n_origin: Optional[int] = None       # ASNs originadores vistos nas rotas dos route servers
    n_br_origin: Optional[int] = None
    n_membros: Optional[int] = None      # membros cadastrados (ixbr_members_count)
    v4_rotas: Optional[int] = None
    v4_prefixos: Optional[int] = None
    v6_rotas: Optional[int] = None
    v6_prefixos: Optional[int] = None


class LinhaOperadora(_Base):
    """Uma linha por CNPJ e snapshot (weekly/{date}/operadora.jsonl.gz), somando os ASNs BR da organização."""
    cnpj: str
    grupo_id: Optional[str] = None       # grupo societário (id; nunca nome de sócio)
    n_asns: int
    users: int = 0
    v6users: int = 0
    users_ma4: Optional[float] = None    # média das amostras dos últimos 28 dias (inclui a atual)
    n_ma4: int = 1                       # amostras usadas na média
    p4: int = 0
    p6: int = 0
    n_ixd: int = 0
    n_roa: int = 0
    rpki_valid: int = 0
    rpki_invalid: int = 0
    rpki_not_found: int = 0
    n_alertas: int = 0


class LinhaUf(_Base):
    """Uma linha por UF e snapshot (weekly/{date}/uf.jsonl.gz), pela UF da sede das organizações dos ASNs BR."""
    uf: str
    n_asns: int
    n_cnpjs: int
    users: int = 0
    v6users: int = 0
    users_ma4: Optional[float] = None
    n_ma4: int = 1
    p4: int = 0
    p6: int = 0
    n_roa: int = 0
    rpki_valid: int = 0
    rpki_invalid: int = 0
    rpki_not_found: int = 0
