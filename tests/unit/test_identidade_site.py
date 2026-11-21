# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Identidade do site.

- o nome do software não aparece em texto visível do frontend, no OpenAPI nem no inventário do MCP (lá entra o nome do `.env`);
- Internet Bit a Bit só no Sobre, na Privacidade e no Uso aceitável (e nos cabeçalhos de copyright, que não são texto visível);
- os valores vêm do ambiente, com padrões."""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from core.site import PADROES, carregar, com_identidade, com_identidade_json, com_identidade_nos_dados

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "frontend" / "src"


def _linhas_de_codigo(p: Path):
    """Linhas do arquivo fora de comentários (cabeçalho SPDX, `//`, blocos `/** … */`)."""
    em_bloco = False
    for n, linha in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
        s = linha.strip()
        if em_bloco:
            em_bloco = "*/" not in s
            continue
        if s.startswith("/*"):
            em_bloco = "*/" not in s
            continue
        if s.startswith("//") or s.startswith("*"):
            continue
        yield n, re.sub(r"\s//\s.*$", "", linha)


def _fontes_do_front():
    for p in sorted(SRC.rglob("*.ts*")):
        if ".test." in p.name or p.name.endswith(".d.ts") or "types" in p.parts or "test" in p.parts:
            continue
        yield p


def _achados(padrao: str, permitido) -> list[str]:
    rx = re.compile(padrao)
    out = []
    for p in _fontes_do_front():
        rel = p.relative_to(SRC).as_posix()
        for n, linha in _linhas_de_codigo(p):
            if rx.search(linha) and not permitido(rel, linha):
                out.append(f"{rel}:{n}: {linha.strip()[:120]}")
    return out


def test_nome_antigo_nao_aparece_no_frontend():
    assert _achados(r"Arandurap[eé]", lambda rel, l: rel == "lib/site.ts") == []
    assert "Arandurap" not in (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")


def test_internet_bit_a_bit_so_nas_paginas_institucionais():
    paginas = {"pages/Sobre.tsx", "pages/Privacidade.tsx", "pages/UsoAceitavel.tsx", "lib/site.ts"}
    assert _achados(r"Bit a Bit|internetbitabit", lambda rel, l: rel in paginas) == []


def test_emails_de_contato_vem_do_env():
    """Endereço de e-mail só como padrão em `lib/site.ts` (`SITE_CONTATO`, `SITE_CONTATO_PRIVACIDADE`); as páginas usam `SITE.contato*`."""
    assert _achados(r"[\w.+-]+@[\w-]+\.[\w.-]+", lambda rel, l: rel == "lib/site.ts") == []
    html = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")
    assert "@" not in re.sub(r"<script.*?</script>", "", html, flags=re.S)
    assert "Mapa da Internet brasileira" not in html, "a descrição usa %VITE_SITE_NOME_EXTENSO%"


# O nome padrão é o do software ("Arandurapé"), que também é o marcador trocado por `com_identidade`: com o padrão a troca não se vê.
# Por isso o OpenAPI e o inventário do MCP são conferidos num processo à parte, com outra identidade no ambiente (o `SITE` é lido na
# importação).
_OUTRA = {"SITE_NOME": "Sítio de Teste", "SITE_URL": "https://exemplo.example", "SITE_MCP_ESQUEMA": "tst"}


def _em_outro_processo(codigo: str) -> dict:
    env = {**os.environ, **_OUTRA}
    r = subprocess.run([sys.executable, "-c", codigo], cwd=ROOT, env=env, capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stderr[-2000:]
    return json.loads(r.stdout.strip().splitlines()[-1])


def test_openapi_usa_o_nome_do_site():
    saida = _em_outro_processo(
        "import json\nfrom api.main import app\nprint(json.dumps({'titulo': app.openapi()['info']['title'], "
        "'txt': json.dumps(app.openapi(), ensure_ascii=False)}))")
    assert saida["titulo"] == _OUTRA["SITE_NOME"]
    assert not re.search(r"Arandurap[eé]|ARANDURAP|arandurape://|Internet Bit a Bit", saida["txt"])


def test_mcp_usa_o_nome_e_o_esquema_do_site():
    saida = _em_outro_processo("""
import asyncio, json
from mcp_server.app import mcp

async def coleta():
    ts, rs, tp, ps = await mcp.list_tools(), await mcp.list_resources(), await mcp.list_resource_templates(), await mcp.list_prompts()
    textos = ([t.description or "" for t in ts] + [r.description or "" for r in rs] + [str(r.uri) for r in rs] + [t.uriTemplate for t in tp]
              + [t.description or "" for t in tp] + [p.name for p in ps] + [p.description or "" for p in ps] + [mcp.instructions or ""])
    return {"textos": textos, "uris": [str(r.uri) for r in rs], "prompts": [p.name for p in ps], "nome": mcp.name}

