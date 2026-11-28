// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { lazy, Suspense, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ComoLer } from '../../../components/ui/ComoLer'
import { Kpi } from '../../../components/ui/Kpi'
import { ResumoEmTexto, type FraseResumo } from '../../../components/ui/ResumoEmTexto'
import { GrupoFontes } from '../../../components/ui/FontesEDatas'
import { COR_SEM_DADO } from '../../../components/maps/coresCoropletico'
import { useAreaInfluenciaPtt, useCentroides } from '../../../hooks/entidades'
import { expressaoFaixas, formatarKm, frasesArea, pct, ROTULO_FAIXA, ROTULO_FAIXA_CURTO, ROTULO_VISAO, TONS_UM_MATIZ, type Faixa } from '../../../lib/areaInfluencia'
import { palavra } from '../../../lib/sintese'
import type { AreaInfluenciaPtt, AreaInfluenciaVisao, VisaoArea } from '../../../types/areaInfluencia'
import type { BlocoProps } from '../../entidade/registry'
import type { PttCtx } from '../contexto'

const Coropletico = lazy(() => import('../../../components/maps/Coropletico').then((m) => ({ default: m.Coropletico })))
const VISOES: VisaoArea[] = ['diretos', 'todos']
const FAIXAS: Faixa[] = [1, 2, 3]
const CHAVE_FAIXA = { 1: 'ate_p50', 2: 'p50_a_p80', 3: 'alem_p80' } as const
const POR_PAGINA = 50
const n = (v: number) => v.toLocaleString('pt-BR')
const FONTE = 'SICI (Anatel) e looking glass do IX.br'

/** Bloco "Área de influência observada" da página de PTT: onde atuam as operadoras que aparecem no PTT, por acessos do SICI. */
export function AreaInfluenciaBloco({ dados }: BlocoProps<PttCtx>) {
  const q = useAreaInfluenciaPtt(dados.code)
  if (q.isLoading) return <p className="text-sm text-gray-500" role="status">Carregando a área de influência…</p>
  if (q.isError || !q.data) return <p className="text-sm text-gray-600">A área de influência deste PTT não foi calculada para este snapshot.</p>
  return <Corpo d={q.data} />
}

function Seletor({ visao, aoMudar, disponiveis }: { visao: VisaoArea; aoMudar: (v: VisaoArea) => void; disponiveis: Record<VisaoArea, boolean> }) {
  return (
    <div role="group" aria-label="Visão da área de influência" className="inline-flex overflow-hidden rounded-md border border-gray-200 text-xs" data-testid="seletor-visao">
      {VISOES.map((v) => (
        <button key={v} type="button" aria-pressed={v === visao} onClick={() => aoMudar(v)}
          className={`px-3 py-1.5 ${v === visao ? 'bg-primario-600 text-white' : 'bg-white text-gray-700 hover:bg-gray-50'}`}>
          {ROTULO_VISAO[v]}{disponiveis[v] ? '' : ' (sem dados)'}
        </button>
      ))}
    </div>
  )
}

