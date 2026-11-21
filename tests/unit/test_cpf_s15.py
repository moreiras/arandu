# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""o CPF que a Receita e a Anatel publicam na razão social de EI/MEI sai mascarado."""
import gzip
import json
from pathlib import Path

import pytest

from core.cpf import cpf_valido, mascarar_cpf, mascarar_cpf_em, mascarar_snapshot, pode_ter_cpf


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


def test_api_serve_o_publicado_sem_mascarar_na_leitura(tmp_path):
    """A máscara é da publicação (`mascarar_snapshot`); a API serve o arquivo como está, sem percorrer o documento a cada leitura."""
    from api.repos.base import ArtifactRepo
    from api.store import Store
    pub = tmp_path / "published" / "2026-11-13"
    (pub / "asns").mkdir(parents=True)
    (pub / "manifest.json").write_text("{}")
    with gzip.open(pub / "scm.json.gz", "wt") as f:
        json.dump({"scms": [{"razao_social": f"FULANO {CPF}"}]}, f)
    (pub / "asns" / "65000.json").write_text(json.dumps({"asn": 65000, "name": f"FULANO {CPF}"}))
    assert ArtifactRepo(lambda d: tmp_path / "published" / d).ler("2026-11-13", "scm.json.gz")["scms"][0]["razao_social"] == f"FULANO {CPF}"
    mascarar_snapshot(pub)
    assert ArtifactRepo(lambda d: tmp_path / "published" / d).ler("2026-11-13", "scm.json.gz")["scms"][0]["razao_social"] == "FULANO ***456789**"
    assert Store(tmp_path).asn_detail("2026-11-13", 65000)["name"] == "FULANO ***456789**"


def test_razao_social_lida_de_normalized_sai_mascarada(tmp_path):
    """`normalized/` não passa pela máscara da publicação; o `geo_orgs.json.gz` leva a razão social para o perfil do AS (`alt_names`)."""
    from api.store import Store
    (tmp_path / "published" / "2026-11-13").mkdir(parents=True)
    (tmp_path / "published" / "2026-11-13" / "manifest.json").write_text("{}")
    norm = tmp_path / "normalized" / "2026-11-13" / "summary"
    norm.mkdir(parents=True)
    with gzip.open(norm / "geo_orgs.json.gz", "wt") as f:
        json.dump({"orgs": {"65000": {"razao_social": f"FULANO {CPF}", "cnpj": "12345678000199"}}}, f)
    assert Store(tmp_path)._load_geo_orgs("2026-11-13")[65000]["razao_social"] == "FULANO ***456789**"


def test_mascarar_snapshot_regrava_so_o_que_muda_no_mesmo_formato(tmp_path):
    pub = tmp_path / "2026-11-13"
    (pub / "asns").mkdir(parents=True)
    (pub / "maps").mkdir()
    (pub / "manifest.json").write_text(json.dumps({"x": f"FULANO {CPF}"}))                     # o manifesto nunca é tocado
    (pub / "asns" / "1.json").write_text(json.dumps({"asn": 1, "name": f"FULANA {CPF}"}, ensure_ascii=False, indent=2) + "\n")
    (pub / "asns" / "2.json").write_text(json.dumps({"asn": 2, "name": "SEM CPF"}))
    (pub / "asns" / "3.json").write_text(json.dumps({"asn": 3, "fistel": CPF}))              # 11 dígitos fora de campo de nome
    (pub / "maps" / "scms.geojson").write_text(json.dumps({"features": [{"properties": {"razao_social": f"X {CPF}"}}]},
                                                          separators=(",", ":")))
    with gzip.open(pub / "scm.json.gz", "wt") as f:
        json.dump({"scms": [{"razao_social": f"FULANO {CPF}"}]}, f)
    antes = {p: p.stat().st_mtime_ns for p in pub.rglob("*") if p.is_file()}
    assert mascarar_snapshot(pub, gravar=False).keys() == {"asns/1.json", "maps/scms.geojson", "scm.json.gz"}
    assert {p: p.stat().st_mtime_ns for p in pub.rglob("*") if p.is_file()} == antes           # simulação não grava
    copias = tmp_path / "originais"
    alterados = mascarar_snapshot(pub, copia_em=copias)
    assert alterados.keys() == {"asns/1.json", "maps/scms.geojson", "scm.json.gz"}
    from core.integridade import sha256_arquivo
    assert all(alterados[r] == sha256_arquivo(pub / r) for r in alterados)
    um = (pub / "asns" / "1.json").read_text()
    assert um == json.dumps({"asn": 1, "name": "FULANA ***456789**"}, ensure_ascii=False, indent=2) + "\n"
    assert (pub / "maps" / "scms.geojson").read_text() == '{"features":[{"properties":{"razao_social":"X ***456789**"}}]}'
    assert CPF in (copias / "asns" / "1.json").read_text()
    assert CPF in (pub / "manifest.json").read_text() and CPF in (pub / "asns" / "3.json").read_text()
    assert mascarar_snapshot(pub) == {}                                                       # idempotente


