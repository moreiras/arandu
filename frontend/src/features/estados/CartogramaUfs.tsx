// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useState } from 'react'
import { Link } from '../../components/layout/LinkDatado'
import type { ResumoUf } from '../../types/api'
import { corDaEscala, ESCALA_SEQUENCIAL, ESCALA_UM_TOM, LEGENDA_SEQUENCIAL, LEGENDA_UM_TOM } from '../../lib/escalasMapa'
import { nomeUf } from '../../lib/ufs'
import { VerDados } from '../../components/ui/VerDados'

/** Posição (coluna, linha) de cada UF numa grade que lembra o mapa do Brasil — todas do mesmo tamanho, para a área não distorcer a comparação. */
export const POSICAO_UF: Record<string, [number, number]> = {
  RR: [2, 0], AP: [4, 0],
  AM: [1, 1], PA: [3, 1], MA: [4, 1], CE: [5, 1], RN: [6, 1],
  AC: [0, 2], RO: [1, 2], TO: [3, 2], PI: [4, 2], PE: [5, 2], PB: [6, 2],
  MT: [2, 3], GO: [3, 3], BA: [4, 3], AL: [5, 3], SE: [6, 3],
  MS: [2, 4], DF: [3, 4], MG: [4, 4], ES: [5, 4],
  PR: [2, 5], SP: [3, 5], RJ: [4, 5],
  SC: [2, 6], RS: [2, 7],
}

export interface MetricaUf {
  id: string
  rotulo: string
  valor: (u: ResumoUf) => number | null
  texto: (v: number) => string
  /** Frase curta sob o mapa: o que o número é e de onde vem. */
  nota?: string
  /** true = normalizada (razão ou percentual, comparável entre UFs de tamanhos diferentes); false = valor absoluto. */
  normalizada?: boolean
  /** Grupo do botão quando o cartograma agrupa (`agrupar`). */
  grupo?: GrupoMetrica
  /** Base do valor (n), mostrada sempre ao lado dele: na célula, no título e na tabela. */
  n?: (u: ResumoUf) => number | null
  /** Escala de um só tom (a cor só ordena, sem sugerir alerta nem melhora). */
  umTom?: boolean
  /** Indicador que não é veredito nem ranking: o aviso de leitura fica sempre visível junto dele. */
  aviso?: boolean
}

export type GrupoMetrica = 'Mercado' | 'Infraestrutura e rede'

/** Aviso que acompanha, sempre visível, a prontidão e o HHI do trânsito: não é veredito nem ranking. */
export const AVISO_REDE_UFS = 'A prontidão em segurança de roteamento e o HHI do trânsito não são veredito sobre a segurança nem sobre o mercado de um estado e não devem ser lidos como ranking. São estimativas e inferências a partir de rotas observadas e de acessos declarados, e a UF é a da sede das redes. Cada valor vem com o n em que se apoia; com n pequeno, a mediana e o HHI variam muito com poucas redes.'

const n0 = (v: number) => v.toLocaleString('pt-BR', { maximumFractionDigits: 0 })
const n1 = (v: number) => v.toLocaleString('pt-BR', { maximumFractionDigits: 1 })
const pctN0 = (v: number) => `${n0(v)}%`
const compacto = (v: number) => (v >= 1e6 ? `${(v / 1e6).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} mi` : v >= 1e3 ? `${n0(v / 1e3)} mil` : n0(v))

