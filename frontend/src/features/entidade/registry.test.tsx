// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { fixtures } from '../../test/server'
import '../asn'
import '../operadora'
import '../ptt'
import { EntityPage } from './EntityPage'
import { MemoryRouter, useLocation } from 'react-router-dom'
import { fireEvent } from '@testing-library/react'
import { abasDe, blocosDe, registrarAbas, registrarBloco, todosOsBlocos } from './registry'

const fontesCatalogo: string[] = JSON.parse(readFileSync(resolve(__dirname, '../../../../docs/fontes.json'), 'utf-8')).fontes.map((f: { id: string }) => f.id)

describe('invariantes do registro de blocos', () => {
  it('todo bloco declara título, fontes e dependências, e as fontes existem no catálogo', () => {
    expect(todosOsBlocos().length).toBeGreaterThan(0)
    for (const b of todosOsBlocos()) {
      expect(b.titulo, b.id).not.toBe('')
      expect(b.fontes.length, `${b.id} sem fonte`).toBeGreaterThan(0)
      expect(b.depende.length, `${b.id} sem dependência`).toBeGreaterThan(0)
      for (const f of b.fontes) expect(fontesCatalogo, `${b.id}: fonte ${f} fora do catálogo`).toContain(f)
    }
  })

  it('ordem estritamente crescente por entidade e ids únicos', () => {
    const asn = blocosDe('asn')
    expect(asn.map((b) => b.ordem)).toEqual([...asn.map((b) => b.ordem)].sort((a, b) => a - b))
    expect(() => registrarBloco({ ...asn[0] })).toThrow(/duplicado/)
  })
})

describe('blocos de ASN', () => {
  const ctxMin = { doc: fixtures.asnDetail as any, date: '2026-09-20', ixpPaths: {}, pathNodeMeta: {}, ixpMemberCodes: [], carregandoCaminhos: false }
  const aplicaveis = (doc: any) => blocosDe('asn').filter((b) => !b.aplicavel || b.aplicavel({ ...ctxMin, doc })).map((b) => b.id)

  it('fixa os 30 blocos e a ordem de exibição (a ordem da página de antes)', () => {
    expect(blocosDe('asn').map((b) => b.id)).toEqual([
      'metricas', 'usuarios', 'linha-do-tempo', 'alertas', 'seguranca', 'prontidao', 'recursos-ipv4', 'route-servers', 'organizacao', 'bloqueios', 'radar', 'exposicao', 'politica-rs', 'instalacoes', 'estabilidade', 'diagnostico', 'prefixos-rir', 'roa', 'aspa', 'tabela-global', 'presenca',
      'interconexao-mensuravel', 'acessos', 'mapa', 'ixps-externos', 'peeringdb', 'outorga-scm', 'outorga-smp', 'outorga-stfc', 'outorga-seac', 'relacoes',
    ])
  })

  it('blocos condicionais só aparecem quando há dado (mesmas regras da página de antes)', () => {
    const vazio = { ...fixtures.asnDetail, apnic_users: null, is_br: false, aspa_providers: null, aspa_customers: null, scm: [], smp: [], stfc: [], seac: [],
      global_prefixes_v4: [], global_prefixes_v6: [], upstreams: [], downstreams: [],
      upstreams_global_v4: [], upstreams_global_v6: [], downstreams_global_v4: [], downstreams_global_v6: [] }
    const ids = aplicaveis(vazio)
    for (const naoDeve of ['usuarios', 'estabilidade', 'diagnostico', 'aspa', 'tabela-global', 'acessos', 'ixps-externos', 'peeringdb', 'outorga-scm', 'outorga-smp', 'relacoes']) {
      expect(ids, naoDeve).not.toContain(naoDeve)
    }
    for (const deve of ['metricas', 'alertas', 'prefixos-rir', 'roa', 'presenca', 'mapa']) expect(ids, deve).toContain(deve)
    const cheio = { ...vazio, apnic_users: 10, is_br: true, aspa_providers: [], scm: [{ cnpj: '1' }], external_ixps: ['x'], global_prefixes_v4: ['1.0.0.0/24'] }
    expect(aplicaveis(cheio)).toEqual(expect.arrayContaining(['usuarios', 'aspa', 'acessos', 'ixps-externos', 'peeringdb', 'outorga-scm', 'tabela-global']))
  })
})

