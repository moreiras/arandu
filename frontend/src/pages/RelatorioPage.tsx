// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useParams } from 'react-router-dom'
import { Link } from '../components/layout/LinkDatado'
import { useQuery } from '@tanstack/react-query'
import { fetchASNsLote, fetchGrupo, fetchMunicipioPerfil, fetchOperadoraPerfil } from '../services/api'
import { useActiveDate } from '../hooks/useSnapshot'
import { EstadoDados, ehErroDeAcessoOuFalha } from '../components/ui/EstadoDados'
import { DESCRICAO_SELO, ROTULO_SELO, type Selo } from '../components/entidade'
import { avisoLinkCitacao, linkPermanente, montarCitacao } from '../components/entidade/citacao'
import { useFontes } from '../hooks/entidades/entidades'
import { useAppStore } from '../store/app'
import { compararAs, compararMunicipios, compararOperadoras, type Comparacao } from '../features/comparar/entidades'
import { sinteseAs } from '../features/asn/sintese'
import { sinteseOperadora } from '../features/operadora/sintese'
import { derivarOperadora, type OperadoraCtx } from '../features/operadora/contexto'
import { sinteseMunicipio } from '../features/municipio/sintese'
import type { GrupoDetalhe } from '../types/api'
import { SITE } from '../lib/site'
import { asnValido, cnpjValido } from '../lib/identificadores'

interface Relatorio { titulo: string; subtitulo?: string; frases: Array<{ id: string; texto: string; selo: Selo }>; quadro: Comparacao; fontes: string[]; snapshot: string | null; caminho: string }
const COR_SELO = { fato: 'bg-fato-600', inferido: 'bg-inferido-600', estimado: 'bg-estimado-600' } as const
const TEXTO_SELO = { fato: 'text-fato-700', inferido: 'text-inferido-700', estimado: 'text-estimado-700' } as const

/** Selo em texto (WCAG 1.4.1): a cor do ponto é reforço; o rótulo fica visível na tela, no leitor de tela e no papel sem fundos. */
function SeloTexto({ selo }: { selo: Selo }) {
  return <span className={`mr-1.5 rounded border border-current px-1 text-xs font-medium uppercase leading-4 ${TEXTO_SELO[selo]}`} title={DESCRICAO_SELO[selo]} data-selo={selo}>{ROTULO_SELO[selo]}</span>
}
const TIPOS = ['asn', 'operadora', 'municipio', 'grupo'] as const
type Tipo = (typeof TIPOS)[number]
const n = (v: number) => v.toLocaleString('pt-BR', { maximumFractionDigits: 0 })

function quadroGrupo(g: GrupoDetalhe): Comparacao {
  const l = (id: string, rotulo: string, v: string | null, selo: Selo = 'fato', nota?: string) => ({ id, rotulo, celulas: [v], selo, nota })
  return {
    colunas: [{ id: g.grupo_id, nome: 'Grupo', to: `/grupo/${g.grupo_id}` }],
    linhas: [
      l('empresas', 'Empresas (CNPJs raiz)', n(g.empresas)), l('cnpjs', 'CNPJs', n(g.cnpjs.length)), l('assinantes', 'Acessos fixos declarados', n(g.assinantes), 'fato', 'soma dos CNPJs do grupo, declarada ao SICI'),
      l('asns', 'ASNs', n(g.asns.length)), l('municipios', 'Municípios com acessos', n(g.municipios.length)), l('usuarios', 'Usuários estimados (APNIC)', n(g.usuarios_apnic), 'estimado'),
      l('class', 'Correspondência societária', g.classificacao, 'inferido', 'por quadro societário em comum; só estrutura entre empresas, sem sócios pessoa física'),
    ],
  }
}