function Corpo({ d }: { d: AreaInfluenciaPtt }) {
  const navigate = useNavigate()
  const { data: centroides } = useCentroides()
  const diretos = d.visoes.diretos ?? null
  const todos = d.visoes.todos ?? null
  const [visao, setVisao] = useState<VisaoArea>(diretos ? 'diretos' : 'todos')
  const atual = d.visoes[visao] ?? null
  const mesSici = d.fontes.sici

  const frases = frasesArea(diretos, todos)
  const resumo: FraseResumo[] = [
    { id: 'diretos', texto: frases.diretos, selo: 'inferido', fonte: FONTE, dataRef: mesSici },
    { id: 'todos', texto: frases.todos, selo: 'inferido', fonte: FONTE, dataRef: mesSici },
    ...(frases.mediana ? [{ id: 'mediana', texto: frases.mediana, selo: 'inferido' as const, fonte: FONTE, dataRef: mesSici }] : []),
  ]

  const cor = useMemo(() => (atual ? expressaoFaixas(atual.municipios_faixa) : COR_SEM_DADO), [atual])
  const pontos = useMemo(() => d.pix.pontos.map(([lat, lon]) => ({ lat, lon })), [d.pix.pontos])
  const caixa = useMemo<[[number, number], [number, number]] | undefined>(() => {
    const pts: Array<[number, number]> = d.pix.pontos.map(([lat, lon]) => [lon, lat])
    if (centroides && atual) for (const ibge of Object.keys(atual.municipios_faixa)) if (centroides[ibge]) pts.push([centroides[ibge][0], centroides[ibge][1]])
    if (pts.length === 0) return undefined
    const lons = pts.map((p) => p[0]), lats = pts.map((p) => p[1])
    return [[Math.min(...lons) - 0.5, Math.min(...lats) - 0.5], [Math.max(...lons) + 0.5, Math.max(...lats) + 0.5]]
  }, [centroides, atual, d.pix.pontos])

  return (
    <div className="space-y-4" data-testid="area-influencia">
      <Seletor visao={visao} aoMudar={setVisao} disponiveis={{ diretos: !!diretos, todos: !!todos }} />

      <GrupoFontes snapshot={d.snapshot_date}>
        {atual ? (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4" data-testid="area-kpis">
            <Kpi rotulo="Operadoras com acessos atribuídos" valor={n(atual.operadoras)} selo="inferido" fonte={FONTE} dataRef={mesSici} explicacao="Operadoras (CNPJs do SICI com ASN ligado) cujos acessos vão para este PTT por ser o mais próximo entre os que elas enxergam." />
            <Kpi rotulo="Municípios" valor={n(atual.municipios)} selo="inferido" fonte={FONTE} dataRef={mesSici} />
            <Kpi rotulo="Acessos atribuídos" valor={n(atual.acessos)} selo="inferido" fonte={FONTE} dataRef={mesSici} explicacao="Acessos de banda larga fixa declarados ao SICI, contados uma vez, no PTT mais próximo entre os que a operadora enxerga." />
            <Kpi rotulo="Mediana por operadora" valor={formatarKm(atual.mediana_operadora_km)} selo="inferido" fonte={FONTE} dataRef={mesSici} explicacao="Distância mediana entre as operadoras do PTT, cada uma contando uma vez. Mede outra população que o P50." />
            <Kpi rotulo="P50: a maioria dos acessos" valor={formatarKm(atual.p50_km)} selo="inferido" fonte={FONTE} dataRef={mesSici} explicacao="Distância em linha reta até a qual está metade dos acessos atribuídos ao PTT." />
            <Kpi rotulo="P80: quase todos" valor={formatarKm(atual.p80_km)} selo="inferido" fonte={FONTE} dataRef={mesSici} />
            <Kpi rotulo="P90" valor={formatarKm(atual.p90_km)} selo="inferido" fonte={FONTE} dataRef={mesSici} />
          </div>
        ) : (
          <p className="text-sm text-gray-600" data-testid="area-sem-visao">Nenhuma operadora tem acessos atribuídos a este PTT na visão “{ROTULO_VISAO[visao]}”.</p>
        )}
        <ResumoEmTexto frases={resumo} regras="area-influencia-1" snapshot={d.snapshot_date} notaComoLer="Os números são inferidos dos acessos do SICI e não medem a rede nem o tráfego." />
      </GrupoFontes>

      {d.pix.aproximado && (
        <p className="text-sm text-gray-700" data-testid="area-pix-aproximado">
          {n(d.pix.endereco + d.pix.sede)} {palavra(d.pix.endereco + d.pix.sede, 'PIX deste PTT não tem coordenada no cadastro e teve a posição aproximada', 'PIX deste PTT não têm coordenada no cadastro e tiveram a posição aproximada')} pelo centroide do município
          ({d.pix.endereco > 0 ? `${n(d.pix.endereco)} pelo endereço` : ''}{d.pix.endereco > 0 && d.pix.sede > 0 ? ' e ' : ''}{d.pix.sede > 0 ? `${n(d.pix.sede)} pela sede do PTT` : ''}).
          As distâncias deste PTT carregam essa imprecisão.
        </p>
      )}

      <div className="grid min-w-0 items-start gap-4 lg:grid-cols-[minmax(0,1fr)_15rem]">
        <Suspense fallback={<p className="text-sm text-gray-400" role="status">Carregando o mapa…</p>}>
          <Coropletico cor={cor} nivel="municipio" altura={420} caixa={caixa} pontos={pontos}
            descricao={`Mapa dos municípios com acessos atribuídos ao PTT ${d.nome} na visão ${ROTULO_VISAO[visao].toLowerCase()}, pintados pela faixa de distância. O ponto com anel marca o PIX. Os mesmos números estão nas tabelas abaixo.`}
            rotulo={(ibge, nome, uf) => {
              const m = atual?.municipios_faixa[ibge]
              return m ? `${nome}/${uf}: ${ROTULO_FAIXA_CURTO[m[1] as Faixa]}, ${n(m[0])} ${palavra(m[0], 'acesso atribuído', 'acessos atribuídos')}` : `${nome}/${uf}: sem acessos atribuídos a este PTT`
            }}
            aoClicar={(codigo, nivel) => navigate(nivel === 'uf' ? `/uf/${codigo}` : `/municipio/${codigo}`)} />
        </Suspense>
        <figure aria-label="Legenda do mapa" className="space-y-1 text-xs text-gray-600" data-testid="legenda-area">
          <figcaption className="font-medium text-gray-800">Faixa de distância ao PIX</figcaption>
          <ul className="space-y-0.5">
            {FAIXAS.map((f) => (
              <li key={f} className="flex items-center gap-2"><span className="inline-block h-3 w-5 rounded-sm border border-gray-300" style={{ background: TONS_UM_MATIZ[f] }} aria-hidden="true" />{ROTULO_FAIXA[f]}</li>
            ))}
            <li className="flex items-center gap-2"><span className="inline-block h-3 w-5 rounded-sm border border-gray-300" style={{ background: COR_SEM_DADO }} aria-hidden="true" />Sem acessos atribuídos a este PTT</li>
            <li className="flex items-center gap-2"><span className="inline-block h-3 w-3 rounded-full border-2 border-gray-900 bg-white" aria-hidden="true" />PIX do PTT</li>
          </ul>
          <p>Tons de uma cor só, do mais escuro (perto) ao mais claro (longe). A cor só ordena as faixas.</p>
        </figure>
      </div>

      {atual && <TabelaFaixas visao={atual} />}
      {atual && <TabelaMunicipios visao={atual} nomes={d.municipios_nomes} />}

      <ComoLer titulo="Como ler a área de influência">
        <p>
          Cada acesso de banda larga fixa declarado ao SICI, por município e operadora (CNPJ), é atribuído ao PTT mais próximo entre os que a operadora enxerga. A operadora enxerga os PTTs onde algum ASN ligado ao seu CNPJ aparece.
          Nenhum acesso conta duas vezes: um CNPJ com vários ASNs soma os PTTs deles e entra uma vez só.
        </p>
        <p>
          A visão “{ROTULO_VISAO.diretos}” usa os ASNs com sessão própria no PTT e prefixo próprio visto nele. A visão “{ROTULO_VISAO.todos}” inclui também os ASNs que anunciam prefixo próprio pelo PTT sem sessão, levados por outro participante; a primeira está contida na segunda.
          Não há exclusão de operadoras.
        </p>
        <p>
          A distância é em linha reta, do centroide do município ao PIX mais próximo do PTT (não é distância por rodovia ou fibra). PIX sem coordenada no cadastro é posicionado no centroide do município do endereço ou, sem endereço reconhecível, no da sede do PTT.
          O P50, o P80 e o P90 pesam por acessos; a mediana por operadora conta cada operadora uma vez e por isso mede outra população.
        </p>
        <p>
          Os acessos são do mês {mesSici ?? 'de referência'} do SICI, diferente do mês do snapshot ({d.snapshot_date}). O selo é <strong>inferido</strong>: o mapa mostra onde as operadoras que aparecem no PTT declaram acessos.
          A rede delas e o caminho do tráfego ficam fora do que estes dados provam, e isto não é cobertura de rede. Operadora sem ASN ligado ao CNPJ não entra.
        </p>
      </ComoLer>
    </div>
  )
}

