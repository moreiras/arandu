// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useQuery } from '@tanstack/react-query'
import { ComoLer, Kpi, TabelaDados } from '../../components/ui'
import { useActiveDate } from '../../hooks/useSnapshot'
import { fetchBrasilIndicadores } from '../../services/api'
import type { MedicaoApnicPais } from '../../types/api'

const pct = (v?: number | null, casas = 1) => (v == null ? null : `${v.toLocaleString('pt-BR', { maximumFractionDigits: casas })}%`)
const num = (v?: number | null) => (v == null ? null : v.toLocaleString('pt-BR'))
const CLASSES: [string, string][] = [['pronto', 'Pronto'], ['em_progresso', 'Em progresso'], ['atrasado', 'Atrasado'], ['sem_dados', 'Sem dados']]

/** Agregados do país (`/brasil/indicadores`, rota aberta): IPv6 do APNIC, DNSSEC, ROV e prontidão. */
export function useBrasilIndicadores() {
  const date = useActiveDate()
  return useQuery({ queryKey: ['brasil-indicadores', date], queryFn: () => fetchBrasilIndicadores(date ?? undefined), enabled: !!date, staleTime: Infinity, retry: false })
}

/**
 * Referência de uma medição do APNIC que se exibe como média ponderada (TRANSV-E6): a mediana das redes, quantas foram medidas e a distribuição por faixa.
 * A média ponderada pelas amostras é dominada pelas redes grandes; sozinha, esconde que a maioria das redes medidas está longe dela.
 */
export function referenciaMedicao(m?: MedicaoApnicPais | null): string | undefined {
  if (!m || m.mediana_pct == null) return undefined
  const f = m.faixas
  const faixas = f ? `; ASes por faixa: ${num(f.ate_10)} até 10%, ${num(f.de_10_a_90)} de 10% a 90%, ${num(f.acima_de_90)} acima de 90%` : ''
  return `mediana das redes: ${pct(m.mediana_pct, 2)}${m.asns != null ? ` (${num(m.asns)} ASes medidos)` : ''}${faixas}`
}

/** "Como ler" das médias ponderadas e do IPv6 da faixa de números do país: o que cada percentual conta (PT-15 / TRANSV-E5, TRANSV-E6). */
export function ComoLerNumerosPais() {
  return (
    <ComoLer titulo="Como ler: IPv6, médias ponderadas e medianas">
      <p>As medidas de IPv6 contam coisas diferentes. &ldquo;ASNs brasileiros que anunciam IPv6&rdquo; conta as redes com prefixo IPv6 na tabela global. &ldquo;Usuários com IPv6&rdquo; conta os usuários estimados pelo APNIC Labs. Ter um bloco IPv6 alocado, anunciado ou visto num PTT é outra medida, que não indica anúncio nem uso.</p>
      <p>ROV e DNSSEC aparecem como média ponderada pelas amostras do APNIC Labs, que dá mais peso às redes com mais medições. A mediana trata todas as redes do mesmo modo, e as faixas mostram quantas redes ficam em cada parte da escala. Por isso a mediana pode ficar longe da média. A prontidão em segurança de roteamento usa outra ponderação: os usuários estimados de cada rede.</p>
      <p>A variação do IPv6, em pontos percentuais, vem da série semanal do histórico. Essa série usa uma base de ASNs e de usuários diferente da deste indicador, então a variação mostrada é a do percentual dentro da própria série, nunca a diferença entre totais de bases distintas. Onde os pontos não são comparáveis, a variação não aparece. As séries de segurança e de roteamento, com a regra completa, estão em Estado da segurança de roteamento e na Tabela BGP.</p>
    </ComoLer>
  )
}

export const EXPLICA = {
  ipv6: 'Proporção dos usuários de Internet no Brasil que usam IPv6: soma das estimativas do APNIC Labs por ASN do Brasil (usuários com IPv6 ÷ usuários). Difere do número por país que o APNIC publica, que usa a amostra do país.',
  dnssec: 'Proporção das medições do APNIC Labs em que o resolvedor de DNS do usuário valida DNSSEC (média ponderada pelas amostras dos ASNs do Brasil com amostra suficiente).',
  prontidao: 'Índice de 0 a 100 de prontidão em segurança de roteamento (filtragem, anti-spoofing, coordenação e validação global), média dos ASNs do Brasil ponderada pelos usuários estimados. Não é veredito sobre empresas.',
  rov: 'Proporção das medições do APNIC Labs em que o usuário não alcança uma rota RPKI-inválida (a rede descarta rotas inválidas), média ponderada.',
}

