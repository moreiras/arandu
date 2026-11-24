// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useState } from 'react'
import { Link } from '../../../components/layout/LinkDatado'
import type { BlocoProps } from '../../entidade/registry'
import type { RegiaoVinculo } from '../../../types/api'
import type { MunicipioCtx } from '../contexto'
import { fmt } from '../ui'
import { BarraClasses } from '../../prontidao/blocos'
import { ThOrdenavel } from '../../../components/ui/ThOrdenavel'
import { useOrdenacao } from '../../../lib/ordenacao'

const pct = (v: number | null | undefined) => (v == null ? '—' : `${v.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`)
const ROTULO: Record<RegiaoVinculo, { texto: string; dica: string; cor: string }> = {
  sici: { texto: 'SICI', dica: 'a operadora declara acessos no município (Anatel)', cor: 'bg-primario-50 text-primario-700 border-primario-100' },
  sede: { texto: 'sede', dica: 'o CNPJ do ASN tem a sede no município', cor: 'bg-aviso-50 text-aviso-700 border-aviso-100' },
  geo: { texto: 'IPs', dica: 'prefixos do ASN geolocalizados no município (DB-IP, precisão de cidade)', cor: 'bg-estimado-50 text-estimado-700 border-estimado-100' },
}

/** Nome dos PTTs (vem na própria resposta de `/regiao`); sem nome, o código. */
const nomeDosPtts = (nomes: Record<string, string>) => (c: string) => nomes[c] ?? c.toUpperCase()

function ListaPtts({ codigos, nome }: { codigos: string[]; nome: (c: string) => string }) {
  if (codigos.length === 0) return <span className="text-gray-300">—</span>
  return <>{codigos.slice(0, 4).map((c, i) => <span key={c}>{i > 0 && ', '}<Link to={`/ixp/${c}`} className="text-primario-600 hover:underline">{nome(c)}</Link></span>)}{codigos.length > 4 && <span className="text-gray-400"> +{codigos.length - 4}</span>}</>
}

function Limites({ texto }: { texto?: string }) {
  return <p className="mt-2 text-xs text-gray-500">{texto}</p>
}