describe('blocos de PTT', () => {
  const ctx = (v4: unknown, v6: unknown) => ({ v4, v6 }) as any

  it('fixa os 18 blocos e a ordem de exibição (os indicadores em destaque e depois o resumo em texto, PT-22 e PT-30; a tabela única de participantes substitui "Participantes e filtros" e "Membros sem peering direto")', () => {
    expect(blocosDe('ixp').map((b) => b.id)).toEqual([
      'destaque', 'sintese', 'indicadores-as', 'indicadores-v6', 'indicadores-v4', 'potencial', 'route-servers', 'rejeicoes', 'instalacoes', 'mapa', 'hilbert-v6', 'hilbert-v4',
      'linha-do-tempo', 'participantes', 'entrou-saiu', 'conteudo', 'peers-v6', 'peers-v4',
    ])
  })

  it('Hilbert só aparece com dado e a tabela de participantes aparece sempre (regras da página de antes)', () => {
    const ap = (c: any) => blocosDe('ixp').filter((b) => !b.aplicavel || b.aplicavel(c)).map((b) => b.id)
    expect(ap(ctx(null, null))).not.toEqual(expect.arrayContaining(['hilbert-v6']))
    expect(ap(ctx(null, null))).toContain('participantes')
    expect(ap(ctx({}, {}))).toEqual(expect.arrayContaining(['hilbert-v6', 'hilbert-v4', 'participantes']))
  })
})

describe('blocos de operadora', () => {
  const ap = (c: any) => blocosDe('operadora').filter((b) => !b.aplicavel || b.aplicavel(c)).map((b) => b.id)

  it('fixa os 18 blocos e a ordem de exibição', () => {
    expect(blocosDe('operadora').map((b) => b.id)).toEqual(['rede', 'presenca-fisica', 'credito-publico', 'sancoes', 'contratos', 'empresas-relacionadas', 'scm', 'indicadores', 'recursos-ipv4', 'smp', 'estacoes-smp', 'multas', 'qualidade', 'reclamacoes', 'consumidor', 'prontidao', 'stfc', 'sobreposicao', 'seac', 'linha-do-tempo'])
  })

  it('cada bloco só aparece se a fonte correspondente existir (CNPJ só com SMP não mostra SCM)', () => {
    expect(ap({ dataMovel: {}, servicos: [{ sigla: 'SMP', tipo: 'outorga', desde: null, registros: 1 }], hasStfc: false, hasSeac: false })).toEqual(['empresas-relacionadas', 'smp'])
    // OPERADORA-E8: o documento móvel existe só porque o CNPJ tem ASN; sem outorga, credenciamento nem acesso não há bloco SMP
    expect(ap({ dataMovel: { asns: [64500], outorgas_smp: [] }, servicos: [], hasStfc: false, hasSeac: false })).toEqual(['empresas-relacionadas'])
    expect(ap({ dataMovel: { asns: [], outorgas_smp: [], acessos: 10 }, servicos: [], hasStfc: false, hasSeac: false })).toEqual(['empresas-relacionadas', 'smp'])
    expect(ap({ data: {}, rede: {}, hasStfc: true, hasSeac: true })).toEqual(['rede', 'empresas-relacionadas', 'scm', 'stfc', 'seac'])
  })

  it('os blocos de acessos citam o SICI e avisam das duas datas', () => {
    for (const id of ['scm', 'smp']) {
      const b = blocosDe('operadora').find((x) => x.id === id)!
      expect(b.fontes.join()).toMatch(/anatel_sici/)
      expect(b.nota).toMatch(/duas datas/)
    }
  })
})

