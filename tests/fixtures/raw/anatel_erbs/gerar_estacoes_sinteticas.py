# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Gera `estacoes_smp_sintetico.zip`: 12 estações inventadas no layout do `estacoes_smp.zip` da Anatel (41 colunas, UTF-8 com BOM, `;`).

Reproduz o que se mediu no arquivo real: várias linhas por estação (setores × tecnologias × faixas) e cada registro repetido 3 vezes, com o código IBGE só em uma das cópias.
Casos plantados: estação de 4 operadoras; CNPJ em branco em parte das linhas; posição que varia entre linhas; fora do Brasil; sem posição; só 2G; 5G SA e NSA.
Uso: python tests/fixtures/raw/anatel_erbs/gerar_estacoes_sinteticas.py
"""
import csv
import io
import zipfile
from pathlib import Path

COLS = ["Número Fistel", "Número Estação", "NumCnpjCpf", "NumServico", "Frequência (MHz)", "Banda_MHZ", "Frequência Inicial", "Frequência Final", "FreqTxMHz", "FreqRxMHz",
        "Designação Emissão", "Número Ato", "Data Validade", "Entidade", "NumSetor", "Tecnologia", "Tipo de Tecnologia 5G", "Latitude", "Longitude", "Latitude decimal",
        "Longitude decimal", "EnderecoEstacao", "EndBairro", "EndNumero", "EndComplemento", "Cep", "ClassInfraFisica", "Data Primeiro Licenciamento", "Data Licenciamento",
        "AnoMesLic", "Situacao", "Caráter", "Empresa Estação", "Faixa Estação", "Subfaixa Estação", "Geração", "Código Nacional", "Código IBGE", "Município-UF", "UF", "Nome da UF"]
GER = {"GSM": "2G", "WCDMA": "3G", "LTE": "4G", "NR": "5G"}
OPER = {"VIVO": ("02558157000162", "TELEFONICA BRASIL S.A."), "CLARO": ("40432544000147", "CLARO S.A."), "TIM": ("02421421000111", "TIM S A"), "BRISANET": ("00000000000191", "BRISANET SERVICOS DE TELECOMUNICACOES S.A")}
# (fistel, estação, marca, ibge, uf, lat, lon, [(tecnologia, tipo5g, faixa, setor)], infra, ano)
E = [
    ("50000000001", "1001", "VIVO", "3550308", "SP", -23.55, -46.63, [("GSM", "", "1800", "1"), ("LTE", "", "1800", "1"), ("LTE", "", "2500", "2"), ("WCDMA", "", "2100", "3")], "Rooftop", 2003),
    ("50000000001", "1002", "VIVO", "3550308", "SP", -23.56, -46.65, [("LTE", "", "700", "1"), ("NR", "SA-NSA", "3500", "1"), ("NR", "SA-NSA", "3500", "2")], "Greenfield", 2022),
    ("50000000002", "2001", "CLARO", "3304557", "RJ", -22.9, -43.2, [("GSM", "", "850", "1"), ("LTE", "", "1800", "2")], "Greenfield", 2010),
    ("50000000002", "2002", "CLARO", "3304557", "RJ", -22.95, -43.18, [("NR", "NSA", "3500", "1")], "Indoor", 2024),
    ("50000000003", "3001", "TIM", "3106200", "MG", -19.92, -43.94, [("LTE", "", "1800", "1"), ("WCDMA", "", "2100", "1")], "Rooftop", 2012),
    ("50000000003", "3002", "TIM", "3106200", "MG", -19.93, -43.95, [("GSM", "", "850", "")], "", 1999),                      # só 2G, sem setor
    ("50000000004", "4001", "BRISANET", "2304400", "CE", -3.73, -38.52, [("LTE", "", "2500", "1"), ("NR", "SA", "3500", "1")], "Greenfield", 2021),
    ("50000000004", "4002", "BRISANET", "2304400", "CE", -3.74, -38.53, [("LTE", "", "2500", "1")], "Greenfield", 2021),
    ("50000000005", "5001", "VIVO", "5300108", "DF", None, None, [("LTE", "", "1800", "1")], "Rooftop", 2015),                 # sem posição
    ("50000000005", "5002", "CLARO", "5300108", "DF", 40.0, 10.0, [("LTE", "", "1800", "1")], "Rooftop", 2015),                # fora do Brasil
    ("50000000005", "5003", "TIM", "4106902", "PR", "VAR", None, [("LTE", "", "1800", "1")], "Rooftop", 2016),                 # posição varia entre linhas
    ("50000000005", "5004", "VIVO", None, "AM", -3.1, -60.02, [("LTE", "", "700", "1")], "Greenfield", 2018),                  # nenhuma linha com IBGE
]


def linhas():
    for fistel, num, marca, ibge, uf, lat, lon, comb, infra, ano in E:
        cnpj, entidade = OPER[marca]
        for k, (tec, t5, faixa, setor) in enumerate(comb):
            for copia in range(3):                                    # junção: 3 cópias, o IBGE só na primeira
                la, lo = (lat, lon)
                if lat == "VAR":
                    la, lo = (-25.43, -49.27) if (k + copia) % 2 == 0 else (-25.44, -49.28)
                r = dict.fromkeys(COLS, "")
                r.update({"Número Fistel": fistel, "Número Estação": num, "NumCnpjCpf": cnpj if copia == 0 and k % 2 == 0 else "", "NumServico": "010", "FreqTxMHz": faixa, "Entidade": entidade,
                          "NumSetor": setor, "Tecnologia": tec, "Tipo de Tecnologia 5G": t5, "Latitude decimal": "" if la is None else str(la), "Longitude decimal": "" if lo is None else str(lo),
                          "ClassInfraFisica": infra, "Data Primeiro Licenciamento": f"01/06/{ano}", "Situacao": "Licenciada", "Empresa Estação": marca, "Faixa Estação": faixa,
                          "Geração": GER[tec], "UF": uf if (copia == 0 and ibge) else "", "Código IBGE": ibge if (copia == 0 and ibge) else ""})
                yield r


def main():
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLS, delimiter=";", lineterminator="\r\n")
    w.writeheader()
    w.writerows(linhas())
    destino = Path(__file__).with_name("estacoes_smp_sintetico.zip")
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(zipfile.ZipInfo("Estacoes_SMP.csv", (2026, 11, 1, 0, 0, 0)), "﻿" + buf.getvalue())
    print(destino, destino.stat().st_size)


if __name__ == "__main__":
    main()
