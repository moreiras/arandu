# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""o CPF que a Receita e a Anatel publicam na razão social de EI/MEI sai mascarado."""
import gzip
import json

import pytest

from core.cpf import cpf_valido, mascarar_cpf, mascarar_cpf_em, pode_ter_cpf


def _cpf(base9: str) -> str:
    d = [int(c) for c in base9]
    for n in (9, 10):
        d.append(sum(d[i] * (n + 1 - i) for i in range(n)) * 10 % 11 % 10)
    return "".join(map(str, d))


CPF = _cpf("123456789")          # 12345678909


def test_cpf_valido():
    assert CPF == "12345678909" and cpf_valido(CPF)
    assert not cpf_valido("12345678900") and not cpf_valido("11111111111") and not cpf_valido("1234567890")


@pytest.mark.parametrize("texto,esperado", [
    (f"FULANO DE TAL {CPF}", "FULANO DE TAL ***456789**"),
    ("FULANO 123.456.789-09 ME", "FULANO ***456789** ME"),
    (f"{CPF} FULANO", "***456789** FULANO"),
])
def test_cpf_valido_na_razao_social_vira_mascara_da_receita(texto, esperado):
    assert mascarar_cpf(texto) == esperado


@pytest.mark.parametrize("texto", ["EMPRESA 12345678000195 LTDA", "FULANO 12345678900", "FULANO 11111111111", "AS 263276", "FONE 1199999999",
                                   f"X{CPF}9", "PEDIDO 0" + CPF])
def test_cnpj_numero_invalido_ou_encostado_em_digito_nao_muda(texto):
    assert mascarar_cpf(texto) == texto


def test_so_campos_de_nome_e_em_qualquer_profundidade():
    doc = {"scms": [{"razao_social": f"FULANO {CPF}", "num_servico": CPF, "cnpj": "12345678000195"}],
           "x": {"y": [{"nome": f"BELTRANO {CPF}"}]}, "name": f"AS {CPF}"}
    assert mascarar_cpf_em(doc) is doc
    assert doc["scms"][0]["razao_social"] == "FULANO ***456789**" and doc["scms"][0]["num_servico"] == CPF
    assert doc["x"]["y"][0]["nome"] == "BELTRANO ***456789**" and doc["name"] == "AS ***456789**"


def test_pre_filtro_em_bytes():
    assert pode_ter_cpf(f'{{"razao_social": "F {CPF}"}}'.encode()) and not pode_ter_cpf(b'{"cnpj": "12345678000195", "asn": 263276}')


def test_repositorio_e_store_servem_mascarado(tmp_path):
    from api.repos.base import ArtifactRepo
    from api.store import Store
    pub = tmp_path / "published" / "2026-11-13"
    (pub / "asns").mkdir(parents=True)
    (pub / "manifest.json").write_text("{}")
    with gzip.open(pub / "scm.json.gz", "wt") as f:
        json.dump({"scms": [{"razao_social": f"FULANO {CPF}"}]}, f)
    (pub / "asns" / "65000.json").write_text(json.dumps({"asn": 65000, "name": f"FULANO {CPF}"}))
    assert ArtifactRepo(lambda d: tmp_path / "published" / d).ler("2026-11-13", "scm.json.gz")["scms"][0]["razao_social"] == "FULANO ***456789**"
    assert Store(tmp_path).asn_detail("2026-11-13", 65000)["name"] == "FULANO ***456789**"


def test_campo_de_nome_pelo_padrao_da_chave():
    """Uma lista fechada deixaria passar `sici_empresa`: o critério é o padrão da chave."""
    doc = {"sici_empresa": f"FULANO {CPF}", "org_nome": f"FULANO {CPF}", "owner": f"FULANO {CPF}", "prestadora_origem_nome": f"FULANO {CPF}",
           "nomes": [f"FULANO {CPF}", "OUTRO"], "marcas": [{"marca": f"FULANO {CPF}"}],
           "numero_fistel": CPF, "cnpj_cpf_socio": CPF, "org_id": CPF, "codigo": CPF, "outros": [f"FULANO {CPF}"]}
    mascarar_cpf_em(doc)
    for k in ("sici_empresa", "org_nome", "owner", "prestadora_origem_nome"):
        assert doc[k] == "FULANO ***456789**", k
    assert doc["nomes"] == ["FULANO ***456789**", "OUTRO"] and doc["marcas"][0]["marca"] == "FULANO ***456789**"
    for k in ("numero_fistel", "cnpj_cpf_socio", "org_id", "codigo"):
        assert doc[k] == CPF, k                                  # identificador de 11 dígitos não é nome
    assert doc["outros"] == [f"FULANO {CPF}"]                   # lista sob chave que não é de nome fica como está


def test_mapa_por_asn_com_nome():
    """`asns/names.json` é {ASN: nome}: a chave é número, o valor é nome (com letra); valor sem letra (prefixo, IP) não é tocado."""
    doc = {"266187": f"FULANO {CPF}", "65000": "200.160.100.10", "65001": CPF}
    mascarar_cpf_em(doc)
    assert doc == {"266187": "FULANO ***456789**", "65000": "200.160.100.10", "65001": CPF}
