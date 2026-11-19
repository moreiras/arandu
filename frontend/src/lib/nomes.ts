// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html

const MINUSCULAS = new Set(['de', 'da', 'do', 'das', 'dos', 'e', 'em', 'para', 'a', 'o'])
// Siglas e formas societárias que ficam em maiúsculas. "S.A." e "S/A" também.
const SIGLAS = new Set(['ltda', 'me', 'epp', 'eireli', 'sa', 's.a.', 's/a', 'ti', 'ix', 'br', 'uf', 'asn', 'cnpj', 'ssp', 'scm', 'smp', 'stfc', 'seac', 'cdn', 'ipv4', 'ipv6', 'isp', 'pix', 'rj', 'sp', 'mg', 'df', 'ii', 'iii', 'iv'])
// Acentos que o cadastro original perdeu (a Anatel e a Receita gravam em maiúsculas sem acento). Só entra palavra sem ambiguidade;
// o que não está aqui fica sem acento em vez de ser adivinhado. O nome do cadastro continua no detalhe.
const ACENTOS: Record<string, string> = {
  servicos: 'Serviços', servico: 'Serviço', telecomunicacoes: 'Telecomunicações', telecomunicacao: 'Telecomunicação', comunicacao: 'Comunicação',
  comunicacoes: 'Comunicações', informatica: 'Informática', tecnologia: 'Tecnologia', conexao: 'Conexão', conexoes: 'Conexões',
  solucoes: 'Soluções', solucao: 'Solução', eletronica: 'Eletrônica', eletronicos: 'Eletrônicos', multimidia: 'Multimídia',
  distribuicao: 'Distribuição', participacoes: 'Participações', administracao: 'Administração', operacoes: 'Operações',
  informacao: 'Informação', informacoes: 'Informações', transmissao: 'Transmissão', producao: 'Produção', educacao: 'Educação',
  sao: 'São', sudeste: 'Sudeste', brasilia: 'Brasília', goias: 'Goiás', ceara: 'Ceará', para: 'para', maranhao: 'Maranhão',
  paraiba: 'Paraíba', piaui: 'Piauí', amapa: 'Amapá', rondonia: 'Rondônia', londrina: 'Londrina', uniao: 'União', pais: 'País',
}
const semAcento = (s: string) => s.normalize('NFD').replace(/[̀-ͯ]/g, '')

/**
 * Nome para exibição: "BRISANET SERVICOS DE TELECOMUNICACOES S.A." → "Brisanet Serviços de Telecomunicações S.A.".
 * Só ajusta caixa e restaura acentos de um dicionário curto; nome que já tem minúsculas é devolvido como veio (já foi cuidado
 * na origem). O valor original do cadastro deve aparecer no detalhe da entidade.
 */
export function nomeExibicao(nome: string | null | undefined): string {
  if (!nome) return ''
  const t = nome.trim().replace(/\s+/g, ' ')
  if (t !== t.toUpperCase()) return t
  return t.split(' ').map((p, i) => {
    const k = p.toLowerCase()
    if (SIGLAS.has(k)) return p.toUpperCase()
    if (i > 0 && MINUSCULAS.has(k)) return k
    if (ACENTOS[semAcento(k)] && semAcento(k) !== 'para') return ACENTOS[semAcento(k)]
    // Identificadores (AS64500, 4G), siglas curtas (GVT, TIM, UOL) e formas com ponto (IX.BR) ficam como vieram: não dá para saber se são sigla.
    if (/\d/.test(p) || p.length <= 3 || /[./]/.test(p)) return p
    return k.charAt(0).toUpperCase() + k.slice(1)
  }).join(' ')
}
