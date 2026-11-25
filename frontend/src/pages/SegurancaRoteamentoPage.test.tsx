// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it, vi } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { server } from '../test/server'
import { SegurancaRoteamentoPage, TEXTO_LISTA_NOMINAL_PUBLICA, TEXTO_SEM_LISTA_NOMINAL } from './SegurancaRoteamentoPage'
import { ProntidaoAsnBloco, ProntidaoOperadoraBloco, ProntidaoUfBloco } from '../features/prontidao/blocos'
import type { ProntidaoAgregado, ProntidaoAsn, ProntidaoMeta } from '../types/api'

vi.mock('../auth/AuthContext', () => ({ useAuth: () => ({ anon: null, loading: false }) }))

const regras = {
  versao: 1, hash: 'abc123', minimos: { amostras_rov: 100, pilares: 2 }, classes: { pronto: 80, em_progresso: 50 },
  pilares: {
    filtragem: { nome: 'Filtragem', peso: 25, descricao: 'Descarta rotas inválidas.', componentes: { rov: { peso: 3, descricao: 'ROV do APNIC' }, sem_bogon: { peso: 1, descricao: 'Sem bogon' } } },
    anti_spoofing: { nome: 'Anti-spoofing', peso: 25, descricao: 'Testes do Spoofer.', componentes: { spoofer: { peso: 1, descricao: 'Sessões bloqueadas' } } },
    coordenacao: { nome: 'Coordenação', peso: 20, descricao: 'Encontrável.', componentes: { peeringdb: { peso: 1, descricao: 'PeeringDB' } } },
    validacao_global: { nome: 'Validação global', peso: 30, descricao: 'ROA e IRR.', componentes: { roa: { peso: 3, descricao: 'ROA válido' } } },
  },
}
const meta: ProntidaoMeta = { snapshot_date: '2026-11-02', natureza: 'indice_composto', limites: 'Não é veredito sobre a empresa.', regras: regras as never,
  fontes: { spoofer: { fonte: 'CAIDA Spoofer', citacao: 'The CAIDA UCSD Spoofer Project', janela: null }, irr: { fonte: 'TC IRR e RADB', citacao: null, serial: { TC: '1', RADB: '2' } }, seguranca: { fonte: 'APNIC iROV, bogons' } } }
const agg: ProntidaoAgregado = { asns: 100, asns_com_indice: 80, classes: { pronto: 20, em_progresso: 40, atrasado: 20, sem_dados: 20 }, media_ponderada_usuarios: 62.5, mediana: 58, usuarios: 1000,
  cobertura_pilares: { filtragem: 50, anti_spoofing: 2, coordenacao: 100, validacao_global: 90 },
  medicoes: { rov: { pilar: 'filtragem', asns: 50, media: 71.4, media_ponderada_usuarios: 88.2 }, spoofer: { pilar: 'anti_spoofing', asns: 2, media: 100, media_ponderada_usuarios: 100 }, aspa: { pilar: 'validacao_global', asns: 5, media: 100, media_ponderada_usuarios: 100 } } }
const montar = (el: JSX.Element) => render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter>{el}</MemoryRouter></QueryClientProvider>)

