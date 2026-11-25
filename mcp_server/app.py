# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
Arandurape — Servidor MCP (Model Context Protocol).

Expõe o snapshot mais recente do Arandurape como ferramentas, recursos e prompt
para LLMs responderem perguntas em linguagem natural sobre ASNs, IXPs, tabelas
globais, Registro.br/LACNIC, participantes do IX.br, CDNs/CAPs e geolocalização —
com a semântica e os cruzamentos do projeto.

Princípio: casca fina sobre `api.store.Store`. Os dados são pré-computados e
imutáveis em `data/published/{date}/`; o MCP serve exatamente os mesmos números
da API e da interface.

Superfície: tools de entidade (drill-down) + uma camada de consulta genérica
(`query` com filtro/agg/near, `describe_schema`, `resolve_*`, analíticos
`ixp_nearby`/`operator_reach`, `get_asns` em lote) + 12 tools de visualização
(avançadas), 4 resources semânticos (incl. <esquema>://schema, `SITE_MCP_ESQUEMA`) e 1 prompt.
Ver proposta-mcp.md e proposta-query-layer.md.

Execução:
  - HTTP remoto (produção):  uvicorn mcp_server.app:app --host 0.0.0.0 --port 8001
  - stdio (validação local): python -m mcp_server.app   (ou: mcp dev mcp_server/app.py)

Dividido em módulos para ficar abaixo de 800 linhas: o contexto comum está em `contexto.py`, o playbook em `instrucoes.py`, as tools em
`tools_entidades.py`, `tools_visualizacao.py`, `tools_consulta.py` e `tools_mercado.py` (mais `list_scms`/`get_scm`, geradas de
`serve/capabilities/scm.yaml`), os resources e o prompt em `recursos.py`. Este módulo só monta o servidor e expõe o app ASGI.
"""
# ruff: noqa: E402, F401
from __future__ import annotations

import functools
import inspect

from api.store import Store
from core.common import data_dir
from mcp_server.contexto import _resolve, mcp          # reexportados: testes e ferramentas leem `mcp_server.app.mcp`

# Uma única Store por processo — cache lazy de snapshot, seguro para leitura concorrente. As tools a leem daqui (`contexto._store`).
_store = Store(data_dir())

# Teto de memória (api/memoria.py, como na API): a data mais recente e `MCP_DATAS_EXTRAS` outras ficam em memória (o compose põe 0:
# só a mais recente); a data antiga é servida e expurgada ao fim da tool; perto do teto tudo é expurgado. `MCP_MEMORIA=0` desliga.
from api.memoria import GuardaMemoria, ligado as _memoria_ligada  # noqa: E402

_guarda = GuardaMemoria(_store, lambda: _store.resolve_date(None), prefixo="MCP") if _memoria_ligada("MCP") else None
if _guarda is not None:
    _guarda.iniciar_thread()

# A ordem de importação é a ordem de registro das tools (e do `tools/list`)
from mcp_server import tools_entidades, tools_visualizacao, tools_consulta
from mcp_server.capacidades import registrar_tools

registrar_tools(mcp, lambda: _store, _resolve)          # list_scms e get_scm

from mcp_server import tools_mercado, tools_bgp, tools_infra, tools_historico, tools_politica, recursos
from mcp_server import tools_instalacoes  # noqa: E402,F401
from mcp_server import tools_bloqueios  # noqa: E402,F401
from mcp_server import tools_radar  # noqa: E402,F401
from mcp_server import tools_exposicao  # noqa: E402,F401
from mcp_server import tools_financiamento  # noqa: E402,F401
from mcp_server import tools_grupo  # noqa: E402,F401
from mcp_server import tools_interconexao  # noqa: E402,F401
from mcp_server import tools_contratos  # noqa: E402,F401
from mcp_server import tools_contatos  # noqa: E402,F401

# App ASGI para uvicorn (transporte Streamable HTTP, produção).
# Limites: nginx (taxa grossa por endereço) e, na aplicação, o orçamento por cliente registrado abaixo (api/limites.py). O SlowAPIMiddleware
# não serve aqui: o endpoint do MCP é uma instância ASGI (StreamableHTTPASGIApp), não uma função, e o slowapi respondia 500 a toda requisição.
from mcp_server import nomes

nomes.aplicar(mcp)                                      # nomes por domínio; os antigos viram aliases ocultos

from mcp_server.descricoes import DESCRICOES  # noqa: E402

# o que o modelo lê de cada tool: as descrições curtas medidas com modelos locais; os docstrings ficam como documentação
for _nome, _tool in mcp._tool_manager._tools.items():
    if _nome in DESCRICOES:
        _tool.description = DESCRICOES[_nome]


def _aplicar_identidade(servidor) -> None:
    """Descrições de tools, resources, templates e prompts com o nome do site e o esquema de URI do `.env`.
    Os docstrings seguem escritos com o nome do software, que serve de marcador (`core.site.com_identidade`)."""
    from core.site import com_identidade
    colecoes = (servidor._tool_manager._tools, servidor._resource_manager._resources, servidor._resource_manager._templates,
                servidor._prompt_manager._prompts)
    for col in colecoes:
        for item in col.values():
            if getattr(item, "description", None):
                item.description = com_identidade(item.description)


_aplicar_identidade(mcp)

app = mcp.streamable_http_app()

# Log de uso: cada tool (nome, duração, tamanho) e cada chamada HTTP
# (sem IP em claro; ver api/usage_log.py e /privacidade). Não bloqueia nada.
from api.usage_log import UsageLogMiddleware, instrument_mcp_tools  # noqa: E402

# Limites do MCP: orçamento por cliente em janelas de minuto, hora e dia (conta da chave ou rede, IPv6
# pelo /64; api/limites.py) e no máximo `MCP_MAX_INFLIGHT` chamadas em andamento (`MCP_MAX_INFLIGHT_POR_CLIENTE` por cliente). Ficam DENTRO
# do `ChaveMiddleware` (registrados antes dele), que põe o `conta_id` no escopo.
from api.concurrency import ConcurrencyLimitMiddleware  # noqa: E402
from api.limites import OrcamentoMiddleware  # noqa: E402

app.add_middleware(ConcurrencyLimitMiddleware, prefixo="MCP", isentos=())
app.add_middleware(OrcamentoMiddleware, perfil="mcp")

# Chave de MCP: dentro do log de uso (que continua o mais externo e vê também as respostas 401/429)
from mcp_server.chave import ChaveMiddleware  # noqa: E402

app.add_middleware(ChaveMiddleware)
# Prévia sem chave: antes da instrumentação, para o log de uso também registrar o pedido recusado.
from mcp_server import previa  # noqa: E402

# Pré-carga (mcp_server/precarga.py): as funções originais das tools, antes da prévia e do log de uso, numa thread de fundo
from mcp_server import precarga  # noqa: E402

_funcoes_originais = {nome: tool.fn for nome, tool in mcp._tool_manager._tools.items()}
previa.aplicar(mcp, lambda: _store.list_snapshots()[-2:])


def _com_guarda(servidor, guarda) -> int:
    """Cada tool roda dentro de `guarda.usando(date)`: a data antiga fica protegida do expurgo durante a tool e é expurgada depois dela
    (o `?date=` do middleware da API, aqui pelo argumento). As de histórico leem várias datas sem `date`: a passada seguinte as limpa."""
    n = 0
    for tool in servidor._tool_manager._tools.values():
        fn = tool.fn
        if getattr(fn, "_guarda", False):
            continue

        if inspect.iscoroutinefunction(fn):
            @functools.wraps(fn)
            async def envoltorio(*a, __fn=fn, **kw):
                with guarda.usando(kw.get("date")):
                    return await __fn(*a, **kw)
        else:
            @functools.wraps(fn)
            def envoltorio(*a, __fn=fn, **kw):
                with guarda.usando(kw.get("date")):
                    return __fn(*a, **kw)
        envoltorio._guarda = True                               # type: ignore[attr-defined]
        for attr in ("_previa", "_usage_logged"):
            if getattr(fn, attr, False):
                setattr(envoltorio, attr, True)
        tool.fn = envoltorio
        n += 1
    return n


if _guarda is not None:
    _com_guarda(mcp, _guarda)


def _sem_pessoa_natural(valor):
    """Resultado de tool e resource sem o nome civil de EI/MEI nem o ponto exato da sede (D1, PT-11): última barreira do MCP, igual à da REST."""
    from core import pessoa_natural

    try:
        idx = _store.pessoa_natural_indice()
    except AttributeError:                                      # Store falsa dos testes
        return valor
    return pessoa_natural.na_saida(valor, idx)


def _com_identidade(servidor) -> int:
    """Resultado de cada tool, resource e template com o nome do site: os artefatos do pipeline dizem "o Arandurapé coletou" (limitações,
    metodologia, fonte) e o cliente repetia o nome do software nas respostas e nas citações. As descrições já passam por `_aplicar_identidade`."""
    from core.site import com_identidade_nos_dados

    def na_saida(valor):
        return com_identidade_nos_dados(_sem_pessoa_natural(valor))

    def envolver(fn):
        if getattr(fn, "_identidade", False):
            return fn
        if inspect.iscoroutinefunction(fn):
            @functools.wraps(fn)
            async def envoltorio(*a, __fn=fn, **kw):
                return na_saida(await __fn(*a, **kw))
        else:
            @functools.wraps(fn)
            def envoltorio(*a, __fn=fn, **kw):
                return na_saida(__fn(*a, **kw))
        for attr in ("_previa", "_usage_logged", "_guarda"):
            if getattr(fn, attr, False):
                setattr(envoltorio, attr, True)
        envoltorio._identidade = True                           # type: ignore[attr-defined]
        return envoltorio

    n = 0
    for col in (servidor._tool_manager._tools, servidor._resource_manager._resources, servidor._resource_manager._templates):
        for item in col.values():
            if callable(getattr(item, "fn", None)):
                item.fn = envolver(item.fn)
                n += 1
    return n


_com_identidade(mcp)
instrument_mcp_tools(mcp, data_dir)
app.add_middleware(UsageLogMiddleware, data_dir=data_dir, src="mcp")
precarga.iniciar(_funcoes_originais, _store)


if __name__ == "__main__":
    # Execução local via stdio (MCP Inspector / clientes desktop).
    mcp.run()
