# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Capacidades declaradas: o que uma entidade oferece, escrito uma vez em `serve/capabilities/<entidade>.yaml`.

A declaração é dado puro (sem FastAPI nem MCP): este módulo a carrega, valida e entrega estruturas imutáveis. Quem gera as rotas REST é
`api/capacidades.py`; quem gera as tools do MCP é `mcp_server/capacidades.py`; a matriz API × MCP × UI vem de `core/cobertura.py`. Rotas e
tools escritas à mão continuam permitidas (mapas, Hilbert): entram na matriz por `serve/capabilities/_manuais.yaml`.

Vocabulário (o que a declaração pode pedir, em `FILTROS` e `TIPOS_OPERACAO`) fica aqui, em código, para a validação apontar o erro na
hora de carregar, não no primeiro acesso à rota.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

import yaml

from core.outorgas import SERVICOS as _SERVICOS_OUTORGA

RAIZ = Path(__file__).resolve().parents[1]
PASTA = RAIZ / "serve" / "capabilities"

TIPOS_OPERACAO = ("lista_outorgas", "stats_outorgas", "por_cnpj")


@dataclass(frozen=True)
class FiltroModelo:
    """Um filtro do vocabulário: como vira parâmetro de consulta e como se aplica a uma lista de registros."""
    tipo: str                    # igual | substring | busca | tem_asn | ativo | minimo
    campo: Optional[str]         # campo do registro (None para `busca` e `tem_asn`, que têm campos fixos)
    descricao: str               # `{plural}` é trocado pelo plural da entidade


FILTROS: dict[str, FiltroModelo] = {
    "uf": FiltroModelo("igual", "uf", "Filtrar por UF (ex: SP, RJ)."),
    "municipio": FiltroModelo("substring", "municipio", "Filtrar por município (substring)."),
    "q": FiltroModelo("busca", None, "Busca por razão social, nome fantasia ou CNPJ."),
    "com_asn": FiltroModelo("tem_asn", "asns", "Se true, retorna apenas {plural} com ASN identificado."),
    "situacao": FiltroModelo("igual", "situacao", "Filtrar por situação (ex: ATI, EXT)."),
    "ativo": FiltroModelo("ativo", "sici_ativo", "True = só operadoras que declaram acessos ao SICI."),
    "min_acessos": FiltroModelo("minimo", "sici_acessos", "Mínimo de acessos declarados (SICI)."),
}

STATS_BLOCOS = ("top_municipios", "cobertura_asn", "rede_virtual")


class CapacidadeErro(ValueError):
    """Declaração inválida; a mensagem diz o arquivo e o campo."""


@dataclass(frozen=True)
class Filtro:
    nome: str
    modelo: FiltroModelo
    descricao: str

    @property
    def tipo(self) -> str:
        return self.modelo.tipo

    @property
    def campo(self) -> Optional[str]:
        return self.modelo.campo


@dataclass(frozen=True)
class McpTool:
    """Como a operação aparece no MCP: o nome da tool, o subconjunto dos filtros e o que difere da REST."""
    tool: str
    descricao: str                               # o docstring da tool (o MCP não tem descrição por argumento)
    filtros: tuple[str, ...] = ()
    limite_max: int = 500
    deduplicar_por_cnpj: bool = False            # a REST deduplica por CNPJ no SCM; a tool historicamente devolve todas as outorgas
    chave_resposta: str = "outorgas"             # nome da lista na resposta de `por_cnpj`


@dataclass(frozen=True)
class Operacao:
    id: str
    tipo: str
    http: str                                    # "GET /scms/{cnpj}"
    funcao: str                                  # nome da função da rota (vira o operationId do OpenAPI)
    summary: str
    descricao: str
    mcp: Optional[McpTool] = None                # a tool do MCP gerada desta operação (ou None)
    filtros: tuple[Filtro, ...] = ()
    ordena_por: tuple[str, ...] = ()
    paginacao: dict[str, str] = field(default_factory=dict)      # descrições de page/limit/sort_desc (omitidas = sem descrição)
    deduplicar_por_cnpj: bool = False
    blocos: tuple[str, ...] = ()                 # blocos extras do stats
    dica_ausente: str = ""                       # complemento da mensagem 404 "Dados de X não disponíveis…"
    sem_ui: Optional[str] = None                 # justificativa de a interface não consumir a operação (matriz)
    sem_mcp: Optional[str] = None                # idem para o MCP

    @property
    def metodo(self) -> str:
        return self.http.split(" ", 1)[0]

    @property
    def caminho(self) -> str:
        return self.http.split(" ", 1)[1]