/** Três KPIs para "O Brasil em números" (home): IPv6, DNSSEC e prontidão. */
export function KpisSegurancaPais() {
  const { data } = useBrasilIndicadores()
  const d = data?.snapshot_date
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3" data-testid="kpis-pais">
      <Kpi selo="estimado" rotulo="Usuários com IPv6 (estimativa)" valor={pct(data?.ipv6.pct_usuarios_ipv6)} tom="v6" explicacao={EXPLICA.ipv6} fonte="APNIC Labs" dataRef={d} />
      <Kpi selo="estimado" rotulo="Validação de DNSSEC (média ponderada por amostras)" valor={pct(data?.dnssec?.media_ponderada_pct, 2)} tom="tecnico" referencia={referenciaMedicao(data?.dnssec)} explicacao={EXPLICA.dnssec} fonte="APNIC Labs" dataRef={data?.dnssec?.fonte?.as_of ?? d} />
      <Kpi selo="estimado" rotulo="Filtragem de rotas inválidas (ROV, média ponderada por amostras)" valor={pct(data?.rov?.media_ponderada_pct, 2)} tom="tecnico" referencia={referenciaMedicao(data?.rov)} explicacao={EXPLICA.rov} fonte="APNIC Labs" dataRef={data?.rov?.fonte?.as_of ?? d} />
      <Kpi selo="inferido" rotulo="Prontidão em segurança de roteamento (média ponderada por usuários)" valor={data?.prontidao?.agregado.media_ponderada_usuarios != null ? `${data.prontidao.agregado.media_ponderada_usuarios.toLocaleString('pt-BR', { maximumFractionDigits: 1 })} de 100` : null}
        tom="tecnico" explicacao={EXPLICA.prontidao} fonte="índice do site sobre medições de terceiros" dataRef={d} />
    </div>
  )
}

/** KPIs de adoção de IPv6 pelos usuários (APNIC), para a aba IPv6 do Panorama técnico. */
export function Ipv6Apnic() {
  const { data } = useBrasilIndicadores()
  const v = data?.ipv6
  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4" data-testid="ipv6-apnic">
      <Kpi selo="estimado" rotulo="Usuários com IPv6 (estimativa)" valor={pct(v?.pct_usuarios_ipv6)} tom="v6" explicacao={EXPLICA.ipv6} fonte="APNIC Labs" dataRef={data?.snapshot_date} />
      <Kpi selo="estimado" rotulo="Usuários estimados com IPv6" valor={num(v?.usuarios_ipv6)} tom="v6" explicacao="Soma das estimativas do APNIC de usuários com IPv6 nos ASNs do Brasil." fonte="APNIC Labs" dataRef={data?.snapshot_date} />
      <Kpi selo="estimado" rotulo="ASes BR com usuários em IPv6" valor={v ? `${num(v.asns_com_ipv6)} de ${num(v.asns_com_estimativa)}` : null} tom="v6" explicacao="ASNs do Brasil com estimativa de usuários do APNIC e, deles, quantos têm usuários em IPv6." fonte="APNIC Labs" dataRef={data?.snapshot_date} />
    </div>
  )
}

function Distribuicao({ faixas }: { faixas?: Record<string, number> }) {
  if (!faixas) return null
  const rot: Record<string, string> = { ate_10: 'até 10%', de_10_a_90: 'de 10% a 90%', acima_de_90: 'acima de 90%' }
  return (
    <ul className="flex flex-wrap gap-2 text-sm">
      {Object.entries(faixas).map(([k, n]) => <li key={k} className="rounded border border-gray-200 bg-white px-2 py-1"><span className="text-gray-500">{rot[k] ?? k}:</span> <span className="tabular-nums font-medium">{num(n)}</span> ASes</li>)}
    </ul>
  )
}

