# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Acessos declarados à Anatel (SICI) publicados: banda larga fixa (`sici*.json.gz`) e telefonia móvel (`sici_movel*.json.gz`).

Os dois artefatos têm o mesmo formato, então uma classe cobre os dois (`prefixo="sici"` ou `"sici_movel"`). Só a leitura e as
consultas diretas ficam aqui; os cruzamentos com outorgas, ASNs e geo ficam nos serviços.

O mês de referência do SICI é DIFERENTE da data do snapshot: quem responde precisa citar as duas.
"""
from __future__ import annotations

from typing import Optional

from api.repos.base import ArtifactRepo


class SiciRepo(ArtifactRepo):
    def __init__(self, pub, prefixo: str = "sici", validar=None):
        super().__init__(pub, validar)
        self.prefixo = prefixo
        self.arquivo = f"{prefixo}.json.gz"
        self.arquivo_municipios = f"{prefixo}_municipios.json.gz"

    # -- documentos ---------------------------------------------------------
    def dados(self, date_str: str) -> Optional[dict]:
        """O documento completo (`cnpjs`, `asn_to_cnpj`, séries…) ou None se o pipeline não o publicou."""
        return self.ler(date_str, self.arquivo)

    def municipios_doc(self, date_str: str) -> Optional[dict]:
        """Índice invertido IBGE → operadores."""
        return self.ler(date_str, self.arquivo_municipios)

    def invalidar_snapshot(self, date_str: str) -> None:
        self.invalidar(date_str)

    # -- consultas diretas ----------------------------------------------------
    def meta(self, date_str: str) -> dict:
        """Metadados da coleta: mês de referência, totais e meses disponíveis."""
        data = self.dados(date_str)
        if not data:
            return {}
        return {
            "mes_referencia": data.get("mes_referencia", ""),
            "meses_disponiveis": data.get("meses_disponiveis", []),
            "total_acessos": data.get("total_acessos", 0),
            "total_cnpjs": data.get("total_cnpjs", 0),
            "matched_cnpjs": data.get("matched_cnpjs", 0),
            "matched_acessos": data.get("matched_acessos", 0),
            "fonte": data.get("fonte", ""),
        }

    def for_cnpj(self, date_str: str, cnpj: str) -> Optional[dict]:
        """Acessos declarados por um CNPJ no mês de referência. None se não declara."""
        data = self.dados(date_str)
        return data.get("cnpjs", {}).get(cnpj) if data else None

    def cnpj_for_asn(self, date_str: str, asn: int) -> Optional[str]:
        data = self.dados(date_str)
        return data.get("asn_to_cnpj", {}).get(str(asn)) if data else None

    def for_asn(self, date_str: str, asn: int) -> Optional[dict]:
        """Acessos do CNPJ que detém o ASN. ASN→CNPJ é 1:1, o inverso não: CNPJ com mais de um ASN recebe o total integral em cada
        (`acessos_compartilhados`), e somar ASes do mesmo CNPJ é errado."""
        data = self.dados(date_str)
        if not data:
            return None
        cnpj = data.get("asn_to_cnpj", {}).get(str(asn))
        return data.get("cnpjs", {}).get(cnpj) if cnpj else None

    def serie(self, date_str: str, cnpj: str) -> list[list]:
        """Série mensal [mes, acessos, pf, pj] de um CNPJ, do mais antigo ao recente."""
        data = self.dados(date_str)
        return data.get("serie_por_cnpj", {}).get(cnpj, []) if data else []

    def serie_total(self, date_str: str) -> list[dict]:
        data = self.dados(date_str)
        return data.get("serie_total", []) if data else []

    def distribuicao(self, date_str: str, chave: str) -> dict[str, dict]:
        """UF → {"pf": {faixa|modalidade: acessos}, "pj": {...}} do mês de referência (`chave` = distrib_velocidade | distrib_modalidade)."""
        data = self.dados(date_str)
        return data.get(chave, {}) if data else {}

    def divergencia(self, date_str: str, asn: int) -> Optional[dict]:
        data = self.dados(date_str)
        return data.get("divergencia", {}).get(str(asn)) if data else None

    def divergencias(self, date_str: str) -> dict[str, dict]:
        data = self.dados(date_str)
        return data.get("divergencia", {}) if data else {}

    def municipio(self, date_str: str, ibge: str) -> Optional[dict]:
        data = self.municipios_doc(date_str)
        return data.get("municipios", {}).get(ibge) if data else None

    def municipios(self, date_str: str) -> dict[str, dict]:
        data = self.municipios_doc(date_str)
        return data.get("municipios", {}) if data else {}
