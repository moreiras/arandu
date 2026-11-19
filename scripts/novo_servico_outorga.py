#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Novo serviço de outorga da Anatel: gera os arquivos que acompanham uma entrada em `core/outorgas.py`.

Fluxo para um quinto serviço ("xyz"):
  1. escreva a entrada em `core/outorgas.py::SERVICOS` (código do serviço no CSV, nome da lista, como reconhecer o nome) — o ÚNICO
     arquivo editado à mão;
  2. `python3 scripts/novo_servico_outorga.py xyz --nome "Serviço XYZ"` cria o coletor e o enriquecedor (módulos finos), as duas fontes
     e as duas etapas do catálogo (modelo: o STFC). Coleta, geocodificação, publicação, API e manifesto já derivam do registro.

`--raiz DIR` grava em outra árvore (testes); sem `--raiz`, no repositório. Não sobrescreve arquivo existente.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.outorgas import SERVICOS  # noqa: E402

CABECALHO_PY = """# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""
CABECALHO_YAML = "# Catálogo do Arandurapé. Edite aqui; `python3 scripts/gen_docs.py` regenera docs/.\n"
MODELO = "stfc"


def _trocar(x, de: str, para: str):
    if isinstance(x, str):
        return x.replace(de, para).replace(de.upper(), para.upper())
    if isinstance(x, list):
        return [_trocar(i, de, para) for i in x]
    if isinstance(x, dict):
        return {k: _trocar(v, de, para) for k, v in x.items()}
    return x


def _yaml(dados: dict) -> str:
    return CABECALHO_YAML + yaml.safe_dump(dados, allow_unicode=True, sort_keys=False, width=110)


def arquivos(sigla: str, nome: str, raiz_modelo: Path = ROOT) -> dict[str, str]:
    """{caminho relativo: conteúdo} do que acompanha o serviço `sigla` (que já deve estar no registro)."""
    if sigla not in SERVICOS:
        raise SystemExit(f"'{sigla}' não está em core/outorgas.py::SERVICOS — escreva essa entrada primeiro.")
    cat = raiz_modelo / "catalog"
    saida: dict[str, str] = {}
    for modulo, arq, rot, resumo in (("anatel_" + sigla, "collect", "M-" + sigla, "coleta"), (sigla + "_geo", "enrich", "M-" + sigla + "b", "geocodificação")):
        saida[f"sources/{modulo}/__init__.py"] = f'{CABECALHO_PY}"""Pacote `sources.{modulo}`."""\n'
    saida[f"sources/anatel_{sigla}/collect.py"] = f'''{CABECALHO_PY}"""Coleta das outorgas {nome} da Anatel (configuração em core/outorgas.py; parser em sources/anatel_outorgas)."""
from __future__ import annotations

import sys
from pathlib import Path

from core.common import configure_logging, data_dir, today_str
from sources.anatel_outorgas.servicos import SERVICOS, parse_csv, rodar

SERVICO = SERVICOS["{sigla}"]


def _parse_csv(content: bytes) -> list[dict]:
    return parse_csv(content, SERVICO)


def run(date_str: str, base: Path, log) -> dict:
    return rodar(SERVICO, date_str, base, log)


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Coleta de outorgas {sigla.upper()} da Anatel")
    parser.add_argument("--date", default=today_str())
    args = parser.parse_args(argv)
    try:
        run(date_str=args.date, base=data_dir(), log=configure_logging())
    except Exception:
        configure_logging().exception("unexpected error")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''
    saida[f"sources/{sigla}_geo/enrich.py"] = f'''{CABECALHO_PY}"""Geolocalização das outorgas {nome} (lógica comum em sources/anatel_outorgas/geo.py)."""
from __future__ import annotations

import sys
from pathlib import Path

from core.outorgas import SERVICOS
from sources.anatel_outorgas import geo as _geo

SERVICO = SERVICOS["{sigla}"]


def run(date_str: str, base: Path, force: bool, log) -> dict:
    return _geo.rodar(SERVICO, date_str, base, force, log)


def main(argv: list[str] | None = None) -> int:
    return _geo.main_geo(SERVICO, "M-{sigla}b", argv)


if __name__ == "__main__":
    sys.exit(main())
'''
    ordem = 1 + max(int(yaml.safe_load(p.read_text(encoding="utf-8"))["ordem"]) for p in (cat / "steps").glob("*.yaml"))
    for destino, modelo_id, novo_id, novo_nome, modulo in (
        (f"anatel_{sigla}", f"anatel_{MODELO}", f"anatel_{sigla}", f"Outorgas {sigla.upper()} (Anatel)", f"sources.anatel_{sigla}.collect"),
        (f"{sigla}_geo", f"{MODELO}_geo", f"{sigla}_geo", f"Geolocalização das outorgas {sigla.upper()}", f"sources.{sigla}_geo.enrich"),
    ):
        fonte = _trocar(yaml.safe_load((cat / "sources" / f"{modelo_id}.yaml").read_text(encoding="utf-8")), MODELO, sigla)
        fonte.update({"id": novo_id, "nome": novo_nome, "modulo": modulo, "publicavel": False, "exposicao": "nenhuma"})
        for c in fonte.get("campos") or []:
            c.pop("publicado_em", None)          # o produto `outorgas` só declara os campos dos quatro serviços atuais
        fonte["pendencias"] = list(fonte.get("pendencias") or []) + [f"Serviço novo ({sigla}): revisar nome, descrição e publicação no catálogo."]
        saida[f"catalog/sources/{destino}.yaml"] = _yaml(fonte)
        etapa = _trocar(yaml.safe_load((cat / "steps" / f"{modelo_id}.yaml").read_text(encoding="utf-8")), MODELO, sigla)
        etapa.update({"id": novo_id, "nome": novo_nome, "ordem": ordem, "modulo": modulo, "fontes": [novo_id]})
        ordem += 1
        saida[f"catalog/steps/{destino}.yaml"] = _yaml(etapa)
    return saida


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("sigla")
    p.add_argument("--nome", required=True, help="nome por extenso do serviço")
    p.add_argument("--raiz", type=Path, default=ROOT, help="onde gravar (padrão: o repositório)")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args(argv)
    novos = arquivos(a.sigla, a.nome)
    existentes = [c for c in novos if (a.raiz / c).exists()]
    if existentes:
        print("ERRO: já existem (nada foi gravado):", *existentes, sep="\n  ", file=sys.stderr)
        return 1
    for caminho, conteudo in novos.items():
        print(("criaria " if a.dry_run else "criou   ") + caminho)
        if not a.dry_run:
            destino = a.raiz / caminho
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_text(conteudo, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