describe('EntityPage', () => {
  const Teste = ({ dados }: { dados: { texto: string } }) => <p>{dados.texto}</p>

  it('renderiza cada bloco aplicável com título e proveniência, na ordem', () => {
    registrarBloco<any>({ id: 'b2', entidade: 'uf', titulo: 'Segundo', ordem: 20, depende: ['x'], fontes: ['lg_ixbr'], Componente: Teste })
    registrarBloco<any>({ id: 'b1', entidade: 'uf', titulo: 'Primeiro', ordem: 10, depende: ['x'], fontes: ['apnic_pop'], selo: 'estimado', Componente: Teste })
    render(<EntityPage entidade="uf" dados={{ texto: 'oi' }} snapshot="2026-09-20" fontes={[{ id: 'apnic_pop', as_of: '2026-09-20', frescor: 'ok' }]} />)
    const secoes = screen.getAllByRole('region')
    expect(secoes[0]).toHaveAccessibleName('Primeiro')
    expect(secoes[1]).toHaveAccessibleName('Segundo')
    expect(within(secoes[0]).getByTestId('proveniencia')).toHaveTextContent('Estimado')
    expect(within(secoes[0]).getByTestId('proveniencia')).toHaveTextContent('apnic_pop · ref. 20/09/2026')
    expect(secoes.every((s) => within(s).queryByTestId('proveniencia'))).toBe(true)
  })

  it('bloco vazio mostra o estado vazio com a data, não some', () => {
    registrarBloco<any>({ id: 'vz', entidade: 'prefixo', titulo: 'Vazio', ordem: 1, depende: ['x'], fontes: ['lg_ixbr'], vazio: () => true, mensagemVazio: 'Nada aqui', Componente: Teste })
    render(<EntityPage entidade="prefixo" dados={{ texto: 'x' }} snapshot="2026-09-20" />)
    expect(screen.getByRole('status')).toHaveTextContent('Nada aqui (20/09/2026).')
  })

  it('bloco não aplicável não aparece', () => {
    registrarBloco<any>({ id: 'so-teste', entidade: 'grupo', titulo: 'Só teste', ordem: 1, depende: ['x'], fontes: ['lg_ixbr'], aplicavel: () => false, Componente: () => <p>oculto</p> })
    render(<EntityPage entidade="grupo" dados={{}} snapshot={null} />)
    expect(screen.queryByText('oculto')).toBeNull()
  })
})


describe('abas por lente', () => {
  it('todo bloco de entidade com abas pertence a uma aba que existe e tem título', () => {
    for (const e of ['asn'] as const) {
      const ids = abasDe(e).map((a) => a.id)
      expect(ids.length, e).toBeGreaterThan(1)
      for (const b of blocosDe(e)) {
        expect(b.aba, `${e}/${b.id} sem aba`).toBeTruthy()
        expect(ids, `${e}/${b.id}: aba ${b.aba} não existe`).toContain(b.aba)
        expect(b.titulo, b.id).not.toBe('')
      }
      for (const a of abasDe(e)) {
        expect(a.rotulo).not.toBe('')
        expect(blocosDe(e).some((b) => b.aba === a.id), `aba ${a.id} sem bloco`).toBe(true)
      }
    }
  })

  it('o AS tem as seis lentes da decisão 3 do portão 1, na ordem', () => {
    expect(abasDe('asn').map((a) => a.id)).toEqual(['resumo', 'roteamento', 'seguranca', 'interconexao', 'mercado', 'historico'])
  })

  it('blocos recolhidos têm título próprio e os "Como ler" não ficam vazios', () => {
    for (const b of blocosDe('asn')) {
      if (b.recolhido) expect(b.semTitulo, b.id).toBeFalsy()
      if (b.comoLer !== undefined) expect(b.comoLer.length, b.id).toBeGreaterThan(30)
    }
    expect(blocosDe('asn').filter((b) => b.comoLer).length).toBeGreaterThanOrEqual(5)
  })

  it('abas duplicadas falham alto', () => {
    expect(() => registrarAbas('grupo', [{ id: 'a', rotulo: 'A', descricao: 'x' }, { id: 'a', rotulo: 'B', descricao: 'y' }])).toThrow(/duplicadas/)
  })
})

