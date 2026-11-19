# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Linha de comando do `arandu`."""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from arandu import compare as cmp_  # noqa: E402
from arandu import executor, lockfile, ops, repair as rp, status as st  # noqa: E402
from arandu.runner import SubprocessRunner  # noqa: E402
from core.catalog.loader import dependencias_de_etapas, load_catalog, validate  # noqa: E402
from core import store as armazem  # noqa: E402


def _data_dir(arg: Optional[str]) -> Path:
    if arg:
        return Path(arg)
    from core.common import data_dir

    return data_dir()


def _versao() -> str:
    try:
        return (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        return "desconhecida"


def _script(nome: str):
    spec = importlib.util.spec_from_file_location(f"arandu_{nome}", ROOT / "scripts" / f"{nome}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _catalogo():
    cat = load_catalog(ROOT / "catalog")
    erros = validate(cat)
    if erros:
        for e in erros:
            print(f"ERRO de catálogo: {e}", file=sys.stderr)
        raise SystemExit(2)
    return cat


def cmd_plan(a) -> int:
    cat = _catalogo()
    deps = dependencias_de_etapas(cat)
    for i, s in enumerate(executor.planejar(cat, a.only), 1):
        extra = f"  (host)" if s.runner == "host" else ""
        print(f"{i:3d}. {s.id:34s} {s.politica_falha:18s} ← {', '.join(sorted(deps[s.id])) or '—'}{extra}")
    return 0


def cmd_run(a) -> int:
    cat = _catalogo()
    date = a.date or executor.hoje()
    data = _data_dir(a.data_dir)
    if a.compare:
        rep = cmp_.comparar(cat, date, data, keep=a.keep, work_dir=Path(a.work_dir) if a.work_dir else None)
        saida = Path(a.out) if a.out else data / "ops" / "compare" / f"{date}.json"
        saida.parent.mkdir(parents=True, exist_ok=True)
        saida.write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
        print(cmp_.resumo(rep))
        return 1 if (cmp_.diferencas_novas(rep) or rep.get("etapa_falhou")) else 0
    try:
        rel = executor.executar(cat, date, data, SubprocessRunner({"DATA_DIR": str(data)} if a.data_dir else None),
                                only=a.only, due=a.due, retomar=a.retomar, pin_sources=a.pin_sources, dry_run=a.dry_run, force=a.force, versao=_versao(),
                                publicar=getattr(a, "publicar", False))
    except executor.LockOcupado as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 3
    except KeyError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2
    for e in rel.etapas:
        print(f"  {e.status:18s} {e.id}" + (f"  — {e.motivo}" if e.motivo else ""))
    print(f"arandu {date}: {'ok' if rel.ok else 'ABORTADA em ' + str(rel.abortada_em)}"
          + ("" if a.dry_run else f" — {rel.duracao_s} s — {executor.caminho_relatorio(data, date)}"))
    return 0 if rel.ok else 1


def _alvo(a, campo: str) -> int:
    cat = _catalogo()
    etapas = executor.etapas_de(cat, a.id)
    if not etapas:
        print(f"ERRO: nenhuma etapa produz '{a.id}'", file=sys.stderr)
        return 2
    a.only, a.due, a.retomar, a.pin_sources, a.force, a.compare = etapas, False, False, False, False, False
    a.dry_run = getattr(a, "dry_run", False)
    return cmd_run(a)


def cmd_publish(a) -> int:
    a.only, a.due, a.retomar, a.pin_sources, a.force, a.compare, a.dry_run = ["snapshot_completo"], False, False, False, False, False, False
    return cmd_run(a)


def cmd_status(a) -> int:
    cat = _catalogo()
    linhas = st.status_das_fontes(cat, _data_dir(a.data_dir), a.date or executor.hoje())
    print(json.dumps(linhas, ensure_ascii=False, indent=1) if a.json else st.texto(linhas))
    return 1 if any(l["estado"] == "atrasado" and l["politica_falha"] == "critica" for l in linhas) else 0


def cmd_doctor(a) -> int:
    cat = load_catalog(ROOT / "catalog")
    r = ops.diagnostico(cat, _data_dir(a.data_dir), ROOT, a.date or executor.hoje())
    for x in r:
        print(f"  {x['estado']:6s} {x['nome']:16s} {x['detalhe']}")
    return 1 if any(x["estado"] == "erro" for x in r) else 0


def _cmd_compactar(a, data: Path) -> int:
    """`arandu gc --compactar|--descompactar [--datas D…]`: snapshots antigos em `layout_version` 2, reversível."""
    from arandu import compactacao, retencao

    if a.apply == a.dry_run:
        print("ERRO: informe --dry-run ou --apply.", file=sys.stderr)
        return 2
    base = Path(data)
    pubs = sorted(d.name for d in (base / "published").iterdir() if d.is_dir() and (d / "manifest.json").is_file())
    if a.datas:
        alvos = a.datas
    else:
        try:
            protegidas = set(retencao.carregar(ROOT / "catalog" / "retencao.yaml", a.perfil).protegidas)
        except ValueError as exc:
            print(f"ERRO: {exc}", file=sys.stderr)
            return 2
        alvos = [d for d in pubs[: max(0, len(pubs) - a.manter_recentes)] if d not in protegidas]
    lk = data / "ops" / "arandu.lock"
    if a.apply and lockfile.ocupado(lk) is not None:
        print("ERRO: há uma execução do arandu em andamento (data/ops/arandu.lock): a compactação não roda em paralelo.", file=sys.stderr)
        return 2
    falhou = False
    for d in alvos:
        try:
            if a.descompactar:
                r = compactacao.descompactar(base, d) if a.apply else {"data": d, "estado": "descompactaria"}
            else:
                r = compactacao.compactar(base, d) if a.apply else compactacao.plano(base, d)
        except Exception as exc:  # noqa: BLE001 — uma data com problema não impede as outras; o código de saída acusa
            print(f"  FALHOU {d}: {exc}", file=sys.stderr)
            falhou = True
            continue
        extra = ""
        if r.get("estado") == "compactavel":
            comp = sum(i["bytes"] for i in r["compartilhaveis"])
            extra = f"{r['asns_arquivos']} arquivos em asns/ ({r['asns_bytes'] / 2**20:.0f} MiB) viram 1 ZIP; {len(r['compartilhaveis'])} camadas ({comp / 2**20:.0f} MiB) vão para _shared/"
        elif r.get("estado") == "compactado":
            extra = f"{r['arquivos_removidos']} arquivos → 1 ZIP ({r['zip_bytes'] / 2**20:.0f} MiB); liberou {r['liberado_bytes'] / 2**20:.0f} MiB"
        print(f"  {d}: {r['estado']} {extra}")
    return 1 if falhou else 0


def cmd_gc(a) -> int:
    from arandu import retencao

    data = _data_dir(a.data_dir)
    if a.compactar or a.descompactar:
        return _cmd_compactar(a, data)
    try:
        perfil = retencao.carregar(ROOT / "catalog" / "retencao.yaml", a.perfil)
    except ValueError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2
    if a.apply == a.dry_run:
        print("ERRO: informe --dry-run (lista o que sairia) ou --apply (remove, depois de um --dry-run revisado).", file=sys.stderr)
        return 2
    cat = _catalogo()
    por_fonte = {f.id: f.armazem.manter_versoes for f in cat.sources.values() if f.armazem and f.armazem.manter_versoes}
    p = retencao.plano(data, a.date or executor.hoje(), perfil, por_fonte)
    print(f"perfil '{p['perfil']}': {p['descricao']}")
    for camada, r in p["resumo"].items():
        print(f"  {camada:10s} {r['datas']} data(s); removeria {r['removeriam']}")
    print(f"removeria {len(p['itens'])} item(ns), {p['liberaria_bytes'] / 2**30:.2f} GiB")
    for i in p["itens"]:
        print(f"  - {i['camada']}/{i['item']}  {i['bytes'] / 2**20:.0f} MiB")
    for s_ in p["seguradas_pelos_pisos"]:
        print(f"  = {s_['camada']}/{s_['item']} mantida pelo piso do código: {s_['motivo']}")
    if a.dry_run:
        retencao.registrar_dry_run(data, p)
        return 0
    ativo = lockfile.ocupado(data / "ops" / "arandu.lock") is not None
    try:
        rel = retencao.aplicar(data, p, lock_ativo=ativo)
    except RuntimeError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 2
    print(f"removidos {len(rel['removidos'])}, falhas {len(rel['falhas'])}, liberados {rel['liberados_bytes'] / 2**30:.2f} GiB")
    for f in rel["falhas"]:
        print(f"  FALHOU {f['item']}: {f['erro']}", file=sys.stderr)
    return 1 if rel["falhas"] else 0


def cmd_recomputar_alertas(a) -> int:
    """`arandu build alerts --date D --recompute`: alertas de um snapshot antigo com as regras atuais, em área separada (alerts/)."""
    if not a.recompute:
        print("ERRO: `build alerts` só recalcula alertas de um snapshot já publicado: informe --recompute.", file=sys.stderr)
        return 2
    from api.store import Store
    from core.common import configure_logging
    from products.alerts.recompute import diretorio, recomputar

    data = _data_dir(a.data_dir)
    date = a.date or executor.hoje()
    meta = recomputar(data, date, configure_logging(), Store)
    print(f"alertas de {date} recalculados com as regras {meta['rules_version']} "
          f"(snapshot: {meta['rules_version_do_snapshot'] or 'anterior ao 1.2.8'}): {meta['asns']} ASes, {meta['alertas']} alertas")
    print(f"  {diretorio(data, date)}  conteudo_sha256={meta['conteudo_sha256'][:16]}…")
    return 0


def cmd_source(a) -> int:
    """`arandu source new <id>`: gera uma fonte nova de CSV (catálogo, coletor, amostra e teste)."""
    from arandu import novafonte

    try:
        criados = novafonte.criar(a.id, a.nome or a.id.replace("_", " ").title(), a.url, Path(a.raiz) if a.raiz else ROOT, a.dry_run)
    except (ValueError, FileExistsError) as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1
    for c in criados:
        print(("criaria " if a.dry_run else "criou   ") + c)
    if not a.dry_run:
        print(f"\nPróximos passos: ajuste URL, `parse_csv` e a amostra; rode `pytest tests/sources/test_t1_{a.id}.py`, "
              f"`python3 scripts/gen_docs.py` e `arandu run --only {a.id} --date AAAA-MM-DD`.")
    return 0


def cmd_repair(a) -> int:
    cat = _catalogo()
    date = a.date or executor.hoje()
    data = _data_dir(a.data_dir)
    plano = rp.plano_de_reparo(cat, data, date)
    if not plano["faltam"]:
        print(f"snapshot {date}: todas as {sum(1 for s in cat.steps.values() if s.runner == 'worker')} etapas têm saída primária; nada a reparar.")
        return 0
    print(f"snapshot {date}: sem saída primária: {', '.join(plano['faltam'])}")
    print(f"reexecutaria (com dependentes): {', '.join(plano['reexecutar'])}")
    if a.dry_run:
        return 0
    a.only, a.due, a.retomar, a.pin_sources, a.force, a.compare, a.dry_run = plano["reexecutar"], False, False, False, False, False, False
    return cmd_run(a)


def cmd_store(a) -> int:
    cat = _catalogo()
    data = _data_dir(a.data_dir)
    if a.acao == "list":
        fontes = [a.fonte] if a.fonte else sorted(s.id for s in cat.sources.values() if s.tipo != "curada")
        for f in fontes:
            vs = armazem.listar(data, f)
            ult = armazem.ultima_verificacao(data, f)
            print(f"{f:32} {len(vs):3d} versão(ões)" + (f"  última: {vs[-1].nome} (coletada {vs[-1].coletado_em}); verificada {ult}" if vs else ""))
        return 0
    if a.acao == "resolve":
        v = armazem.resolver(data, a.fonte, a.date or executor.hoje())
        print(json.dumps({"fonte": a.fonte, "versao": v and v.nome, "as_of": v and v.as_of, "coletado_em": v and v.coletado_em,
                          "hash": v and v.hash}, ensure_ascii=False))
        return 0 if v else 1
    if a.acao == "legacy-index":
        datas = ([a.date] if a.date else sorted(p.name for p in (data / "published").iterdir()
                                                  if p.is_dir() and len(p.name) == 10 and p.name[:2] == "20"))
        for d in datas:
            destino = armazem.escrever_indice_legado(cat, data, d, sobrescrever=a.force)
            print(f"{d}: {destino}")
        return 0
    if a.acao == "backfill":
        if not (a.fonte and a.date):
            print("ERRO: backfill exige --source e --date", file=sys.stderr)
            return 2
        r = armazem.registrar_da_fonte(cat, data, a.fonte, a.date, pipeline_version=_versao(), coletado_em=f"{a.date}T00:00:00Z")
        print("sem arquivos para a fonte nessa data" if r is None else f"{a.fonte}: {r[1]} {r[0].nome}")
        return 0 if r else 1
    return 2


def cmd_repasse(nome: str, rest: list[str]) -> int:
    return int(_script(nome).main(rest) or 0)


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="arandu", description=__doc__.splitlines()[0])
    sp = ap.add_subparsers(dest="cmd", required=True)

    def comum(p):
        p.add_argument("--date", help="AAAA-MM-DD (padrão: hoje, UTC)")
        p.add_argument("--data-dir", help="raiz dos dados (padrão: DATA_DIR / config)")

    p = sp.add_parser("plan", help="mostra a ordem calculada das etapas")
    p.add_argument("--only", nargs="+")
    p.set_defaults(f=cmd_plan)
    p = sp.add_parser("run", help="executa o pipeline (--only etapas; --due pela cadência do catálogo; --retomar continua o dia; --compare reexecuta e compara)")
    comum(p)
    p.add_argument("--only", nargs="+", metavar="ETAPA")
    p.add_argument("--due", action="store_true", help="só coleta o que a cadência do catálogo manda; das demais fontes restaura a última versão do armazém")
    p.add_argument("--publicar", action="store_true", help="com --due: abre a janela de publicação (roda análises e produtos mesmo antes do intervalo de ARANDU_PUBLICACAO_DIAS, padrão 7)")
    p.add_argument("--pin-sources", dest="pin_sources", action="store_true", help="reconstrói o snapshot com as versões de fonte fixadas no manifesto (não coleta)")
    p.add_argument("--retomar", action="store_true", help="pula as etapas já concluídas no dia (relatório do arandu)")
    p.add_argument("--force", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--compare", action="store_true", help="reexecuta as etapas reprodutíveis em diretório de teste e compara (critério do replay)")
    p.add_argument("--keep", action="store_true")
    p.add_argument("--work-dir")
    p.add_argument("--out", help="relatório JSON do compare (padrão: data/ops/compare/AAAA-MM-DD.json)")
    p.set_defaults(f=cmd_run)
    for nome, ajuda in (("collect", "executa a etapa de uma fonte"), ("build", "executa a etapa de um produto")):
        p = sp.add_parser(nome, help=ajuda)
        p.add_argument("id")
        comum(p)
        p.add_argument("--dry-run", action="store_true")
        if nome == "build":
            p.add_argument("--recompute", action="store_true",
                           help="`build alerts --recompute`: recalcula os alertas de um snapshot publicado com as regras atuais, em alerts/ (não toca no publicado)")
            p.set_defaults(f=lambda a: cmd_recomputar_alertas(a) if a.id == "alerts" and a.recompute else _alvo(a, "build"))
        else:
            p.set_defaults(f=lambda a, n=nome: _alvo(a, n))
    p = sp.add_parser("publish", help="monta o snapshot (etapa `snapshot_completo`)")
    comum(p)
    p.set_defaults(f=cmd_publish)
    p = sp.add_parser("store", help="armazém de versões de fonte (list | resolve | legacy-index | backfill)")
    p.add_argument("acao", choices=["list", "resolve", "legacy-index", "backfill"])
    p.add_argument("--source", dest="fonte")
    p.add_argument("--force", action="store_true")
    comum(p)
    p.set_defaults(f=cmd_store)
    p = sp.add_parser("repair", help="reexecuta etapas sem saída primária (com dependentes)")
    comum(p)
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(f=cmd_repair)
    p = sp.add_parser("status", help="última versão e frescor por fonte")
    comum(p)
    p.add_argument("--json", action="store_true")
    p.set_defaults(f=cmd_status)
    p = sp.add_parser("doctor", help="disco, inodes, lock, versões, catálogo, última execução")
    comum(p)
    p.set_defaults(f=cmd_doctor)
    p = sp.add_parser("source", help="fontes: `source new <id>` gera uma fonte de CSV do catálogo à publicação (6 arquivos)")
    p.add_argument("acao", choices=["new"])
    p.add_argument("id")
    p.add_argument("--nome")
    p.add_argument("--url", default="https://exemplo.invalid/dados.csv")
    p.add_argument("--raiz", help="grava em outra árvore (padrão: o repositório)")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(f=cmd_source)
    p = sp.add_parser("gc", help="retenção por perfil (catalog/retencao.yaml): --dry-run lista, --apply remove")
    comum(p)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--apply", action="store_true")
    p.add_argument("--perfil", default=None, help="perfil de retenção (padrão: ARANDU_RETENCAO ou o do catálogo)")
    p.add_argument("--compactar", action="store_true", help="snapshots antigos em layout_version 2 (asns.zip + _shared/), com verificação e reversível")
    p.add_argument("--descompactar", action="store_true", help="desfaz --compactar")
    p.add_argument("--datas", nargs="+", help="com --compactar/--descompactar: só estas datas (padrão: todas menos as --manter-recentes mais novas)")
    p.add_argument("--manter-recentes", type=int, default=12, help="com --compactar: nº de snapshots mais recentes que ficam como estão (padrão 12)")
    p.set_defaults(f=cmd_gc)
    for nome in ("replay", "scorecard", "docs", "catalog"):
        sp.add_parser(nome, help=f"envelope de scripts/{ {'docs': 'gen_docs', 'catalog': 'catalog_validate'}.get(nome, nome) }.py", add_help=False)
    return ap


def main(argv: Optional[list[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in ("replay", "scorecard", "docs", "catalog"):
        cmd, rest = argv[0], argv[1:]
        if cmd == "catalog":
            if not rest or rest[0] != "validate":
                print("uso: arandu catalog validate [--json]", file=sys.stderr)
                return 2
            return cmd_repasse("catalog_validate", rest[1:])
        return cmd_repasse({"docs": "gen_docs"}.get(cmd, cmd), rest)
    a = parser().parse_args(argv)
    return int(a.f(a) or 0)


if __name__ == "__main__":
    sys.exit(main())
