# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T1 — listas de numeração do Registro.br e do LACNIC e vigia de diretórios: amostras sintéticas no formato real, sem rede."""
import gzip
import json

import httpx
import pytest
import respx

from core import ipv4_listas as L
from core.common import read_json_gz
from core.vigia_diretorios import cabecalho, comparar, padrao, parse_indice
from sources.ipv4_listas import enrich as nz
from sources.ipv4_vigia import collect as vg


class _Log:
    def info(self, *a, **k): pass
    def warning(self, *a, **k): self.avisos = getattr(self, "avisos", []) + [k]


def _txt(fx, nome):
    return fx("ipv4_listas", nome).read_text(encoding="latin-1")


def test_cidr_abreviado_e_faixas():
    assert L.normalizar_cidr("200.234.0/22") == "200.234.0.0/22" and L.normalizar_cidr("2804:5330::/32") == "2804:5330::/32" and L.normalizar_cidr("x/y") is None
    assert L.faixa_para_cidrs("45.68.105.0", 768) == ["45.68.105.0/24", "45.68.106.0/23"] and L.enderecos(["198.18.0.0/22", "2001:db8::/32"]) == 1024


def test_transferencias_registrobr_com_e_sem_conjunto_original(fx):
    regs, ign = L.parse_transferencias_registrobr(_txt(fx, "registrobr-transferencias-diretas-lacnic"))
    assert len(regs) == 5 and ign == [] and regs[2]["blocos"] == ["198.18.8.0/22"] and regs[2]["blocos_originais"] == ["198.18.8.0/22"] and regs[3]["pais_destino"] == "AR"
    simples, _ = L.parse_transferencias_registrobr(_txt(fx, "registrobr-transferencias-diretas"))
    assert [r["id"] for r in simples] == [r["id"] for r in regs] and "blocos_originais" not in simples[0]
    _, ign = L.parse_transferencias_registrobr("2025-01-01|so|tres|campos\nlixo\n")
    assert len(ign) == 2


def test_recuperacao_recuperados_e_log_do_lacnic_com_registro_invalido_contado(fx):
    rec, i1 = L.parse_recuperacao(_txt(fx, "registrobr-recuperacao"))
    assert [(r["tipo"], r["recurso"]) for r in rec] == [("bloco", "198.19.4.0/24"), ("asn", "64999"), ("bloco6", "2001:db8:1::/48")] and rec[0]["fim"] == "2026-11-30" and i1 == []
    rd, i2 = L.parse_recuperados(_txt(fx, "registrobr-recuperados"))
    assert len(rd) == 3 and i2 == []
    log, i3 = L.parse_lacnic_log((fx("ipv4_listas", "lacnic-transfers.json")).read_text())
    assert len(log) == 2 and len(i3) == 1 and log[0]["blocos"] == ["198.19.0.0/24"] and log[0]["data"] == "2026-01-15" and log[0]["enderecos"] == 256


def test_delegated_ipv4_chaveia_por_inicio_e_quantidade(fx):
    bl, ign = L.parse_delegated_ipv4(gzip.decompress(fx("ipv4_listas", "delegated-lacnic-extended-20261101.gz").read_bytes()).decode())
    assert ign == [] and bl["198.18.0.0/1024"]["opaque"] == "org-beta" and bl["198.19.4.0/256"]["status"] == "reserved" and bl["198.19.4.0/256"]["opaque"] is None and len(bl) == 6


def test_mascara_de_pessoa_fisica_so_para_nome_brasileiro_sem_marcador_de_empresa():
    assert L.mascarar_nome("JOAO DA SILVA SANTOS", "BR") == "Pessoa física"
    assert L.mascarar_nome("ALFA TELECOM LTDA", "BR") == "ALFA TELECOM LTDA" and L.mascarar_nome("Maria Souza", "AR") == "Maria Souza" and L.mascarar_nome("SetarNet", "BR") == "SetarNet"


