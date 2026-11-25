// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
/**
 * Os universos de contagem (PT-15): cada número que aparece com o mesmo nome em páginas diferentes ("ASNs brasileiros", "participantes",
 * "declarantes", "municípios", "usuários") conta coisas diferentes, e o rótulo diz qual. Fonte única dos rótulos da tela e do texto
 * "Por que há vários totais" de `/sobre#contagens`. Referência: `docs/glossario-contagens.md` (definição, origem e valor medido de cada um).
 * Regra: o mesmo rótulo nunca designa dois universos (`universos.test.ts`).
 */
export interface Universo {
  /** Nome do universo, como escrito na tela. */
  rotulo: string
  /** O que entra na contagem, em uma frase. */
  definicao: string
}

export const UNIVERSOS = {
  asnsLacnic: { rotulo: 'ASNs brasileiros (delegados pela LACNIC ao Brasil)', definicao: 'ASNs que a LACNIC delegou ao Brasil. É a regra única de "ASN brasileiro" do site.' },
  asnsRegistroBr: { rotulo: 'ASNs na lista do Registro.br', definicao: 'ASNs do arquivo de alocações do Registro.br: os da delegação da LACNIC ao Brasil e mais alguns de empresas estrangeiras com bloco no Registro.br. Usada pela análise de rotas.' },
  asnsObservados: { rotulo: 'ASNs observados no snapshot (Brasil e exterior)', definicao: 'Todo ASN com documento no snapshot: os brasileiros e os vistos como origem na tabela global ou nos PTTs.' },
  asnsComUf: { rotulo: 'ASNs brasileiros com UF da sede conhecida', definicao: 'ASNs brasileiros cuja organização tem UF no cadastro de CNPJ. A UF é a da sede, não a de operação.' },
  asnsVisiveis: { rotulo: 'ASNs brasileiros (LACNIC) com prefixo visível na tabela global', definicao: 'ASNs brasileiros que originam ao menos um prefixo IPv6 ou IPv4 na tabela global dos coletores.' },
  asnsAnunciamV6: { rotulo: 'ASNs brasileiros que anunciam IPv6 na tabela global', definicao: 'ASNs brasileiros com ao menos um prefixo IPv6 originado na tabela global. Ter bloco IPv6 alocado não basta.' },
  asnsAlgumV6: { rotulo: 'ASNs brasileiros com algum IPv6 (alocado, anunciado ou visto num PTT)', definicao: 'Mede a existência de IPv6 em qualquer das três formas; não mede anúncio nem uso.' },
  sessaoRs: { rotulo: 'ASNs com sessão em route server do IX.br', definicao: 'ASNs com sessão BGP com algum route server de PTT do IX.br (todos os países), sem repetição entre PTTs. Não é peering bilateral.' },
  sessaoRsBr: { rotulo: 'ASNs brasileiros com sessão em route server do IX.br', definicao: 'O mesmo conjunto, restrito aos ASNs brasileiros (LACNIC).' },
  membroCadastro: { rotulo: 'ASNs no cadastro de participantes do IX.br', definicao: 'ASNs na lista oficial de participantes de cada PTT, com ou sem sessão com o route server.' },
  originadoresBr: { rotulo: 'ASNs brasileiros cujos prefixos aparecem no IX.br', definicao: 'Os originadores restritos aos ASNs brasileiros (LACNIC).' },
  originadores: { rotulo: 'ASNs cujos prefixos aparecem no IX.br', definicao: 'ASNs de origem de ao menos uma rota vista no looking glass de algum PTT, inclusive por trânsito de outro participante.' },
  externosBr: { rotulo: 'ASNs brasileiros que declaram presença em IXPs fora do IX.br (PeeringDB)', definicao: 'União por ASN dos brasileiros listados como rede em algum IXP externo.' },
  declarantesFixo: { rotulo: 'CNPJs que declararam acessos fixos ao SICI', definicao: 'CNPJs no SICI de banda larga fixa do mês de referência, com ou sem outorga SCM no cadastro.' },
  scmDeclarantes: { rotulo: 'CNPJs com outorga SCM que declararam acessos fixos', definicao: 'Interseção dos CNPJs com outorga SCM com os declarantes de acesso fixo.' },
  scmFixoOuMovel: { rotulo: 'CNPJs com outorga SCM que declararam acesso fixo ou móvel', definicao: 'CNPJs com outorga SCM cuja soma de acesso fixo e móvel declarado é maior que zero.' },
  municipiosIbge: { rotulo: 'municípios do Brasil (tabela do IBGE)', definicao: 'Os municípios da tabela do IBGE que o site carrega, incluindo os criados depois do Censo 2022.' },
  municipiosCenso: { rotulo: 'municípios do Censo 2022', definicao: 'A lista do Censo 2022, sem os municípios criados depois dele.' },
  usuariosPais: { rotulo: 'usuários estimados em ASNs brasileiros (soma APNIC por ASN)', definicao: 'Soma da estimativa do APNIC Labs por ASN brasileiro. Não é o número que o APNIC publica para o país.' },
  usuariosUf: { rotulo: 'usuários estimados em ASNs com sede na UF', definicao: 'A mesma soma, agrupada pela UF da sede do ASN; ASNs sem UF ficam fora. Não é a população conectada da UF.' },
  usuariosPtt: { rotulo: 'usuários estimados alcançáveis por este PTT (IPv4)', definicao: 'Usuários do APNIC de cada ASN que origina prefixos no PTT, ponderados pela fração do espaço IPv4 visível ali, inclusive o que chega por trânsito. Não aditivos: o mesmo usuário conta em cada PTT onde o seu ASN aparece.' },
  usuariosIx: { rotulo: 'usuários estimados alcançáveis pelo IX.br (IPv4, sem dupla contagem)', definicao: 'A mesma conta com os prefixos de todos os PTTs unidos antes do cálculo, de modo que cada usuário conta uma vez.' },
} as const satisfies Record<string, Universo>

/**
 * Rótulos curtos da relação de um ASN com um PTT do IX.br, para legendas, colunas e tooltips (não são universos de contagem e não entram em
 * `/sobre#contagens`). `sessaoRs` é o que o looking glass mostra (`asn_direct`, `ixps_direct`); `membroCadastro` é a lista oficial de
 * participantes (`m`, `ixps_membro`), com ou sem sessão. O termo antigo para a sessão é vetado em `tests/unit/test_textos_falsos.py`.
 */
export const RELACAO_PTT = {
  sessaoRs: 'Sessão com o route server',
  asnsSessaoRs: 'ASNs com sessão no route server',
  membroCadastro: 'Membro do cadastro',
  papelSessaoRs: 'com sessão no route server',
  pttsSessaoRs: 'PTTs com sessão no route server',
} as const

export type ChaveUniverso = keyof typeof UNIVERSOS

/** Rótulo de tela de um universo, com a inicial maiúscula para título de indicador. */
export const rotuloDe = (k: ChaveUniverso): string => UNIVERSOS[k].rotulo.charAt(0).toUpperCase() + UNIVERSOS[k].rotulo.slice(1)

/** `UNIVERSOS` em ordem de exibição (a de `/sobre#contagens`). */
export const LISTA_UNIVERSOS: Array<Universo & { chave: ChaveUniverso }> = (Object.keys(UNIVERSOS) as ChaveUniverso[]).map((chave) => ({ chave, rotulo: rotuloDe(chave), definicao: UNIVERSOS[chave].definicao }))
