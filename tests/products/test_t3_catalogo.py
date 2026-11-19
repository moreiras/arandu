# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T3 — consistência do catálogo: código × catálogo × arquivos produzidos.

(a) todo módulo de collector/ e enrich/ tem source.yaml (e o catálogo não aponta para módulo inexistente);
(b) todo arquivo de raw/, normalized/ e published/ do dataset sintético está declarado;
(c) todo campo publicado (chave de primeiro nível) tem `significado`: cobertura ≥ 90%.
Mais: referências `publicado_em` válidas, cenários citados existem, docs gerados em dia (`gen_docs --check`),
fonte com exposição restrita nunca é copiada para published/.
"""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

from core.catalog.coverage import cobertura
from core.catalog.loader import load_catalog, pattern_matches, validate
from tests.synth.world import T0, T1

ROOT = Path(__file__).resolve().parents[2]
CENARIOS_SINTETICO = {  # tests/synth/README.md, tabela "Cenários plantados"
    "rpki_invalido_moas", "scm_sem_sici", "cnpj_dois_asns", "grupos_societarios",
    "ptt_coleta_parcial", "mudanca_de_origem", "contatos_fora_do_published", "municipio_sem_ptt",
}


@pytest.fixture(scope="module")
def cat():
    return load_catalog()


def _padroes(cat, campo):
    out = []
    for it in [*cat.sources.values(), *cat.products.values()]:
        out += getattr(it.saidas, campo)
    return out


def _arquivos(raiz: Path):
    return sorted(p for p in raiz.rglob("*") if p.is_file())


def test_catalogo_valido(cat):
    assert validate(cat) == []
    assert len(cat.sources) >= 39 and len(cat.products) >= 1


def test_todo_modulo_tem_source_yaml_e_vice_versa(cat):
    declarados = {s.modulo for s in cat.sources.values() if s.modulo}
    existentes = set()
    for pasta in sorted((ROOT / "sources").iterdir()):
        if not pasta.is_dir() or pasta.name.startswith(("_", ".")):
            continue
        for arq in ("collect", "enrich"):
            if (pasta / f"{arq}.py").exists():
                existentes.add(f"sources.{pasta.name}.{arq}")
    assert existentes - declarados == set(), "módulo sem source.yaml"
    assert {m for m in declarados if m.startswith("sources.")} - existentes == set(), "catálogo cita módulo inexistente"
    for m in declarados:
        assert importlib.util.find_spec(m) is not None, m


def test_pasta_de_cada_fonte_tem_o_id_do_catalogo(cat):
    for s in cat.sources.values():
        if s.modulo and s.modulo.startswith("sources."):
            assert s.modulo.split(".")[1] == s.id, (s.id, s.modulo)


def test_fontes_curadas_apontam_para_arquivo_existente(cat):
    for s in cat.sources.values():
        if s.tipo == "curada":
            assert (ROOT / s.arquivo).is_file(), s.arquivo


def test_todo_arquivo_do_dataset_sintetico_esta_declarado(cat, pipeline):
    base, _ = pipeline
    bruto, norm, pub = _padroes(cat, "bruto"), _padroes(cat, "normalizado"), _padroes(cat, "publicado")
    nao = []
    for tipo, pads in (("raw", bruto), ("normalized", norm), ("published", pub)):
        for data in (T0, T1):
            raiz = base / tipo / data
            if not raiz.is_dir():
                continue
            for f in _arquivos(raiz):
                rel = f.relative_to(raiz).as_posix()
                if not any(pattern_matches(p, rel) for p in pads):
                    nao.append(f"{tipo}/{rel}")
    # caches fora da pasta da data (normalized/holdings_cache, geo_cache…) são declarados com '../'
    raiz_norm = base / "normalized"
    for f in _arquivos(raiz_norm):
        rel = f.relative_to(raiz_norm).as_posix()
        if rel.split("/")[0] in (T0, T1):
            continue
        if not any(pattern_matches(p[3:], rel) for p in norm if p.startswith("../")):
            nao.append(f"normalized/{rel}")
    assert sorted(set(nao)) == [], "arquivos não declarados no catálogo"


def test_todo_campo_publicado_tem_significado(cat, pipeline):
    base, _ = pipeline
    for data in (T0, T1):
        c = cobertura(cat, base / "published" / data, amostra_por_padrao=3)
        assert c["nao_declarado"] == []
        assert c["pct"] >= 90.0, f"{data}: {c['pct']}% — faltam {c['faltam']}"
    for it in [*cat.sources.values(), *cat.products.values()]:
        for campo in it.campos:
            assert campo.significado.strip() not in ("", "nao_verificado"), (it.id, campo.nome)


def test_cobertura_no_snapshot_real_quando_existir(cat):
    pubs = sorted((ROOT / "data" / "published").glob("20*"))
    if not pubs:
        pytest.skip("sem data/published (CI)")
    c = cobertura(cat, pubs[-1])
    assert c["nao_declarado"] == [], c["nao_declarado"]
    assert c["pct"] >= 90.0, c["faltam"]


def test_cenarios_citados_existem_no_dataset_sintetico(cat):
    citados = {c for p in cat.products.values() for c in p.cenarios_de_teste}
    assert citados <= CENARIOS_SINTETICO, citados - CENARIOS_SINTETICO


def test_fonte_nao_aberta_nao_vaza_para_published(cat, pipeline):
    """Licença: o que não é 'aberta' (exposicao login/nenhuma) não pode ter arquivo em published/."""
    base, _ = pipeline
    nomes = set()
    for data in (T0, T1):
        nomes |= {p.name for p in _arquivos(base / "published" / data)}
    for s in cat.sources.values():
        if s.exposicao == "aberta":
            continue
        saidas = [*s.saidas.bruto, *s.saidas.normalizado, *s.saidas.publicado]
        for pad in saidas:
            base_nome = pad.rsplit("/", 1)[-1]
            for n in nomes:
                assert not pattern_matches(base_nome, n), f"{s.id} ({s.exposicao}) vazou {n} para published/"
        assert not s.saidas.publicado


def test_fonte_nao_publicavel_nao_alimenta_produto_publicado(cat):
    for s in cat.sources.values():
        if s.publicavel:
            continue
        usos = [p.id for p in cat.products.values() if any(e.source == s.id for e in p.entradas)]
        assert usos == [], f"{s.id} (publicavel=false) alimenta {usos}"


def test_toda_fonte_tem_uso_comercial_e_publicavel_preenchidos(cat):
    """Licença: 100% das fontes brutas têm uso_comercial; derivadas herdam (efetivo), curadas declaram."""
    from core.catalog.loader import uso_comercial_efetivo

    for s in cat.sources.values():
        assert isinstance(s.publicavel, bool)
        assert uso_comercial_efetivo(cat, s.id) in {"permitido", "restrito", "nao_verificado"}
        if s.tipo == "bruta":
            assert s.origem is not None and s.origem.uso_comercial


def test_docs_gerados_estao_em_dia():
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "gen_docs.py"), "--check"], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_fontes_json_e_consistente(cat):
    d = json.loads((ROOT / "docs" / "fontes.json").read_text(encoding="utf-8"))
    assert {f["id"] for f in d["fontes"]} == set(cat.sources)
    assert {p["id"] for p in d["produtos"]} == set(cat.products)
