// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import type { AreaInfluenciaNacional, AreaInfluenciaPtt, AreaInfluenciaResumoPtt, AreaInfluenciaVisao } from '../../types/areaInfluencia'

/** Respostas de exemplo (municípios e PTTs fictícios) para os testes dos blocos de área de influência. */
const meta = {
  snapshot_date: '2026-09-20', natureza: 'inferido', limites: 'Inferência, não cobertura de rede.', metodo: { atribuicao: 'PTT mais próximo' },
  fontes: { sici: '2026-08', ptts: 'looking glasses do IX.br (snapshot)', pix: 'cadastro de PIX do IX.br (config/pix.yaml)', centroides: 'IBGE' },
  faixas: { '1': 'ate_p50', '2': 'p50_a_p80', '3': 'alem_p80' },
}
const totais = { acessos: 1000, acessos_atribuidos: 900, acessos_sem_ptt: 100, acessos_sem_centroide: 0, cnpjs_com_varios_asns: 1 }

export const VISAO_DIRETOS: AreaInfluenciaVisao = {
  operadoras: 4, municipios: 3, acessos: 600, p50_km: 12.4, p80_km: 80, p90_km: 150.6, mediana_operadora_km: 30,
  faixas: { ate_p50: { municipios: 1, acessos: 300 }, p50_a_p80: { municipios: 1, acessos: 200 }, alem_p80: { municipios: 1, acessos: 100 } },
  municipios_faixa: { '9900001': [300, 1], '9900004': [200, 2], '9900005': [100, 3] },
}
export const VISAO_TODOS: AreaInfluenciaVisao = {
  operadoras: 6, municipios: 4, acessos: 900, p50_km: 20, p80_km: 200, p90_km: 410, mediana_operadora_km: 55,
  faixas: { ate_p50: { municipios: 2, acessos: 450 }, p50_a_p80: { municipios: 1, acessos: 250 }, alem_p80: { municipios: 1, acessos: 200 } },
  municipios_faixa: { '9900001': [300, 1], '9900002': [150, 1], '9900004': [250, 2], '9900005': [200, 3] },
}

export const AREA_PTT: AreaInfluenciaPtt = {
  ...meta, ixp: 'za', nome: 'Arandurápolis', uf: 'SP',
  pix: { total: 2, coordenada: 1, endereco: 0, sede: 1, aproximado: true, pontos: [[-23.6, -46.7, 'coordenada'], [-23.5, -46.6, 'sede']] },
  totais: { diretos: totais, todos: totais },
  visoes: { diretos: VISAO_DIRETOS, todos: VISAO_TODOS },
  municipios_nomes: { '9900001': 'Arandurápolis/SP', '9900002': 'Tupãnópolis/RJ', '9900004': 'Itapuãzinho/SP', '9900005': 'Curumim do Sul/RS' },
}

const resumo = (v: AreaInfluenciaVisao, extra: Omit<AreaInfluenciaResumoPtt, keyof Omit<AreaInfluenciaVisao, 'municipios_faixa'>>): AreaInfluenciaResumoPtt => {
  const { municipios_faixa: _lista, ...numeros } = v
  return { ...numeros, ...extra }
}

export const AREA_NACIONAL: AreaInfluenciaNacional = {
  ...meta, visao: 'todos', rotulo_visao: 'Todos que anunciam no PTT',
  campos_municipio: ['ptt_principal', 'faixa', 'acessos_principal', 'acessos_municipio', 'ptts'],
  total: totais, ptts_com_pix_aproximado: ['zb'],
  ptts: {
    za: resumo(VISAO_TODOS, { nome: 'Arandurápolis', uf: 'SP', pix_aproximado: false, ponto: [-23.6, -46.7] }),
    zb: resumo(VISAO_DIRETOS, { nome: 'Tupãnópolis', uf: 'RJ', pix_aproximado: true, ponto: [-22.95, -43.25] }),
    zc: resumo(VISAO_DIRETOS, { nome: 'Guaraniópolis', uf: 'PR', pix_aproximado: false, ponto: [-25.45, -49.3] }),
  },
  municipios: { '9900001': ['za', 1, 300, 300, 1], '9900002': ['zb', 2, 150, 150, 1], '9900003': ['zc', 3, 90, 90, 1] },
}