export const METRICAS: MetricaUf[] = [
  { id: 'acessos', rotulo: 'Acessos fixos', valor: (u) => u.acessos, texto: compacto, grupo: 'Mercado' },
  { id: 'fibra', rotulo: '% de fibra', valor: (u) => u.fibra_pct, texto: (v) => `${v.toLocaleString('pt-BR', { maximumFractionDigits: 0 })}%`, normalizada: true, grupo: 'Mercado',
    nota: '% dos acessos fixos em fibra (SICI/Anatel).' },
  { id: 'usuarios', rotulo: 'Usuários (sede da rede)', valor: (u) => u.usuarios, texto: compacto, grupo: 'Infraestrutura e rede',
    nota: 'Usuários estimados (APNIC) em ASNs com sede na UF: a UF é a da sede do ASN, não a de quem usa. Não é a população conectada nem o uso de Internet na UF; para isso, a página Uso da Internet (TIC Domicílios).' },
  { id: 'ptts', rotulo: 'PTTs', valor: (u) => u.ptts, texto: n0, grupo: 'Infraestrutura e rede' },
  { id: 'penetracao', rotulo: 'Acessos por 100 domicílios', valor: (u) => (u.penetracao == null ? null : u.penetracao * 100), texto: n0, normalizada: true, grupo: 'Mercado',
    nota: 'Acessos fixos declarados à Anatel ÷ domicílios projetados do IBGE, por 100. Estimativa: um domicílio pode ter vários acessos ou nenhum, e o Censo é de 2022.' },
  { id: 'longe', rotulo: '% de municípios longe de PTT', valor: (u) => (u.municipios && u.municipios_sem_ptt != null ? (100 * u.municipios_sem_ptt) / u.municipios : null), texto: (v) => `${n0(v)}%`, normalizada: true, grupo: 'Infraestrutura e rede',
    nota: 'Municípios a mais de 100 km em linha reta de um PTT do IX.br, entre os que declaram acessos ao SICI.' },
  { id: 'transito_unico', rotulo: '% de acessos com um só provedor de trânsito (inferido)', valor: (u) => u.rede?.transito_unico_pct ?? null, texto: pctN0, normalizada: true, grupo: 'Infraestrutura e rede', umTom: true,
    nota: 'Inferência: % dos acessos fixos de operadoras cujos ASNs têm um só provedor de trânsito inferido pelas rotas observadas. Um só provedor pode ser falta de observação; não é contrato nem tráfego. A UF é a da sede.' },
  { id: 'ipv6', rotulo: '% de acessos em IPv6 (estimado)', valor: (u) => u.rede?.ipv6_pct ?? null, texto: pctN0, normalizada: true, grupo: 'Infraestrutura e rede', umTom: true,
    nota: 'Estimativa: acessos fixos × adoção de IPv6 do AS da operadora (APNIC), supondo a mesma adoção em todos os municípios da operadora. Não mede tráfego.' },
  { id: 'rov', rotulo: '% de usuários atrás de ROV (estimado)', valor: (u) => u.rede?.rov_pct ?? null, texto: pctN0, normalizada: true, grupo: 'Infraestrutura e rede', umTom: true,
    nota: 'Estimativa: % dos usuários estimados (APNIC) em ASNs que validam ROV (APNIC IRoV), entre os ASNs medidos. A UF é a da sede do ASN.' },
  { id: 'prontidao', rotulo: 'Prontidão em segurança de roteamento (mediana)', valor: (u) => u.rede?.prontidao_mediana ?? null, texto: n1, grupo: 'Infraestrutura e rede', umTom: true, aviso: true,
    n: (u) => u.rede?.prontidao_n ?? null,
    nota: 'Mediana do índice de prontidão (0 a 100) dos ASNs com sede na UF que têm índice; n é o número desses ASNs. O índice soma medições de terceiros com regras públicas.' },
  { id: 'hhi_transito', rotulo: 'HHI do trânsito', valor: (u) => u.rede?.hhi_transito ?? null, texto: n0, grupo: 'Infraestrutura e rede', umTom: true, aviso: true,
    n: (u) => u.rede?.hhi_transito_n ?? null,
    nota: 'Inferência: concentração (0 a 10.000) dos provedores de trânsito inferidos dos ASNs com sede na UF; n é o número de ASNs com ao menos um provedor inferido. Mede a concentração entre provedores de trânsito, não a de um mercado de receita.' },
  { id: 'nao_visto', rotulo: 'Mercado não visto por 100 domicílios (estimado)', valor: (u) => u.territorio?.nao_visto_por_100_dom ?? null, texto: n0, normalizada: true, grupo: 'Mercado', umTom: true,
    nota: 'Estimativa: domicílios com Internet (taxa da PNAD) sem acesso fixo de pessoa física declarado ao SICI, por 100 domicílios projetados. Inclui quem usa só o celular ou outro meio.' },
]

