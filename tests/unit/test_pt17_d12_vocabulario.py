# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""PT-17 (D12): o vocabulário "omissão" saiu da interface, da API, do MCP, do catálogo e dos docs.

Critério de aceite da decisão: a busca por "omiss" nessas áreas só encontra o alias do nome antigo e a nota de depreciação. A busca ignora
palavras que contêm a sequência por acaso (compromisso, comissão, promissor). Arquivos gerados do contrato (OpenAPI) só podem trazer a rota
alias, marcada como tal.
"""
import gzip
import json
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
AREAS = ("frontend/src", "frontend/public", "api", "mcp_server", "docs", "catalog", "serve", "products", "core", "sources", "publish")
EXTENSOES = {".py", ".ts", ".tsx", ".md", ".json", ".yaml", ".yml", ".txt", ".html"}
PADRAO = re.compile(r"(?<![cr])omiss", re.IGNORECASE)          # não pega compromisso, comissão, promissor
MARCAS = re.compile(r"alias|antigo|anterior|obsolet|deprecia|renomead", re.IGNORECASE)
GERADOS = {"frontend/src/types/openapi.json", "frontend/src/types/openapi.gen.ts"}


def _ocorrencias():
    for area in AREAS:
        for p in sorted((RAIZ / area).rglob("*")):
            if p.suffix not in EXTENSOES or "node_modules" in p.parts or not p.is_file():
                continue
            linhas = p.read_text(encoding="utf-8", errors="replace").splitlines()
            for i, linha in enumerate(linhas):
                if PADRAO.search(linha):
                    yield p.relative_to(RAIZ).as_posix(), i, linhas


def test_omissao_so_aparece_como_alias_ou_nota_de_depreciacao():
    soltas = []
    for rel, i, linhas in _ocorrencias():
        if rel in GERADOS:
            janela = " ".join(linhas[max(0, i - 30):i + 30])
        else:
            janela = " ".join(linhas[max(0, i - 3):i + 4])
        if not MARCAS.search(janela):
            soltas.append(f"{rel}:{i + 1}: {linhas[i].strip()[:120]}")
    assert soltas == [], "vocabulário 'omissão' fora do alias/nota de depreciação (D12):\n" + "\n".join(soltas)


def test_o_alias_existe_onde_a_decisao_manda_manter():
    """Nome antigo nunca some: rota (API), collection (API/MCP), arquivo publicado (leitura) e visão (front)."""
    from api.query_catalogo import COLECOES_ALIAS
    from api.repos.sici_indicadores import ARQUIVO_ANTIGO
    from api import deprecation

    assert COLECOES_ALIAS == {"omissao_sici": "sem_declaracao_sici"}
    assert ARQUIVO_ANTIGO == "omissao_sici.json.gz"
    assert deprecation.sucessor("/api/v1/omissao-sici") == "/api/v1/sem-declaracao-sici"
    assert "visao === 'omissao'" in (RAIZ / "frontend/src/pages/OperadorasPage.tsx").read_text(encoding="utf-8")


def test_repo_le_snapshot_antigo_com_o_nome_antigo_do_arquivo(tmp_path):
    from api.repos.sici_indicadores import ARQUIVO_ANTIGO, SiciIndicadoresRepo

    pub = tmp_path / "2026-10-11"
    pub.mkdir()
    (pub / "manifest.json").write_text("{}")
    with gzip.open(pub / ARQUIVO_ANTIGO, "wt", encoding="utf-8") as f:
        json.dump({"itens": {"1": {}}}, f)
    repo = SiciIndicadoresRepo(lambda d: tmp_path / d)
    assert repo.sem_declaracao("2026-10-11") == {"itens": {"1": {}}}
    pub2 = tmp_path / "2026-11-22"
    pub2.mkdir()
    (pub2 / "manifest.json").write_text("{}")
    with gzip.open(pub2 / "sem_declaracao_sici.json.gz", "wt", encoding="utf-8") as f:
        json.dump({"itens": {}}, f)
    assert repo.sem_declaracao("2026-11-22") == {"itens": {}}
