# SPDX-License-Identifier: AGPL-3.0-or-later
"""T1 — sócios da Receita Federal (WebDAV do Nextcloud + ZIPs em streaming)."""
import httpx
import pytest
import respx

from sources.receita_socios import collect as rs
from tests.sources.conftest import make_zip, read_gz, write_gz


def multistatus(base_href: str, entries: list[tuple[str, bool]]) -> str:
    """Resposta PROPFIND depth=1 do Nextcloud: a 1ª <response> é a própria pasta."""
    def item(name: str, is_dir: bool, href: str) -> str:
        rtype = "<d:resourcetype><d:collection/></d:resourcetype>" if is_dir else "<d:resourcetype/>"
        return (f"<d:response><d:href>{href}</d:href><d:propstat><d:prop><d:displayname>{name}</d:displayname>{rtype}"
                f"</d:prop><d:status>HTTP/1.1 200 OK</d:status></d:propstat></d:response>")
    body = item("raiz", True, base_href) + "".join(item(n, d, base_href + n) for n, d in entries)
    return f'<?xml version="1.0"?><d:multistatus xmlns:d="DAV:">{body}</d:multistatus>'


@pytest.fixture()
def alvo(base, date_str):
    """Outorgas já normalizadas definem o conjunto-alvo de CNPJs."""
    write_gz(base / "normalized" / date_str / "summary" / "anatel_scm.json.gz",
             {"by_cnpj": {"19438160000145": [], "17131007000145": [], "18362941000130": []}})


@pytest.fixture()
def dump(fx):
    return make_zip("K3241.K03200Y0.D60913.SOCIOCSV", fx("receita_socios", "Socios0.sample.csv").read_bytes())


def mount(respx_mock, dump_zip, months=("2026-07", "2026-08"), files=("Socios0.zip", "Empresas0.zip", "Socios1.zip")):
    respx_mock.route(method="PROPFIND", url=rs.WEBDAV_ROOT).respond(207, text=multistatus(rs.WEBDAV_ROOT, [(m, True) for m in months] + [("leiame.txt", False)]))
    latest = sorted(months)[-1]
    respx_mock.route(method="PROPFIND", url=f"{rs.WEBDAV_ROOT}{latest}/").respond(207, text=multistatus(f"{rs.WEBDAV_ROOT}{latest}/", [(f, False) for f in files]))
    respx_mock.get(url__regex=rf"{rs.WEBDAV_ROOT}{latest}/Socios\d\.zip").respond(200, content=dump_zip)


@respx.mock
def test_filtra_pelos_cnpjs_basicos_da_base(base, log, alvo, dump, date_str):
    mount(respx, dump)
    r = rs.run(date_str, base, log)
    assert r["dump_reference"] == "2026-08" and r["parts_processed"] == 2          # Empresas0.zip é ignorado
    assert r["target_cnpj_basicos"] == 3 and r["matched_cnpj_basicos"] == 3
    soc = r["by_cnpj_basico"]
    assert "99999999" not in soc
    assert [s["nome_socio"] for s in soc["19438160"] if s["identificador_socio"] == "2"][0].startswith("JOAO")
    # a mesma parte é servida 2× (Socios0 e Socios1): as linhas dobram — o coletor não deduplica entre partes
    assert len(soc["19438160"]) == 4
    assert soc["17131007"][0]["identificador_socio"] == "1"
    assert soc["19438160"][0]["cnpj_cpf_socio"].startswith("***")                    # CPF mascarado pela RFB


@respx.mock
def test_decodifica_latin1(base, log, alvo, dump, date_str):
    mount(respx, dump, files=("Socios0.zip",))
    r = rs.run(date_str, base, log)
    assert r["by_cnpj_basico"]["18362941"][0]["nome_socio"] == "JOSÉ AÇAÍ FICTÍCIO"


@respx.mock
def test_grava_normalizado_e_usa_credencial_do_compartilhamento(base, log, alvo, dump, date_str):
    mount(respx, dump, files=("Socios0.zip",))
    rs.run(date_str, base, log)
    assert read_gz(base / "normalized" / date_str / "summary" / "receita_socios.json.gz")["source_index"] == rs.WEBDAV_ROOT
    auth = [c.request.headers.get("Authorization", "") for c in respx.calls]
    assert auth and all(a.startswith("Basic ") for a in auth)


def test_sem_cnpjs_alvo_levanta(base, log, date_str):
    with pytest.raises(RuntimeError, match="Nenhum CNPJ base"):
        rs.run(date_str, base, log)


@respx.mock
def test_sem_pastas_de_mes_levanta(base, log, alvo, date_str):
    respx.route(method="PROPFIND", url=rs.WEBDAV_ROOT).respond(207, text=multistatus(rs.WEBDAV_ROOT, [("leiame.txt", False)]))
    with pytest.raises(RuntimeError, match="pasta de mês"):
        rs.run(date_str, base, log)


@respx.mock
def test_mes_sem_arquivos_de_socios_levanta(base, log, alvo, dump, date_str):
    mount(respx, dump, files=("Empresas0.zip",))
    with pytest.raises(RuntimeError, match="Nenhum arquivo de sócios"):
        rs.run(date_str, base, log)


@respx.mock
def test_http_erro_no_propfind(base, log, alvo, date_str):
    respx.route(method="PROPFIND", url=rs.WEBDAV_ROOT).respond(401)
    with pytest.raises(httpx.HTTPStatusError):
        rs.run(date_str, base, log)


def test_load_target_cnpjs_une_as_quatro_fontes(base, log, date_str):
    s = base / "normalized" / date_str / "summary"
    write_gz(s / "anatel_scm.json.gz", {"by_cnpj": {"1": [], "2": []}})
    write_gz(s / "anatel_stfc.json.gz", {"by_cnpj": {"2": [], "3": []}})
    assert rs._load_target_cnpjs(base, date_str, log) == {"1", "2", "3"}