/** Os botões da página `/estados`; cada grupo mostra os seus, na ordem desta lista. */
export const METRICAS_ESTADOS = ['acessos', 'fibra', 'penetracao', 'nao_visto', 'usuarios', 'ptts', 'longe', 'transito_unico', 'ipv6', 'rov', 'prontidao', 'hhi_transito']

/** Métricas normalizadas, para comparar UFs de tamanhos muito diferentes (usadas na home). */
export const METRICAS_NORMALIZADAS = ['penetracao', 'fibra', 'longe']   // a ordem é a dos botões; a primeira abre selecionada

const luminancia = (hex: string) => {
  const [r, g, b] = [0, 1, 2].map((k) => parseInt(hex.slice(1 + 2 * k, 3 + 2 * k), 16) / 255).map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4))
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}
/** Razão de contraste (WCAG) do fundo com o texto branco e com o texto preto das células (o cinza 900 não bastava nos tons médios): o texto é o de maior contraste, nunca um limiar fixo de posição na escala. */
export const contrasteComBranco = (fundo: string) => 1.05 / (luminancia(fundo) + 0.05)
export const contrasteComEscuro = (fundo: string) => (luminancia(fundo) + 0.05) / (luminancia('#000000') + 0.05)

/** Cor da célula na escala Viridis: roxo = menor, amarelo = maior valor da métrica (linear entre 0 e o máximo); `escuro` diz se o texto da célula deve ser branco. */
export function corDaCelula(valor: number | null, maximo: number, escala: readonly string[] = ESCALA_SEQUENCIAL): { fundo: string; escuro: boolean } {
  if (valor == null || maximo <= 0) return { fundo: 'rgb(243 244 246)', escuro: false }
  const t = Math.min(1, Math.max(0, valor / maximo))
  // Viridis (segura para daltonismo, legível em cinza); o texto escuro só vale nas faixas verde-amarelas.
  const fundo = corDaEscala(escala, t)
  return { fundo, escuro: contrasteComBranco(fundo) >= contrasteComEscuro(fundo) }
}

/**
 * A grade das 27 UFs (reutilizável: cartograma da home e de `/estados`, pequenos múltiplos): uma célula por UF no lugar aproximado do mapa, todas do mesmo tamanho.
 * As células são decorativas (`aria-hidden`); a lista de UFs da página é o caminho por teclado e leitor de tela.
 */
export function GradeUfs({ valores, maximo, texto, rotulo, pequeno = false, minimo = 0, destaque, escala, nDe }: { valores: (uf: string) => number | null; maximo: number; texto: (v: number) => string; rotulo: string; pequeno?: boolean; minimo?: number; destaque?: string; escala?: readonly string[]; nDe?: (uf: string) => number | null }) {
  return (
    <div className={`grid gap-1 mx-auto ${pequeno ? 'max-w-[17rem]' : 'max-w-md'}`} style={{ gridTemplateColumns: 'repeat(7, minmax(0, 1fr))' }} data-testid="cartograma">
      {Object.entries(POSICAO_UF).map(([uf, [col, lin]]) => {
        const v = valores(uf)
        const { fundo, escuro } = corDaCelula(v == null ? null : v - minimo, maximo - minimo, escala)
        const n = v == null ? null : nDe?.(uf) ?? null
        return (
          <Link key={uf} to={`/uf/${uf}`} aria-hidden tabIndex={-1} title={`${uf}: ${v == null ? 'sem dado' : `${texto(v)}${n != null ? `; n=${n0(n)}` : ''}`} (${rotulo.toLowerCase()})`}
            aria-current={uf === destaque ? 'true' : undefined}
            className={`aspect-square rounded flex flex-col items-center justify-center leading-tight hover:ring-2 hover:ring-primario-400 ${uf === destaque ? 'ring-2 ring-offset-1 ring-gray-900' : ''} ${escuro ? 'text-white' : 'text-black'}`}
            style={{ gridColumn: col + 1, gridRow: lin + 1, background: fundo }}>
            <span className="text-xs font-semibold">{uf}</span>
            <span className="text-xs tabular-nums">{v == null ? '—' : texto(v)}</span>
            {n != null && <span className="text-xs tabular-nums">n={n0(n)}</span>}
          </Link>
        )
      })}
    </div>
  )
}

