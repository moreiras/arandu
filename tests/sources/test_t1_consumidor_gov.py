# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T1 — Consumidor.gov.br: amostra sintética no leiaute real, sem rede."""
import io
import json
import zipfile

import httpx
import pytest
import respx

from core import consumidor
from core.common import read_json_gz
from sources.consumidor_gov import collect as f


class _Log:
    def info(self, *a, **k): pass
    warning = info


def _csv(fx):
    with zipfile.ZipFile(fx("consumidor_gov", "finalizadas_sintetico.zip")) as z:
        return io.BytesIO(z.read("finalizadas_2026-09.csv"))


def test_agrega_so_telecom_e_descarta_a_pessoa(fx):
    d = consumidor.agregar_csv(_csv(fx))
    r = d["resumo"]
    assert r["linhas"] == 11 and r["telecom"] == 9 and r["marcas"] == 2 and r["celulas"] == 3         # saúde, aparelho e a linha truncada ficam de fora
    assert r["segmentos"] == ["Operadoras de Telecomunicações (Telefonia, Internet, TV por assinatura)"]
    c = {(x["marca"], x["uf"], x["cidade"]): x for x in d["cidades"]}
    alfa = c[("Alfa Telecom", "SP", "Alfa do Norte")]
    assert (alfa["n"], alfa["respondidas"], alfa["avaliadas"], alfa["resolvidas"]) == (6, 5, 4, 3)
    assert (alfa["tempo_n"], alfa["tempo_soma"], alfa["nota_n"], alfa["nota_soma"]) == (5, 34, 4, 15)       # a não respondida não tem tempo e a não avaliada não tem nota
    assert c[("Alfa Telecom", "MG", "São Gonçalo do Rio")]["n"] == 1
    assert not any(k in json.dumps(d, ensure_ascii=False) for k in ("Sexo", "Faixa", "entre 31", "\"F\""))   # nada de pessoa no agregado


def test_leiaute_novo_de_2026_10_cabecalho_snake_case_data_br_e_sim_nao():
    """O arquivo de 2026-10 trocou o cabeçalho para snake_case, a data para dd/mm/aaaa e Respondida para Sim/Não; o mesmo parser lê os dois leiautes."""
    tel = "Operadoras de Telecomunicações (Telefonia, Internet, TV por assinatura)"
    cab = "regiao;uf;cidade;sexo;faixa_etaria;data_finalizacao;tempo_resposta;nome_fantasia;segmento_de_mercado;area;assunto;grupo_problema;problema;como_comprou_contratou;procurou_empresa;respondida;situacao;avaliacao_reclamacao;nota_do_consumidor"
    linhas = [f"SE;SP;Alfa do Norte;M;entre 41 a 50 anos;09/10/2026;4;Alfa Telecom;{tel};Telecomunicações;Internet Fixa;Cobrança;x;Internet;Não;Sim;Finalizada avaliada;Resolvida;5",
              f"SE;SP;Alfa do Norte;F;entre 31 a 40 anos;09/10/2026;;Alfa Telecom;{tel};Telecomunicações;Internet Fixa;Cobrança;x;Internet;Não;Não;Finalizada não avaliada;Não Avaliada;",
              f"SE;SP;Alfa do Norte;F;entre 31 a 40 anos;09/10/2026;6;Alfa Telecom;{tel};Telecomunicações;Internet Fixa;Cobrança;x;Internet;Não;Sim;Finalizada avaliada;Não Resolvida;2"]
    d = consumidor.agregar_csv(io.BytesIO(("﻿" + cab + "\r\n" + "\r\n".join(linhas) + "\r\n").encode("utf-8")))
    (c,) = d["cidades"]
    assert (c["n"], c["respondidas"], c["avaliadas"], c["resolvidas"], c["tempo_n"], c["tempo_soma"], c["nota_n"], c["nota_soma"]) == (3, 2, 2, 1, 2, 10, 2, 7)


def test_assuntos_e_grupos(fx):
    d = consumidor.agregar_csv(_csv(fx))
    assert {(x["marca"], x["assunto"]): x["n"] for x in d["assuntos"]}[("Alfa Telecom", "Internet Fixa")] == 6
    assert {(x["marca"], x["grupo"]): x["n"] for x in d["grupos"]}[("Alfa Telecom", "Cobrança / Contestação")] == 3


def test_segmento_telecom_nao_pega_aparelho_nem_saude():
    assert consumidor.segmento_telecom("Operadoras de Telecomunicações (Telefonia, Internet, TV por assinatura)")
    assert not consumidor.segmento_telecom("Produtos de Telefonia e Informática") and not consumidor.segmento_telecom("Operadoras de Planos de Saúde e Administradoras de Benefícios")


def test_leiaute_mudou_falha_alto():
    with pytest.raises(RuntimeError, match="leiaute mudou"):
        consumidor.agregar_csv(io.BytesIO("UF;Cidade\nSP;x\n".encode()))


