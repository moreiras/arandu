# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""T0 — resumo e perfil das UFs (`api/services/perfis.py`): contagem de PTT e distância com a mesma lista (EST-E1) e ausência de SICI
como ausência, não zero (EST-E2)."""
from api.services.perfis import PerfisService

D = "2026-08-30"


class _Store:
    def __init__(self, ixps, pix, sici):
        self._ixps, self._pix, self._sici = ixps, pix, sici

    def ixp_index(self, d):
        return self._ixps

    def _pix_features(self, d):
        return [{"geometry": {"coordinates": [lon, lat]}, "properties": {"ixp_code": c, "ixp_name": c}} for c, lon, lat in self._pix]

    def sici_municipios(self, d):
        return self._sici

    def sici_meta(self, d):
        return {"mes_referencia": "2026-06"} if self._sici else None

    def operadora_index(self, d):
        return []

    def _load_sici(self, d):          # operadoras_presentes_uf (PT-05) lê o SICI fixo; aqui o teste não depende dele
        return None


def _svc(ixps, pix, sici):
    s = PerfisService(_Store(ixps, pix, sici))
    s.asns_por_uf = lambda d: {"AP": {"quantidade": 3, "usuarios": 10}}
    s.territorio_linhas = lambda d: []
    s._centroides = {"1600303": [-51.07, 0.03], "1600055": [-51.40, 1.0]}       # Macapá e um município a ~120 km
    return s


SICI_AP = {"1600303": {"uf": "AP", "acessos": 100, "nome": "Macapá"}, "1600055": {"uf": "AP", "acessos": 5, "nome": "Serra do Navio"}}


def test_ptt_sem_coleta_conta_na_uf_e_na_distancia_igualmente():
    """AP com o PTT `ap` em status missing: a contagem dava 0 ("sem PTT na UF") e a distância usava o PTT (12 municípios "longe")."""
    s = _svc([{"code": "ap", "uf": "AP", "status": "missing"}], [("ap", -51.07, 0.03)], SICI_AP)
    linha = next(r for r in s.resumo_ufs(D) if r["uf"] == "AP")
    assert linha["ptts"] == 1 and linha["ptts_com_coleta"] == 0
    perfil = s.perfil_uf(D, "AP")
    assert len(perfil["ixps"]) == linha["ptts"]
    assert linha["municipios_sem_ptt"] == perfil["totais"]["municipios_sem_ptt"] == 1


def test_pix_de_ptt_fora_do_snapshot_nao_entra_na_distancia():
    """PTT que ainda não existia no snapshot (fora do `ixps/index.json` da data) não serve de PTT mais próximo."""
    s = _svc([{"code": "rr", "uf": "RR", "status": "ok"}], [("ap", -51.07, 0.03), ("rr", -60.67, 2.82)], SICI_AP)
    perfil = s.perfil_uf(D, "AP")
    assert {m["ptt_codigo"] for m in perfil["municipios"]} == {"rr"}
    linha = next(r for r in s.resumo_ufs(D) if r["uf"] == "AP")
    assert linha["ptts"] == 0 and linha["municipios_sem_ptt"] == 2


def test_snapshot_sem_sici_devolve_ausencia_e_nao_zero():
    s = _svc([{"code": "ap", "uf": "AP", "status": "ok"}], [("ap", -51.07, 0.03)], {})
    linha = next(r for r in s.resumo_ufs(D) if r["uf"] == "AP")
    assert linha["ptts"] == 1 and linha["asns"] == 3
    assert linha["acessos"] is None and linha["municipios"] is None and linha["municipios_sem_ptt"] is None and linha["fibra_pct"] is None
    t = s.perfil_uf(D, "AP")["totais"]
    assert t["acessos"] is None and t["municipios"] is None and t["municipios_sem_ptt"] is None and t["acessos_sem_ptt"] is None
    assert t["asns"] == 3


def test_sem_nenhum_ptt_georreferenciado_a_distancia_e_ausente():
    s = _svc([{"code": "ap", "uf": "AP", "status": "ok"}], [], SICI_AP)
    linha = next(r for r in s.resumo_ufs(D) if r["uf"] == "AP")
    assert linha["acessos"] == 105 and linha["municipios_sem_ptt"] is None
