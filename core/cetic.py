# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Tabelas oficiais das pesquisas TIC do Cetic.br|NIC.br: descoberta do arquivo, leitura e formato longo.

Não há API nem URL estável: a página `cetic.br/pt/pesquisa/<pesquisa>/microdados/` lista os arquivos da edição vigente com links diretos
`cetic.br/media/microdados/<id>/<nome>_v1.0.zip`, em que o `<id>` muda por arquivo e o nome é previsível. Cada ZIP de tabelas traz quatro planilhas com a
mesma forma (uma aba por indicador): `proporcao` (%), `margem_de_erro` (pontos percentuais da proporção), `total` (unidades) e `margem_de_erro_total`.
Cada aba: linha 0 título ("A1 - DOMICÍLIOS COM COMPUTADOR¹"), linha 1 universo, linhas 2 e 3 cabeçalho (item da pergunta e resposta), depois as linhas de dados
(`dimensão`, `recorte`, valores) e, por fim, notas e fonte. As quatro planilhas são cruzadas por posição.
"""
from __future__ import annotations

import hashlib
import io
import re
import time
import zipfile
from pathlib import Path
from typing import Callable, Optional

import httpx

from core.common import normalized_path, now_iso, raw_path, write_json_gz
from core.xlsx_leve import ler_xlsx
from core.site import USER_AGENT

PAGINA = "https://cetic.br/pt/pesquisa/{pesquisa}/microdados/"
LICENCA = "CC BY 4.0"
HEADERS = {"User-Agent": USER_AGENT}
PAUSA_S = 2.0                                      # entre requisições: o site já limitou conexões; são 3 por execução
TENTATIVAS = 3
PLANILHAS = ("proporcao", "margem_de_erro", "total", "margem_de_erro_total")
_SEM_VALOR = {"", "-", "..", "..."}


def descobrir(html: str, prefixo: str, sufixo: str = r"[a-z_]*?xlsx_v[\d.]+\.zip") -> tuple[str, int, str]:
    """(url, ano da edição, nome do arquivo) do arquivo da edição mais recente listada na página: `<prefixo>_AAAA_<sufixo>` (por padrão, o ZIP de tabelas XLSX)."""
    achados = re.findall(rf'href="(https://cetic\.br/media/microdados/\d+/({re.escape(prefixo)}_(\d{{4}})_{sufixo}))"', html)
    if not achados:
        raise RuntimeError(f"cetic: nenhum arquivo '{prefixo}_AAAA_...' na página (o padrão do nome mudou?)")
    url, nome, ano = max(achados, key=lambda a: (a[2], a[1]))
    return url, int(ano), nome


def _numero(v: Optional[str]) -> Optional[float]:
    if v is None or v.strip() in _SEM_VALOR:
        return None
    try:
        return float(v)
    except ValueError:
        return None


def _limpa(v: Optional[str]) -> str:
    return re.sub(r"[¹²³⁰-⁹]+$", "", (v or "").strip()).strip()


def planilhas(zip_bytes: bytes) -> dict[str, dict]:
    """{proporcao|margem_de_erro|total|margem_de_erro_total: abas} do ZIP; falha se faltar alguma das quatro."""
    z = zipfile.ZipFile(io.BytesIO(zip_bytes))
    out: dict[str, dict] = {}
    for nome in z.namelist():
        for p in sorted(PLANILHAS, key=len, reverse=True):          # `margem_de_erro_total` antes de `margem_de_erro`
            if nome.endswith(f"tabela_{p}_v1.0.xlsx") or re.search(rf"tabela_{p}_v[\d.]+\.xlsx$", nome):
                out.setdefault(p, ler_xlsx(z.read(nome)))
                break
    faltam = [p for p in PLANILHAS if p not in out]
    if faltam:
        raise RuntimeError(f"cetic: o ZIP não traz as planilhas {faltam}")
    return out


def _cabecalho(aba: list[list]) -> tuple[list[tuple[str, str]], int]:
    """([(item, resposta) por coluna de dados a partir da 3ª], índice da primeira linha de dados)."""
    nivel1, nivel2 = aba[2], aba[3]
    itens, ultimo = [], ""
    for j in range(2, max(len(nivel1), len(nivel2))):
        a = _limpa(nivel1[j] if j < len(nivel1) else None)
        b = _limpa(nivel2[j] if j < len(nivel2) else None)
        ultimo = a or ultimo
        itens.append(("" if ultimo == b else ultimo, b))
    inicio = next(i for i in range(4, len(aba)) if aba[i] and aba[i][0] == "TOTAL")
    return itens, inicio


def normalizar(zip_bytes: bytes, minimo_tabelas: int) -> tuple[dict, list[dict]]:
    """({tabela: {titulo, universo, notas}}, linhas longas). Cada linha: tabela, dimensao, recorte, item, resposta, proporcao, margem_proporcao, total,
    margem_total (`None` onde a planilha não traz valor, nunca zero inventado)."""
    pl = planilhas(zip_bytes)
    base = pl["proporcao"]
    if len(base) < minimo_tabelas:
        raise RuntimeError(f"cetic: só {len(base)} tabelas (esperado ≥ {minimo_tabelas})")
    tabelas: dict[str, dict] = {}
    linhas: list[dict] = []
    for aba, dados in base.items():
        for p in PLANILHAS:
            if aba not in pl[p]:
                raise RuntimeError(f"cetic: a aba {aba} não existe na planilha {p}")
        titulo = _limpa(dados[0][0])
        codigo, _, nome = titulo.partition(" - ")
        itens, inicio = _cabecalho(dados)
        fim = inicio
        while fim < len(dados) and len(dados[fim]) > 1 and dados[fim][1]:
            fim += 1
        notas = [_limpa(r[0]) if r else "" for r in dados[fim:]]
        tabelas[aba] = {"codigo": codigo.strip(), "titulo": (nome.strip() or titulo).capitalize(), "universo": _limpa(dados[1][0] if len(dados) > 1 else ""),
                        "notas": [n for n in notas if n]}
        for i in range(inicio, fim):
            for j, (item, resposta) in enumerate(itens, start=2):
                if not resposta:
                    continue
                vals = {}
                for p, campo in (("proporcao", "proporcao"), ("margem_de_erro", "margem_proporcao"), ("total", "total"), ("margem_de_erro_total", "margem_total")):
                    linha = pl[p][aba][i] if i < len(pl[p][aba]) else []
                    if len(pl[p][aba][i]) > 1 and (_limpa(linha[1]) != _limpa(dados[i][1])):
                        raise RuntimeError(f"cetic: a aba {aba} difere entre planilhas na linha {i}")
                    vals[campo] = _numero(linha[j]) if j < len(linha) else None
                if all(v is None for v in vals.values()):
                    continue
                linhas.append({"tabela": aba, "dimensao": _limpa(dados[i][0]).capitalize(),
                               "recorte": _limpa(dados[i][1]), "item": item, "resposta": resposta,
                               "proporcao": vals["proporcao"], "margem_proporcao": vals["margem_proporcao"],
                               "total": vals["total"], "margem_total": vals["margem_total"]})
    return tabelas, linhas


def _get(client: httpx.Client, url: str, dormir: Callable[[float], None]) -> httpx.Response:
    ultimo: Optional[Exception] = None
    for t in range(TENTATIVAS):
        try:
            r = client.get(url)
            r.raise_for_status()
            return r
        except httpx.HTTPError as e:
            ultimo = e
            dormir(PAUSA_S * 5 * (t + 1))
    raise RuntimeError(f"cetic {url}: {ultimo}")


def run_pesquisa(pesquisa: str, prefixo: str, saida: str, rotulo: str, minimo_tabelas: int, date_str: str, base: Path, log,
                 client: Optional[httpx.Client] = None, dormir: Callable[[float], None] = time.sleep) -> dict:
    """Descobre a edição vigente na página da pesquisa, baixa o ZIP de tabelas (bruto, byte a byte), normaliza e grava `summary/{saida}.json.gz`."""
    proprio = client is None
    client = client or httpx.Client(timeout=120, follow_redirects=True, headers=HEADERS)
    try:
        pagina = PAGINA.format(pesquisa=pesquisa)
        url, ano, nome = descobrir(_get(client, pagina, dormir).text, prefixo)
        dormir(PAUSA_S)
        conteudo = _get(client, url, dormir).content
    finally:
        if proprio:
            client.close()
    tabelas, linhas = normalizar(conteudo, minimo_tabelas)
    bruto = raw_path(base, date_str, "summary")
    bruto.mkdir(parents=True, exist_ok=True)
    (bruto / nome).write_bytes(conteudo)
    destino = normalized_path(base, date_str, "summary")
    destino.mkdir(parents=True, exist_ok=True)
    write_json_gz(destino / f"{saida}.json.gz", {
        "snapshot_date": date_str, "generated_at": now_iso(), "pesquisa": rotulo, "edicao": ano, "fonte": f"Cetic.br|NIC.br, {rotulo} {ano} (tabelas)",
        "licenca": LICENCA, "pagina": pagina, "url": url, "arquivo": nome, "sha256": hashlib.sha256(conteudo).hexdigest(),
        "total_tabelas": len(tabelas), "total_linhas": len(linhas), "tabelas": tabelas, "linhas": linhas})
    log.info("cetic written", pesquisa=rotulo, edicao=ano, tabelas=len(tabelas), linhas=len(linhas))
    return {"edicao": ano, "tabelas": len(tabelas), "linhas": len(linhas)}