/** Os provedores (ASNs) da região: quem declara acessos no SICI, quem tem sede e quem tem IPs geolocalizados ali, mesmo sem assinantes informados. */
export function ProvedoresRegiaoBloco({ dados }: BlocoProps<MunicipioCtx>) {
  const r = dados.regiao!
  const nomePtt = nomeDosPtts(r.ptts_nomes)
  const [todos, setTodos] = useState(false)
  // A API corta a lista em 300: só se ordena no navegador quando ela veio inteira (reordenar um recorte esconderia quem lidera a coluna).
  const inteira = r.provedores_total <= r.provedores.length
  const { ordenados, props: propsLocal } = useOrdenacao(r.provedores, {
    asn: { valor: (p) => p.asn, primeiro: 'asc' },
    vinculo: (p) => p.vinculos.map((k) => ROTULO[k].texto).join(' '),
    acessos: (p) => (p.acessos_fixo + p.acessos_movel > 0 ? p.acessos_fixo + p.acessos_movel : null),
    prefixos: (p) => (p.prefixos_geo > 0 ? p.prefixos_geo : null),
    ptts: (p) => p.ptts_diretos.length || null,
  })
  const props = (c: Parameters<typeof propsLocal>[0]) => (inteira ? propsLocal(c) : { campo: c, ordem: null })
  const lista = todos ? ordenados : ordenados.slice(0, 15)
  const v = r.asns.por_vinculo
  return (
    <div className="space-y-2" data-testid="regiao-provedores">
      <p className="text-sm text-gray-700">
        <strong className="tabular-nums">{fmt(r.asns.total)}</strong> ASNs ligados {r.ibges.length > 1 ? 'aos municípios' : 'ao município'}:{' '}
        {fmt(v.sici)} com acessos declarados ao SICI, {fmt(v.sede)} com sede ali e {fmt(v.geo)} com IPs geolocalizados ali (um ASN pode ter mais de um vínculo).
      </p>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead><tr className="text-left text-xs text-gray-400 border-b border-gray-100"><ThOrdenavel {...props('asn')} className="px-2 py-1">ASN</ThOrdenavel><ThOrdenavel {...props('vinculo')} className="px-2 py-1">Vínculo</ThOrdenavel><ThOrdenavel {...props('acessos')} alinhar="right" className="px-2 py-1 text-right" title="total declarado pela operadora do ASN no recorte; operadora com vários ASNs repete o mesmo total em cada um">Acessos da operadora (fixo + móvel)</ThOrdenavel><ThOrdenavel {...props('prefixos')} alinhar="right" className="px-2 py-1 text-right">Prefixos ali</ThOrdenavel><ThOrdenavel {...props('ptts')} className="px-2 py-1">PTTs diretos</ThOrdenavel></tr></thead>
          <tbody className="divide-y divide-gray-50">
            {lista.map((p) => (
              <tr key={p.asn}>
                <td className="px-2 py-1"><Link to={`/asn/${p.asn}`} className="text-primario-600 hover:underline">AS{p.asn}</Link> <span className="text-gray-600">{p.nome}</span></td>
                <td className="px-2 py-1 whitespace-nowrap">{p.vinculos.map((k) => <span key={k} title={ROTULO[k].dica} className={`mr-1 px-1.5 py-0.5 rounded border text-xs ${ROTULO[k].cor}`}>{ROTULO[k].texto}</span>)}</td>
                <td className="px-2 py-1 text-right tabular-nums">{p.acessos_fixo + p.acessos_movel > 0 ? fmt(p.acessos_fixo + p.acessos_movel) : '—'}</td>
                <td className="px-2 py-1 text-right tabular-nums">{p.prefixos_geo > 0 ? fmt(p.prefixos_geo) : '—'}</td>
                <td className="px-2 py-1"><ListaPtts codigos={p.ptts_diretos} nome={nomePtt} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {r.provedores.length > 15 && <button type="button" className="text-xs text-primario-600 hover:underline" onClick={() => setTodos(!todos)}>{todos ? 'Mostrar só os 15 primeiros' : `Mostrar todos (${fmt(r.provedores.length)}${r.provedores_total > r.provedores.length ? ` de ${fmt(r.provedores_total)}` : ''})`}</button>}
      <p className="text-xs text-gray-500">Os acessos são da operadora (CNPJ) do ASN: quando ela tem vários ASNs o mesmo total aparece em cada linha, então não some as linhas.</p>
      <Limites texto={r.limites} />
    </div>
  )
}

/** Participação dos ASNs da região nos PTTs: direta (sessão no PTT) e indireta (visto como origem por meio de outro ASN). */
export function PttsRegiaoBloco({ dados }: BlocoProps<MunicipioCtx>) {
  const r = dados.regiao!
  const p = r.participacao_ptts
  const nomePtt = nomeDosPtts(r.ptts_nomes)
  // A lista de PTTs vem inteira: ordena-se toda e só depois corta nos 20 primeiros.
  const { ordenados, props } = useOrdenacao(p.ptts, {
    ptt: (t) => nomePtt(t.codigo),
    direto: (t) => t.direto,
    indireto: (t) => t.indireto,
    pct: (t) => t.pct_total,
  })
  return (
    <div className="space-y-3" data-testid="regiao-ptts">
      <dl className="grid grid-cols-3 gap-3 text-sm">
        <div><dt className="text-xs text-gray-500">Com sessão em PTT (direto)</dt><dd className="text-lg font-semibold tabular-nums">{pct(p.pct_direto)}</dd><dd className="text-xs text-gray-500">{fmt(p.com_ptt_direto)} de {fmt(r.asns.total)} ASNs</dd></div>
        <div><dt className="text-xs text-gray-500">Só indireto</dt><dd className="text-lg font-semibold tabular-nums">{pct(p.pct_indireto)}</dd><dd className="text-xs text-gray-500">{fmt(p.so_indireto)} ASNs, por meio de outro ASN</dd></div>
        <div><dt className="text-xs text-gray-500">Em nenhum PTT</dt><dd className="text-lg font-semibold tabular-nums">{pct(p.pct_sem_ptt)}</dd><dd className="text-xs text-gray-500">{fmt(p.sem_ptt)} ASNs</dd></div>
      </dl>
      {p.ptts.length > 0 && (
        <table className="w-full text-sm">
          <thead><tr className="text-left text-xs text-gray-400 border-b border-gray-100"><ThOrdenavel {...props('ptt')} className="px-2 py-1">PTT</ThOrdenavel><th scope="col" className="px-2 py-1 w-1/3">ASNs da região</th><ThOrdenavel {...props('direto')} alinhar="right" className="px-2 py-1 text-right">Direto</ThOrdenavel><ThOrdenavel {...props('indireto')} alinhar="right" className="px-2 py-1 text-right">Indireto</ThOrdenavel><ThOrdenavel {...props('pct')} alinhar="right" className="px-2 py-1 text-right">% dos ASNs</ThOrdenavel></tr></thead>
          <tbody className="divide-y divide-gray-50">
            {ordenados.slice(0, 20).map((t) => (
              <tr key={t.codigo}>
                <td className="px-2 py-1"><Link to={`/ixp/${t.codigo}`} className="text-primario-600 hover:underline">{nomePtt(t.codigo)}</Link></td>
                <td className="px-2 py-1"><div className="flex h-2 rounded bg-gray-100 overflow-hidden" aria-hidden><div className="bg-primario-600" style={{ width: `${t.pct_direto ?? 0}%` }} /><div className="bg-primario-300" style={{ width: `${(t.pct_total ?? 0) - (t.pct_direto ?? 0)}%` }} /></div></td>
                <td className="px-2 py-1 text-right tabular-nums">{fmt(t.direto)}</td>
                <td className="px-2 py-1 text-right tabular-nums">{fmt(t.indireto)}</td>
                <td className="px-2 py-1 text-right tabular-nums">{pct(t.pct_total)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <p className="text-xs text-gray-500">Direto: o ASN tem sessão no PTT. Indireto: o PTT recebe rotas originadas por ele, mas por meio de outro ASN. Dados dos looking glasses do IX.br.</p>
    </div>
  )
}

/** Provedores de trânsito mais comuns entre os ASNs da região (relações inferidas, ARC v1, com o nível de confiança). */
export function TransitoRegiaoBloco({ dados }: BlocoProps<MunicipioCtx>) {
  const r = dados.regiao!
  const nomePtt = nomeDosPtts(r.ptts_nomes)
  return (
    <div className="space-y-2" data-testid="regiao-transito">
      <table className="w-full text-sm">
        <thead><tr className="text-left text-xs text-gray-400 border-b border-gray-100"><th className="px-2 py-1">Provedor de trânsito</th><th className="px-2 py-1 text-right">ASNs da região</th><th className="px-2 py-1 text-right" title="confirmado / provável / possível">Confiança</th><th className="px-2 py-1">Está em</th></tr></thead>
        <tbody className="divide-y divide-gray-50">
          {r.transito.map((t) => (
            <tr key={t.asn}>
              <td className="px-2 py-1"><Link to={`/asn/${t.asn}`} className="text-primario-600 hover:underline">AS{t.asn}</Link> <span className="text-gray-600">{t.nome}</span>{t.na_regiao && <span className="ml-1 px-1.5 py-0.5 rounded border text-xs bg-gray-50 text-gray-600" title="este provedor também é um dos ASNs da região">da região</span>}</td>
              <td className="px-2 py-1 text-right tabular-nums">{fmt(t.asns)} <span className="text-gray-400">({pct(t.pct)})</span></td>
              <td className="px-2 py-1 text-right tabular-nums text-gray-600">{t.niveis.confirmado} / {t.niveis.provavel} / {t.niveis.possivel}</td>
              <td className="px-2 py-1"><ListaPtts codigos={t.ptts_diretos} nome={nomePtt} /></td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="text-xs text-gray-500">Relação provedor–cliente inferida dos caminhos BGP (ARC v1); nível: confirmado, provável ou possível. Os {fmt(r.transito_total)} provedores distintos estão ordenados por quantos ASNs da região os usam com confiança confirmada ou provável.</p>
    </div>
  )
}

/** ASNs que levam os ASNs da região até os PTTs: o vizinho observado nos caminhos que está ele mesmo num PTT. */
export function CarregadoresRegiaoBloco({ dados }: BlocoProps<MunicipioCtx>) {
  const r = dados.regiao!
  const nomePtt = nomeDosPtts(r.ptts_nomes)
  return (
    <div className="space-y-2" data-testid="regiao-carregadores">
      <table className="w-full text-sm">
        <thead><tr className="text-left text-xs text-gray-400 border-b border-gray-100"><th className="px-2 py-1">ASN que carrega</th><th className="px-2 py-1 text-right">ASNs da região</th><th className="px-2 py-1">PTTs onde tem sessão</th></tr></thead>
        <tbody className="divide-y divide-gray-50">
          {r.carregadores.map((c) => (
            <tr key={c.asn}>
              <td className="px-2 py-1"><Link to={`/asn/${c.asn}`} className="text-primario-600 hover:underline">AS{c.asn}</Link> <span className="text-gray-600">{c.nome}</span>{c.na_regiao && <span className="ml-1 px-1.5 py-0.5 rounded border text-xs bg-gray-50 text-gray-600">da região</span>}</td>
              <td className="px-2 py-1 text-right tabular-nums">{fmt(c.asns)} <span className="text-gray-400">({pct(c.pct)})</span></td>
              <td className="px-2 py-1"><ListaPtts codigos={c.ptts_diretos} nome={nomePtt} /></td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="text-xs text-gray-500">
        Conta só os ASNs da região que chegam aos PTTs de forma indireta ({fmt(r.participacao_ptts.so_indireto)}); a % é sobre eles.
        {r.indiretos_sem_carregador > 0 && ` Em ${fmt(r.indiretos_sem_carregador)} deles nenhum vizinho observado tem sessão em PTT.`} O ASN carregador é o vizinho visto nos caminhos dos PTTs, não um contrato.
      </p>
    </div>
  )
}

const MEDICOES: Record<string, string> = {
  rov: 'ROV: não alcança rota RPKI-inválida (APNIC)', roa: 'Prefixos com ROA válido', aspa: 'Publica ASPA', irr: 'Prefixos com objeto IRR', irr_aut_num: 'Objeto aut-num no IRR',
  irr_as_set: 'as-set IRR no PeeringDB', peeringdb: 'Registro no PeeringDB', spoofer: 'Anti-spoofing (CAIDA Spoofer)', sem_bogon: 'Sem prefixo bogon',
}

/** Segurança de roteamento dos ASNs da região: o mesmo índice de prontidão agregado, com quantos ASNs sustentam cada número. Sem mínimo: com 1 ASN o número é o dele. */
export function ProntidaoRegiaoBloco({ dados }: BlocoProps<MunicipioCtx>) {
  const p = dados.regiao?.prontidao
  if (!p) return null
  const a = p.agregado
  if (!a) return <p className="text-sm text-gray-600" data-testid="regiao-prontidao">Nenhum dos ASNs da região tem índice de prontidão neste snapshot.</p>
  const linhas = Object.entries(a.medicoes ?? {}).filter(([, m]) => m.asns > 0)
  return (
    <div className="space-y-3 text-sm" data-testid="regiao-prontidao">
      <div className="flex flex-wrap items-baseline gap-x-6 gap-y-1">
        <div><span className="text-2xl font-semibold tabular-nums">{a.media_ponderada_usuarios == null ? '—' : a.media_ponderada_usuarios.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}</span> <span className="text-gray-500">média do índice ponderada pelos usuários estimados</span></div>
        <div className="text-gray-600">{fmt(a.asns_com_indice)} de {fmt(a.asns)} ASNs da região com índice · Brasil {p.brasil.media_ponderada_usuarios?.toLocaleString('pt-BR', { maximumFractionDigits: 1 }) ?? '—'}</div>
      </div>
      {a.asns < 5 && <p className="text-xs text-aviso-700">Poucos ASNs sustentam este recorte ({a.asns}): o número descreve esses ASNs, não a região como um todo.</p>}
      <BarraClasses a={a} />
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead><tr className="text-left text-gray-500"><th className="py-1 pr-3">Medição</th><th className="pr-3 text-right">ASNs com dado</th><th className="pr-3 text-right">Região</th><th className="text-right">Brasil</th></tr></thead>
          <tbody>
            {linhas.map(([c, m]) => (
              <tr key={c} className="border-t border-gray-100">
                <td className="py-1 pr-3">{MEDICOES[c] ?? c}</td>
                <td className="pr-3 text-right tabular-nums">{fmt(m.asns)}</td>
                <td className="pr-3 text-right tabular-nums">{pct(m.media)}</td>
                <td className="text-right tabular-nums text-gray-500">{pct(p.brasil.medicoes?.[c]?.media)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-gray-500">Média simples entre os ASNs que têm o dado; nas medições sim/não é a % de ASNs com sim. Só entram ASNs do Brasil ligados à região por inferência (SICI, sede ou IPs geolocalizados). DNSSEC e IPv6 não existem por ASN neste dataset e não entram. {p.limites} <Link to="/seguranca-de-roteamento" className="text-primario-600 hover:underline">Metodologia e panorama</Link>.</p>
    </div>
  )
}