def test_cpf_embutido_no_nome_sai_mascarado_em_qualquer_parte():
    """IPV4-E14: a parte estrangeira não passa pela heurística de pessoa física, mas o CPF embutido (regra de `core.cpf`) vale para todas;
    no `blocos_br` o nome vai dentro de uma linha em lista, que a máscara da publicação não percorre."""
    assert L.mascarar_nome("JOAO DA SILVA 12345678909", "BR") == "JOAO DA SILVA ***456789**"
    assert L.mascarar_nome("JOAO DA SILVA 12345678909", "US") == "JOAO DA SILVA ***456789**"
    assert L.mascarar_nome("EXAMPLE NETWORKS LLC 12345678900", "US") == "EXAMPLE NETWORKS LLC 12345678900"      # DV inválido: não é CPF
    from products.ipv4.build import blocos_br
    estado = {"blocos": {"b": {"inicio": "198.18.0.0", "quantidade": 256, "status": "allocated", "cc": "BR", "data": "2020-01-01", "opaque": "o1"}}}
    linha = blocos_br(estado, {"198.18.0.0/24": {"asn": 64496, "org": "JOAO DA SILVA 12345678909"}})[0]
    assert linha[5:] == [64496, "JOAO DA SILVA ***456789**"]


def _bruto(base, fx, data, sem_ultima=False):
    pasta = base / "raw" / data / "summary"
    pasta.mkdir(parents=True)
    for prefixo, arq in (("registrobr-transferencias-diretas", "registrobr-transferencias-diretas"), ("registrobr-transferencias-diretas-lacnic", "registrobr-transferencias-diretas-lacnic"),
                         ("registrobr-recuperacao", "registrobr-recuperacao"), ("registrobr-recuperados", "registrobr-recuperados")):
        txt = _txt(fx, arq)
        if sem_ultima and "transferencias" in arq:
            txt = "\n".join(ln for ln in txt.splitlines() if not ln.startswith("2026-10-29")) + "\n"
        (pasta / f"{prefixo}-{data}.gz").write_bytes(gzip.compress(txt.encode("latin-1"), mtime=0))
    (pasta / f"lacnic-transfers-{data}.gz").write_bytes(gzip.compress(fx("ipv4_listas", "lacnic-transfers.json").read_bytes(), mtime=0))


def test_normalizar_marca_primeira_vez_visto_e_anterior_a_coleta(fx, tmp_path, monkeypatch):
    _bruto(tmp_path, fx, "2026-10-28", sem_ultima=True)
    _bruto(tmp_path, fx, "2026-10-30")
    monkeypatch.setattr(nz, "MINIMOS", {})
    r = nz.normalizar(tmp_path, "2026-10-30", _Log())
    doc = read_json_gz(tmp_path / "normalized" / "2026-10-30" / "summary" / "ipv4_listas.json.gz")
    t = {}
    for x in doc["transferencias_registrobr"]:
        t.setdefault(x["data"] + x["destino"], x)                       # o lote de 2025-03-10 tem 2 linhas; vale a primeira
    novo = t["2026-10-29EPSILON COMUNICACOES LTDA"]
    assert novo["primeira_vez_visto"] == "2026-10-30" and novo["anterior_a_coleta"] is False
    antigo = t["2025-03-10BETA REDES LTDA - ME"]
    assert antigo["primeira_vez_visto"] == "2026-10-28" and antigo["anterior_a_coleta"] is True and antigo["blocos_originais"] == ["198.18.0.0/22"]
    assert r["transferencias_registrobr"]["novos_na_data"] == 1 and r["transferencias_lacnic"]["ignoradas"] == 1 and r["transferencias_registrobr"]["primeira_data_coletada"] == "2026-10-28"
    assert len(doc["recuperacao"]) == 3 and len(doc["transferencias_lacnic"]) == 2


def test_normalizar_falha_alto_sem_bruto_e_com_arquivo_truncado(fx, tmp_path):
    with pytest.raises(FileNotFoundError):
        nz.normalizar(tmp_path, "2026-10-30", _Log())
    _bruto(tmp_path, fx, "2026-10-30")
    with pytest.raises(RuntimeError, match="esperado ≥"):
        nz.normalizar(tmp_path, "2026-10-30", _Log())


