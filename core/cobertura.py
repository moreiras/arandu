# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Matriz de cobertura API × MCP × UI: cada rota de dados da API tem de existir, ou ter justificativa, no MCP e na interface.

  * **API:** as rotas GET do OpenAPI (as `deprecated` são alias e entram pelas rotas que as substituem);
  * **MCP:** a tool que atende a rota — das capacidades declaradas (`serve/capabilities/<entidade>.yaml`) ou das rotas escritas à mão
    (`serve/capabilities/_manuais.yaml`); `query:<collection>` quando a cobertura é a consulta genérica;
  * **UI:** detectada no código do frontend (a rota aparece em `frontend/src`), ou justificada (`sem_ui`).

Lacuna sem justificativa falha o CI (`tests/unit/test_cobertura.py`). Justificativa que começa por `pendente:` marca uma lacuna
ainda a resolver: a matriz a lista à parte. Sem FastAPI nem MCP: quem chama passa o que leu do OpenAPI, do MCP e do frontend.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

import yaml

from core.capacidades import PASTA, RAIZ, carregar_todas

PENDENTE = re.compile(r"^(pendente|\d+\.\d+\.\d+):")      # o prefixo numérico (`1.4.6:`) segue aceito como alias


@dataclass(frozen=True)
class Linha:
    rota: str                       # "GET /asns/{asn}"
    mcp: Optional[str]              # tool (ou "query:<collection>")
    sem_mcp: Optional[str]
    ui: bool
    sem_ui: Optional[str]
    declarada: bool                 # veio de uma capacidade declarada (gerada) e não de uma rota escrita à mão

    @property
    def lacunas(self) -> list[str]:
        """Camadas ausentes sem justificativa."""
        out = []
        if not self.mcp and not self.sem_mcp:
            out.append("mcp")
        if not self.ui and not self.sem_ui:
            out.append("ui")
        return out

    @property
    def pendente(self) -> bool:
        return any(j and PENDENTE.match(j) for j in (self.sem_mcp, self.sem_ui))


def carregar_manuais(arquivo: Optional[Path] = None) -> dict[str, dict]:
    arquivo = arquivo or PASTA / "_manuais.yaml"
    brutos = yaml.safe_load(arquivo.read_text(encoding="utf-8")) or []
    out: dict[str, dict] = {}
    for b in brutos:
        if b["http"] in out:
            raise ValueError(f"{arquivo.name}: '{b['http']}' repetida")
        if bool(b.get("mcp")) == bool(b.get("sem_mcp")):
            raise ValueError(f"{arquivo.name}: '{b['http']}' precisa de exatamente um entre 'mcp' e 'sem_mcp'")
        out[b["http"]] = b
    return out