function TabelaFaixas({ visao }: { visao: AreaInfluenciaVisao }) {
  const limite = { 1: `até ${formatarKm(visao.p50_km)}`, 2: `até ${formatarKm(visao.p80_km)}`, 3: `além de ${formatarKm(visao.p80_km)}` }
  return (
    <div className="overflow-x-auto" data-testid="tabela-faixas">
      <table className="min-w-full text-sm">
        <caption className="mb-1 text-left text-xs font-semibold text-gray-700">Municípios e acessos por faixa de distância</caption>
        <thead className="text-xs text-gray-600"><tr>
          <th scope="col" className="px-2 py-1 text-left">Faixa</th>
          <th scope="col" className="px-2 py-1 text-right">Distância</th>
          <th scope="col" className="px-2 py-1 text-right">Municípios</th>
          <th scope="col" className="px-2 py-1 text-right">Acessos atribuídos</th>
          <th scope="col" className="px-2 py-1 text-right">Parcela dos acessos</th>
        </tr></thead>
        <tbody className="divide-y divide-gray-100">
          {FAIXAS.map((f) => {
            const x = visao.faixas[CHAVE_FAIXA[f]]
            return (
              <tr key={f}>
                <th scope="row" className="px-2 py-1 text-left font-normal">{ROTULO_FAIXA[f]}</th>
                <td className="px-2 py-1 text-right tabular-nums">{limite[f]}</td>
                <td className="px-2 py-1 text-right tabular-nums">{n(x.municipios)}</td>
                <td className="px-2 py-1 text-right tabular-nums">{n(x.acessos)}</td>
                <td className="px-2 py-1 text-right tabular-nums">{pct(x.acessos, visao.acessos)}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function TabelaMunicipios({ visao, nomes }: { visao: AreaInfluenciaVisao; nomes: Record<string, string> }) {
  const [faixa, setFaixa] = useState<0 | Faixa>(0)
  const [ate, setAte] = useState(POR_PAGINA)
  const linhas = useMemo(() => Object.entries(visao.municipios_faixa)
    .map(([ibge, [acessos, f]]) => ({ ibge, nome: nomes[ibge] ?? ibge, acessos, faixa: f as Faixa }))
    .filter((l) => faixa === 0 || l.faixa === faixa)
    .sort((a, b) => a.faixa - b.faixa || b.acessos - a.acessos || a.nome.localeCompare(b.nome, 'pt-BR')), [visao, nomes, faixa])
  return (
    <details className="text-sm text-gray-700" data-testid="tabela-municipios">
      <summary className="cursor-pointer select-none text-xs font-medium text-primario-700 hover:text-primario-900">Municípios por faixa, em tabela ({n(Object.keys(visao.municipios_faixa).length)})</summary>
      <div className="mt-2 space-y-2">
        <label className="flex items-center gap-2 text-xs text-gray-700">
          Mostrar
          <select value={faixa} onChange={(e) => { setFaixa(Number(e.target.value) as 0 | Faixa); setAte(POR_PAGINA) }} className="rounded border border-gray-300 px-1 py-0.5">
            <option value={0}>todas as faixas</option>
            {FAIXAS.map((f) => <option key={f} value={f}>{ROTULO_FAIXA[f]}</option>)}
          </select>
        </label>
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <caption className="sr-only">Municípios com acessos atribuídos ao PTT, por faixa de distância</caption>
            <thead className="text-xs text-gray-600"><tr>
              <th scope="col" className="px-2 py-1 text-left">Município</th>
              <th scope="col" className="px-2 py-1 text-left">Faixa</th>
              <th scope="col" className="px-2 py-1 text-right">Acessos atribuídos</th>
            </tr></thead>
            <tbody className="divide-y divide-gray-100">
              {linhas.slice(0, ate).map((l) => (
                <tr key={l.ibge}>
                  <th scope="row" className="px-2 py-1 text-left font-normal">{l.nome}</th>
                  <td className="px-2 py-1">{ROTULO_FAIXA_CURTO[l.faixa]}</td>
                  <td className="px-2 py-1 text-right tabular-nums">{n(l.acessos)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {linhas.length > ate && (
          <button type="button" onClick={() => setAte(ate + POR_PAGINA)} className="text-xs font-medium text-primario-700 hover:underline">
            Mostrar mais {n(Math.min(POR_PAGINA, linhas.length - ate))} ({n(linhas.length - ate)} {palavra(linhas.length - ate, 'restante', 'restantes')})
          </button>
        )}
      </div>
    </details>
  )
}