INDICE = ('<tr><td><a href="/pub/">Parent Directory</a></td><td>&nbsp;</td><td align="right">  - </td></tr>\n'
          '<tr><td><a href="delegated-lacnic-20261031">x</a></td><td align="right">2026-10-31 02:56  </td><td align="right">4.4M</td><td>&nbsp;</td></tr>\n'
          '<tr><td><a href="README">x</a></td><td align="right">2004-01-07 10:52  </td><td align="right">593 </td><td>&nbsp;</td></tr>\n'
          '<tr><td><a href="2026/">x</a></td><td align="right">2026-10-31 21:16  </td><td align="right">  - </td><td>&nbsp;</td></tr>\n')


def test_indice_do_apache_vira_padroes():
    it = parse_indice(INDICE)
    assert [i["nome"] for i in it] == ["delegated-lacnic-20261031", "README", "2026/"] and it[0]["padrao"] == "delegated-lacnic-AAAAMMDD" and it[2]["padrao"] == "AAAA/"
    assert padrao("22548v4.csv") == "<asn>v4.csv" and padrao("transfers_20261031T080000Z.json") == "transfers_AAAAMMDDTHHMMSSZ.json"


def test_comparar_detecta_padrao_novo_arquivo_novo_e_cabecalho_mudado():
    def v(nomes, cab):
        return {"diretorios": {"u/": [{"nome": n, "padrao": padrao(n), "data": "d", "tamanho": "1"} for n in nomes]}, "cabecalhos": {"u/arq": {"hash": cab}}}
    ant = v(["delegated-lacnic-20261030", "README"], "h1")
    assert comparar(v(["delegated-lacnic-20261030"], "h1"), None) == []
    assert comparar(v(["delegated-lacnic-20261030", "delegated-lacnic-20261031", "README"], "h1"), ant) == []                      # arquivo diário novo não é novidade
    a = comparar(v(["delegated-lacnic-20261030", "README", "subasignaciones-latest.json", "NOVO.txt"], "h2"), ant)
    assert {x["tipo"] for x in a} == {"padrao_novo", "cabecalho_mudou"} and {x["nome"] for x in a if x["tipo"] == "padrao_novo"} == {"subasignaciones-latest.json", "NOVO.txt"}
    assert comparar(v(["delegated-lacnic-20261030"], "h1"), ant)[0] == {"tipo": "padrao_removido", "url": "u/", "padrao": "README"}


def test_cabecalho_ignora_a_data_de_geracao_e_le_chaves_de_json():
    a = cabecalho(b"# Generated on 2026-11-02\n# Format: <a>|<b>\n2025-01-01|x\n")
    b = cabecalho(b"# Generated on 2026-11-03\n# Format: <a>|<b>\n2025-02-02|y\n")
    c = cabecalho(b"# Generated on 2026-11-03\n# Format: <a>|<b>|<c>\n2025-02-02|y\n")
    assert a["hash"] == b["hash"] != c["hash"] and cabecalho(b'{"transfers": [], "version": "1"}')["chaves"] == ["transfers", "version"]


