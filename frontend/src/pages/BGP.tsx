import { useQuery } from '@tanstack/react-query'
import { fetchRoutingAnalysis, fetchBgpStability, fetchBgpStabilityDeep, fetchBgpStabilityHistory, fetchBgpStabilityVisaoGeral, fetchBgpStabilityCarga } from '../services/api'
import { useActiveDate } from '../hooks/useSnapshot'
import { useNearViewport } from '../hooks/useNearViewport'
import { useState } from 'react'
import { SummaryCards }            from '../components/bgp/SummaryCards'
import { PbrCompositionChart }      from '../components/bgp/PbrCompositionChart'
import { PrefixLengthHistogram }    from '../components/bgp/PrefixLengthHistogram'
import { MoreSpecificsSection }     from '../components/bgp/MoreSpecificsSection'
import { AggregationTable }         from '../components/bgp/AggregationTable'
import { RegistroBrCoverageTable }  from '../components/bgp/RegistroBrCoverageTable'
import { AvisoMoasNaoMedido, moasMedido } from '../features/prefixo/blocks/MoasBloco'
import { MoasTable }                from '../components/bgp/MoasTable'
import { TooSpecificTable }         from '../components/bgp/TooSpecificTable'
import { AsPathSection }            from '../components/bgp/AsPathSection'
import { StabilitySection }         from '../components/bgp/StabilitySection'
import { AccessError } from '../services/api'
import { EstadoDados } from '../components/ui/EstadoDados'
import { AccessPanel } from '../components/AccessPanel'
import { useSearchParams } from 'react-router-dom'
import { ComoLer } from '../components/ui/ComoLer'
import { BarraDeAbas } from '../features/entidade/EntityPage'
import { SeriesDaFamilia } from '../features/series/SeriesDaFamilia'

function Section({ title, desc, children }: {
  title: string
  desc: string
  children: React.ReactNode
}) {
  // a explicação longa vai para o "Como ler", fechado por padrão.
  return (
    <section className="space-y-2">
      <h2 className="text-titulo-3 text-gray-800">{title}</h2>
      <ComoLer className="max-w-3xl"><p>{desc}</p></ComoLer>
      {children}
    </section>
  )
}

/** A página em abas, como o Panorama técnico (estado em `?aba=`). */
const ABAS_BGP = [
  { id: 'visao-geral', rotulo: 'Visão geral', descricao: 'Números centrais, composição dos prefixos brasileiros e distribuição por tamanho' },
  { id: 'prefixos', rotulo: 'Prefixos', descricao: 'Mais específicos e prefixos potencialmente filtráveis' },
  { id: 'agregacao', rotulo: 'Agregação e cobertura', descricao: 'Potencial de agregação por ASN e cobertura dos blocos do Registro.br' },
  { id: 'moas', rotulo: 'MOAS', descricao: 'Prefixos brasileiros com mais de um ASN de origem observado' },
  { id: 'caminhos', rotulo: 'Caminhos', descricao: 'AS_PATH, prepending e communities' },
  { id: 'estabilidade', rotulo: 'Estabilidade', descricao: 'ASes com volume desproporcional de updates BGP' },
]

