# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""projeção pública do cadastro da Receita (`geo_org`) servido junto do prefixo."""
from api.privacidade import GEO_ORG_PUBLICO, e_chave_de_contato, geo_org_publico

# Formato real do `geo_orgs.json.gz` (chaves conferidas no snapshot de 2026-10-11; valores inventados).
REAL = {"bairro": "Centro", "cache_version": 3, "cached_at": "2026-10-01", "cep": "01000000", "city": "São Paulo", "cnae_fiscal": 6110801,
        "cnae_fiscal_descricao": "Serviços de telefonia fixa comutada", "cnaes_secundarios": [], "cnpj": "00000000000191", "codigo_municipio": 7107,
        "codigo_municipio_ibge": 3550308, "codigo_natureza_juridica": 2062, "codigo_porte": 5, "complemento": "Sala 1", "data_inicio_atividade": "2000-01-01",
        "ddd_telefone_1": "1199999999", "ddd_telefone_2": "", "descricao_identificador_matriz_filial": "MATRIZ", "descricao_motivo_situacao_cadastral": "",
        "descricao_situacao_cadastral": "ATIVA", "descricao_tipo_de_logradouro": "RUA", "email": "x@exemplo.org", "geo_confidence": "address",
        "geo_source": "nominatim", "identificador_matriz_filial": 1, "lat": -23.5, "logradouro": "Rua X", "lon": -46.6, "motivo_situacao_cadastral": 0,
        "municipio": "São Paulo", "name": "EXEMPLO", "natureza_juridica": "Sociedade Anônima", "nome_fantasia": "Exemplo", "numero": "1", "porte": "DEMAIS",
        "razao_social": "EXEMPLO S.A.", "situacao_cadastral": 2, "uf": "SP"}


def test_sem_contato_endereco_nem_coordenada():
    g = geo_org_publico(REAL)
    assert not [k for k in g if e_chave_de_contato(k)]
    for k in ("logradouro", "numero", "complemento", "bairro", "cep", "lat", "lon", "descricao_tipo_de_logradouro", "cache_version", "cached_at"):
        assert k not in g, k
    assert g["cnpj"] == REAL["cnpj"] and g["name"] == "EXEMPLO" and g["uf"] == "SP"


def test_lista_de_permitidos_nao_tem_contato_e_campo_novo_nao_passa():
    assert not [k for k in GEO_ORG_PUBLICO if e_chave_de_contato(k)]
    assert "whatsapp_novo" not in geo_org_publico({**REAL, "whatsapp_novo": "x", "campo_futuro": 1})
    assert "campo_futuro" not in geo_org_publico({**REAL, "campo_futuro": 1})
    assert geo_org_publico(None) is None