print(json.dumps(asyncio.run(coleta()), ensure_ascii=False))
""")
    esquema = _OUTRA["SITE_MCP_ESQUEMA"]
    assert not re.search(r"Arandurap[eé]|arandurape://", " ".join(saida["textos"]))
    assert saida["uris"] and all(u.startswith(f"{esquema}://") for u in saida["uris"])
    assert saida["nome"] == esquema and esquema in saida["prompts"]


def test_valores_vem_do_ambiente_com_padroes():
    padrao = carregar({})
    assert (padrao.nome, padrao.url, padrao.mcp_esquema) == ("Arandurapé", "http://localhost", "arandurape")
    outro = carregar({"SITE_NOME": "Teste", "SITE_URL": "https://exemplo.test/", "SITE_MCP_ESQUEMA": "tst://"})
    assert (outro.nome, outro.url, outro.mcp_esquema, outro.uri("asn/1")) == ("Teste", "https://exemplo.test", "tst", "tst://asn/1")
    assert com_identidade("ver arandurape://glossario do Arandurapé", outro) == "ver tst://glossario do Teste"
    assert set(PADROES) >= {"SITE_NOME", "SITE_NOME_EXTENSO", "SITE_URL", "SITE_MCP_ESQUEMA", "SITE_PREFIXO_ARQUIVOS", "SITE_SOFTWARE",
                            "SITE_CODIGO_FONTE"}
    # contato de segurança (security.txt) cai no geral quando vazio
    assert carregar({"SITE_CONTATO": "a@exemplo.test"}).contato_seguranca == "a@exemplo.test"
    assert carregar({"SITE_CONTATO": "a@exemplo.test", "SITE_CONTATO_SEGURANCA": "abuse@exemplo.test"}).contato_seguranca == "abuse@exemplo.test"
    # AGPL §13: a instância oferece o código que roda; quem modifica aponta para o próprio repositório
    assert padrao.codigo_fonte.startswith("https://")
    assert carregar({"SITE_CODIGO_FONTE": "https://git.exemplo.test/fork/"}).codigo_fonte == "https://git.exemplo.test/fork"


def test_dados_das_respostas_levam_o_nome_do_site():
    """Os artefatos do pipeline dizem "o Arandurapé coletou": a API e o MCP trocam pelo nome do site na saída, só nos valores."""
    outro = carregar({"SITE_NOME": 'Sítio "Teste"', "SITE_MCP_ESQUEMA": "tst"})
    dados = {"limitacoes": ["n_redes conta os vínculos que o Arandurapé coletou"], "Arandurapé": 1, "n": 3, "ok": ("sem nome",)}
    trocado = com_identidade_nos_dados(dados, outro)
    assert trocado["limitacoes"] == ['n_redes conta os vínculos que o Sítio "Teste" coletou']
    assert "Arandurapé" in trocado, "chave não muda"
    sem_nome = {"a": ["x", {"b": "y"}], "c": 1}
    assert com_identidade_nos_dados(sem_nome, outro) is sem_nome, "sem nada a trocar, sem cópia"
    corpo = json.dumps(dados, ensure_ascii=False)
    assert json.loads(com_identidade_json(corpo, outro))["limitacoes"] == trocado["limitacoes"], "nome com aspas segue JSON válido"


def test_api_e_mcp_trocam_o_nome_nos_dados():
    saida = _em_outro_processo("""
import asyncio, json
from api.respostas import JSONResponse
from mcp.server.fastmcp import FastMCP
from mcp_server.app import _com_identidade

api = json.loads(JSONResponse({"limitacoes": "vínculos que o Arandurapé coletou"}).body)
srv = FastMCP("t")

@srv.tool()
def exemplo() -> dict:
    return {"fonte": {"nome": "Arandurapé: relações inferidas"}}

_com_identidade(srv)
conteudo = asyncio.run(srv.call_tool("exemplo", {}))
blocos = conteudo[0] if isinstance(conteudo, tuple) else conteudo
print(json.dumps({"api": api["limitacoes"], "mcp": " ".join(b.text for b in blocos)}, ensure_ascii=False))
""")
    assert saida["api"] == f"vínculos que o {_OUTRA['SITE_NOME']} coletou"
    assert _OUTRA["SITE_NOME"] in saida["mcp"] and "Arandurap" not in saida["mcp"]