def codigo_do_frontend(raiz: Optional[Path] = None) -> str:
    """Texto de todo o código do frontend que chama a API (sem testes nem tipos gerados)."""
    raiz = raiz or RAIZ / "frontend" / "src"
    partes = []
    for f in sorted(raiz.rglob("*.ts*")):
        if "openapi.gen" in f.name or ".test." in f.name or "/test/" in str(f):
            continue
        partes.append(f.read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(partes)


def ui_usa(caminho: str, codigo: str) -> bool:
    """O código do frontend chama `/api/v1<caminho>` (parâmetros `{x}` casam `${...}`)."""
    rx = re.escape("/api/v1" + caminho)
    rx = re.sub(r"\\\{[^}]+\\\}", r"(?:\\$\\{[^}]+\\}|[^/'\"`?]+)", rx)
    return re.search(rx + r"(?![\w/-])", codigo) is not None


def montar(operacoes: Iterable[tuple[str, str, bool]], codigo_ui: str, manuais: Optional[dict] = None) -> tuple[list[Linha], list[str]]:
    """(linhas da matriz, erros de consistência). `operacoes` = (método, caminho sem /api/v1, deprecated)."""
    manuais = carregar_manuais() if manuais is None else manuais
    declaradas = {f"{o.metodo} {o.caminho}": o for c in carregar_todas() for o in c.operacoes}
    linhas: list[Linha] = []
    erros: list[str] = []
    vistas = set()
    for metodo, caminho, deprecated in sorted(operacoes):
        if metodo != "GET" or deprecated:
            continue
        rota = f"{metodo} {caminho}"
        vistas.add(rota)
        if rota in declaradas:
            o = declaradas[rota]
            mcp = f"{o.mcp.tool}" if o.mcp else None
            linhas.append(Linha(rota, mcp, o.sem_mcp, ui_usa(caminho, codigo_ui), o.sem_ui, True))
            continue
        m = manuais.get(rota)
        if m is None:
            erros.append(f"{rota}: rota sem decisão — declare a capacidade ou acrescente a '_manuais.yaml' (mcp: ou sem_mcp:)")
            continue
        linhas.append(Linha(rota, m.get("mcp"), m.get("sem_mcp"), ui_usa(caminho, codigo_ui), m.get("sem_ui"), False))
    for l in linhas:
        if l.ui and l.sem_ui:
            erros.append(f"{l.rota}: 'sem_ui' obsoleto — a interface já consome a rota")
    for rota in sorted(set(manuais) - vistas):
        erros.append(f"{rota}: está em '_manuais.yaml' mas não é uma rota GET (não deprecated) da API")
    return linhas, erros


def validar_tools(linhas: list[Linha], tools: set[str], colecoes: set[str]) -> list[str]:
    """A tool citada tem de existir no MCP; `query:<x>` exige a collection x."""
    erros = []
    for l in linhas:
        if not l.mcp:
            continue
        if l.mcp.startswith("query:"):
            if l.mcp.split(":", 1)[1] not in colecoes:
                erros.append(f"{l.rota}: collection '{l.mcp}' não existe em api/query.py")
        elif l.mcp not in tools:
            erros.append(f"{l.rota}: tool '{l.mcp}' não existe no MCP")
    return erros


def resumo(linhas: list[Linha]) -> dict:
    n = len(linhas)
    return {
        "rotas": n, "com_mcp": sum(1 for l in linhas if l.mcp), "com_ui": sum(1 for l in linhas if l.ui),
        "geradas": sum(1 for l in linhas if l.declarada), "pendentes": sum(1 for l in linhas if l.pendente),
        "lacunas_sem_justificativa": sum(1 for l in linhas if l.lacunas),
    }


def para_markdown(linhas: list[Linha], tools_geradas: int, tools_total: int) -> str:
    r = resumo(linhas)
    sim = lambda b: "✔" if b else "—"          # noqa: E731
    out = [
        "# Cobertura API × MCP × interface",
        "",
        "Gerado por `python3 scripts/gen_cobertura.py` a partir do OpenAPI, do MCP, do frontend e de `serve/capabilities/`.",
        "Não edite à mão. Rota nova precisa de uma entrada em `serve/capabilities/_manuais.yaml` (ou de uma capacidade declarada); lacuna",
        "sem justificativa falha o CI. Alias `deprecated` ficam de fora: valem pelas rotas que os substituem.",
        "",
        f"- Rotas de dados (GET, não deprecated): **{r['rotas']}**; com tool no MCP: **{r['com_mcp']}**; consumidas pela interface: **{r['com_ui']}**.",
        f"- Pendências marcadas (`pendente:`): **{r['pendentes']}**; lacunas sem justificativa: **{r['lacunas_sem_justificativa']}**.",
        f"- Tools do MCP geradas de capacidade declarada: **{tools_geradas}** de {tools_total}.",
        "",
        "| Rota | MCP | UI | Observação |",
        "|---|---|---|---|",
    ]
    for l in linhas:
        obs = "; ".join(x for x in (f"MCP: {l.sem_mcp}" if l.sem_mcp else "", f"UI: {l.sem_ui}" if l.sem_ui else "") if x)
        out.append(f"| `{l.rota}` | {('`' + l.mcp + '`') if l.mcp else '—'} | {sim(l.ui)} | {obs} |")
    return "\n".join(out) + "\n"
