# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""`arandu source new <id>`: gera uma fonte nova de CSV, do catálogo até a publicação, em 6 arquivos.

Gera: `catalog/sources/<id>.yaml` (com a etapa e a publicação declaradas ali mesmo), `sources/<id>/{__init__,collect}.py`, a amostra
e o README em `tests/fixtures/raw/<id>/` e o teste T1. Nada é editado à mão em arquivo existente: o catálogo descobre a etapa, o armazém
versiona o normalizado e o manifesto passa a listar a fonte e os checksums do arquivo publicado.

O que o autor precisa fazer depois: trocar a URL e a amostra pela fonte real, ajustar `parse_csv` ao formato, preencher licença e campos
(`nao_verificado` até conferir) e rodar `arandu run --only <id>`.
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")
CAB_PY = """# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
CAB_YAML = "# Catálogo do Arandurapé (gerado por `arandu source new`). Edite aqui; `python3 scripts/gen_docs.py` regenera docs/.\n"

COLLECT = CAB_PY + '''"""{nome} (fonte gerada por `arandu source new`).

Fonte:       {url}
Raw:         data/raw/{{date}}/summary/{id}-{{date}}.csv.gz   (o CSV original, comprimido)
Normalizado: data/normalized/{{date}}/summary/{id}.json.gz   {{snapshot_date, generated_at, total, registros: [...]}}
Publicado:   published/{{date}}/{id}.json.gz  (cópia do normalizado, declarada em `publicar:` no catálogo)

Uso:
    python -m sources.{id}.collect --date 2026-10-24
"""
from __future__ import annotations

import argparse
import csv
import io
import sys
from pathlib import Path

import httpx

from core.common import configure_logging, data_dir, gravar_texto_gz, normalized_path, now_iso, raw_path, today_str, write_json_gz
from core.site import USER_AGENT

URL = "{url}"
HEADERS = {{"User-Agent": USER_AGENT}}


def parse_csv(texto: str) -> list[dict]:
    """Linhas do CSV como dicionários (cabeçalho = chaves), com espaços aparados e linhas vazias ignoradas. Ajuste ao formato real."""
    amostra = texto[:4096]
    delimitador = ";" if amostra.count(";") > amostra.count(",") else ","
    registros = []
    for linha in csv.DictReader(io.StringIO(texto), delimiter=delimitador):
        reg = {{(k or "").strip(): (v or "").strip() for k, v in linha.items()}}
        if any(reg.values()):
            registros.append(reg)
    return registros


def run(date_str: str, base: Path, log) -> dict:
    with httpx.Client(timeout=60, follow_redirects=True, headers=HEADERS) as client:
        resp = client.get(URL)
        resp.raise_for_status()
    texto = resp.text
    raw_dir = raw_path(base, date_str, "summary")
    raw_dir.mkdir(parents=True, exist_ok=True)
    gravar_texto_gz(raw_dir / f"{id}-{{date_str}}.csv.gz", texto)
    registros = parse_csv(texto)
    if not registros:
        raise RuntimeError("{id}: o arquivo veio sem registros")
    saida = {{"snapshot_date": date_str, "generated_at": now_iso(), "total": len(registros), "registros": registros}}
    destino = normalized_path(base, date_str, "summary")
    destino.mkdir(parents=True, exist_ok=True)
    write_json_gz(destino / "{id}.json.gz", saida)
    log.info("{id} written", total=len(registros))
    return saida


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="{nome}")
    p.add_argument("--date", default=today_str())
    a = p.parse_args(argv)
    log = configure_logging()
    try:
        run(a.date, data_dir(), log)
    except Exception:
        log.exception("falha na coleta de {id}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''

TESTE = CAB_PY + '''"""T1 — {nome} (gerado por `arandu source new`): download → bruto comprimido → normalizado, sem rede."""
import gzip

import respx

from core.common import read_json_gz
from sources.{id} import collect as fonte


@respx.mock
def test_normaliza_a_amostra_e_guarda_o_bruto(base, log, fx, date_str):
    respx.get(fonte.URL).respond(200, text=fx("{id}", "amostra.csv").read_text(encoding="utf-8"))
    r = fonte.run(date_str, base, log)
    assert r["total"] >= 1 and r["snapshot_date"] == date_str
    norm = read_json_gz(base / "normalized" / date_str / "summary" / "{id}.json.gz")
    assert norm["registros"] == r["registros"]
    bruto = base / "raw" / date_str / "summary" / f"{id}-{{date_str}}.csv.gz"
    assert gzip.decompress(bruto.read_bytes()).decode("utf-8") == fx("{id}", "amostra.csv").read_text(encoding="utf-8")
'''

README = """# Amostra de `{id}`