@dataclass(frozen=True)
class Capacidade:
    entidade: str
    rotulo: str                                  # "STFC"
    plural: str                                  # "STFCs"
    nome_longo: str
    servico: str                                 # sigla em core.outorgas.SERVICOS (de onde vêm a lista, o arquivo e o mapa)
    tag: str
    operacoes: tuple[Operacao, ...]
    descricao_llm: str = ""
    colecao_query: Optional[str] = None
    privacidade: str = "sem_contatos"
    arquivo: str = ""

    def operacao(self, id_: str) -> Operacao:
        for o in self.operacoes:
            if o.id == id_:
                return o
        raise KeyError(id_)


def _obrigatorio(d: dict, chave: str, onde: str) -> Any:
    if chave not in d or d[chave] in (None, ""):
        raise CapacidadeErro(f"{onde}: falta '{chave}'")
    return d[chave]


def _descricao(texto: str) -> str:
    """Descrição de várias linhas: o YAML (`|`) termina em '\\n'; o texto original das rotas começava e terminava por quebra de linha."""
    return "\n" + texto if "\n" in texto.strip() else texto.strip()


def _filtros(brutos: list, plural: str, onde: str) -> tuple[Filtro, ...]:
    saida = []
    for item in brutos or []:
        nome, ajuste = (item, {}) if isinstance(item, str) else next(iter(item.items()))
        if nome not in FILTROS:
            raise CapacidadeErro(f"{onde}: filtro desconhecido '{nome}' (válidos: {', '.join(sorted(FILTROS))})")
        modelo = FILTROS[nome]
        descricao = (ajuste or {}).get("descricao") or modelo.descricao
        saida.append(Filtro(nome, modelo, descricao.replace("{plural}", plural)))
    return tuple(saida)


def _mcp(bruto: Optional[dict], filtros: tuple[Filtro, ...], tipo: str, onde: str) -> Optional[McpTool]:
    if not bruto:
        return None
    if tipo == "stats_outorgas":
        raise CapacidadeErro(f"{onde}: a tool de stats não é gerada (use 'sem_mcp')")
    nomes = tuple(bruto.get("filtros") or ())
    fora = [n for n in nomes if n not in {f.nome for f in filtros}]
    if fora:
        raise CapacidadeErro(f"{onde}: mcp.filtros {fora} não são filtros da operação")
    return McpTool(tool=_obrigatorio(bruto, "tool", f"{onde} mcp"), descricao=_obrigatorio(bruto, "descricao", f"{onde} mcp").strip("\n"),
                   filtros=nomes, limite_max=int(bruto.get("limite_max", 500)),
                   deduplicar_por_cnpj=bool(bruto.get("deduplicar_por_cnpj")), chave_resposta=bruto.get("chave_resposta", "outorgas"))