export function BGP() {
  const date = useActiveDate()
  const [params, setParams] = useSearchParams()
  const aba = ABAS_BGP.find((a) => a.id === params.get('aba'))?.id ?? ABAS_BGP[0].id
  const abrir = (id: string) => setParams((ant) => { const n = new URLSearchParams(ant); if (id === ABAS_BGP[0].id) n.delete('aba'); else n.set('aba', id); return n })

  const { data, isLoading, isError, error } = useQuery({
    queryKey:  ['routing-analysis', date],
    queryFn:   () => fetchRoutingAnalysis(date ?? undefined),
    staleTime: 5 * 60 * 1000,
    gcTime:    Infinity,
    enabled:   !!date,
  })

  // A estabilidade é buscada só quando a seção está perto de aparecer na tela, e em versão enxuta: a visão
  // geral (período, distribuição, categorias, top 10) tem dezenas de KB. O documento completo (~46 MB) só vem se o visitante
  // pedir "Ver todos". A página inteira já foi desenhada antes disso.
  const [secaoEstabilidade, pertoDaEstabilidade] = useNearViewport()
  const [pediuTodos, setPediuTodos] = useState(false)

  const { data: visaoGeral, isLoading: carregandoEstabilidade } = useQuery({
    queryKey:  ['bgp-stability-overview', date],
    queryFn:   () => fetchBgpStabilityVisaoGeral(date ?? undefined),
    staleTime: 5 * 60 * 1000,
    gcTime:    Infinity,
    enabled:   !!date && !!data && pertoDaEstabilidade,
    retry:     false,
  })

  const { data: estabilidadeCompleta, isLoading: carregandoTodos } = useQuery({
    queryKey:  ['bgp-stability', date],
    queryFn:   () => fetchBgpStability(date ?? undefined),
    staleTime: 5 * 60 * 1000,
    gcTime:    Infinity,
    enabled:   !!date && pediuTodos,
    retry:     false,
  })
  // `stability` é o que a seção desenha: o documento completo, se já veio; senão a visão geral no formato do documento
  const stability = estabilidadeCompleta ?? visaoGeral

  const { data: stabilityDeep } = useQuery({
    queryKey:  ['bgp-stability-deep', date],
    queryFn:   () => fetchBgpStabilityDeep(date ?? undefined),
    staleTime: 5 * 60 * 1000,
    gcTime:    Infinity,
    enabled:   !!visaoGeral,
    retry:     false,
  })

  const { data: stabilityHistory } = useQuery({
    queryKey:  ['bgp-stability-history', date],
    queryFn:   () => fetchBgpStabilityHistory(date ?? undefined, 6, true),
    staleTime: 5 * 60 * 1000,
    gcTime:    Infinity,
    enabled:   !!visaoGeral,
    retry:     false,
  })

  // ASes com mais updates nas mesmas 6 semanas do gráfico de atividade: alguns KB, montado pela API a partir das séries semanais
  const { data: stabilityCarga } = useQuery({
    queryKey:  ['bgp-stability-carga', date],
    queryFn:   () => fetchBgpStabilityCarga(date ?? undefined, 6, 10),
    staleTime: 5 * 60 * 1000,
    gcTime:    Infinity,
    enabled:   !!visaoGeral,
    retry:     false,
  })

  if (isLoading || !date) {
    return (
      <div className="flex justify-center items-center py-24 text-sm text-gray-400">
        <svg className="animate-spin h-5 w-5 mr-2 text-gray-300" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.4 0 0 5.4 0 12h4z" />
        </svg>
        Carregando análise BGP…
      </div>
    )
  }

  if (isError && error instanceof AccessError) {
    if (error.kind === 'taxa') return <EstadoDados variante="pagina" erro={error} oQue="a análise BGP" />
    return <AccessPanel reason={error.kind === 'limit' ? 'esgotado' : 'geral'} />
  }

  if (isError) {
    const msg = error instanceof Error ? error.message : String(error)
    const notReady = msg.includes('404')
    return (
      <div className="py-12 text-center">
        <p className="text-gray-500 text-sm">
          {notReady
            ? 'Análise BGP ainda não gerada para este snapshot. Execute: python -m analysis.routing_analysis'
            : `Erro ao carregar: ${msg}`}
        </p>
      </div>
    )
  }

  if (!data) return null

  return (
    <div className="space-y-8">
      {/* Cabeçalho */}
      <div>
        <h1 className="text-titulo-1 text-gray-900">Tabela BGP Global: Brasil</h1>
        <p className="text-sm text-gray-500 mt-1">
          Análise dos prefixos e ASNs brasileiros na tabela de roteamento global.
          Snapshot: <span className="font-mono">{data.snapshot_date}</span>.
          {data.has_path_data && (
            <span className="ml-2 text-ok-600 text-xs">✓ Dados de AS_PATH disponíveis</span>
          )}
        </p>
      </div>

      <BarraDeAbas abas={ABAS_BGP} ativa={aba} aoEscolher={abrir} rotulo="Seções da Tabela BGP" />
      <div role="tabpanel" id={`painel-${aba}`} aria-labelledby={`aba-${aba}`} className="space-y-8">
      {aba === 'visao-geral' && <>
      {/* Cards de sumário */}
      <SummaryCards data={data} />

      {/* Composição */}
      <Section
        title="Composição dos prefixos brasileiros"
        desc="Classifica cada rota brasileira em três categorias mutuamente exclusivas: Completa (ASN e prefixo ambos alocados ao Brasil pelo Registro.br), Apenas origem BR (ASN brasileiro anuncia prefixo não alocado ao Brasil) e Apenas prefixo BR (prefixo alocado ao Brasil anunciado por ASN estrangeiro). Um perfil saudável concentra a maioria das rotas na categoria 'Completa'. As demais categorias não indicam problemas necessariamente; podem refletir acordos legítimos ou recursos adquiridos fora do Brasil."
      >
        <div className="grid md:grid-cols-3 gap-4">
          <PbrCompositionChart data={data} />
          {/* IPv6 primeiro */}
          <PrefixLengthHistogram data={data.prefix_length_dist.v6} afi="v6" />
          <PrefixLengthHistogram data={data.prefix_length_dist.v4} afi="v4" />
        </div>
      </Section>

      {/* Série semanal do estado RPKI das rotas brasileiras, com a regra de comparabilidade (PT-28) */}
      <SeriesDaFamilia familia="roteamento" titulo="Estado RPKI das rotas brasileiras, por snapshot" />

      </>}
      {aba === 'prefixos' && <>
      {/* Mais específicos */}
      <Section
        title="Mais específicos (More Specifics)"
        desc="Um prefixo mais específico é um sub-bloco de um prefixo já anunciado. Exemplo: se 200.0.0.0/16 está na tabela e também 200.0.1.0/24, o /24 é um more specific. Usos legítimos incluem engenharia de tráfego (Traffic Engineering), multihoming e anycast. Alta proporção de more specifics em relação a prefixos raiz pode indicar fragmentação desnecessária da tabela global. Estar nesta lista não implica problema; é um indicador que merece análise caso a caso."
      >
        <MoreSpecificsSection data={data} date={date ?? undefined} />
      </Section>

      </>}
      {aba === 'agregacao' && <>
      {/* Potencial de agregação */}
      <Section
        title="Potencial de agregação por ASN"
        desc="Indica quantas rotas cada ASN poderia eliminar da tabela global se consolidasse seus blocos contíguos em prefixos agregados. Calculado com o algoritmo padrão ipaddress.collapse_addresses (RFC 4632). Um ASN com alto potencial de agregação anuncia blocos que poderiam ser sintetizados em menos prefixos, contribuindo desnecessariamente para o crescimento da tabela. Estar nesta lista não é necessariamente ruim; pode haver motivos operacionais legítimos para a fragmentação, como engenharia de tráfego ou multihoming."
      >
        <AggregationTable data={data.aggregation_by_asn} date={date ?? undefined} />
      </Section>

      {/* Cobertura Registro.br */}
      <Section
        title="Cobertura dos blocos alocados pelo Registro.br"
        desc="Para cada bloco IP alocado pelo Registro.br a um ASN brasileiro, verifica se há rotas na tabela global que cobrem aquele espaço. 'Não anunciado' pode indicar recurso não utilizado, anunciado apenas internamente ou visível somente por coletores não utilizados nesta análise. 'Parcial' indica que apenas parte do bloco está roteada. 'Completo com agregado' é a configuração mais eficiente. 'Coberto por várias origens, sem agregado' quer dizer que o bloco está todo coberto por rotas mais específicas de origens diferentes e nenhuma rota cobre o bloco inteiro; descreve a forma do anúncio, não a causa."
      >
        <RegistroBrCoverageTable data={data.registro_br_coverage} date={date ?? undefined} />
      </Section>

      </>}
      {aba === 'moas' && <>
      {/* MOAS */}
      <Section
        title="MOAS: prefixos com mais de um ASN de origem"
        desc={moasMedido(data)
          ? `${data.moas_resumo!.definicao} ${data.moas_resumo!.como_ler} Limites: ${data.moas_resumo!.limites}`
          : 'Multiple Origin AS: o mesmo prefixo anunciado por mais de um ASN de origem.'}
      >
        {moasMedido(data)
          ? <MoasTable data={data.moas!} resumo={data.moas_resumo!} date={date ?? undefined} />
          : <AvisoMoasNaoMedido texto={data.moas_indisponivel} />}
      </Section>

      </>}
      {aba === 'prefixos' && <>
      {/* Prefixos filtráveis */}
      <Section
        title="Prefixos potencialmente filtráveis"
        desc="Prefixos IPv6 mais específicos que /48 e IPv4 mais específicos que /24 são frequentemente filtrados por operadores de backbone, pois excedem os limites de granularidade aceitos na Internet pública. Se um prefixo filtrável tem um agregado menos específico na tabela (coluna 'Tem agregado?'), o tráfego continuaria sendo absorvido pelo agregado mesmo se o mais-específico fosse descartado. Se não há agregado, filtrar o prefixo causaria blackhole do tráfego destinado àquele bloco."
      >
        <TooSpecificTable
          v4={data.too_specific.v4}
          v6={data.too_specific.v6}
          date={date ?? undefined}
        />
      </Section>

      </>}
      {aba === 'caminhos' && <>
      {/* AS_PATH */}
      <Section
        title="AS_PATH, prepending e communities BGP"
        desc="Estatísticas derivadas dos caminhos de roteamento completos das rotas brasileiras. Requer coleta de full table com AS_PATH e communities (fase 2 do pipeline). O prepending (repetição de ASN no caminho) é uma técnica usada para influenciar a seleção do caminho de entrada de tráfego. Communities são atributos BGP opcionais que sinalizam políticas de roteamento entre operadores. A seção de higiene detecta anomalias como loops de AS, Private ASes visíveis externamente e outros indicadores de má configuração."
      >
        {data.has_path_data && data.as_path_stats ? (
          <AsPathSection stats={data.as_path_stats} date={date ?? undefined} />
        ) : (
          <div className="bg-primario-50 border border-primario-200 rounded-lg px-4 py-3 text-sm text-primario-700">
            Análises de AS_PATH disponíveis a partir do próximo snapshot. Os dados de caminho são
            capturados automaticamente pelo pipeline após a próxima coleta semanal.
          </div>
        )}
      </Section>

      </>}
      {aba === 'estabilidade' && <>
      {/* Estabilidade BGP */}
      <Section
        title="Estabilidade de anúncios BGP"
        desc="Mostra o volume de updates BGP de cada AS brasileiro em relação ao número de prefixos que ele anuncia (updates por prefixo por dia). Causas possíveis não são observáveis neste dado: ele conta updates, não diz por que ocorreram. A análise cobre os 7 dias anteriores ao snapshot com granularidade diária."
      >
        <div ref={secaoEstabilidade}>
        {stability ? (
          <StabilitySection
            data={stability} deepData={stabilityDeep} history={stabilityHistory?.weeks} carga={stabilityCarga}
            categorias={visaoGeral?.categorias} totalMedioOuMaior={visaoGeral?.medio_ou_maior}
            onPedirTodos={() => setPediuTodos(true)} carregandoTodos={carregandoTodos}
          />
        ) : !pertoDaEstabilidade || carregandoEstabilidade ? (
          <div className="bg-gray-50 border border-gray-200 rounded-lg px-4 py-10 text-sm text-gray-400 text-center animate-pulse" role="status">
            {carregandoEstabilidade ? 'Carregando a análise de estabilidade (documento grande)…' : 'A análise de estabilidade carrega quando esta seção se aproxima da tela.'}
          </div>
        ) : (
          <div className="bg-gray-50 border border-gray-200 rounded-lg px-4 py-3 text-sm text-gray-500">
            Análise de estabilidade BGP não disponível para este snapshot.
            Execute: <code className="font-mono text-xs">python -m collector.bgp_updates_routeviews</code> e{' '}
            <code className="font-mono text-xs">python -m analysis.bgp_stability</code>
          </div>
        )}
        </div>
      </Section>

      </>}
      </div>

      {/* Metodologia */}
      <div className="text-xs text-gray-400 border-t border-gray-200 pt-4">
        <p>
          <strong>Metodologia:</strong> Rota brasileira = prefixo contido em bloco alocado pelo Registro.br (strict_br e prefix_only_br);
          a origem do anúncio não define. Rotas de ASN da lista do Registro.br em espaço de outro RIR ficam fora do total, contadas à parte
          (asn_br_fora_de_bloco; snapshots gerados antes desta regra as somavam como origin_only_br). Mais específicos detectados via trie
          de prefixos. Potencial de agregação calculado com{' '}
          <code className="font-mono">ipaddress.collapse_addresses</code> por ASN.
          Dados representam um ponto de observação: múltiplos coletores RouteViews e RIPE RIS.
        </p>
      </div>
    </div>
  )
}