def test_vigia_grava_a_varredura_alerta_so_com_anterior_e_falha_alto_sem_diretorios(tmp_path):
    log = _Log()
    with respx.mock:
        for u in vg.DIRETORIOS:
            respx.get(u).mock(return_value=httpx.Response(200, text=INDICE))
        for u in vg.ARQUIVOS:
            respx.get(u).mock(return_value=httpx.Response(206, content=b"# Generated on 2026-11-02\n# Format: a|b\n"))
        r1 = vg.run("2026-11-01", tmp_path, log, dormir=lambda s: None)
        assert r1["primeira_varredura"] is True and r1["alertas"] == 0 and r1["diretorios"] == 7
        novo = INDICE + '<tr><td><a href="bitacora-subasignaciones.json">x</a></td><td align="right">2026-11-02 09:00  </td><td align="right">3K</td><td>&nbsp;</td></tr>\n'
        respx.get(vg.DIRETORIOS[4]).mock(return_value=httpx.Response(200, text=novo))
        r2 = vg.run("2026-11-02", tmp_path, log, dormir=lambda s: None)
    assert r2["alertas"] == 1
    doc = json.loads(vg.caminho(tmp_path, "2026-11-02").read_text())
    assert doc["alertas"][0]["tipo"] == "padrao_novo" and doc["alertas"][0]["nome"] == "bitacora-subasignaciones.json"
    assert any(a.get("nome") == "bitacora-subasignaciones.json" for a in log.avisos)
    with respx.mock:
        for u in vg.DIRETORIOS:
            respx.get(u).mock(return_value=httpx.Response(500))
        for u in vg.ARQUIVOS:
            respx.get(u).mock(return_value=httpx.Response(500))
        with pytest.raises(RuntimeError, match="diretórios listados"):
            vg.run("2026-11-03", tmp_path, log, dormir=lambda s: None)


def test_subasignacao_esquema_hipotetico_ignora_o_invalido_e_conta(fx):
    from core import ipv4_subasignacao as S
    regs, ign = S.parse(fx("ipv4_listas", "subasignacoes_hipotetico.json").read_text())
    assert [r["receptor_asn"] for r in regs] == [64500, 64501, 64502] and len(ign) == 2 and regs[0]["cedente_asn"] == 64496 and regs[1]["fim"] is None
    csv = "bloco,receptor_asn,inicio,fim\n198.18.0.0/24,AS64500,2026-12-01,\n"
    assert S.parse(csv, "csv")[0][0]["receptor_asn"] == 64500


def test_subasignacao_validacoes_dizem_none_quando_falta_dado_e_nao_inventam():
    from core import ipv4_subasignacao as S
    r = {"bloco": "198.18.0.0/24", "receptor_asn": 64500, "inicio": "2026-12-01", "fim": None}
    v = S.validar(r, None, None, None, None, None)
    assert v == {"receptor_origina": None, "tem_roa": None, "tamanho": True, "receptor_ipv6": None, "prazo_3_anos": True, "nao_infra_critica": None}
    v = S.validar(r, {64500}, {64500}, True, "2025-06-01", ["198.18.0.0/22"])
    assert v["receptor_origina"] and v["tem_roa"] and v["receptor_ipv6"] and v["prazo_3_anos"] is False and v["nao_infra_critica"] is False
    assert S.validar({**r, "bloco": "198.18.0.0/16"}, {1}, {1}, True, "2020-01-01", [])["tamanho"] is False
    assert S.parse_infra_critica("lacnic|BR|ipv4|198.18.0.0|1024|20200101|x|org|doc|IXP\nlacnic|BR|ipv6|2001:db8::|32|x\nruim") == ["198.18.0.0/22"]


def test_subasignacao_adaptador_desativado_sem_url_e_ativo_com_url(fx, tmp_path, monkeypatch):
    from sources.ipv4_subasignacao import collect as sa
    monkeypatch.delenv("ARANDU_SUBASIGNACAO_URL", raising=False)
    assert sa.run("2026-12-02", tmp_path, _Log()) == {"ativa": False} and not (tmp_path / "normalized").exists()
    with respx.mock:
        respx.get("https://exemplo.invalid/bitacora.json").mock(return_value=httpx.Response(200, content=fx("ipv4_listas", "subasignacoes_hipotetico.json").read_bytes()))
        r = sa.run("2026-12-02", tmp_path, _Log(), url="https://exemplo.invalid/bitacora.json")
    assert r == {"ativa": True, "registros": 3, "ignoradas": 2}
    doc = read_json_gz(tmp_path / "normalized" / "2026-12-02" / "summary" / "ipv4_subasignacoes.json.gz")
    assert len(doc["registros"]) == 3 and doc["ignoradas"] == 2 and len(doc["sha256"]) == 64