async function carregar(tipo: Tipo, id: string, date?: string): Promise<Relatorio | null> {
  if (tipo === 'asn') {
    const r = await fetchASNsLote([id], { date }); const d = r.items[0] as any
    if (!d) return null
    return { titulo: `AS${d.asn}`, subtitulo: d.name, frases: sinteseAs(d), quadro: compararAs([d]), fontes: ['fulltable_routeviews', 'registro_br', 'apnic_pop'], snapshot: d.snapshot_date, caminho: `/asn/${d.asn}` }
  }
  if (tipo === 'operadora') {
    const p = await fetchOperadoraPerfil(id, date)
    if (!p) return null
    const nome = p.indicadores?.empresa ?? p.scm?.empresa ?? p.smp?.empresa ?? p.cnpj
    // mesma derivação da página (`derivarOperadora`): outorga só com registro, B2C sobre os acessos fixos declarados
    const fontes = { data: p.scm ?? undefined, dataMovel: p.smp ?? undefined, dataStfc: p.stfc ?? undefined, dataSeac: p.seac ?? undefined }
    const ctx = { ...fontes, data: p.scm ? { ...p.scm, snapshot_date: p.snapshot_date, cnpj: p.cnpj } : undefined, indicadores: p.indicadores, ...derivarOperadora(fontes) } as unknown as OperadoraCtx
    return { titulo: nome, subtitulo: `CNPJ ${p.cnpj}`, frases: sinteseOperadora(nome, ctx), quadro: compararOperadoras([p]), fontes: ['anatel_sici', 'anatel_outorgas', 'registro_br'], snapshot: p.snapshot_date, caminho: `/operadora/${p.cnpj}` }
  }
  if (tipo === 'municipio') {
    const p = await fetchMunicipioPerfil(id, date)
    if (!p) return null
    const ctx = { ibge: p.ibge, fixo: p.fixo ?? undefined, movel: p.movel ?? undefined, indicadores: p.indicadores, territorio: p.territorio, proximos: (p.ptts_proximos ?? []) } as any
    return { titulo: `${p.nome}/${p.uf}`, subtitulo: `IBGE ${p.ibge}`, frases: sinteseMunicipio(p.nome, ctx), quadro: compararMunicipios([p]), fontes: ['anatel_sici', 'ibge_censo_pnad', 'curada_pix'], snapshot: p.snapshot_date, caminho: `/municipio/${p.ibge}` }
  }
  const g = await fetchGrupo(id, date)
  const nome = g.cnpjs[0]?.empresa || g.grupo_id
  return { titulo: g.tamanho > 1 ? `Grupo de ${nome}` : nome, subtitulo: `${g.empresas} empresa${g.empresas === 1 ? '' : 's'}`, frases: [], quadro: quadroGrupo(g), fontes: ['anatel_sici', 'receita_cnpj', 'registro_br'], snapshot: g.snapshot_date, caminho: `/grupo/${g.grupo_id}` }
}

/**
 * Relatório de uma página: síntese, indicadores com selo, fontes, citação e link permanente de uma entidade, em um A4 (Ctrl+P ou "Salvar como PDF" do navegador).
 * O menu, o rodapé e os botões somem na impressão (`print:hidden`); a página não tem mapas nem gráficos de propósito, para caber numa folha.
 */