describe('EntityPage com abas', () => {
  const Onde = () => <div data-testid="onde">{useLocation().search}</div>
  const Corpo = ({ dados }: { dados: { texto: string } }) => <p>{dados.texto}</p>
  const montar = (rota: string) => {
    registrarAbas('grupo', [{ id: 'um', rotulo: 'Um', descricao: 'primeira' }, { id: 'dois', rotulo: 'Dois', descricao: 'segunda' }, { id: 'vazia', rotulo: 'Vazia', descricao: 'sem bloco' }])
    for (const [id, aba, ordem] of [['t-a', 'um', 10], ['t-b', 'um', 20], ['t-c', 'dois', 30], ['t-d', 'dois', 40]] as const) {
      if (!blocosDe('grupo').some((b) => b.id === id)) registrarBloco<any>({ id, entidade: 'grupo', titulo: `Bloco ${id}`, ordem, aba, depende: ['x'], fontes: ['lg_ixbr'], comoLer: id === 't-a' ? 'Mostra o que o bloco A traz e o que ele não prova.' : undefined, Componente: Corpo })
    }
    return render(<MemoryRouter initialEntries={[rota]}><EntityPage entidade="grupo" dados={{ texto: 'conteúdo' }} snapshot="2026-09-20" /><Onde /></MemoryRouter>)
  }
  const titulos = () => screen.getAllByRole('region').map((r) => r.getAttribute('aria-label') ?? r.querySelector('h2')?.textContent)

  it('mostra só a primeira aba por padrão, e só as abas que têm bloco', () => {
    montar('/grupo/x')
    expect(screen.getAllByRole('tab').map((t) => t.textContent)).toEqual(['Um', 'Dois'])
    expect(screen.getByRole('tab', { name: 'Um' })).toHaveAttribute('aria-selected', 'true')
    expect(titulos()).toEqual(['Bloco t-a', 'Bloco t-b'])
    expect(screen.getByRole('tabpanel')).toHaveTextContent('primeira')
  })

  it('?aba= escolhe a lente; aba desconhecida ou sem bloco cai na primeira', () => {
    montar('/grupo/x?aba=dois')
    expect(titulos()).toEqual(['Bloco t-c', 'Bloco t-d'])
  })
  it('aba desconhecida volta à primeira', () => {
    montar('/grupo/x?aba=nao-existe')
    expect(titulos()).toEqual(['Bloco t-a', 'Bloco t-b'])
    montar('/grupo/x?aba=vazia')
    expect(screen.getAllByRole('tab', { selected: true }).map((t) => t.textContent)).toEqual(['Um', 'Um'])
  })

  it('clicar numa aba troca o conteúdo e põe o estado na URL; a primeira aba limpa o parâmetro', () => {
    montar('/grupo/x?x=1')
    fireEvent.click(screen.getByRole('tab', { name: 'Dois' }))
    expect(screen.getByTestId('onde')).toHaveTextContent('aba=dois')
    expect(screen.getByTestId('onde')).toHaveTextContent('x=1')
    expect(titulos()).toEqual(['Bloco t-c', 'Bloco t-d'])
    fireEvent.click(screen.getByRole('tab', { name: 'Um' }))
    expect(screen.getByTestId('onde').textContent).not.toContain('aba=')
  })

  it('teclado: → ativa a próxima, End a última, ← volta; só a aba ativa entra na ordem de Tab', () => {
    montar('/grupo/x')
    const um = screen.getByRole('tab', { name: 'Um' })
    expect(um).toHaveAttribute('tabindex', '0')
    expect(screen.getByRole('tab', { name: 'Dois' })).toHaveAttribute('tabindex', '-1')
    fireEvent.keyDown(um, { key: 'ArrowRight' })
    expect(screen.getByRole('tab', { name: 'Dois' })).toHaveAttribute('aria-selected', 'true')
    fireEvent.keyDown(screen.getByRole('tab', { name: 'Dois' }), { key: 'ArrowLeft' })
    expect(screen.getByRole('tab', { name: 'Um' })).toHaveAttribute('aria-selected', 'true')
    fireEvent.keyDown(screen.getByRole('tab', { name: 'Um' }), { key: 'End' })
    expect(screen.getByRole('tab', { name: 'Dois' })).toHaveAttribute('aria-selected', 'true')
  })

  it('?versao=1 mostra a página antiga: todos os blocos, sem abas', () => {
    montar('/grupo/x?versao=1')
    expect(screen.queryByRole('tablist')).toBeNull()
    expect(titulos()).toEqual(['Bloco t-a', 'Bloco t-b', 'Bloco t-c', 'Bloco t-d'])
  })

  it('link para #bloco-… abre a aba que tem o bloco', () => {
    montar('/grupo/x#bloco-t-d')
    expect(screen.getByRole('tab', { name: 'Dois' })).toHaveAttribute('aria-selected', 'true')
  })

  it('"Como ler" aparece só no bloco que o declara, recolhido por padrão', () => {
    montar('/grupo/x')
    const como = screen.getAllByTestId('como-ler')
    expect(como).toHaveLength(1)
    expect(como[0]).not.toHaveAttribute('open')
    expect(como[0]).toHaveTextContent('o que ele não prova')
  })
})