def _operacao(bruto: dict, cap: dict, onde: str) -> Operacao:
    id_ = _obrigatorio(bruto, "id", onde)
    onde = f"{onde} operação '{id_}'"
    tipo = _obrigatorio(bruto, "tipo", onde)
    if tipo not in TIPOS_OPERACAO:
        raise CapacidadeErro(f"{onde}: tipo '{tipo}' desconhecido (válidos: {', '.join(TIPOS_OPERACAO)})")
    http = _obrigatorio(bruto, "http", onde)
    if http.split(" ", 1)[0] != "GET" or " /" not in http:
        raise CapacidadeErro(f"{onde}: http deve ser 'GET /caminho', veio {http!r}")
    if bruto.get("mcp") and bruto.get("sem_mcp"):
        raise CapacidadeErro(f"{onde}: 'mcp' e 'sem_mcp' juntos")
    blocos = tuple(bruto.get("blocos") or ())
    for b in blocos:
        if b not in STATS_BLOCOS:
            raise CapacidadeErro(f"{onde}: bloco '{b}' desconhecido (válidos: {', '.join(STATS_BLOCOS)})")
    if tipo == "lista_outorgas" and not bruto.get("ordena_por"):
        raise CapacidadeErro(f"{onde}: lista precisa de ordena_por")
    filtros = _filtros(bruto.get("filtros"), cap["plural"], onde)
    return Operacao(
        id=id_, tipo=tipo, http=http, funcao=_obrigatorio(bruto, "funcao", onde),
        summary=_obrigatorio(bruto, "summary", onde), descricao=_descricao(bruto.get("descricao") or ""),
        mcp=_mcp(bruto.get("mcp"), filtros, tipo, onde), filtros=filtros,
        ordena_por=tuple(bruto.get("ordena_por") or ()), paginacao=dict(bruto.get("paginacao") or {}),
        deduplicar_por_cnpj=bool(bruto.get("deduplicar_por_cnpj")), blocos=blocos,
        dica_ausente=bruto.get("dica_ausente") or "", sem_ui=bruto.get("sem_ui"), sem_mcp=bruto.get("sem_mcp"),
    )


def carregar_arquivo(caminho: Path) -> Capacidade:
    onde = caminho.name
    bruto = yaml.safe_load(caminho.read_text(encoding="utf-8"))
    if not isinstance(bruto, dict):
        raise CapacidadeErro(f"{onde}: o arquivo deve ser um mapa")
    entidade = _obrigatorio(bruto, "entidade", onde)
    if caminho.stem != entidade:
        raise CapacidadeErro(f"{onde}: 'entidade' ({entidade}) deve ser o nome do arquivo")
    servico = _obrigatorio(bruto, "servico", onde)
    if servico not in _SERVICOS_OUTORGA:
        raise CapacidadeErro(f"{onde}: servico '{servico}' não está em core/outorgas.py (válidos: {', '.join(_SERVICOS_OUTORGA)})")
    if bruto.get("privacidade", "sem_contatos") != "sem_contatos":
        raise CapacidadeErro(f"{onde}: privacidade só aceita 'sem_contatos' (contatos nunca saem em rota pública nem no MCP)")
    ops = tuple(_operacao(o, bruto, onde) for o in _obrigatorio(bruto, "operacoes", onde))
    ids = [o.id for o in ops]
    if len(set(ids)) != len(ids):
        raise CapacidadeErro(f"{onde}: ids de operação repetidos")
    return Capacidade(
        entidade=entidade, rotulo=_obrigatorio(bruto, "rotulo", onde), plural=_obrigatorio(bruto, "plural", onde),
        nome_longo=_obrigatorio(bruto, "nome_longo", onde), servico=servico, tag=_obrigatorio(bruto, "tag", onde),
        operacoes=ops, descricao_llm=(bruto.get("descricao_llm") or "").strip(), colecao_query=bruto.get("colecao_query"),
        privacidade=bruto.get("privacidade", "sem_contatos"), arquivo=str(caminho.relative_to(RAIZ)) if caminho.is_relative_to(RAIZ) else str(caminho),
    )


@lru_cache(maxsize=None)
def carregar_todas(pasta: Optional[Path] = None) -> tuple[Capacidade, ...]:
    """Todas as capacidades de `serve/capabilities/*.yaml` (arquivos que começam por `_` são auxiliares), em ordem de nome."""
    pasta = pasta or PASTA
    caps = tuple(carregar_arquivo(p) for p in sorted(pasta.glob("*.yaml")) if not p.name.startswith("_"))
    vistos: dict[str, str] = {}
    for c in caps:
        for o in c.operacoes:
            for chave in (f"{o.metodo} {o.caminho}", f"funcao:{o.funcao}"):
                if chave in vistos:
                    raise CapacidadeErro(f"{c.arquivo}: '{chave}' já declarado em {vistos[chave]}")
                vistos[chave] = c.arquivo
    return caps


def capacidade(entidade: str) -> Capacidade:
    for c in carregar_todas():
        if c.entidade == entidade:
            return c
    raise KeyError(entidade)
