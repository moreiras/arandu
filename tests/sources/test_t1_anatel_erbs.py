# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T1 — Anatel, estações do SMP licenciadas: amostra sintética no layout real, sem rede."""
import io
import zipfile

import httpx
import pytest
import respx

from core import erbs
from core.common import read_json_gz
from sources.anatel_erbs import collect as fonte


class _Log:
    def info(self, *a, **k): pass
    warning = info


def _csv(fx) -> io.BytesIO:
    with zipfile.ZipFile(fx("anatel_erbs", "estacoes_smp_sintetico.zip")) as z:
        return io.BytesIO(z.read(z.namelist()[0]))


def _por_chave(fx):
    est, resumo = erbs.consolidar(_csv(fx))
    return {e["estacao"]: e for e in est}, resumo


def test_uma_linha_por_estacao_e_ibge_vem_da_unica_copia_preenchida(fx):
    est, resumo = _por_chave(fx)
    assert resumo["estacoes"] == 12 and resumo["linhas"] == 3 * sum(e["combinacoes"] for e in est.values())
    assert est["1001"]["ibge"] == "3550308" and est["1001"]["uf"] == "SP" and est["1001"]["linhas"] == 12 and est["1001"]["combinacoes"] == 4
    assert est["5004"]["ibge"] is None and resumo["sem_ibge"] == 1


def test_tecnologias_geracoes_faixas_e_5g(fx):
    est, _ = _por_chave(fx)
    v = est["1001"]
    assert v["geracoes"] == ["2G", "3G", "4G"] and v["tecnologias"] == ["GSM", "LTE", "WCDMA"] and v["faixas"] == ["1800", "2100", "2500"] and v["setores"] == 3
    assert est["1002"]["geracoes"] == ["4G", "5G"] and est["1002"]["tipo_5g"] == ["SA-NSA"] and est["2002"]["tipo_5g"] == ["NSA"] and est["4001"]["tipo_5g"] == ["SA"]
    assert est["3002"]["geracoes"] == ["2G"] and est["3002"]["setores"] == 0 and est["1002"]["primeira_licenca"] == 2022 and est["1001"]["infra"] == "Rooftop"


def test_cnpj_em_branco_nas_linhas_vem_da_marca(fx):
    est, resumo = _por_chave(fx)
    assert est["3002"]["cnpj"] == "02421421000111" == resumo["cnpj_da_marca"]["TIM"] and est["2001"]["cnpj"] == "40432544000147"
    assert all(e["cnpj"] for e in est.values())


def test_posicao_ausente_fora_do_brasil_e_variavel(fx):
    est, resumo = _por_chave(fx)
    assert est["5001"]["lat"] is None and est["5002"]["lat"] is None and resumo["sem_posicao"] == 1 and resumo["fora_do_brasil"] == 1
    assert est["5003"]["posicao_variavel"] and est["5003"]["lat"] in (-25.43, -25.44) and resumo["posicao_variavel"] == 1
    assert est["1001"]["lat"] == -23.55 and est["1001"]["lon"] == -46.63


def test_coluna_ausente_falha_alto():
    with pytest.raises(ValueError, match="colunas ausentes"):
        erbs.consolidar(io.BytesIO("a;b\n1;2\n".encode()))


def test_coleta_baixa_guarda_o_zip_e_valida_o_tamanho(fx, tmp_path, monkeypatch):
    zip_bytes = fx("anatel_erbs", "estacoes_smp_sintetico.zip").read_bytes()
    with respx.mock:
        respx.get(fonte.URL).mock(return_value=httpx.Response(200, content=zip_bytes, headers={"last-modified": "Sun, 01 Nov 2026 10:52:35 GMT"}))
        with pytest.raises(RuntimeError, match="esperado ≥"):                       # 12 estações < mínimo: protege contra arquivo truncado
            fonte.run("2026-11-02", tmp_path, _Log())
        monkeypatch.setattr(fonte, "MINIMO_ESTACOES", 10)
        monkeypatch.setattr(fonte, "MAX_SEM_POSICAO", 0.5)
        r = fonte.run("2026-11-02", tmp_path, _Log())
    assert r["estacoes"] == 12
    assert (tmp_path / "raw" / "2026-11-02" / "summary" / "estacoes_smp-2026-11-02.zip").read_bytes() == zip_bytes
    doc = read_json_gz(tmp_path / "normalized" / "2026-11-02" / "summary" / "anatel_erbs.json.gz")
    assert doc["data_arquivo"].startswith("Sun, 01 Nov 2026") and len(doc["estacoes"]) == 12 and len(doc["sha256"]) == 64