describe('correspondência do AS: nenhum bloco ficou fora das abas', () => {
  const ESPERADO: Record<string, string[]> = {
    resumo: ['metricas', 'usuarios', 'alertas'],
    roteamento: ['recursos-ipv4', 'radar', 'estabilidade', 'diagnostico', 'prefixos-rir', 'tabela-global', 'mapa', 'relacoes'],
    seguranca: ['seguranca', 'prontidao', 'bloqueios', 'exposicao', 'roa', 'aspa'],
    interconexao: ['route-servers', 'politica-rs', 'instalacoes', 'presenca', 'interconexao-mensuravel', 'ixps-externos', 'peeringdb'],
    mercado: ['organizacao', 'acessos', 'outorga-scm', 'outorga-smp', 'outorga-stfc', 'outorga-seac'],
    historico: ['linha-do-tempo'],
  }

  it('cada um dos 31 blocos registrados está em exatamente uma aba, na ordem esperada', () => {
    const porAba: Record<string, string[]> = {}
    for (const b of blocosDe('asn')) (porAba[b.aba!] ??= []).push(b.id)
    expect(Object.fromEntries(Object.entries(porAba).map(([k, v]) => [k, [...v].sort()]))).toEqual(Object.fromEntries(Object.entries(ESPERADO).map(([k, v]) => [k, [...v].sort()])))
    expect(Object.values(porAba).flat()).toHaveLength(blocosDe('asn').length)
    expect(blocosDe('asn')).toHaveLength(31)
  })

  it('com todos os dados presentes, a união das abas é a página de antes (nenhum bloco some)', () => {
    const cheio: any = {
      doc: { ...(fixtures.asnDetail as any), apnic_users: 10, is_br: true, aspa_providers: [], scm: [{ cnpj: '1' }], smp: [{ cnpj: '1' }], stfc: [{ cnpj: '1' }], seac: [{ cnpj: '1' }], external_ixps: ['x'],
        global_prefixes_v4: ['1.0.0.0/24'], upstreams: [1], pdb_registered: true },
      date: '2026-09-20', ixpPaths: {}, pathNodeMeta: {}, ixpMemberCodes: [], carregandoCaminhos: false,
      historico: {}, seguranca: {}, prontidao: {}, routeServers: {}, politicaRs: {}, organizacao: {}, abuso: {}, bloqueios: {}, radar: {}, exposicao: {}, facilities: {}, peering: {}, asnStability: {}, asnDiagnosis: {},
    }
    const aplicaveis = blocosDe('asn').filter((b) => !b.aplicavel || b.aplicavel(cheio)).map((b) => b.id)
    for (const essencial of ['estabilidade', 'diagnostico', 'politica-rs', 'linha-do-tempo', 'relacoes', 'radar', 'exposicao', 'bloqueios', 'organizacao']) expect(aplicaveis, essencial).toContain(essencial)
    const emAbas = Object.values(ESPERADO).flat()
    expect(aplicaveis.filter((id) => !emAbas.includes(id))).toEqual([])
  })
})
