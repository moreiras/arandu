# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Tabela por ASN das páginas de país do APNIC Labs: `stats.labs.apnic.net/rpki/BR` (I-RoV) e `/dnssec/BR` (validação de DNSSEC).

O JSON por ASN existe, mas pesa 0,8 MB (ROV) e 4 MB (DNSSEC) por chamada, o que daria dezenas de GB por semana para ~9 mil ASNs. A página do país
embute **todos os ASNs** numa tabela (1,3 a 1,5 MB no total). Conferido em 2026-10-31 contra o JSON por ASN: valores e contagem de amostras idênticos
(10 ASNs de ROV e 5 de DNSSEC). O cabeçalho das colunas é conferido a cada leitura: layout diferente falha alto, não grava lixo.

Significado (cabeçalho da própria página): "RPKI Validates" = % das medições em que a rede NÃO alcançou o destino de rota RPKI-inválida (campo
`filter_rate` do JSON); "DNSSEC Validates" e "Partial Validation" = % de clientes que validam total ou parcialmente. Alto = valida. Janela das páginas
(padrão): ROV 7 dias, DNSSEC 1 dia; `amostras` é o tamanho da amostra daquela janela.
"""
from __future__ import annotations

import re

COLUNAS = {
    "rpki": ["ASN", "AS Name", "RPKI Validates", "Samples"],
    "dnssec": ["ASN", "AS Name", "DNSSEC Validates", "Partial Validation", "Samples"],
}
_LINHA = re.compile(r'\["<a href=\\"/(?P<tipo>\w+)/AS(?P<asn>\d+)\?[^"]*\\">AS\d+</a>","(?P<nome>[^"]*)",(?P<valores>.*?),(?P<amostras>\d+)\]')
_VALOR = re.compile(r"\{v: ([\d.]+), f: ?'[^']*'\}")


class LayoutMudou(RuntimeError):
    pass


def _bloco_da_tabela(html: str) -> tuple[str, list[str]]:
    i = html.find("['ASN'")
    if i < 0:
        raise LayoutMudou("tabela por ASN não encontrada na página")
    fim = html.find("]);", i)
    bloco = html[i:fim]
    cabecalho = [c.strip().strip("'") for c in re.match(r"\[([^\]]*)\]", bloco).group(1).split(",")]
    return bloco, cabecalho


def parse_tabela(html: str, tipo: str) -> dict:
    """{asn: {valores: [pct…], amostras}} e o contador de linhas sem valor (ASN visto sem medição suficiente)."""
    bloco, cabecalho = _bloco_da_tabela(html)
    if cabecalho != COLUNAS[tipo]:
        raise LayoutMudou(f"cabeçalho {cabecalho} diferente do esperado {COLUNAS[tipo]}")
    esperados = len(COLUNAS[tipo]) - 3
    asns: dict[int, dict] = {}
    sem_valor = 0
    for m in _LINHA.finditer(bloco):
        if m.group("tipo") != tipo:
            raise LayoutMudou(f"link {m.group('tipo')} dentro da tabela de {tipo}")
        valores = [float(v) for v in _VALOR.findall(m.group("valores"))]
        if len(valores) != esperados:
            sem_valor += 1                                   # valor vazio ("") na página
            continue
        asns[int(m.group("asn"))] = {"valores": valores, "amostras": int(m.group("amostras"))}
    linhas = bloco.count('["<a href')
    if not asns or linhas != len(asns) + sem_valor:
        raise LayoutMudou(f"{linhas} linhas na tabela, {len(asns)} lidas e {sem_valor} sem valor")
    return {"asns": asns, "sem_valor": sem_valor}


def ultima_data_da_serie(html: str) -> str | None:
    """Última data da série do país (primeiro gráfico da página): data a que a janela se refere."""
    i = html.find("arrayToDataTable")
    fim = html.find("]);", i)
    datas = re.findall(r"new Date\('(\d{4}-\d{2}-\d{2})'\)", html[i:fim])
    return datas[-1] if datas else None
