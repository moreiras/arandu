# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Contas, chave de MCP, limite de tentativas e uso por conta: unidade, sem rede e sem dado real. A chave só existe na memória do teste."""
from datetime import date, datetime, timedelta, timezone

import pytest

from api import uso_conta
from api.auth import chaves_mcp, contas, sessao, storage
from api.auth.manutencao import executar
from api.auth.tentativas import BLOQUEIO_S, FALHAS_GLOBAIS, FALHAS_POR_CLIENTE, LimiteTentativas

PEPPER = "p" * 40


@pytest.fixture(autouse=True)
def _env(monkeypatch):
    monkeypatch.setenv("MCP_KEY_ATIVA", "1")
    monkeypatch.setenv("MCP_KEY_PEPPER", PEPPER)
    sessao.limpar_cache()


# ── contas ────────────────────────────────────────────────────────────────

def test_login_cria_conta_com_uuid_e_atualiza_o_acesso(tmp_path):
    c = contas.registrar_login(tmp_path, "a@example.org", "A", "google")
    assert len(c.conta_id) == 36 and c.email == "a@example.org"
    c2 = contas.registrar_login(tmp_path, "a@example.org", "A2", "google")
    assert c2.conta_id == c.conta_id and c2.nome == "A2"


def test_exclusao_nunca_e_imediata_conta_fica_desativada_e_o_login_e_recusado(tmp_path):
    c = contas.registrar_login(tmp_path, "a@example.org", "A", "google")
    pedida = contas.solicitar_exclusao(tmp_path, c.conta_id)
    assert pedida.desativada and pedida.exclusao_efetiva_em() == (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%d")
    assert contas.registrar_login(tmp_path, "a@example.org", "A", "google") is None            # não dá para recriar nem entrar no prazo
    assert contas.por_id(tmp_path, c.conta_id) is not None                                 # o registro continua (a prevenção de abuso depende dele)
    assert contas.vencidas(tmp_path) == []
    assert [x.conta_id for x in contas.vencidas(tmp_path, datetime.now(timezone.utc) + timedelta(days=31))] == [c.conta_id]


def test_pedido_repetido_nao_reinicia_o_prazo(tmp_path):
    c = contas.registrar_login(tmp_path, "a@example.org", "A", "google")
    a = contas.solicitar_exclusao(tmp_path, c.conta_id).exclusao_solicitada_em
    assert contas.solicitar_exclusao(tmp_path, c.conta_id).exclusao_solicitada_em == a


def test_sair_de_todos_invalida_token_anterior(tmp_path):
    c = contas.registrar_login(tmp_path, "a@example.org", "A", "google")
    antes = int(datetime.now(timezone.utc).timestamp()) - 5
    assert contas.sessao_valida(contas.por_id(tmp_path, c.conta_id), antes)
    contas.sair_de_todos(tmp_path, c.conta_id)
    assert not contas.sessao_valida(contas.por_id(tmp_path, c.conta_id), antes)
    assert contas.sessao_valida(contas.por_id(tmp_path, c.conta_id), int(datetime.now(timezone.utc).timestamp()) + 1)


def test_jwt_antigo_sem_cid_resolve_pelo_email(tmp_path):
    from api.auth.jwt_utils import create_token
    t = create_token("velho@example.org", "V", "google", "s" * 32)
    u = sessao.usuario_do_cookie(t, "s" * 32, tmp_path)
    assert u and u["conta_id"] == contas.por_email(tmp_path, "velho@example.org").conta_id


# ── chave de MCP ──────────────────────────────────────────────────────────

def test_chave_tem_formato_e_valida_so_enquanto_ativa(tmp_path):
    chave, meta = chaves_mcp.gerar(tmp_path, "conta-1", "meu cliente")
    from core.site import prefixo_chave_mcp
    assert chave.startswith(prefixo_chave_mcp() + meta["id"] + "_") and len(chave.split("_")[-1]) >= 52     # 256 bits em base32
    assert chaves_mcp.verificar(tmp_path, chave) == "conta-1"
    assert chaves_mcp.verificar(tmp_path, chave + "A") is None
    assert chaves_mcp.verificar(tmp_path, "arandu_mcp_XXXXXXXX_" + chave.split("_")[-1]) is None
    assert chaves_mcp.verificar(tmp_path, "qualquer") is None and chaves_mcp.verificar(tmp_path, "") is None
    assert chaves_mcp.revogar(tmp_path, "conta-1") is True
    assert chaves_mcp.verificar(tmp_path, chave) is None



def test_prefixo_segue_o_esquema_do_site_e_chave_antiga_continua_valida(tmp_path, monkeypatch):
    """O prefixo vem de SITE_MCP_ESQUEMA; quem autentica é id + segredo, então mudar o esquema não derruba as chaves emitidas."""
    from core import site
    from core.site import FORMATO_CHAVE_MCP, carregar, prefixo_chave_mcp
    assert prefixo_chave_mcp(carregar({"SITE_MCP_ESQUEMA": "exemplo"})) == "exemplo_mcp_"
    assert prefixo_chave_mcp(carregar({"SITE_MCP_ESQUEMA": "Exemplo Brasil"})) == "exemplo-brasil_mcp_"
    monkeypatch.setattr(site, "SITE", carregar({"SITE_MCP_ESQUEMA": "exemplo"}))
    chave, meta = chaves_mcp.gerar(tmp_path, "conta-2")
    assert chave.startswith("exemplo_mcp_" + meta["id"] + "_")
    segredo = chave.split("_")[-1]
    for prefixo in ("arandu_mcp_", "arandurape_mcp_", "exemplo_mcp_"):             # chaves emitidas antes da troca do esquema
        assert chaves_mcp.verificar(tmp_path, f"{prefixo}{meta['id']}_{segredo}") == "conta-2"
    assert chaves_mcp.verificar(tmp_path, f"EXEMPLO_mcp_{meta['id']}_{segredo}") is None   # fora do formato
    assert not FORMATO_CHAVE_MCP.fullmatch("_mcp_" + meta["id"] + "_" + segredo)


def test_rotacao_revoga_a_anterior_e_so_ha_uma_ativa(tmp_path):
    velha, _ = chaves_mcp.gerar(tmp_path, "c")
    nova, meta = chaves_mcp.gerar(tmp_path, "c")
    assert chaves_mcp.verificar(tmp_path, velha) is None and chaves_mcp.verificar(tmp_path, nova) == "c"
    assert chaves_mcp.da_conta(tmp_path, "c")["id"] == meta["id"]


def test_banco_nao_guarda_a_chave_nem_o_segredo(tmp_path):
    chave, _ = chaves_mcp.gerar(tmp_path, "c")
    segredo = chave.split("_")[-1]
    chaves_mcp.verificar(tmp_path, chave)
    for arq in (tmp_path / "auth").glob("*"):
        assert segredo.encode() not in arq.read_bytes(), arq
    meta = chaves_mcp.da_conta(tmp_path, "c")
    assert "hash" not in meta and segredo not in str(meta)


def test_sem_pepper_a_chave_fica_desligada(tmp_path, monkeypatch):
    monkeypatch.setenv("MCP_KEY_PEPPER", "curto")
    assert not chaves_mcp.ativa()
    with pytest.raises(RuntimeError):
        chaves_mcp.gerar(tmp_path, "c")


def test_pepper_diferente_nao_valida_chave_antiga(tmp_path, monkeypatch):
    chave, _ = chaves_mcp.gerar(tmp_path, "c")
    monkeypatch.setenv("MCP_KEY_PEPPER", "q" * 40)
    assert chaves_mcp.verificar(tmp_path, chave) is None


def test_ultimo_uso_e_so_o_dia(tmp_path):
    chave, _ = chaves_mcp.gerar(tmp_path, "c")
    assert chaves_mcp.da_conta(tmp_path, "c")["ultimo_uso_dia"] is None
    chaves_mcp.verificar(tmp_path, chave)
    assert chaves_mcp.da_conta(tmp_path, "c")["ultimo_uso_dia"] == datetime.now(timezone.utc).strftime("%Y-%m-%d")


# ── limite de tentativas ──────────────────────────────────────────────────

def test_dez_falhas_bloqueiam_o_cliente_e_o_bloqueio_dobra_na_reincidencia():
    t = [0.0]
    lim = LimiteTentativas(lambda: t[0])
    for _ in range(FALHAS_POR_CLIENTE):
        lim.falha("x")
    assert lim.espera("x") == BLOQUEIO_S and lim.espera("outro") is None
    t[0] += BLOQUEIO_S + 1
    assert lim.espera("x") is None
    for _ in range(FALHAS_POR_CLIENTE):
        lim.falha("x")
    assert lim.espera("x") == BLOQUEIO_S * 2


def test_sucesso_zera_as_falhas_e_o_limite_global_satura():
    lim = LimiteTentativas(lambda: 0.0)
    for _ in range(FALHAS_POR_CLIENTE - 1):
        lim.falha("x")
    lim.sucesso("x")
    lim.falha("x")
    assert lim.espera("x") is None
    g = LimiteTentativas(lambda: 0.0)
    for i in range(FALHAS_GLOBAIS):
        g.falha(f"c{i}")
    assert g.saturado()


# ── uso por conta ─────────────────────────────────────────────────────────

def test_registro_de_uso_nao_tem_ip_nem_querystring_e_resume_por_dia(tmp_path):
    uso_conta.registrar(tmp_path, "c1", "api", "/api/v1/asns?q=segredo", 200, 10, 3.2, "metered")
    uso_conta.registrar(tmp_path, "c1", "mcp", "/mcp", 200)
    uso_conta.registrar(tmp_path, "c2", "site", "/api/v1/ixps", 200)
    texto = next((tmp_path / "ops" / "uso_conta").glob("*.jsonl")).read_text()
    assert "segredo" not in texto and "ip" not in texto.replace("ts", "").lower().split('"conta"')[0]
    assert uso_conta.resumo_dias(tmp_path, "c1")[-1]["chamadas"] == 2 and uso_conta.chamadas_no_dia(tmp_path, "c2") == 1


def test_manutencao_agrega_o_detalhe_com_mais_de_90_dias_e_descarta_agregado_de_mais_de_12_meses(tmp_path):
    d = tmp_path / "ops" / "uso_conta"
    d.mkdir(parents=True)
    hoje = date(2026, 11, 12)
    velho, recente, antigo = (hoje - timedelta(days=100)).isoformat(), (hoje - timedelta(days=5)).isoformat(), (hoje - timedelta(days=400)).isoformat()
    ln = '{"ts":"x","conta":"c1","origem":"api","rota":"/r","status":200,"bytes":0,"ms":1,"classe":"login"}\n'
    (d / f"{velho}.jsonl").write_text(ln * 3)
    (d / f"{recente}.jsonl").write_text(ln)
    (d / "agregado.jsonl").write_text(f'{{"dia":"{antigo}","conta":"c1","origem":"api","classe":"login","n":9}}\n')
    r = uso_conta.manutencao(tmp_path, hoje)
    assert r["detalhes_apagados"] == 1 and not (d / f"{velho}.jsonl").exists() and (d / f"{recente}.jsonl").exists()
    agg = (d / "agregado.jsonl").read_text()
    assert f'"dia":"{velho}"' in agg and '"n":3' in agg and antigo not in agg


def test_apagar_conta_remove_o_detalhe_e_anonimiza_as_contagens(tmp_path):
    uso_conta.registrar(tmp_path, "c1", "api", "/r", 200)
    uso_conta.registrar(tmp_path, "c2", "api", "/r", 200)
    (tmp_path / "ops" / "uso_conta" / "agregado.jsonl").write_text('{"dia":"2026-01-01","conta":"c1","origem":"api","classe":"x","n":4}\n')
    r = uso_conta.apagar_conta(tmp_path, "c1")
    assert r == {"linhas_apagadas": 1, "agregados_anonimizados": 1}
    todo = "".join(p.read_text() for p in (tmp_path / "ops" / "uso_conta").glob("*"))
    assert "c1" not in todo and "c2" in todo and '"n":4' in todo


def test_manutencao_de_contas_apaga_tudo_depois_dos_30_dias(tmp_path):
    storage.upsert_user(tmp_path, "a@example.org", "A", "google")
    c = contas.registrar_login(tmp_path, "a@example.org", "A", "google")
    chaves_mcp.gerar(tmp_path, c.conta_id)
    uso_conta.registrar(tmp_path, c.conta_id, "api", "/r", 200)
    contas.solicitar_exclusao(tmp_path, c.conta_id)
    assert executar(tmp_path)["contas_apagadas"] == 0
    r = executar(tmp_path, datetime.now(timezone.utc) + timedelta(days=31))
    assert r["contas_apagadas"] == 1
    assert contas.por_id(tmp_path, c.conta_id) is None and chaves_mcp.da_conta(tmp_path, c.conta_id) is None
    assert "a@example.org" not in (tmp_path / "auth" / "emails.csv").read_text()
    assert c.conta_id not in "".join(p.read_text() for p in (tmp_path / "ops" / "uso_conta").glob("*"))