def test_mascarar_snapshot_no_zip_do_formato_compactado(tmp_path):
    import zipfile
    pub = tmp_path / "2026-07-05"
    pub.mkdir()
    with zipfile.ZipFile(pub / "asns.zip", "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("1.json", json.dumps({"asn": 1, "name": f"FULANO {CPF}"}))
        z.writestr("2.json", json.dumps({"asn": 2, "name": "OUTRO"}))
    alterados = mascarar_snapshot(pub)
    assert list(alterados) == ["asns/1.json"]                                                 # como nos checksums do manifesto
    with zipfile.ZipFile(pub / "asns.zip") as z:
        assert json.loads(z.read("1.json"))["name"] == "FULANO ***456789**" and json.loads(z.read("2.json"))["name"] == "OUTRO"
        assert z.getinfo("1.json").compress_type == zipfile.ZIP_DEFLATED


def test_fechamento_do_snapshot_mascara_antes_dos_checksums(tmp_path):
    from publish.coleta_checks import refresh_manifest
    pub = tmp_path / "published" / "2026-11-13"
    (pub / "asns").mkdir(parents=True)
    (pub / "manifest.json").write_text(json.dumps({"date": "2026-11-13"}))
    (pub / "asns" / "1.json").write_text(json.dumps({"asn": 1, "name": f"FULANO {CPF}"}))
    man = refresh_manifest(tmp_path, "2026-11-13", checksums=True)
    from core.integridade import sha256_arquivo
    assert "***456789**" in (pub / "asns" / "1.json").read_text()
    assert man["checksums"]["asns/1.json"] == sha256_arquivo(pub / "asns" / "1.json")


def test_script_corrige_os_publicados_e_o_manifesto(tmp_path):
    import importlib.util
    pub = tmp_path / "data" / "published" / "2026-11-13"
    (pub / "asns").mkdir(parents=True)
    (pub / "asns" / "1.json").write_text(json.dumps({"asn": 1, "name": f"FULANO {CPF}"}))
    from core.integridade import sha256_arquivo
    (pub / "manifest.json").write_text(json.dumps({"checksums": {"asns/1.json": sha256_arquivo(pub / "asns" / "1.json")}}))
    spec = importlib.util.spec_from_file_location("mascarar", Path(__file__).resolve().parents[2] / "scripts" / "mascarar_cpf_publicados.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.main([str(tmp_path / "data")]) == 0                                            # simulação
    assert CPF in (pub / "asns" / "1.json").read_text()
    assert mod.main([str(tmp_path / "data"), "--aplicar", "--copias", str(tmp_path / "orig")]) == 0
    man = json.loads((pub / "manifest.json").read_text())
    assert man["checksums"]["asns/1.json"] == sha256_arquivo(pub / "asns" / "1.json") and len(man["correcoes"]) == 1
    assert CPF in (tmp_path / "orig" / "2026-11-13" / "asns" / "1.json").read_text()
    assert mod.main([str(tmp_path / "data"), "--aplicar"]) == 0                               # idempotente: nenhuma correção nova
    assert len(json.loads((pub / "manifest.json").read_text())["correcoes"]) == 1


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