/**
 * Cartograma das 27 UFs: uma célula por UF no lugar aproximado do mapa, colorida pela métrica escolhida.
 * Mostra de relance onde estão os acessos, a fibra, os usuários e os PTTs. As células são decorativas: a alternativa em texto é a
 * tabela "Ver dados" com todas as métricas das 27 UFs (NBR 17225 5.2.4), alcançável por teclado.
 */
export function CartogramaUfs({ ufs, metricas, titulo = 'Brasil por UF', inicial, compacto: pequeno = false, destaque, agrupar = false }: { ufs: ResumoUf[]; metricas?: string[]; titulo?: string; inicial?: string; compacto?: boolean; destaque?: string; agrupar?: boolean }) {
  const lista = metricas ? metricas.flatMap((id) => METRICAS.filter((m) => m.id === id)) : METRICAS.filter((m) => ['acessos', 'fibra', 'usuarios', 'ptts'].includes(m.id))
  const [metricaId, setMetricaId] = useState(inicial ?? lista[0].id)
  const metrica = lista.find((m) => m.id === metricaId) ?? lista[0]
  const porUf = new Map(ufs.map((u) => [u.uf, u]))
  const valores = ufs.map((u) => metrica.valor(u)).filter((v): v is number => v != null)
  const maximo = valores.length ? Math.max(...valores) : 0
  const escala = metrica.umTom ? ESCALA_UM_TOM : ESCALA_SEQUENCIAL
  const botao = (m: MetricaUf) => (
    <button key={m.id} type="button" aria-pressed={m.id === metricaId} onClick={() => setMetricaId(m.id)}
      className={`px-2.5 py-1 ${m.id === metricaId ? 'bg-primario-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'}`}>
      {m.rotulo}
    </button>
  )
  const grupos = agrupar ? (['Mercado', 'Infraestrutura e rede'] as GrupoMetrica[]).map((g) => ({ g, itens: lista.filter((m) => m.grupo === g) })).filter((x) => x.itens.length > 0) : []
  const comAviso = lista.some((m) => m.aviso)
  return (
    <section aria-label="Cartograma das UFs" className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
        <h2 className="text-sm font-semibold text-gray-700">{titulo}</h2>
        {grupos.length > 0 ? (
          <div className="flex flex-col gap-1.5 text-xs">
            {grupos.map(({ g, itens }) => (
              <div key={g} role="group" aria-label={g} className="flex flex-wrap items-center gap-2">
                <span className="text-gray-500 w-44 shrink-0">{g}</span>
                <div className="inline-flex flex-wrap rounded-md border border-gray-200 overflow-hidden">{itens.map(botao)}</div>
              </div>
            ))}
          </div>
        ) : (
          <div role="group" aria-label="Métrica do cartograma" className="inline-flex flex-wrap rounded-md border border-gray-200 overflow-hidden text-xs">
            {lista.map(botao)}
          </div>
        )}
      </div>
      <GradeUfs valores={(uf) => { const u = porUf.get(uf); return u ? metrica.valor(u) : null }} maximo={maximo} texto={metrica.texto} rotulo={metrica.rotulo} pequeno={pequeno} destaque={destaque}
        escala={escala} nDe={metrica.n ? (uf) => { const u = porUf.get(uf); return u ? metrica.n!(u) : null } : undefined} />
      <div className={`mt-3 mx-auto ${pequeno ? 'max-w-[17rem]' : 'max-w-md'} flex items-center gap-2 text-xs text-gray-500`} aria-hidden="true">
        <span>menor</span>
        <span className="h-2 flex-1 rounded" style={{ background: `linear-gradient(to right, ${escala.join(', ')})` }} />
        <span>maior</span>
      </div>
      {metrica.nota && <p className="mt-2 text-xs text-gray-600">{metrica.nota}{pequeno ? ` Cada quadrado é uma UF no lugar aproximado do mapa. ${metrica.umTom ? LEGENDA_UM_TOM : LEGENDA_SEQUENCIAL}` : ''}</p>}
      {comAviso && <p className="mt-2 text-xs text-gray-700 border-l-2 border-gray-300 pl-2" data-testid="aviso-rede-ufs">{AVISO_REDE_UFS}</p>}
      {!pequeno && <p className="mt-3 text-xs text-gray-500">
        Cada quadrado é uma UF no lugar aproximado do mapa (mesmo tamanho para todas). {metrica.umTom ? LEGENDA_UM_TOM : LEGENDA_SEQUENCIAL} Acessos e fibra: SICI/Anatel,
        banda larga fixa; usuários: estimativa APNIC dos ASNs com sede na UF (não é censo nem a população conectada); PTTs: IX.br com coleta.
      </p>}
      <VerDados dados={linhasTabela(ufs)} rotulos={ROTULOS_TABELA} campos={Object.keys(ROTULOS_TABELA)} titulo="Ver dados (tabela das UFs)" />
    </section>
  )
}