/** DNSSEC (seção da aba Segurança do Panorama técnico). Não há recorte por UF ou porte da validação de DNSSEC no site. */
export function AbaDnssec() {
  const { data, isLoading } = useBrasilIndicadores()
  if (isLoading) return <div className="h-24 animate-pulse rounded bg-gray-100" />
  const d = data?.dnssec
  if (!d) return <p className="text-sm text-gray-500">Medição de DNSSEC não publicada neste snapshot.</p>
  return (
    <div className="space-y-4" data-testid="aba-dnssec">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Kpi selo="estimado" rotulo="Validação de DNSSEC (média ponderada)" valor={pct(d.media_ponderada_pct)} tom="tecnico" explicacao={EXPLICA.dnssec} fonte={d.fonte?.fonte ?? 'APNIC Labs'} dataRef={d.fonte?.as_of} />
        <Kpi selo="estimado" rotulo="Mediana dos ASes" valor={pct(d.mediana_pct)} tom="tecnico" explicacao="Metade dos ASNs medidos valida em menos que isso, metade em mais. Cada ASN conta igual, seja grande ou pequeno." fonte={d.fonte?.fonte ?? 'APNIC Labs'} dataRef={d.fonte?.as_of} />
        <Kpi selo="fato" rotulo="ASes medidos" valor={num(d.asns)} tom="tecnico" explicacao="ASNs do Brasil com amostra suficiente (pelo menos 100 medições) na janela do APNIC." fonte={d.fonte?.fonte ?? 'APNIC Labs'} dataRef={d.fonte?.as_of} />
      </div>
      <div>
        <h3 className="text-titulo-4 text-gray-800 mb-1">ASes por faixa de validação</h3>
        <Distribuicao faixas={d.faixas} />
      </div>
      <ComoLer>
        <p>O APNIC Labs mede, com anúncios na web, se o resolvedor de DNS usado por cada usuário valida assinaturas DNSSEC. O número é a proporção das medições em que houve validação, por ASN do usuário. A média ponderada dá mais peso aos ASNs com mais medições; a mediana trata cada ASN igual.</p>
        <p>Validar DNSSEC é papel do resolvedor (da operadora ou público, como os de Google e Cloudflare): o número mede o que o usuário recebe, não a assinatura das zonas. Fonte: {d.fonte?.fonte ?? 'APNIC Labs'}{d.fonte?.as_of ? `, dados de ${d.fonte.as_of}` : ''}.</p>
      </ComoLer>
    </div>
  )
}

type LinhaPilar = { nome: string; peso: number; cobertura: number; descricao: string }
type LinhaComponente = { componente: string; pilar: string; descricao: string; asns: number; media: number | null; ponderada: number | null }

