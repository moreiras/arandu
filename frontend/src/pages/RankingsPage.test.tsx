// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'

function Onde() { const l = useLocation(); return <div data-testid="onde">{l.pathname}{l.search}</div> }
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { http, HttpResponse } from 'msw'
import { server } from '../test/server'
import { RankingsPage, RankingsSici } from './RankingsPage'

vi.mock('../auth/AuthContext', () => ({ useAuth: () => ({ anon: { id: 'x' }, loading: false }) }))

const meta = { snapshot_date: '2026-10-31', mes_referencia: '2026-08', fonte: 'Anatel/SICI', metodologia: '/fontes', escopo: { pais: 'BR' } }
// o conteúdo mora em outras páginas; `/rankings` só redireciona
const montar = (aba: 'operadoras' | 'sem-declaracao' | 'route-servers' = 'operadoras') => render(
  <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter><RankingsSici abaFixa={aba} /></MemoryRouter></QueryClientProvider>,
)

describe('página Rankings do SICI', () => {
  it('mostra critério, mês de referência e a lista de operadoras, e avisa a quem não tem login', async () => {
    server.use(http.get('*/api/v1/ranking/operadoras', () => HttpResponse.json({
      ...meta, criterio: 'Acessos declarados (decrescente)', total: 90,
      items: [{ posicao: 1, cnpj: '02558157000162', empresa: 'VIVO', uf_sede: 'SP', acessos: 8542210, share: 14.755, meses_declinio: 0, em_declinio: false, var_aa_pct: 9.46 }],
    })))
    montar()
    await waitFor(() => expect(screen.getByText('VIVO').getAttribute('href')).toBe('/operadora/02558157000162'))
    expect(screen.getByTestId('rotulo-ranking').textContent).toContain('Critério: Acessos declarados (decrescente)')
    expect(screen.getByTestId('rotulo-ranking').textContent).toContain('2026-08')
    expect(screen.getByTestId('previa-lista').textContent).toBe('Prévia: 1 de 90. Entre para ver as demais.')       // D9: as primeiras linhas (até 100) e o aviso, não o erro
    expect(screen.getByText(/Não indica causa nem intenção/i)).toBeTruthy()
  })

  it('variação em 12 meses: rótulo em acessos, base sempre visível, "base pequena" só como rótulo e ordem por variação absoluta (D6, RANKINGS-E6)', async () => {
    let ordemPedida = ''
    let urlPedida = ''
    server.use(http.get('*/api/v1/ranking/operadoras', ({ request }) => {
      ordemPedida = new URL(request.url).searchParams.get('ordem') ?? ''
      urlPedida = request.url
      return HttpResponse.json({
        ...meta, criterio: 'Variação percentual em 12 meses (acessos) (decrescente)', total: 3, base_pequena_abaixo_de: 1000,
        items: [
          { posicao: 1, cnpj: '11111111000111', empresa: 'MINI NET', uf_sede: 'SP', acessos: 9334, share: 0.01, meses_declinio: 0, em_declinio: false, var_aa_abs: 9333, var_aa_pct: 933300, base_aa: 1, base_pequena: true },
          { posicao: 2, cnpj: '02558157000162', empresa: 'VIVO', uf_sede: 'SP', acessos: 8542210, share: 14.755, meses_declinio: 0, em_declinio: false, var_aa_abs: 736000, var_aa_pct: 9.43, base_aa: 7806210, base_pequena: false },
          { posicao: 3, cnpj: '22222222000122', empresa: 'ENTROU DEPOIS', uf_sede: 'MG', acessos: 500, share: 0, meses_declinio: 0, em_declinio: false, var_aa_abs: 500, var_aa_pct: null, base_aa: 0, base_pequena: true },
        ],
      })
    }))
    montar()
    await waitFor(() => expect(screen.getByText('MINI NET')).toBeTruthy())
    expect(screen.getByRole('button', { name: /Variação em 12 meses \(acessos\)/ })).toBeTruthy()
    expect(screen.getByRole('button', { name: /Variação absoluta \(acessos\)/ })).toBeTruthy()
    expect(screen.getByRole('columnheader', { name: /Base \(acessos em 2025-08\)/ })).toBeTruthy()
    const mini = screen.getByText('MINI NET').closest('tr')!
    expect(mini.textContent).toContain('+933.300%')
    expect(mini.textContent).toContain('base pequena')
    expect(screen.getByText('VIVO').closest('tr')!.textContent).not.toContain('base pequena')
    expect(screen.getByText('VIVO').closest('tr')!.textContent).toContain('7.806.210')          // a base fica à vista em toda linha
    expect(screen.getByText('ENTROU DEPOIS').closest('tr')!.textContent).toContain('—')    // sem percentual (base 0): a linha continua na lista
    expect(screen.getAllByText('base pequena')).toHaveLength(2)
    expect(screen.getByTestId('regra-base').textContent).toContain('Sem piso')
    expect(urlPedida).toContain('esquema=2')              // a resposta ganhou campos: a URL muda para não vir do cache imutável do esquema antigo
    fireEvent.change(screen.getByLabelText('Ordenar por'), { target: { value: 'var_aa_abs' } })
    await waitFor(() => expect(ordemPedida).toBe('var_aa_abs'))
  })

  it('na aba sem declaração descreve o fato, com usuários estimados e a marca do grupo, sem juízo', async () => {
    server.use(http.get('*/api/v1/sem-declaracao-sici', () => HttpResponse.json({
      ...meta, criterio: 'Usuários estimados (APNIC) dos ASNs do CNPJ (decrescente)', tipo: 'outorga_sem_declaracao', total: 1, parametros: { usuarios_min: 100 },
      items: [{ posicao: 1, cnpj: '39565567000140', razao_social: 'BTT TELECOMUNICACOES S.A.', uf: 'MG', usuarios_apnic: 367660, classe: 'com_usuarios_apnic', grupo_declara: true, asns: [28656] }],
    })))
    montar('sem-declaracao')
    await waitFor(() => expect(screen.getByText('BTT TELECOMUNICACOES S.A.')).toBeTruthy())
    expect(screen.getByText('367.660')).toBeTruthy()
    expect(screen.getByText('ASN com 100 ou mais usuários estimados (APNIC)', { selector: 'td' })).toBeTruthy()
    expect(screen.getByText('outro CNPJ do grupo declarou')).toBeTruthy()
    const corpo = document.body.textContent ?? ''
    expect(corpo).not.toMatch(/sonegou|omitiu|omi[s]s|irregular/i)
  })

  it('sem declaração: três valores de grupo em texto, causa de rede virtual só com dado, síntese e tabela por UF (PT-26)', async () => {
    const zero = { com_usuarios_apnic: 0, sem_usuarios: 0, nao_comparavel: 0, usuarios_apnic: 0 }
    server.use(http.get('*/api/v1/sem-declaracao-sici', () => HttpResponse.json({
      ...meta, criterio: 'Usuários estimados (APNIC) dos ASNs do CNPJ (decrescente)', tipo: 'outorga_sem_declaracao', total: 3, parametros: { usuarios_min: 100 },
      por_uf: {
        MG: { ...zero, cnpjs_sem_declaracao: 2, com_usuarios_apnic: 1, nao_comparavel: 1, usuarios_apnic: 500, grupo_declarou: 1, credenciadas_rede_virtual: 1 },
        '': { ...zero, cnpjs_sem_declaracao: 1, nao_comparavel: 1, grupo_declarou: 0, credenciadas_rede_virtual: 0 },
      },
      items: [
        { posicao: 1, cnpj: '11111111000111', razao_social: 'A LTDA', uf: 'MG', usuarios_apnic: 500, classe: 'com_usuarios_apnic', grupo_declara: true, asns: [1] },
        { posicao: 2, cnpj: '22222222000122', razao_social: 'B LTDA', uf: 'MG', usuarios_apnic: null, classe: 'nao_comparavel', grupo_declara: false, rede_virtual_origem: '99999999000199', asns: [] },
        { posicao: 3, cnpj: '33333333000133', razao_social: 'C LTDA', uf: '', usuarios_apnic: null, classe: 'nao_comparavel', asns: [] },
      ],
    })))
    montar('sem-declaracao')
    await waitFor(() => expect(screen.getByText('A LTDA')).toBeTruthy())
    expect(screen.getByText(/outro CNPJ do grupo declarou/, { selector: 'td' })).toBeTruthy()
    expect(screen.getByText(/nenhum CNPJ do grupo declarou/, { selector: 'td' })).toBeTruthy()
    expect(screen.getByText(/grupo não identificado/, { selector: 'td' })).toBeTruthy()
    const rv = screen.getByText(/credenciada de rede virtual; acessos declarados pela prestadora de origem/)
    expect(rv.querySelector('a')).toHaveAttribute('href', '/operadora/99999999000199')
    expect(document.querySelectorAll('td a[href="/operadora/99999999000199"]').length).toBe(1)   // só a linha com dado ganha a causa
    const sintese = screen.getByTestId('sintese-sem-declaracao').textContent ?? ''
    expect(sintese).toContain('3')                                           // 2 + 1 CNPJs
    expect(sintese).toMatch(/Em 1 deles outro CNPJ do mesmo grupo declarou/)
    expect(sintese).toMatch(/1 são credenciados de rede virtual/)
    expect(screen.getByRole('table', { name: /por UF do cadastro/ })).toBeTruthy()
    expect(screen.getByText('UF não informada')).toBeTruthy()
    expect(document.body.textContent).not.toMatch(/omi[s]s|dispensada de autoriza|infra[çc]/i)
  })

  it('as abas territoriais viraram a lista de municípios: o link antigo redireciona com a lente certa (alias)', async () => {
    render(<QueryClientProvider client={new QueryClient()}><MemoryRouter initialEntries={['/rankings?aba=penetracao&uf=SP']}>
      <Routes><Route path="/rankings" element={<RankingsPage />} /><Route path="/municipios" element={<Onde />} /></Routes></MemoryRouter></QueryClientProvider>)
    expect(await screen.findByTestId('onde')).toHaveTextContent('/municipios?uf=SP&lente=penetracao')
  })

  it('os links antigos de operadoras, omissão (nome antigo) e route servers redirecionam para o lugar novo (alias)', async () => {
    const ir = async (url: string) => {
      const { unmount } = render(<QueryClientProvider client={new QueryClient()}><MemoryRouter initialEntries={[url]}>
        <Routes><Route path="/rankings" element={<RankingsPage />} /><Route path="*" element={<Onde />} /></Routes></MemoryRouter></QueryClientProvider>)
      const t = (await screen.findByTestId('onde')).textContent; unmount(); return t
    }
    expect(await ir('/rankings')).toBe('/operadoras?visao=ranking')
    expect(await ir('/rankings?aba=omissao&uf=MG')).toBe('/operadoras?visao=sem-declaracao&uf=MG')   // aba=omissao é o nome antigo (alias)
    expect(await ir('/rankings?aba=route-servers&ixp=sp')).toBe('/ixps?visao=route-servers&ixp=sp')
  })

  it('na aba Route servers lista o número medido, sem adjetivo, com o PTT, a data da coleta e o aviso do route server incerto', async () => {
    let pedido = ''
    server.use(http.get('*/api/v1/ranking/route-servers', ({ request }) => {
      pedido = new URL(request.url).search
      return HttpResponse.json({ snapshot_date: '2026-10-31', coletado_em: '2026-10-31T22:54:20Z', fonte: 'x', versao_alice: '6.1.0', parametros: { dias_down: 7, uso_limite: 0.8, idade_max_vizinhos_h: 24 },
        limites: 'Estado do route server no instante da coleta.', criterio: 'sessões down no route server (número absoluto), com o total de sessões do membro ao lado (decrescente)',
        escopo: { pais: 'BR' }, filtros: { apenas_down: false }, total: 1,
        items: [{ posicao: 1, ixp: 'sp', asn: 64496, nome: 'REDE EXEMPLO A', sessoes: 4, up: 1, down: 3, down_certo: 1, max_dias_down: 205, max_uso_limite: null, membro_down: false, rs_incerto: 1 }] })
    }))
    montar('route-servers')
    await waitFor(() => expect(screen.getByText('AS64496').getAttribute('href')).toBe('/asn/64496'))
    expect(screen.getByText('SP').getAttribute('href')).toBe('/ixp/sp')
    expect(screen.getByText('1 de 4')).toBeTruthy()
    expect(screen.getByTestId('rotulo-ranking').textContent).toContain('Route servers do IX.br, coletado em 2026-10-31')
    expect(screen.getByText(/\(\+2 em RS sem frescor confirmado\)/)).toBeTruthy()
    expect(pedido).toContain('criterio=ptt_asn')                                  // D6: a ordem padrão é neutra
    expect(screen.getByTestId('regra-ordem-rs').textContent).toContain('por PTT e, dentro dele, por ASN')
    fireEvent.change(screen.getByLabelText('Ordenar por'), { target: { value: 'sessoes_down' } })
    await waitFor(() => expect(pedido).toContain('criterio=sessoes_down'))      // a ordem por número medido é escolha do usuário
    expect(document.body.textContent).not.toMatch(/pior|melhor|culpa|irregular/i)
  })
  it('pararam de declarar: último nome declarado, grupo em três valores com link e outorga SCM no snapshot (PT-26 / RANKINGS 5.2)', async () => {
    server.use(http.get('*/api/v1/sem-declaracao-sici', () => HttpResponse.json({
      ...meta, criterio: 'Acessos no último mês declarado (decrescente)', tipo: 'parou_de_declarar', total: 3, parametros: {},
      items: [
        { posicao: 1, cnpj: '01778972000174', empresa: 'AMERICA NET LTDA', empresa_fonte: 'sici', ultimo_mes_declarado: '2024-11', meses_sem_declarar: 22, acessos_no_ultimo_mes: 510036, grupo_id: 'g1', grupo_declara: true, scm_vigente: false },
        { posicao: 2, cnpj: '22222222000122', empresa: 'OUTRA LTDA', empresa_fonte: 'cadastro_scm', ultimo_mes_declarado: '2025-01', meses_sem_declarar: 20, acessos_no_ultimo_mes: 1000, grupo_id: 'g2', grupo_declara: false, scm_vigente: true },
        { posicao: 3, cnpj: '33333333000133', empresa: '', ultimo_mes_declarado: '2025-02', meses_sem_declarar: 19, acessos_no_ultimo_mes: 10 },
      ],
    })))
    render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><MemoryRouter initialEntries={['/?tipo=parou']}><RankingsSici abaFixa="sem-declaracao" /></MemoryRouter></QueryClientProvider>)
    await waitFor(() => expect(screen.getByText('AMERICA NET LTDA')).toBeTruthy())
    expect(screen.getByRole('columnheader', { name: 'Empresa (CNPJ)' })).toBeTruthy()
    expect(screen.getByText(/^outro CNPJ do grupo declarou/, { selector: 'td' })).toBeTruthy()
    expect(screen.getByText(/^nenhum CNPJ do grupo declarou/, { selector: 'td' })).toBeTruthy()
    expect(screen.getByText(/^grupo não identificado/, { selector: 'td' })).toBeTruthy()
    expect(screen.getAllByRole('link', { name: 'ver grupo' })[0].getAttribute('href')).toBe('/grupo/g1')
    expect(screen.getAllByTestId('scm-vigente').map((e) => e.textContent)).toEqual(['não', 'sim', '—'])      // snapshot antigo sem o campo: traço, nunca "não"
    expect(document.body.textContent).not.toMatch(/migrou|incorporou|sonegou|omitiu|irregular/i)
  })
})