// Cabeçalhos com a unidade; diferentes dos botões de métrica, para o nome acessível de cada controle ser único.
const ROTULOS_TABELA: Record<string, string> = {
  uf: 'UF', nome: 'Nome', acessos: 'Acessos fixos (SICI)', fibra: 'Fibra (% dos acessos)', usuarios: 'Usuários estimados em ASNs sediados na UF (APNIC)', ptts: 'PTTs (IX.br)',
  penetracao: 'Acessos / 100 domicílios', longe: 'Municípios longe de PTT (%)', municipios: 'Municípios com acessos', asns: 'ASNs',
  transito_unico: 'Acessos com um só provedor de trânsito (% inferido)', ipv6: 'Acessos em IPv6 (% estimado)', rov: 'Usuários atrás de ROV (% estimado)',
  prontidao: 'Prontidão (mediana do índice dos ASNs)', prontidao_n: 'n da prontidão (ASNs com índice)', hhi_transito: 'HHI do trânsito (0 a 10.000)', hhi_transito_n: 'n do HHI (ASNs com provedor inferido)',
  nao_visto: 'Mercado não visto / 100 domicílios (estimado)',
}

/** Linhas da tabela alternativa: os mesmos números do cartograma, todas as métricas de uma vez, na ordem alfabética das UFs. */
function linhasTabela(ufs: ResumoUf[]): Record<string, string | number | null>[] {
  return [...ufs].sort((a, b) => a.uf.localeCompare(b.uf)).map((u) => ({
    uf: u.uf, nome: nomeUf(u.uf), ...Object.fromEntries(METRICAS.map((m) => [m.id, m.valor(u)])),
    prontidao_n: u.rede?.prontidao_n ?? null, hhi_transito_n: u.rede?.hhi_transito_n ?? null, municipios: u.municipios, asns: u.asns,
  }))
}

/** Posição de uma UF entre as que têm valor na métrica: 1 = maior valor. `null` se a UF não tem valor. */
export function posicaoNaMetrica(ufs: ResumoUf[], uf: string, valor: (u: ResumoUf) => number | null): { posicao: number; de: number } | null {
  const com = ufs.map((u) => ({ uf: u.uf, v: valor(u) })).filter((x): x is { uf: string; v: number } => x.v != null)
  const meu = com.find((x) => x.uf === uf)
  if (!meu) return null
  return { posicao: 1 + com.filter((x) => x.v > meu.v).length, de: com.length }
}