Gerada por `arandu source new`. **Fictícia**: troque por um recorte da fonte real (origem, data e o que foi anonimizado vão aqui).
Nunca dado pessoal real (regra do AGENTS.md).
"""
AMOSTRA = "codigo;nome;uf\nexemplo-1;Exemplo Um;SP\nexemplo-2;Exemplo Dois;RJ\n"


def arquivos(id: str, nome: str, url: str) -> dict[str, str]:
    """{caminho relativo: conteúdo} dos 6 arquivos da fonte nova."""
    fonte = {
        "id": id, "nome": nome, "tipo": "bruta", "ativa": True, "modulo": f"sources.{id}.collect", "publicavel": True,
        "descricao": f"{nome}. Gerada por `arandu source new`: descreva o que é, de onde vem e para que serve.",
        "origem": {"url": url, "formato": "csv", "licenca": "nao_verificado", "uso_comercial": "nao_verificado",
                   "nota": "Termos de uso ainda não verificados."},
        "cadencia": {"fonte_atualiza": "nao_verificado", "coleta": "semanal", "coleta_atual": "semanal", "frescor_maximo": "nao_verificado"},
        "politica_falha": "opcional",
        "saidas": {"bruto": [f"summary/{id}-{{as_of}}.csv.gz"], "normalizado": [f"summary/{id}.json.gz"], "publicado": [f"{id}.json.gz"]},
        "chaves": [], "campos": [],
        "limites": "Fonte gerada: descreva limites, defasagem e cobertura.",
        "fixture": f"tests/fixtures/raw/{id}/",
        "pendencias": ["Licença e termos de uso não verificados.", "Descrição dos campos pendente."],
        "etapa": {"tentativas": 3, "espera_s": 60},
        "publicar": {"de": f"summary/{id}.json.gz", "para": f"{id}.json.gz"},
    }
    return {
        f"catalog/sources/{id}.yaml": CAB_YAML + yaml.safe_dump(fonte, allow_unicode=True, sort_keys=False, width=110),
        f"sources/{id}/__init__.py": f'{CAB_PY}"""Pacote `sources.{id}` (gerado por `arandu source new`)."""\n',
        f"sources/{id}/collect.py": COLLECT.format(id=id, nome=nome, url=url),
        f"tests/fixtures/raw/{id}/amostra.csv": AMOSTRA,
        f"tests/fixtures/raw/{id}/README.md": README.format(id=id),
        f"tests/sources/test_t1_{id}.py": TESTE.format(id=id, nome=nome),
    }


def criar(id: str, nome: str, url: str, raiz: Path = ROOT, dry_run: bool = False) -> list[str]:
    if not ID_RE.match(id):
        raise ValueError("id deve casar [a-z][a-z0-9_]*")
    novos = arquivos(id, nome, url)
    existentes = [c for c in novos if (raiz / c).exists()]
    if existentes:
        raise FileExistsError("já existem (nada foi gravado): " + ", ".join(existentes))
    if not dry_run:
        for caminho, conteudo in novos.items():
            destino = raiz / caminho
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_text(conteudo, encoding="utf-8")
    return list(novos)