export function RelatorioPage() {
  const { tipo: t, id = '' } = useParams()
  const tipo = (TIPOS as readonly string[]).includes(t ?? '') ? (t as Tipo) : null
  const date = useActiveDate()
  const { fontes: fontesDoSnapshot } = useFontes()
  const atuais = useAppStore((s) => s.snapshotsAtuais)
  // identificador que a API recusaria (400/422, registrados no console) cai direto em "sem dado"
  const idValido = tipo === 'operadora' ? cnpjValido(id) : tipo === 'asn' ? asnValido(id) : !!id
  const q = useQuery({ queryKey: ['relatorio', tipo, id, date], enabled: !!tipo && idValido, queryFn: () => carregar(tipo!, id, date ?? undefined), staleTime: 10 * 60 * 1000, retry: false })
  if (!tipo) return <p className="text-sm text-gray-500">Relatório disponível para AS, operadora, município e grupo.</p>
  if (q.isLoading) return <div className="h-64 bg-gray-50 rounded animate-pulse" />
  // Login (snapshot histórico), orçamento, taxa ou rede: o relatório não carregou, o que não diz nada sobre a entidade.
  if (q.isError && ehErroDeAcessoOuFalha(q.error)) return <EstadoDados variante="pagina" erro={q.error} oQue="o relatório" aoTentarDeNovo={() => void q.refetch()} className="mx-auto max-w-3xl" />
  const r = q.data
  if (!r) return <p className="text-sm text-gray-500">Sem dado para esta entidade neste snapshot. <Link to="/" className="text-primario-600 hover:underline">Voltar ao início</Link></p>
  const url = linkPermanente(window.location.origin, r.caminho, '', r.snapshot)
  // A citação leva os indicadores do quadro, o snapshot e as fontes com as datas: o link só abre sem login enquanto o snapshot é um dos dois mais recentes (D3).
  const valores = r.quadro.linhas.filter((l) => l.celulas[0]).map((l) => ({ rotulo: l.rotulo, valor: String(l.celulas[0]) }))
  const citacao = montarCitacao({ entidade: r.titulo, bloco: 'Relatório de uma página', valores, fontes: r.fontes, fontesEntradas: fontesDoSnapshot, snapshot: r.snapshot, url, acessoEm: new Date() })
  return (
    <article className="mx-auto max-w-3xl space-y-4 text-sm" data-testid="relatorio">
      <div className="flex flex-wrap items-center gap-2 print:hidden">
        <button type="button" onClick={() => window.print()} className="rounded bg-primario-600 px-3 py-1.5 text-sm text-white hover:bg-primario-700">Imprimir ou salvar em PDF</button>
        <Link to={r.caminho} className="text-sm text-primario-700 hover:underline">← Voltar à página completa</Link>
      </div>
      <header className="border-b border-gray-300 pb-2">
        <p className="text-xs text-gray-500">{SITE.nome} · relatório de uma página</p>
        <h1 className="text-titulo-1 text-gray-900">{r.titulo}</h1>
        {r.subtitulo && <p className="text-gray-600">{r.subtitulo}</p>}
      </header>
      {r.frases.length > 0 && (
        <section aria-label="Síntese"><ul className="space-y-1">
          {r.frases.map((f) => <li key={f.id} className="flex gap-2"><span className={`mt-1.5 h-2 w-2 flex-shrink-0 rounded-full ${COR_SELO[f.selo]}`} aria-hidden="true" /><span><SeloTexto selo={f.selo} />{f.texto}</span></li>)}
        </ul></section>
      )}
      <section aria-label="Indicadores"><table className="w-full text-sm" data-tabela="grade"><tbody>
        {r.quadro.linhas.map((l) => (
          <tr key={l.id} className="border-b border-gray-100 align-top">
            <th scope="row" className="w-1/2 py-1 pr-3 text-left font-normal text-gray-700">
              <span className={`mr-1.5 inline-block h-2 w-2 rounded-full ${COR_SELO[l.selo]}`} aria-hidden="true" /><SeloTexto selo={l.selo} />{l.rotulo}
              {l.nota && <span className="block text-xs text-gray-400">{l.nota}</span>}
            </th>
            <td className="py-1 tabular-nums">{l.celulas[0] ?? '—'}</td>
          </tr>
        ))}
      </tbody></table></section>
      <footer className="space-y-1 border-t border-gray-300 pt-2 text-xs text-gray-600">
        <p><span className="font-medium">Selos:</span> fato (declarado ou medido na fonte), inferido (derivado por regra, pode estar errado) e estimado (amostragem ou modelo). Cada linha tem o seu.</p>
        <p><span className="font-medium">Citar:</span> {citacao}</p>
        <p data-testid="aviso-link-citacao">{avisoLinkCitacao(r.snapshot, atuais)}</p>
      </footer>
    </article>
  )
}
