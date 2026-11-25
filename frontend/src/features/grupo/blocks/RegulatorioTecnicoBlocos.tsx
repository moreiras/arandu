// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurapé.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from '../../../components/layout/LinkDatado'
import { Kpi } from '../../../components/ui'
import { useGrupoBloco } from '../../../hooks/entidades/entidades'
import type { BlocoProps } from '../../entidade/registry'
import type { GrupoCtx } from '../contexto'
import type { GrupoRegulatorio, GrupoTecnico } from '../../../types/api'
import { useOrdenacao } from '../../../lib/ordenacao'
import { ThOrdenavel } from '../../../components/ui/ThOrdenavel'

const n = (v: number | null | undefined) => (v == null ? '—' : v.toLocaleString('pt-BR'))
const pct = (v: number | null | undefined) => (v == null ? '—' : `${v.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`)
const reais = (v: number) => v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL', maximumFractionDigits: 0 })

/**
 * ASes do grupo. Com ASes omitidos (a API detalha só os maiores por usuários estimados), o cabeçalho não ordena: reordenar o recorte
 * esconderia quem lidera a coluna entre os omitidos.
 */
function TabelaAses({ t }: { t: GrupoTecnico }) {
  const { ordenados, props } = useOrdenacao(t.por_asn, {
    asn: { valor: (a) => a.asn, primeiro: 'asc' }, usuarios: (a) => a.usuarios, pct_v6: (a) => a.pct_v6, prefixos_v4: (a) => a.prefixos_v4,
    prefixos_v6: (a) => a.prefixos_v6, roa: (a) => a.roa_valido_pct, ptts: (a) => a.ptts_diretos,
  })
  const completa = t.asns_omitidos === 0
  const th = (campo: Parameters<typeof props>[0]) => (completa ? props(campo) : { campo, ordem: null })
  return (
    <div className="overflow-x-auto"><table className="text-sm min-w-full" aria-label="ASes do grupo" data-tabela="grade">
      <thead><tr className="text-left text-xs text-gray-500 border-b border-gray-200"><ThOrdenavel {...th('asn')} className="py-1 pr-3">AS</ThOrdenavel><ThOrdenavel {...th('usuarios')} alinhar="right" className="pr-3 text-right">Usuários (est.)</ThOrdenavel><ThOrdenavel {...th('pct_v6')} alinhar="right" className="pr-3 text-right">% IPv6</ThOrdenavel><ThOrdenavel {...th('prefixos_v4')} alinhar="right" className="pr-3 text-right">Prefixos v4</ThOrdenavel><ThOrdenavel {...th('prefixos_v6')} alinhar="right" className="pr-3 text-right">Prefixos v6</ThOrdenavel><ThOrdenavel {...th('roa')} alinhar="right" className="pr-3 text-right">ROA válido</ThOrdenavel><ThOrdenavel {...th('ptts')} alinhar="right" className="text-right">PTTs diretos</ThOrdenavel></tr></thead>
      <tbody>{(completa ? ordenados : t.por_asn).map((a) => <tr key={a.asn} className="border-b border-gray-100"><td className="py-1 pr-3"><Link to={`/asn/${a.asn}`} className="text-primario-600 hover:underline">AS{a.asn}</Link> <span className="text-gray-500">{a.nome}</span></td>
        <td className="pr-3 text-right tabular-nums">{n(a.usuarios)}</td><td className="pr-3 text-right tabular-nums">{pct(a.pct_v6)}</td><td className="pr-3 text-right tabular-nums">{n(a.prefixos_v4)}</td><td className="pr-3 text-right tabular-nums">{n(a.prefixos_v6)}</td>
        <td className="pr-3 text-right tabular-nums">{pct(a.roa_valido_pct)}</td><td className="text-right tabular-nums">{n(a.ptts_diretos)}</td></tr>)}</tbody></table></div>
  )
}

function Carrega<T>({ id, bloco, vazio, children }: { id: string; bloco: 'regulatorio' | 'tecnico'; vazio: string; children: (d: T) => JSX.Element }) {
  const q = useGrupoBloco<T>(id, bloco)
  if (q.isLoading) return <div className="h-32 bg-gray-50 rounded animate-pulse" role="status" aria-label="Carregando" />
  if (!q.data) return <p className="text-sm text-gray-500">{vazio}</p>
  return children(q.data)
}

