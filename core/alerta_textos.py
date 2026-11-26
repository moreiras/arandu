# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
# Este arquivo faz parte do Arandurape.
# Licença: GNU Affero General Public License v3 ou posterior.
# Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
"""Textos dos pontos de atenção (alertas) por ASN, em português simples, sem travessão e com singular e plural pelo número (PT-30).

Cada regra de `products/alerts/regras/` e a referência de paridade `api/asn_health.py` chamam estas funções, então o texto só existe aqui.
Mudar o texto (não a regra) não muda a versão da regra. `tests/unit/test_alertas_textos.py` veta travessão e "(s)".
"""
from __future__ import annotations

from typing import Iterable, Optional

TITULO_SINGLE_HOMED = "Um único provedor de trânsito visível"
TITULO_MEMBRO_SEM_PEERING = "Membro de PTT sem sessão no route server"
TITULO_SESSAO_RS_DOWN = "Sessões inativas nos route servers do IX.br"


def palavra(q: int, um: str, varios: str) -> str:
    """A palavra no singular ou no plural pelo número, sem o número."""
    return um if q == 1 else varios


def blocos_inalcancaveis(n: int) -> str:
    return (f"{n} {palavra(n, 'bloco atribuído pelo Registro.br não tem', 'blocos atribuídos pelo Registro.br não têm')} nenhuma rota na tabela de "
            f"roteamento global, nem do próprio bloco, nem de um agregado que {palavra(n, 'o', 'os')} cubra, nem de um mais específico. "
            f"O espaço está alocado, mas não é anunciado.")


def anuncio_por_outro_as(n: int) -> str:
    return (f"{n} {palavra(n, 'prefixo deste AS é originado', 'prefixos deste AS são originados')} na full table por um ASN diferente. "
            "Pode ser um anúncio gerenciado por terceiro; convém confirmar se é intencional.")


def desagregacao(gcount: int, afi: str, base: int) -> str:
    return (f"{gcount} prefixos {afi} anunciados para {base} {palavra(base, 'bloco alocado', 'blocos alocados')}. "
            "Anunciar mais-específicos desnecessários infla a tabela global; avalie agregar.")


def fora_da_alocacao(n: int) -> str:
    return (f"{n} {palavra(n, 'prefixo anunciado não está contido', 'prefixos anunciados não estão contidos')} em nenhum bloco atribuído a este AS "
            "no Registro.br. Pode ser espaço sub-alocado por um provedor ou de terceiros.")


def rpki_invalido(n: int) -> str:
    return (f"{n} {palavra(n, 'prefixo anunciado está inválido', 'prefixos anunciados estão inválidos')} no RPKI (origem ou maxLength não batem com os "
            f"ROAs) e {palavra(n, 'pode', 'podem')} ser descartados por redes que validam.")


def cobertura_rpki_parcial(n: int) -> str:
    return (f"{n} {palavra(n, 'bloco alocado não tem', 'blocos alocados não têm')} ROA que {palavra(n, 'o', 'os')} cubra. "
            "Parte do espaço fica sem proteção de origem.")


def roa_maxlength_folgado(n: int) -> str:
    return (f"{n} {palavra(n, 'ROA tem', 'ROAs têm')} maxLength muito acima do tamanho do prefixo. Isso autoriza mais-específicos não anunciados "
            "e amplia a superfície para sequestro por mais-específico.")


def sem_aspa() -> str:
    return ("O AS tem ROAs no RPKI, mas não publicou objeto ASPA (Autonomous System Provider Authorization). O ASPA declara os provedores de "
            "trânsito autorizados e permite validar o AS_PATH. A falta dele não expõe o AS a risco imediato, mas a publicação é recomendada à "
            "medida que a adoção cresce.")


def politica_v4v6(v6_somente: int, v4_somente: int) -> str:
    partes = []
    if v6_somente:    # IPv6 antes de IPv4 no texto
        partes.append(f"{v6_somente} {palavra(v6_somente, 'PTT com peering só IPv6', 'PTTs com peering só IPv6')}")
    if v4_somente:
        partes.append(f"{v4_somente} {palavra(v4_somente, 'PTT com peering só IPv4', 'PTTs com peering só IPv4')}")
    return ("Peering assimétrico entre as famílias: " + "; ".join(partes) +
            ". Tendo IPv6, o ideal é fazer peering nas duas famílias nos mesmos PTTs.")


def sem_peeringdb(n_ptts: int) -> str:
    return (f"O AS é membro de {palavra(n_ptts, 'um PTT', 'PTTs')} do IX.br, mas não tem registro no PeeringDB, o que dificulta o "
            "estabelecimento de peering.")


def membro_sem_sessao(n: int) -> str:
    return (f"{n} {palavra(n, 'PTT em que', 'PTTs em que')} o AS é membro registrado, mas não aparece com sessão no route server. "
            "Isso pode indicar subaproveitamento ou configuração incorreta.")


def prefixos_filtraveis(n: int) -> str:
    return (f"{n} {palavra(n, 'prefixo excede', 'prefixos excedem')} os limites convencionais (IPv6 >/48, IPv4 >/24) e "
            f"{palavra(n, 'pode ser descartado', 'podem ser descartados')} por operadores de backbone. Se há um agregado menos específico cobrindo o "
            "espaço, o tráfego seria absorvido por ele; do contrário, o descarte causaria blackhole.")


def as_loop(n: int) -> str:
    return (f"{n} {palavra(n, 'prefixo tem', 'prefixos têm')} AS_PATH com loop (o mesmo ASN aparece mais de uma vez de forma não consecutiva no "
            "caminho). Pode indicar má configuração de rota ou manipulação incorreta de AS_PATH.")


def single_homed_inferido(rotulo: str, asn: int, nivel: str, p: object) -> str:
    return (f"Só um provedor de trânsito foi inferido para o AS ({rotulo}): AS{asn} (nível {nivel}, p = {p}), com visibilidade suficiente nos "
            "coletores e nos route servers. A conclusão vem de inferência a partir do AS_PATH, do ASPA e do CAIDA, não de contrato: pode haver "
            "provedor que não aparece nas tabelas públicas.")


def single_homed_legado(afis: str) -> str:
    return (f"O AS parece depender de um único provedor de trânsito {afis} na tabela global, o que representa risco de resiliência.")


def sessoes_inativas(data: str, dias: int, partes: Iterable[str]) -> str:
    return (f"No Alice-LG do IX.br, em {data}, todas as sessões do AS estavam inativas havia {dias} {palavra(dias, 'dia', 'dias')} ou mais nos route servers "
            f"de: {', '.join(partes)}. Esse é o estado medido no route server: não diz a causa, e o AS pode manter peering bilateral no PTT.")


def nome_ptt(code: str, nomes: Optional[dict]) -> str:
    """Nome do PTT com o código entre parênteses ("IX.br São Paulo (SP)"); sem nome conhecido, só o código."""
    nome = (nomes or {}).get(code)
    return f"{nome} ({code.upper()})" if nome and nome.upper() != code.upper() else code.upper()
