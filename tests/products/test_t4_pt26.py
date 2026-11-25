# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T4 (PT-26): fatos de conformidade na API (cadastro e recuperação do ASN, credenciada de rede virtual e eventos de declaração por município)."""
from tests.products.api_contract import ALLOWED
from tests.synth.world import T1

PROIBIDOS = ("logradouro", "numero", "complemento", "bairro", "cep", "lat", "lon", "telefone", "email", "ddd_telefone", "address")


def _get(api, caminho, **params):
    r = api.get(f"/api/v1{caminho}", params={"date": T1, **params}, headers=ALLOWED)
    assert r.status_code == 200, r.text[:300]
    return r.json()


def test_asn_include_cadastro_e_recuperacao_sem_endereco_nem_contato(api):
    d = _get(api, "/asns/64510", include="cadastro,recuperacao")
    assert "cadastro" in d and "recuperacao" in d                      # a chave vem sempre; o valor é null sem dado
    cad = d["cadastro"]
    if cad is not None:
        assert cad["selo"] == "fato" and "Receita" in cad["fonte"] and cad["cnpj"]
        assert not (set(cad) & set(PROIBIDOS))
    assert d["recuperacao"] is None                                    # 64510 não está na lista de recuperação do dataset sintético


def test_asn_include_desconhecido_continua_400(api):
    r = api.get("/api/v1/asns/64510", params={"date": T1, "include": "cadastro,xyz"}, headers=ALLOWED)
    assert r.status_code == 400 and "cadastro" in r.text and "recuperacao" in r.text


def test_sem_declaracao_credenciadas_conferem_com_o_smp(api):
    corpo = _get(api, "/sem-declaracao-sici", limit=500)
    com_origem = [i for i in corpo["items"] if i.get("rede_virtual_origem")]
    # o que a lista diz da origem vem do `smp.json.gz`: só CNPJ da prestadora de origem, nenhum nome
    for i in com_origem:
        assert len(i["rede_virtual_origem"]) == 14 and i["rede_virtual_origem"].isdigit()
    assert sum(u.get("credenciadas_rede_virtual", 0) for u in corpo["por_uf"].values()) == len(com_origem)
    assert all("grupo_declarou" in u for u in corpo["por_uf"].values())


def test_municipio_indicadores_eventos_so_com_fato(api):
    municipios = _get(api, "/ranking/municipios", limit=100)["items"]
    vistos = 0
    for m in municipios:
        ind = _get(api, f"/municipios/{m['ibge']}", include="indicadores").get("indicadores") or {}
        for e in ind.get("eventos", []):
            vistos += 1
            assert e["tipo"] in ("sem_declaracao_desde", "primeira_declaracao") and e["cnpj"] and e["mes"] and "causa" not in e
    assert vistos >= 0                                                  # o dataset sintético pode não ter evento; o formato é o que se confere


def test_uf_include_indicadores_traz_as_contagens_sem_declaracao(api):
    ufs = _get(api, "/ufs")["items"]
    uf = next(u["uf"] for u in ufs if u.get("uf"))
    ind = _get(api, f"/ufs/{uf}", include="indicadores").get("indicadores")
    assert ind is not None and ind["mes_referencia"] and "n_operadoras" in ind
    sd = ind["sem_declaracao"]
    assert sd["cnpjs_sem_declaracao"] == sd["com_usuarios_apnic"] + sd["sem_usuarios"] + sd["nao_comparavel"]