/** Outorgas e multas constituídas das empresas do grupo. Multa constituída não é condenação definitiva; a lista é alfabética (sem ordenar por valor). */
export function OutorgasMultasBloco({ dados }: BlocoProps<GrupoCtx>) {
  return <Carrega<GrupoRegulatorio> id={dados.grupo.grupo_id} bloco="regulatorio" vazio="Não foi possível ler o regulatório deste grupo no snapshot.">{(r) => (
    <div className="space-y-3" data-testid="grupo-outorgas-multas">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        {Object.entries(r.outorgas).map(([s, v]) => <Kpi key={s} rotulo={`Empresas com outorga ${s}`} valor={`${n(v)} de ${n(r.empresas)}`} />)}
      </div>
      <h3 className="text-sm font-medium text-gray-700">Multas constituídas pela Anatel</h3>
      {r.multas.empresas_com_registro === 0 ? <p className="text-sm text-gray-600">Nenhuma empresa do grupo aparece no arquivo de multas constituídas (ausência não é prova de que nunca houve multa).</p> : (
        <>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <Kpi rotulo="Multas constituídas" valor={n(r.multas.multas)} /><Kpi rotulo="Valor original" valor={reais(r.multas.original)} />
            <Kpi rotulo="Valor pago" valor={reais(r.multas.pago)} /><Kpi rotulo="Saldo (com atualização)" valor={reais(r.multas.saldo)} />
          </div>
          <div className="overflow-x-auto"><table className="text-sm min-w-full" aria-label="Multas por empresa do grupo" data-tabela="grade">
            <thead><tr className="text-left text-xs text-gray-500 border-b border-gray-200"><th scope="col" className="py-1 pr-3">Empresa (ordem alfabética)</th><th scope="col" className="pr-3 text-right">Multas</th><th scope="col" className="pr-3 text-right">Original</th><th scope="col" className="text-right">Saldo</th></tr></thead>
            <tbody>{r.multas.por_empresa.map((e) => <tr key={e.raiz} className="border-b border-gray-100"><td className="py-1 pr-3">{e.empresa ?? e.raiz}</td><td className="pr-3 text-right tabular-nums">{n(e.multas)}</td><td className="pr-3 text-right tabular-nums">{reais(e.original)}</td><td className="text-right tabular-nums">{reais(e.saldo)}</td></tr>)}</tbody></table></div>
        </>
      )}
      <p className="text-xs text-gray-500">{n(r.multas.empresas_com_registro)} de {n(r.empresas)} empresas (raízes de CNPJ) têm registro. {r.multas.limites} {r.limites}</p>
    </div>
  )}</Carrega>
}

/** RQUAL (prestadoras ligadas, sem somar) e reclamações (Anatel e Consumidor.gov.br) das marcas ligadas ao grupo. Sem ranking. */
export function QualidadeReclamacoesBloco({ dados }: BlocoProps<GrupoCtx>) {
  return <Carrega<GrupoRegulatorio> id={dados.grupo.grupo_id} bloco="regulatorio" vazio="Não foi possível ler a qualidade e as reclamações deste grupo no snapshot.">{(r) => {
    const ult = r.reclamacoes_anatel.anos[r.reclamacoes_anatel.anos.length - 1]
    return (
      <div className="space-y-3" data-testid="grupo-qualidade">
        <h3 className="text-sm font-medium text-gray-700">Qualidade (RQUAL da Anatel)</h3>
        {r.qualidade.prestadoras.length === 0 ? <p className="text-sm text-gray-600">Nenhuma prestadora medida no RQUAL está ligada a este grupo (o RQUAL cobre só as grandes prestadoras).</p> : (
          <p className="text-sm text-gray-700">Prestadoras ligadas: {r.qualidade.prestadoras.map((p, i) => <span key={`${p.servico}-${p.prestadora}`}>{i > 0 && '; '}{p.prestadora} ({p.servico}, {n(p.municipios)} municípios)</span>)}. Os valores de cada prestadora estão em <Link to="/qualidade" className="text-primario-600 hover:underline">Qualidade</Link>; não se somam entre prestadoras.</p>
        )}
        <h3 className="text-sm font-medium text-gray-700">Reclamações na Anatel</h3>
        {!ult ? <p className="text-sm text-gray-600">Nenhuma marca de reclamação ligada a este grupo.</p> : (
          <p className="text-sm text-gray-700"><strong>{n(ult.reclamacoes)}</strong> reclamações em {ult.ano} nas marcas {r.reclamacoes_anatel.marcas.join(', ')} ({Object.entries(ult.por_servico).map(([s, v]) => `${s}: ${n(v)}`).join('; ')}). O volume depende do tamanho da base de clientes{ult.ano >= new Date().getFullYear() ? `; ${ult.ano} é o ano em curso e pode estar incompleto` : ''}.</p>
        )}
        <h3 className="text-sm font-medium text-gray-700">Consumidor.gov.br{r.consumidor.janela ? ` (${r.consumidor.janela.de} a ${r.consumidor.janela.ate})` : ''}</h3>
        {r.consumidor.marcas.length === 0 ? <p className="text-sm text-gray-600">Nenhuma empresa do Consumidor.gov.br ligada a este grupo.</p> : (
          <div className="overflow-x-auto"><table className="text-sm min-w-full" aria-label="Empresas do Consumidor.gov.br ligadas ao grupo" data-tabela="grade">
            <thead><tr className="text-left text-xs text-gray-500 border-b border-gray-200"><th scope="col" className="py-1 pr-3">Empresa (ordem alfabética)</th><th scope="col" className="pr-3 text-right">Finalizadas</th><th scope="col" className="pr-3 text-right">% respondidas</th><th scope="col" className="pr-3 text-right">Índice de solução</th><th scope="col" className="text-right">Nota</th></tr></thead>
            <tbody>{r.consumidor.marcas.map((m) => <tr key={m.marca} className="border-b border-gray-100"><td className="py-1 pr-3">{m.marca}</td><td className="pr-3 text-right tabular-nums">{n(m.n)}</td><td className="pr-3 text-right tabular-nums">{pct(m.pct_respondidas)}</td><td className="pr-3 text-right tabular-nums">{pct(m.indice_solucao)}</td><td className="text-right tabular-nums">{m.nota_media == null ? '—' : m.nota_media.toLocaleString('pt-BR')}</td></tr>)}</tbody></table></div>
        )}
        <p className="text-xs text-gray-500">Reclamação finalizada não é prova de falha da empresa e depende do tamanho da base; a ligação marca → CNPJ é curada ou por nome fantasia único. Índice de solução, tempo e nota só com 30 ou mais casos. {r.limites}</p>
      </div>
    )
  }}</Carrega>
}

