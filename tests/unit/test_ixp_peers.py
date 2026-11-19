# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Estatísticas por peer: a função do core, o arquivo gravado por `bgp_ixp`/preenchimento e o caminho da API dão o mesmo número."""
import structlog

from api.store import Store
from core.common import normalized_path, read_json_gz, write_json_gz
from core.ixp_peers import espaco, estatisticas_por_peer
from products.bgp_routes.peers_stats import preencher

ROTAS = [
    {"prefix": "10.0.0.0/22", "aspath": [100, 100]},       # próprio do peer 100 (4 × /24)
    {"prefix": "10.1.0.0/24", "aspath": [100, 200]},       # de terceiro, originado por 200
    {"prefix": "10.2.0.0/25", "aspath": [100, 300]},       # mais específico que /24: não conta no espaço
    {"prefix": "10.3.0.0/16", "aspath": [400, 400]},
    {"prefix": "", "aspath": [500, 500]},                  # sem prefixo: ignorada
    {"prefix": "10.9.0.0/24", "aspath": []},               # sem AS_PATH: ignorada
]


def test_estatisticas_por_peer_conta_proprios_terceiros_e_espaco():
    r = estatisticas_por_peer(ROTAS, "v4")
    assert set(r) == {"100", "400"}
    assert r["100"] == {"total_prefixes": 3, "own_prefixes": 1, "third_prefixes": 2, "origin_asns": 3,
                        "own_space_24": 4, "third_space_24": 1}
    assert r["400"]["own_space_24"] == 256
    assert espaco(["2001:db8::/32", "10.0.0.0/8"], "v6") == 1 << 16     # v6 só conta v6, até /48


def test_arquivo_gravado_e_o_caminho_da_api_dao_o_mesmo_resultado(tmp_path):
    data = "2026-09-20"
    rotas = normalized_path(tmp_path, data, "sp") / "routes-v4.json.gz"
    rotas.parent.mkdir(parents=True)
    write_json_gz(rotas, {"routes": ROTAS})
    store = Store(tmp_path)
    sem_arquivo = store.ixp_peers_stats(data, "sp", "v4")                  # recalcula das rotas
    r = preencher(data, tmp_path, structlog.get_logger())
    assert r == {"gravados": 1, "ja_existiam": 0}
    assert preencher(data, tmp_path, structlog.get_logger()) == {"gravados": 0, "ja_existiam": 1}
    assert read_json_gz(rotas.parent / "peers-v4.json.gz") == sem_arquivo
    com_arquivo = Store(tmp_path).ixp_peers_stats(data, "sp", "v4")        # lê o arquivo
    assert com_arquivo == sem_arquivo
    # com o arquivo presente as rotas nem são relidas
    rotas.write_bytes(b"")
    assert Store(tmp_path).ixp_peers_stats(data, "sp", "v4") == sem_arquivo