/** Prontidão (seção da aba Segurança do Panorama técnico): o índice do país e os componentes; o recorte por UF e porte está em /seguranca-de-roteamento. */
export function AbaProntidao() {
  const { data, isLoading } = useBrasilIndicadores()
  if (isLoading) return <div className="h-24 animate-pulse rounded bg-gray-100" />
  const p = data?.prontidao
  if (!p) return <p className="text-sm text-gray-500">Índice de prontidão não publicado neste snapshot.</p>
  const a = p.agregado
  const linhas: LinhaComponente[] = Object.entries(a.medicoes).map(([c, m]) => ({
    componente: c, pilar: p.pilares[m.pilar]?.nome ?? m.pilar, descricao: p.pilares[m.pilar]?.componentes?.[c]?.descricao ?? '',
    asns: m.asns, media: m.media, ponderada: m.media_ponderada_usuarios,
  }))
  return (
    <div className="space-y-5" data-testid="aba-prontidao">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <Kpi selo="inferido" rotulo="Índice do país (ponderado por usuários)" valor={a.media_ponderada_usuarios != null ? `${a.media_ponderada_usuarios.toLocaleString('pt-BR', { maximumFractionDigits: 1 })} de 100` : null} tom="tecnico" explicacao={EXPLICA.prontidao} fonte="índice do site sobre medições de terceiros" dataRef={data?.snapshot_date} />
        <Kpi selo="inferido" rotulo="Mediana dos ASes" valor={a.mediana != null ? `${a.mediana.toLocaleString('pt-BR', { maximumFractionDigits: 1 })} de 100` : null} tom="tecnico" explicacao="Cada ASN conta igual, seja grande ou pequeno." fonte="índice do site sobre medições de terceiros" dataRef={data?.snapshot_date} />
        {CLASSES.slice(0, 2).map(([k, r]) => <Kpi key={k} selo="inferido" rotulo={`ASes "${r.toLowerCase()}"`} valor={num(a.classes[k])} tom="tecnico" fonte="índice do site sobre medições de terceiros" dataRef={data?.snapshot_date} />)}
      </div>
      <section className="rounded-lg border border-gray-200 bg-white p-4 space-y-3">
        <h3 className="text-titulo-4 text-gray-800">ASes por classe</h3>
        <ul className="flex flex-wrap gap-2 text-sm">
          {CLASSES.map(([k, r]) => <li key={k} className="rounded border border-gray-200 px-2 py-1"><span className="text-gray-500">{r}:</span> <span className="tabular-nums font-medium">{num(a.classes[k] ?? 0)}</span></li>)}
        </ul>
      </section>
      <section className="rounded-lg border border-gray-200 bg-white p-4 space-y-3">
        <h3 className="text-titulo-4 text-gray-800">Pilares</h3>
        <TabelaDados<LinhaPilar> rotulo="Pilares do índice de prontidão" tamanhos={[]}
          dados={Object.entries(p.pilares).map(([k, v]) => ({ nome: v.nome, peso: v.peso, cobertura: a.cobertura_pilares[k] ?? 0, descricao: v.descricao }))}
          colunas={[
            { accessorKey: 'nome', header: 'Pilar' },
            { accessorKey: 'peso', header: 'Peso', meta: { alinhar: 'right', dica: 'Peso do pilar na soma do índice.' } },
            { accessorKey: 'cobertura', header: 'ASes com dado', cell: (c) => num(c.getValue() as number), meta: { alinhar: 'right', dica: 'ASNs do Brasil com alguma medição neste pilar.' } },
            { accessorKey: 'descricao', header: 'O que mede', enableSorting: false },
          ]} />
      </section>
      <section className="rounded-lg border border-gray-200 bg-white p-4 space-y-3">
        <h3 className="text-titulo-4 text-gray-800">Componentes</h3>
        <TabelaDados<LinhaComponente> rotulo="Componentes do índice de prontidão" dados={linhas} tamanhos={[]}
          colunas={[
            { accessorKey: 'componente', header: 'Componente', cell: (c) => <span title={c.row.original.descricao}>{c.getValue() as string}</span> },
            { accessorKey: 'pilar', header: 'Pilar' },
            { accessorKey: 'asns', header: 'ASes medidos', cell: (c) => num(c.getValue() as number), meta: { alinhar: 'right' } },
            { accessorKey: 'media', header: 'Média', cell: (c) => pct(c.getValue() as number | null) ?? '—', meta: { alinhar: 'right', dica: 'Média simples dos ASNs medidos (0 a 100).' } },
            { accessorKey: 'ponderada', header: 'Média ponderada', cell: (c) => pct(c.getValue() as number | null) ?? '—', meta: { alinhar: 'right', dica: 'Média ponderada pelos usuários estimados do APNIC em cada ASN.' } },
            { accessorKey: 'descricao', header: 'O que mede', enableSorting: false },
          ]} />
      </section>
      <ComoLer titulo="Como o índice é calculado">
        <p>{EXPLICA.prontidao}</p>
        <p>Cada pilar soma componentes medidos por terceiros (APNIC, CAIDA, IRR, PeeringDB, RPKI), com os pesos da tabela. ASNs sem dado num pilar não são penalizados nele; a cobertura mostra quantos têm dado. Natureza: {p.natureza ?? 'índice composto'}.</p>
        {p.limites && <p>Limites: {Array.isArray(p.limites) ? p.limites.join(' ') : p.limites}</p>}
      </ComoLer>
    </div>
  )
}