/** Os ASes do grupo: usuários estimados, IPv6, prefixos, validação RPKI e PTTs. Estimativas e observações do looking glass, com a data da coleta. */
export function AsesTecnicoBloco({ dados }: BlocoProps<GrupoCtx>) {
  return <Carrega<GrupoTecnico> id={dados.grupo.grupo_id} bloco="tecnico" vazio="Nenhum AS do grupo tem dado técnico neste snapshot.">{(t) => (
    <div className="space-y-3" data-testid="grupo-tecnico">
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <Kpi rotulo="ASes do grupo" valor={`${n(t.asns_com_dado)} de ${n(t.asns_total)}`} />
        <Kpi rotulo="Prefixos na tabela BGP (IPv6 / IPv4)" valor={`${n(t.prefixos.v6)} / ${n(t.prefixos.v4)}`} />
        <Kpi rotulo="Usuários com IPv6 (estimativa APNIC)" valor={pct(t.ipv6.pct_v6)} />
        <Kpi rotulo="Prefixos com ROA válido" valor={pct(t.rpki.valido_pct)} />
      </div>
      {t.asns_omitidos > 0 && <p className="text-sm text-aviso-700" role="status">Mostrando os {n(t.asns_detalhados)} maiores ASes por usuários estimados; {n(t.asns_omitidos)} ficaram de fora do detalhe.</p>}
      <TabelaAses t={t} />
      <p className="text-xs text-gray-500">{t.rpki.invalido > 0 ? `${n(t.rpki.invalido)} prefixo(s) com ROA inválido e ` : ''}{n(t.rpki.sem_roa)} sem ROA, de {n(t.rpki.validados)} validados. {t.limites}</p>
    </div>
  )}</Carrega>
}

/** Trânsito e presença nos PTTs: quem fornece trânsito aos ASes do grupo e em quais PTTs há sessão direta. Fatos observados, não tráfego. */
export function PttsTransitoBloco({ dados }: BlocoProps<GrupoCtx>) {
  return <Carrega<GrupoTecnico> id={dados.grupo.grupo_id} bloco="tecnico" vazio="Nenhum AS do grupo tem dado técnico neste snapshot.">{(t) => (
    <div className="space-y-3" data-testid="grupo-ptts">
      <p className="text-sm text-gray-700">{n(t.ptts.length)} {t.ptts.length === 1 ? 'PTT' : 'PTTs'} com sessão direta de algum AS do grupo; {n(t.transito.asns_multihomed)} dos {n(t.asns_detalhados)} ASes têm mais de um provedor de trânsito observado.</p>
      {t.ptts.length > 0 && <div className="flex flex-wrap gap-2">{t.ptts.map((p) => <Link key={p.ixp} to={`/ixp/${p.ixp}`} title={`ASes: ${p.asns.map((a) => 'AS' + a).join(', ')}`} className="px-2.5 py-1 rounded border border-primario-200 bg-primario-50 text-primario-700 text-xs hover:bg-primario-100">{p.ixp.toUpperCase()} <span className="text-primario-700">({p.asns.length})</span><span className="sr-only">{`, ASes: ${p.asns.map((a) => 'AS' + a).join(', ')}`}</span></Link>)}</div>}
      {t.transito.provedores.length > 0 && (
        <p className="text-sm text-gray-700">Provedores vistos acima dos ASes do grupo (ordem de AS usado por mais ASes do grupo): {t.transito.provedores.map((p, i) => <span key={p.asn}>{i > 0 && ', '}<Link to={`/asn/${p.asn}`} className="text-primario-600 hover:underline">AS{p.asn}</Link> ({p.asns_do_grupo})</span>)}.</p>
      )}
      <p className="text-xs text-gray-500">A interconexão de cada AS (originação sem sessão direta, route servers, rejeições) está na aba Interconexão da página do AS. Peering bilateral não é visível nos dados públicos: nada aqui diz com quem o grupo troca tráfego.</p>
    </div>
  )}</Carrega>
}