ROBOTS = "User-agent: *\nDisallow: /pages/usuario/\nDisallow: /pages/reclamacao/\n"
LISTA = [{"nomeArquivo": "finalizadas_2026-09.zip", "codigo": "20261000000011035", "tamanhoArquivo": 757, "indicadorExclusaoLogica": False, "titulo": "Dados"},
         {"nomeArquivo": "finalizadas_2026-08.zip", "codigo": "20260900000010980", "tamanhoArquivo": 757, "indicadorExclusaoLogica": False},
         {"nomeArquivo": "usuarios_consolidados.csv", "codigo": "1", "tamanhoArquivo": 5}, {"nomeArquivo": "finalizadas_2026-07.zip", "codigo": "9", "tamanhoArquivo": 1, "indicadorExclusaoLogica": True}]


def _mock(fx, robots=ROBOTS):
    respx.get(f"{f.BASE}/robots.txt").mock(return_value=httpx.Response(200, text=robots))
    # o servidor real mistura codificações: o corpo da lista não é UTF-8 válido
    respx.get(f.URL_LISTA).mock(return_value=httpx.Response(200, content=json.dumps(LISTA).encode().replace(b"Dados", b"Dados \xe0s") + b"\n"))
    zip_bytes = fx("consumidor_gov", "finalizadas_sintetico.zip").read_bytes()
    return {c: respx.get(f.URL_DOWNLOAD.format(codigo=c)).mock(return_value=httpx.Response(200, content=zip_bytes)) for c in ("20261000000011035", "20260900000010980")}


@respx.mock
def test_run_incremental_so_baixa_o_que_mudou(fx, tmp_path, monkeypatch):
    monkeypatch.setattr(f, "MINIMO_TELECOM_POR_MES", 5)
    dl = _mock(fx)
    r = f.run("2026-11-06", tmp_path, _Log(), pausa=0)
    assert (r["meses"], r["baixados"], r["mes_inicial"], r["mes_final"]) == (2, 2, "2026-08", "2026-09") and all(m.call_count == 1 for m in dl.values())      # o excluído e o CSV avulso ficam fora
    doc = read_json_gz(tmp_path / "normalized" / "2026-11-06" / "summary" / "consumidor_gov.json.gz")
    assert doc["meses"]["2026-09"]["codigo"] == "20261000000011035" and doc["meses"]["2026-09"]["resumo"]["telecom"] == 9
    assert (tmp_path / "raw" / "2026-11-06" / "summary" / "consumidor_gov" / "finalizadas_2026-09.zip").exists()
    r2 = f.run("2026-11-13", tmp_path, _Log(), pausa=0)                     # semana seguinte: nada mudou na lista, nada é baixado
    assert r2["baixados"] == 0 and all(m.call_count == 1 for m in dl.values()) and r2["reclamacoes_telecom"] == r["reclamacoes_telecom"]
    LISTA[0]["codigo"] = "20261000000011999"                               # mês republicado: código novo, baixa de novo só ele
    try:
        respx.get(f.URL_LISTA).mock(return_value=httpx.Response(200, content=json.dumps(LISTA).encode()))
        dl2 = respx.get(f.URL_DOWNLOAD.format(codigo="20261000000011999")).mock(return_value=httpx.Response(200, content=fx("consumidor_gov", "finalizadas_sintetico.zip").read_bytes()))
        r3 = f.run("2026-11-20", tmp_path, _Log(), pausa=0)
        assert r3["baixados"] == 1 and dl2.call_count == 1
    finally:
        LISTA[0]["codigo"] = "20261000000011035"


def test_zip_sem_csv_ou_ilegivel_vira_mes_indisponivel_e_nao_derruba_a_coleta(tmp_path):
    """Em 2026-05 o zip trouxe um `.7z` e em 2026-06 usou Deflate64: a biblioteca padrão não lê, e o mês fica registrado como indisponível."""
    z7 = tmp_path / "finalizadas_2026-05.zip"
    with zipfile.ZipFile(z7, "w") as z:
        z.writestr("finalizadas_2026-05.7z", b"7z")
    agg, motivo = f.processar_zip(z7)
    assert agg is None and "não traz exatamente um CSV" in motivo
    ruim = tmp_path / "finalizadas_2026-06.zip"
    with zipfile.ZipFile(ruim, "w") as z:
        z.writestr("finalizadas_2026-06.csv", b"x")
    dados = bytearray(ruim.read_bytes())
    dados[8:10] = (9).to_bytes(2, "little")                      # método de compressão 9 = Deflate64, no cabeçalho local
    dados[dados.rfind(b"PK\x01\x02") + 10:dados.rfind(b"PK\x01\x02") + 12] = (9).to_bytes(2, "little")      # e no diretório central
    ruim.write_bytes(bytes(dados))
    agg, motivo = f.processar_zip(ruim)
    assert agg is None and "não é legível" in motivo


@respx.mock
def test_robots_que_proibe_a_publicacao_aborta_sem_baixar(fx, tmp_path):
    dl = _mock(fx, robots="User-agent: *\nDisallow: /pages/publicacao/\n")
    with pytest.raises(RuntimeError, match="robots.txt proíbe"):
        f.run("2026-11-06", tmp_path, _Log(), pausa=0)
    assert all(m.call_count == 0 for m in dl.values())


@respx.mock
def test_arquivo_truncado_falha_alto(fx, tmp_path):
    _mock(fx)
    with pytest.raises(RuntimeError, match="truncado"):
        f.run("2026-11-06", tmp_path, _Log(), pausa=0)                      # a amostra tem 9 reclamações de telecom, abaixo do mínimo real
