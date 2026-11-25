# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Textos que afirmavam o que o dado não mede não voltam ao código.

Cada entrada é um texto que já esteve na interface, na API ou na documentação e descrevia outra coisa que o dado (data fixa de
início do histórico, persistência que não vale para todos os tipos, rótulo de contagem com outra origem…). A busca é textual nos
fontes, fora dos arquivos de teste, que podem citar o texto antigo para provar que ele sumiu.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
EXTS = {".ts", ".tsx", ".py", ".md", ".yaml", ".yml"}

# (expressão, onde procurar, motivo)
PROIBIDOS: list[tuple[str, tuple[str, ...], str]] = [
    (r"outubro de 2026|começou (a ser guardado )?em 2026-10|a partir de 2026-10",
     ("frontend/src", "mcp_server", "api"), "TRANSV-E7: a data inicial vem da lista de snapshots"),
    (r"persistiu por mais de um",
     ("frontend/src",), "MUD-E1: tipos de janela 1 nascem confirmados"),
    (r"colet\w* \(junho de 2026\)",
     ("products/ipv4", "catalog/sources/ipv4_listas.yaml", "docs/fontes/ipv4_listas.md", "api/query_catalogo.py"), "IPV4-E4: a coleta das listas começou em 2026-11-01"),
    (r"(acessos de telefonia fixa \(STFC\)|TV por assinatura \(SeAC\)) declarados à Anatel",
     ("frontend/src/pages/PanoramaMercado.tsx",), "PANORAMA-E3: STFC e SeAC não têm acessos declarados nesta página"),
    (r"~1\.[47]00 CNPJs",
     ("frontend/src/components/stats",), "PANORAMA-E3: a contagem de CNPJs vem do dado"),
    (r"ausentes do BGP|autonomiza|autônomos no BGP|viraram AS",
     ("frontend/src", "api"), "PANORAMA-E4: o critério é ASN no Registro.br com o mesmo CNPJ, não presença no BGP"),
    (r"peering direto observado",
     ("frontend/src/features/ptt/blocks/ConteudoBloco.tsx", "api/services/interconexao.py", "api/routes/cdns.py"),
     "CDN-E2/CDNS-E1: a presença de CDN é a lista de membros do IX.br"),
    (r"CDN da matriz tem peering direto|ASNs com peering direto aqui",
     ("frontend/src",), "CDNS-E1: a coluna mede sessão com o route server"),
    (r"anunciam prefixos em",
     ("frontend/src/features/localizador",), "LOC-E2: `o` é originação vista no route server, não anúncio próprio"),
    (r"'Atualizado em', value: data\.last_updated",
     ("frontend/src/pages/ExternalIXPPage.tsx",), "IXE-E3: last_updated é a data do snapshot"),
    (r"ASN alocados pelo Registro\.br|'ASN BR no IX\.br'",
     ("frontend/src/pages/Snapshots.tsx",), "SNAP-E1/SNAP-E2: rótulo diferente do campo"),
    (r"quanto mais escuro, maior|Mais escuro = mais isolamento|mais escuro = menor",
     ("frontend/src/features/estados", "frontend/src/lib"), "HOME-E10/EST-E3: a escala vai do roxo (menor) ao amarelo (maior)"),
    (r"Data da outorga do serviço|label: 'Outorga'",
     ("frontend/src/features/operadoras/servicos.tsx",), "OPERADORAS-E6: data do cadastro da Anatel, não da outorga original"),
    (r"peering via Route Server ou bilateral",
     ("frontend/src/pages/ASes.tsx",), "ASES-E2: ixps_direct é sessão com o route server"),
    (r"Execute o pipeline|Pipeline completo:|summary\.json não disponível|📭",
     ("frontend/src/pages", "frontend/src/components/layout", "frontend/src/features/panorama"), "TRANSV-E15: instrução de operador na vista pública"),
    (r"ASes brasileiros alocados|ASNs? alocados pelo Registro\.br|ASNs BR alocados|ASNs brasileiros segundo o Registro\.br",
     ("frontend/src", "api", "mcp_server"), "TRANSV-E4/PT-15: 9.129 é a delegação da LACNIC ao Brasil (is_br); a lista do Registro.br tem 9.150"),
    (r"ASNs em peering direto|Participantes diretos|Direto em PTT|usuários brasileiros visíveis via este IXP",
     ("frontend/src",), "PT-15: sessão em route server não é peering direto, e usuários por PTT são alcançáveis e não aditivos"),
    (r"[Pp]eering direto|[Pp]eers? diretos?",
     ("frontend/src",), "PT-15: sessão com o route server (`asn_direct`) não é peering direto, e o cadastro de participantes é outro universo; os rótulos vêm de `RELACAO_PTT` em `lib/universos.ts`"),
    (r"\bpares? diretos?\b",
     ("frontend/src", "api", "mcp_server"), "PT-15: sessão com o route server (`direto`, do looking glass) não é par nem peering direto; membro do cadastro é outro universo"),
    (r"nunca transitiva|controla quem",
     ("frontend/src", "api", "mcp_server"), "GRUPO-E4: o grupo é componente conexo (cadeia de ligações) e não mede controle"),
]


def _fontes(pastas: tuple[str, ...]):
    for pasta in pastas:
        base = RAIZ / pasta
        arquivos = [base] if base.is_file() else base.rglob("*")
        for p in arquivos:
            if p.suffix not in EXTS or not p.is_file() or "node_modules" in p.parts:
                continue
            if ".test." in p.name or p.name.startswith("test_"):
                continue
            yield p


@pytest.mark.parametrize("expr,pastas,motivo", PROIBIDOS, ids=[m.split(":")[0] for _, _, m in PROIBIDOS])
def test_texto_antigo_nao_volta(expr, pastas, motivo):
    rx = re.compile(expr, re.IGNORECASE)
    achados = []
    for p in _fontes(pastas):
        for n, linha in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if rx.search(linha):
                achados.append(f"{p.relative_to(RAIZ)}:{n}: {linha.strip()[:120]}")
    assert not achados, f"{motivo}\n" + "\n".join(achados)


def test_janelas_de_confirmacao_conferem_com_o_texto_de_mudancas():
    """O "Como ler" de /mudancas enumera os tipos confirmados no snapshot em que aparecem; mudou a janela, revise o texto."""
    from products.history.eventos import TIPOS
    janela_1 = {t for t, (janela, _) in TIPOS.items() if janela == 1}
    assert janela_1 == {"ixp_entrada", "ixp_saida", "roa_ganho", "roa_perdido", "aspa_ganho", "aspa_perdido", "outorga_nova"}
    texto = (RAIZ / "frontend/src/pages/MudancasPage.tsx").read_text(encoding="utf-8")
    assert "entradas e saídas do cadastro de PTTs, ROAs ganhos ou perdidos, ASPA e outorgas novas" in texto
