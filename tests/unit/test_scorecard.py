# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T0 — scripts/scorecard.py: seções a partir de arquivos de `data/ops` e do publicado."""
import json
from datetime import date

from scripts import scorecard as sc


def _w(p, text):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text if isinstance(text, str) else json.dumps(text))


def test_secoes_sem_fonte_ficam_indisponiveis_e_nao_inventam_numero(tmp_path):
    s = sc.build(sc.ROOT, tmp_path, date(2026, 10, 12))
    for sec in ("pipeline", "disco", "uso", "coleta", "replay"):
        assert s[sec]["estado"] == "indisponivel", sec
    md = sc.to_markdown(s)
    assert md.count("indisponível") >= 5


def test_pipeline_disco_uso_e_coleta(tmp_path):
    _w(tmp_path / "ops/runs/2026-10-12.json", {"duracao_s": 3300, "ok": True, "etapas": [
        {"id": "lg_ixbr", "status": "ok", "duracao_s": 120}, {"id": "snapshot_completo", "status": "ok", "duracao_s": 3000},
        {"id": "peeringdb_networks", "status": "falha", "duracao_s": 60}]})
    _w(tmp_path / "ops/disk/2026-10-12.json", {"date": "2026-10-12", "data_total_kb": 2 * 1048576,
                                               "by_type": {"raw": 1048576, "published": 1048576},
                                               "by_date": {"published": {"2026-10-05": 1, "2026-10-12": 1}},
                                               "df": {"use_pct": 35, "avail_kb": 1048576}, "inodes": {"use_pct": 18}})
    usage = [{"ts": "2026-10-12T01:00:00Z", "src": "api", "route": "/api/v1/ixps", "status": 200, "bytes": 100, "ms": 10, "tier": "anon"},
             {"ts": "2026-10-12T01:00:01Z", "src": "api", "route": "/api/v1/ixps", "status": 200, "bytes": 300, "ms": 30, "tier": "allowed"},
             {"ts": "2026-10-12T01:00:02Z", "src": "mcp", "route": "tool:get_asn", "status": "erro", "bytes": None, "ms": 5, "tier": None}]
    _w(tmp_path / "ops/usage/2026-10-12.jsonl", "\n".join(json.dumps(u) for u in usage))
    _w(tmp_path / "published/2026-10-05/manifest.json", {"ixps_configured": ["sp"], "ixps_collected": ["sp"]})
    _w(tmp_path / "published/2026-10-12/manifest.json", {
        "ixps_configured": ["sp", "rj"], "ixps_collected": ["sp"], "coleta": "parcial", "coleta_ok": False,
        "checks": {"ptt_coletados": {"status": "falha"}, "vrps": {"status": "ok"}}, "pipeline_version": "1.1.5"})

    s = sc.build(sc.ROOT, tmp_path, date(2026, 10, 12))
    p = s["pipeline"]
    assert p["duracao_total_s"] == 3300 and p["falhas"] == ["peeringdb_networks"] and p["mais_lentas"][0] == {"etapa": "snapshot_completo", "duracao_s": 3000}
    d = s["disco"]
    assert d["total_data_gib"] == 2.0 and d["snapshots_publicados"] == 2 and d["disco_usado_pct"] == 35
    u = s["uso"]
    assert u["chamadas"] == 3 and u["erros_5xx"] == 1 and u["por_origem"] == {"api": 2, "mcp": 1}
    assert u["rotas_mais_usadas"][0]["rota"] == "/api/v1/ixps" and u["rotas_mais_usadas"][0]["bytes_medio"] == 200
    c = s["coleta"]
    assert c["ultimo"] == "2026-10-12" and c["snapshots"] == 2 and c["coleta"] == "parcial" and c["falhas"] == ["ptt_coletados"]
    md = sc.to_markdown(s)
    assert "snapshot_completo" in md and "parcial" in md and "ptt_coletados" in md


def test_usage_since_ignora_chamadas_antigas(tmp_path):
    _w(tmp_path / "ops/usage/2026-10-12.jsonl", "\n".join(json.dumps(u) for u in [
        {"ts": "2026-10-12T00:00:00Z", "route": "/a", "ms": 1}, {"ts": "2026-10-12T05:00:00Z", "route": "/b", "ms": 2}]))
    u = sc.secao_uso(tmp_path, date(2026, 10, 12), desde="2026-10-12T04:00:00Z")
    assert u["chamadas"] == 1 and u["rotas_mais_usadas"][0]["rota"] == "/b"


def test_percentil():
    assert sc._pctl([], 0.5) is None
    assert sc._pctl([10, 20, 30, 40, 50], 0.5) == 30
    assert sc._pctl([1, 2, 3, 4, 100], 0.95) == 100


def test_secao_fase2_traz_as_metas_do_1_2_9():
    from pathlib import Path
    f2 = sc.secao_fase2(Path(__file__).resolve().parents[2])
    assert f2["camadas"]["quebrados"] == 0 and f2["camadas"]["mantidos"] >= 5
    assert f2["documentacao"]["pct"] >= 90 and f2["alertas"]["regras"] == 23
    assert f2["maior_arquivo_de_build"]["linhas"] > 0 and f2["escritas_por_arquivo"]["meta"] == 1
    assert "## Metas da fase 2" in sc.to_markdown({**sc.build(Path(__file__).resolve().parents[2], Path("/nao/existe"), __import__("datetime").date(2026, 10, 24)), "fase2": f2})


def test_testes_indisponivel_quando_nada_e_coletado(tmp_path):
    """Sem pytest ou sem pasta `tests/` a seção sai como indisponível — nunca '0 testes' (regra do painel)."""
    from scripts import scorecard
    r = scorecard.secao_testes(tmp_path, run=False)
    assert r["estado"] == "indisponivel" and "nenhum teste coletado" in r["motivo"]


def test_historico_indisponivel_sem_dados_e_resume_eventos_por_tipo(tmp_path):
    import gzip

    assert sc.secao_historico(tmp_path)["estado"] == "indisponivel"
    h = tmp_path / "history"
    _w(h / "index.json", {"schema_version": 1, "snapshots": [{"date": "2026-10-30", "coleta": "completa", "asn_linhas": 2, "eventos_n": 2}]})
    (h / "weekly/2026-10-30").mkdir(parents=True)
    (h / "weekly/2026-10-30/asn.jsonl.gz").write_bytes(gzip.compress(b"{}\n"))
    (h / "events").mkdir()
    (h / "events/2026-10-30.jsonl.gz").write_bytes(gzip.compress(
        b'{"tipo":"asn_novo","estado":"confirmado"}\n{"tipo":"asn_novo","estado":"pendente"}\n'))
    r = sc.secao_historico(tmp_path)
    assert r["estado"] == "ok" and r["eventos_por_tipo"] == {"asn_novo": {"confirmado": 1, "pendente": 1}}
    md = sc.to_markdown(sc.build(sc.ROOT, tmp_path, date(2026, 10, 31)))
    assert "## Histórico" in md and "asn_novo" in md
