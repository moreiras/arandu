# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Qualidade (RQUAL) e reclamações da Anatel no dataset sintético.

O CSV sintético é lido pelo parser real (`core.rqual`, `core.reclamacoes`): o leiaute é o do arquivo da Anatel e o normalizado sai igual ao de produção. As marcas ALFA, BETA e GAMA são ligadas às
operadoras do mundo sintético pela tabela curada `tests/synth/curada_marcas_sintetica.yaml` (os testes de produto trocam `core.marcas.CAMINHO_CURADA` por ela).
"""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

from core import reclamacoes as rc
from core import rqual as rq
from tests.synth.market import MUN
from tests.synth.world import World

CURADA = Path(__file__).with_name("curada_marcas_sintetica.yaml")
_CAB_RQUAL = ("Ano;Mês;Serviço;Indicador;Descrição;Tipo;Grupo;Código IBGE;Município;UF;Prestadora;Resultado;Unidade de Medida;Número de Coletores;Número de Medidas;Erro Amostral;Estatística;"
              "Limite Inferior;Limite Superior;Valor de Referência Superior;Valor de Referência Inferior")
_CAB_RECL = "DataExtracao;SOLICITAÇÕES;Ano;Mês;AnoMês;UF;Cidade;CO_MUNICIPIO;CanalEntrada;Condição;TipoAtendimento;Serviço;Marca;Assunto;Problema"


def _rq(mes, serv, cod, desc, tipo, ibge, prest, res, un, med="", ref=("", "")):
    m = MUN[ibge]
    return ";".join(str(x) for x in (2026, f"{mes:02d}", serv, cod, desc, tipo, "Redes", ibge, m[1], m[2], prest, res, un, 50 if med else "", med, "4,0000" if med else "", "SIM" if med else "NÃO", "", "", ref[0], ref[1]))


def rqual(world: World, d: str) -> dict:
    """ALFA e BETA na banda larga fixa (BETA sem medidas informadas), GAMA na telefonia móvel; 3 municípios, 2 meses, NA e NO plantados."""
    ind4 = ("Banda Larga Fixa", "IND4", "Cumprimento de velocidade de download e upload", "Indicador IQS")
    linhas = []
    for mes in (7, 8):
        for ibge_, prest, res, med in (("9900007", "ALFA", 80.0 + 5 * (mes - 7), 400), ("9900004", "ALFA", 60.0 + 5 * (mes - 7), 120), ("9900005", "BETA", 90.0, "")):
            linhas.append(_rq(mes, *ind4, ibge_, prest, f"{res:.4f}".replace(".", ","), "%", med, ("90%", "60%")))
        linhas.append(_rq(mes, "Telefonia Móvel", "IND2", "Queda de chamadas", "Indicador IQS", "9900007", "GAMA", "0,8000", "%", "", ("2%", "4%")))
    linhas.append(_rq(8, "Banda Larga Fixa", "INF4-DL", "Velocidade de download", "Informativo", "9900004", "ALFA", "NA", "Mbps"))
    linhas.append(_rq(8, "Telefonia Fixa", "IND8", "Disponibilidade", "Indicador IQS", "9900004", "BETA", "NO", "%", "", ("100%", "98%")))
    doc = rq.consolidar(io.BytesIO(("﻿" + _CAB_RQUAL + "\n" + "\n".join(linhas) + "\n").encode("utf-8")))
    return {"snapshot_date": d, "generated_at": "2026-01-01T00:00:00+00:00", "fonte": "sintético", "url": "", "data_arquivo": "Fri, 06 Nov 2026 11:04:10 GMT", "sha256": "0" * 64, **doc}


def _rc(ext, q, ano, mes, ibge_, canal, tipo, serv, marca, assunto):
    m = MUN[ibge_]
    return ";".join(str(x) for x in (ext, q, ano, mes, f"{ano}-{mes:02d}", m[2], m[1], ibge_, canal, "Nova", tipo, serv, marca, assunto, "x"))


def reclamacoes(world: World, d: str) -> dict:
    """ALFA (curada, SCM e SMP) e BETA (curada), SEMASN1 (automática: concentrada na UF da outorga), SEMASN2 (nome fantasia único, mas as reclamações caem em outra UF: descartada), SEM DONO (sem CNPJ),
    OUTROS e NÃO LOCALIZEI A MINHA EMPRESA. O legado cobre 2018-2019 (mais uma linha de 2024-03 que se sobrepõe ao contexto e é descartada); o contexto vai de 2024-03 a 2026-09, extraído em 2026-10-05."""
    ctx = []
    for ano, mes in ((2024, 3), (2024, 9), (2025, 3), (2025, 11), (2026, 3), (2026, 6), (2026, 9)):
        k = ano - 2023
        e = "2026-10-05"
        ctx += [_rc(e, 10 * k, ano, mes, "9900007", "Call center", "Reclamação", "SCM", "ALFA", "Cobrança"),
                _rc(e, 4 * k, ano, mes, "9900007", "Mobile app", "Reclamação", "SMP_Pós", "ALFA", "Qualidade, funcionamento e reparo"),
                _rc(e, 3 * k, ano, mes, "9900004", "Usuário web", "Reclamação", "SCM", "ALFA", "Cobrança"),
                _rc(e, 2 * k, ano, mes, "9900005", "Usuário web", "Reclamação", "SCM", "BETA", "Cobrança"),
                _rc(e, 2 * k, ano, mes, "9900004", "Call center", "Reclamação", "SCM", "SEMASN1", "Instalação ou ativação ou habilitação"),
                _rc(e, 2 * k, ano, mes, "9900007", "Call center", "Reclamação", "SCM", "SEMASN2", "Cobrança"),
                _rc(e, k, ano, mes, "9900005", "Call center", "Reclamação", "SCM", "SEM DONO", "Cobrança"),
                _rc(e, 5 * k, ano, mes, "9900007", "Call center", "Reclamação", "SCM", "NÃO LOCALIZEI A MINHA EMPRESA", "Outros"),
                _rc(e, k, ano, mes, "9900007", "Call center", "Pedido de informação", "SCM", "ALFA", "Informação")]
    leg = [_rc("2018-04-23", 6, 2018, 5, "9900007", "Fale Conosco", "Reclamação", "SCM", "ALFA", "Outro assunto"), _rc("2018-04-23", 3, 2019, 7, "9900004", "Fale Conosco", "Reclamação", "SCM", "ALFA", "Outro assunto"),
           _rc("2018-04-23", 50, 2024, 3, "9900007", "Fale Conosco", "Reclamação", "SCM", "ALFA", "Sobreposto")]
    ctx = [x + f";{i + 1}" for i, x in enumerate(ctx)]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("reclamacoes_contexto.csv", "﻿" + _CAB_RECL + ";Linha\n" + "\n".join(ctx) + "\n")
        z.writestr("reclamacoes.csv", "﻿" + _CAB_RECL + "\n" + "\n".join(leg) + "\n")
    with zipfile.ZipFile(buf) as z:
        doc = rc.consolidar_zip(lambda n: io.BytesIO(z.read(n)))
    return {"snapshot_date": d, "generated_at": "2026-01-01T00:00:00+00:00", "fonte": "sintético", "url": "", "data_arquivo": "Tue, 13 Oct 2026 10:42:29 GMT", "sha256": "0" * 64, **doc}