describe('Prontidão em segurança de roteamento', () => {
  it('bloco do ASN mostra o índice, os pilares com componentes e o que ficou sem dado', () => {
    const p: ProntidaoAsn = { ...meta, total: 72.4, classe: 'em_progresso', usuarios: 10, pilares_sem_dado: ['anti_spoofing'], comparacao_uf: agg, brasil: agg,
      pilares: { filtragem: { score: 80, peso: 25, componentes: { rov: { valor: 96, peso: 3, detalhe: { amostras: 500 } }, sem_bogon: { valor: 100, peso: 1, detalhe: null } } }, coordenacao: { score: 60, peso: 20, componentes: { peeringdb: { valor: 60, peso: 1, detalhe: null } } } } }
    montar(<ProntidaoAsnBloco dados={{ prontidao: p } as never} snapshot={null} />)
    expect(screen.getByText(/72,4/)).toBeTruthy()
    expect(screen.getByText(/Em progresso/)).toBeTruthy()
    expect(screen.getByText(/Sem dado neste ASN.*Anti-spoofing/)).toBeTruthy()
    expect(screen.getByText('Filtragem')).toBeTruthy()
    expect(screen.getByText(/Não é veredito sobre a empresa/)).toBeTruthy()
    expect(screen.queryByText('Validação global')).toBeNull()
  })

  it('o bloco de UF separa as classes com e sem ROV medido, e as duas linhas somam o total (SEG-E5)', () => {
    const comRov = { pronto: 5, em_progresso: 10, atrasado: 5, sem_dados: 0 }
    const semRov = { pronto: 15, em_progresso: 30, atrasado: 15, sem_dados: 20 }
    montar(<ProntidaoUfBloco dados={{ uf: 'SP', prontidao: { ...meta, uf: 'SP', agregado: { ...agg, classes_com_rov: comRov, classes_sem_rov: semRov }, brasil: agg } } as never} snapshot={null} />)
    const bloco = screen.getByTestId('classes-por-rov').textContent ?? ''
    expect(bloco).toContain('com ROV medido (20 ASNs)')
    expect(bloco).toContain('sem ROV medido (80 ASNs)')
    expect(bloco).toMatch(/com ROV medido.*Pronto 5/)
    expect(bloco).toMatch(/sem ROV medido.*Pronto 15/)
  })

  it('sem os campos novos (snapshot anterior) o bloco não quebra nem inventa as duas linhas', () => {
    montar(<ProntidaoUfBloco dados={{ uf: 'SP', prontidao: { ...meta, uf: 'SP', agregado: agg, brasil: agg } } as never} snapshot={null} />)
    expect(screen.queryByTestId('classes-por-rov')).toBeNull()
  })

  it('ASN sem índice avisa que faltam pilares', () => {
    const p: ProntidaoAsn = { ...meta, total: null, classe: 'sem_dados', usuarios: 0, pilares_sem_dado: ['filtragem', 'anti_spoofing', 'validacao_global'], comparacao_uf: null, brasil: agg,
      pilares: { coordenacao: { score: 100, peso: 20, componentes: { peeringdb: { valor: 100, peso: 1, detalhe: null } } } } }
    montar(<ProntidaoAsnBloco dados={{ prontidao: p } as never} snapshot={null} />)
    expect(screen.getByText(/Menos de 2 pilares com dado/)).toBeTruthy()
  })

  it('blocos de UF e de operadora mostram só o agregado', () => {
    montar(<ProntidaoUfBloco dados={{ uf: 'SP', prontidao: { ...meta, uf: 'SP', agregado: agg, brasil: agg } } as never} snapshot={null} />)
    expect(screen.getByText(/UF SP/)).toBeTruthy()
    montar(<ProntidaoOperadoraBloco dados={{ prontidao: { ...meta, raiz: '11111111', agregado: agg, brasil: agg } } as never} snapshot={null} />)
    expect(screen.getByText(/CNPJ 11111111/)).toBeTruthy()
  })

  it('sem o bloco não renderiza nada', () => {
    const { container } = montar(<ProntidaoAsnBloco dados={{} as never} snapshot={null} />)
    expect(container.innerHTML).toBe('')
  })

  it('página: metodologia, agregados por UF e por porte e ordenação; lista nominal pública com as salvaguardas', async () => {
    server.use(http.get('*/api/v1/prontidao/resumo', () => HttpResponse.json({ ...meta, escopo: { pais: 'BR' }, agregado: agg, por_uf: { SP: agg, RJ: { ...agg, media_ponderada_usuarios: 70, asns: 10 } }, por_faixa_porte: { de_1000_a_10000: agg, ate_1000: agg } })))
    montar(<SegurancaRoteamentoPage />)
    await waitFor(() => expect(screen.getByText('Estado da segurança de roteamento')).toBeTruthy())
    expect(screen.getByText(/Como o índice é calculado/)).toBeTruthy()
    expect(screen.getAllByText(/peso 25/).length).toBeGreaterThan(0)
    const linhas = () => screen.getAllByRole('row').map((r) => r.textContent ?? '').filter((t) => /^(SP|RJ)/.test(t))
    expect(linhas()[0].startsWith('RJ')).toBe(true)                     // maior média primeiro
    fireEvent.click(screen.getByText('número de ASNs'))
    expect(linhas()[0].startsWith('SP')).toBe(true)
    expect(screen.getAllByText('Até 1.000 usuários').length).toBeGreaterThan(0)
    expect(screen.getAllByText('1.000 a 10.000 usuários').length).toBeGreaterThan(0)
    // medições por grupo: ROV médio de cada ASN (71%) e, ponderado pelos usuários, 88%; ASPA = 5 de 100 ASNs do recorte
    expect(screen.getByText('O que foi medido, por grupo')).toBeTruthy()
    expect(screen.getAllByText('71%').length).toBeGreaterThan(0)
    expect(screen.getAllByText('5%').length).toBeGreaterThan(0)
    fireEvent.click(screen.getByText('ponderado pelos usuários estimados'))
    expect(screen.getAllByText('88%').length).toBeGreaterThan(0)
    expect(screen.queryByText('71%')).toBeNull()
    // D2: a lista por ASN é pública; a página não pode negá-la (SEG-E2) e diz as salvaguardas
    const texto = screen.getByTestId('texto-lista-nominal').textContent ?? ''
    expect(texto).toBe(TEXTO_LISTA_NOMINAL_PUBLICA)
    expect(screen.queryByText(/Não há lista nominal/i)).toBeNull()
    expect(texto).toMatch(/não medido/)
    expect(texto).toMatch(/ordem padrão é por ASN/)
  })

  it('página: com a lista desligada na API (lista_nominal=false) diz que a instância não a publica', async () => {
    server.use(http.get('*/api/v1/prontidao/resumo', () => HttpResponse.json({ ...meta, lista_nominal: false, escopo: { pais: 'BR' }, agregado: agg, por_uf: { SP: agg }, por_faixa_porte: { ate_1000: agg } })))
    montar(<SegurancaRoteamentoPage />)
    await waitFor(() => expect(screen.getByTestId('texto-lista-nominal')).toBeTruthy())
    expect(screen.getByTestId('texto-lista-nominal').textContent).toBe(TEXTO_SEM_LISTA_NOMINAL)
  })

  it('página: cartão do MANRS só com agregados, sem supressão (avisos) e com atribuição', async () => {
    const celula = { asns: 100, usuarios: 1000, asns_participantes: 20, pct_asns: 20, usuarios_participantes: 600, pct_usuarios: 60 }
    const manrs = { snapshot_date: '2026-11-02', natureza: 'agregado', atribuicao: 'Provided by the MANRS with support from the Global Cyber Alliance', limites: 'Não é lista de organizações.',
      fonte: { descricao: 'Tabela pública do MANRS', url: 'https://manrs.org/netops/participants/', medido_em: '2026-10-01', coletado_em: '2026-11-02', termos: 'https://manrs.org/terms-of-service/' },
      regras: { minimo_asns_por_recorte: 5, comparacao: 'total e por porte' },
      brasil: { ...celula, organizacoes_com_asn_br: 12, comparacao_prontidao: { participantes: { asns_com_indice: 20, media_ponderada_usuarios: 71.2, mediana: 66, classes: agg.classes }, nao_participantes: { asns_com_indice: 80, media_ponderada_usuarios: 55.1, mediana: 48, classes: agg.classes } } },
      por_faixa_porte: { ate_1000: celula }, por_uf: { SP: celula, AC: { asns: 15, usuarios: 10, asns_participantes: 2, pct_asns: 13.3, usuarios_participantes: 6, pct_usuarios: 60, n_asns_com_dado: 2, peso_top1: 0.7, avisos: ['poucos_casos', 'maior_integrante'] }, RR: { asns: 9, usuarios: 5, suprimido: true, motivo: 'menos de 5 ASNs participantes' } } }
    server.use(http.get('*/api/v1/prontidao/resumo', () => HttpResponse.json({ ...meta, escopo: { pais: 'BR' }, agregado: agg, por_uf: { SP: agg }, por_faixa_porte: { ate_1000: agg }, manrs })))
    montar(<SegurancaRoteamentoPage />)
    await waitFor(() => expect(screen.getByTestId('manrs')).toBeTruthy())
    const cartao = screen.getByTestId('manrs')
    expect(cartao.textContent).toMatch(/20,0%.*dos 100 ASNs do Brasil/)
    expect(cartao.textContent).toMatch(/71,2.*55,1/)                       // prontidão de participantes × demais
    expect(cartao.textContent).toMatch(/AC13%\s*\(2\)/)                       // D6: o recorte pequeno aparece, com o n
    expect(screen.getAllByTestId('aviso-poucos_casos').length).toBeGreaterThan(0)
    expect(screen.getAllByTestId('aviso-maior_integrante').length).toBeGreaterThan(0)
    expect(cartao.textContent).not.toMatch(/oculto/)
    expect(cartao.textContent).toMatch(/RR.*não divulgado neste snapshot/)       // snapshot publicado antes da regra (imutável) ainda traz célula suprimida
    expect(cartao.textContent).toMatch(/Provided by the MANRS with support from the Global Cyber Alliance/)
    expect(cartao.textContent).not.toMatch(/organizações participantes:/i)
  })
})
