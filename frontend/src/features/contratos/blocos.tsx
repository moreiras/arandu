// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from '../../components/layout/LinkDatado'
import type { BlocoProps } from '../entidade/registry'
import type { OperadoraCtx } from '../operadora/contexto'
import type { MunicipioCtx } from '../municipio/contexto'
import type { ContratosCabecalho } from '../../types/api'
import { useOrdenacao } from '../../lib/ordenacao'
import { ThOrdenavel } from '../../components/ui/ThOrdenavel'
import { palavra } from '../../lib/sintese'

const reais = (v?: number | null) => (v == null ? '—' : `R$ ${v.toLocaleString('pt-BR', { maximumFractionDigits: 0 })}`)
const n = (v?: number | null) => (v == null ? '—' : v.toLocaleString('pt-BR'))
const dataBr = (d?: string | null) => (d ? d.slice(0, 10).split('-').reverse().join('/') : '—')
const ESFERA: Record<string, string> = { federal: 'Federal', estadual: 'Estadual', municipal: 'Municipal', distrital: 'Distrital', nao_detalhada: 'Ainda não detalhada' }
const LINHAS = 10

function Rodape({ c, nota }: { c: ContratosCabecalho; nota?: string }) {
  const k = c.cobertura
  return (
    <>
      <p className="text-xs text-gray-500" data-testid="contratos-cobertura">
        Cobertura (snapshot {c.snapshot_date}): {n(k.raizes_com_leitura)} de {n(k.raizes_no_universo)} empresas do universo de telecom já lidas pelo rodízio (leituras de {dataBr(k.leitura_mais_antiga)} a {dataBr(k.leitura_mais_recente)});{' '}
        {n(k.contratacoes_com_detalhe)} de {n(k.contratacoes)} contratações lidas com detalhe (órgão, esfera, objeto). {nota}
      </p>
      <p className="text-xs text-gray-500" data-testid="contratos-fonte">
        Fonte: {c.fonte.nome}, consultada em {dataBr(c.fonte.consultado_em)}; licença dos dados: {c.licenca}. {c.limites}
      </p>
    </>
  )
}

/**
 * Contratos públicos da operadora: resultados de itens publicados no PNCP, com a data da leitura (rodízio). Sem adjetivo: não é contrato assinado nem pagamento, e raiz sem leitura não aparece
 * (a API devolve 204). Raiz lida e sem resultado diz isso com a data.
 */
export function ContratosOperadoraBloco({ dados }: BlocoProps<OperadoraCtx>) {
  const c = dados.contratos
  // por ano fica em ordem cronológica (série curta); esfera e UF ordenam pelo cabeçalho, na lista inteira
  const esferas = useOrdenacao(c?.por_esfera, { esfera: (e) => ESFERA[e.esfera] ?? e.esfera, contratacoes: (e) => e.contratacoes, valor: (e) => e.valor })
  const ufs = useOrdenacao(c?.por_uf, { uf: (u) => u.uf, contratacoes: (u) => u.contratacoes, valor: (u) => u.valor })
  if (!c) return null
  const idade = c.idade_dias == null ? '' : c.idade_dias === 0 ? ' (hoje)' : ` (há ${c.idade_dias} dia${c.idade_dias === 1 ? '' : 's'})`
  return (
    <div className="space-y-3 text-sm" data-testid="contratos-operadora">
      <p className="rounded border border-aviso-200 bg-aviso-50 p-2 text-xs text-aviso-900" data-testid="contratos-aviso">{c.aviso}</p>
      {c.resultado === 'sem_resultado_na_consulta' ? (
        <p data-testid="contratos-vazio">
          Lido em {dataBr(c.lida_em)}{idade}: o PNCP não devolveu resultado de item para o CNPJ de matriz {c.cnpj_consultado ?? ''} desde {dataBr(c.desde)}. Isso não exclui contratos em nome de filial ou anteriores à Lei 14.133.
        </p>
      ) : (
        <>
          <p data-testid="contratos-resumo">
            {palavra(c.itens, 'Resultado de item publicado', 'Resultados de itens publicados')} no PNCP para o CNPJ de matriz, {palavra(c.itens, 'lido', 'lidos')} em {dataBr(c.lida_em)}{idade}: <span className="tabular-nums">{n(c.itens)}</span> {palavra(c.itens, 'item', 'itens')} em <span className="tabular-nums">{n(c.contratacoes)}</span>{' '}
            {palavra(c.contratacoes, 'contratação', 'contratações')} de <span className="tabular-nums">{n(c.orgaos)}</span> {palavra(c.orgaos, 'órgão', 'órgãos')}, entre {dataBr(c.primeiro_resultado)} e {dataBr(c.ultimo_resultado)}, somando <span className="tabular-nums">{reais(c.valor_homologado)}</span>{' '}
            homologados (valor nominal; {n(c.itens_cancelados)} {palavra(c.itens_cancelados, 'item cancelado fica', 'itens cancelados ficam')} fora da soma).
            {c.incompleto ? ' A leitura foi cortada pelo limite de páginas: o total pode ser maior.' : ''}
          </p>
          <div className="grid gap-4 sm:grid-cols-3">
            <table className="w-full text-xs" data-testid="contratos-por-ano">
              <thead><tr className="text-left text-gray-500"><th className="py-1 pr-3">Ano</th><th className="pr-3 text-right">Contratações</th><th className="text-right">Valor</th></tr></thead>
              <tbody>{(c.por_ano ?? []).map((a) => <tr key={a.ano} className="border-t border-gray-100"><td className="py-1 pr-3">{a.ano}</td><td className="pr-3 text-right tabular-nums">{n(a.contratacoes)}</td><td className="text-right tabular-nums">{reais(a.valor)}</td></tr>)}</tbody>
            </table>
            <table className="w-full text-xs" data-testid="contratos-por-esfera">
              <thead><tr className="text-left text-gray-500"><ThOrdenavel {...esferas.props('esfera')} className="py-1 pr-3">Esfera (como informada no PNCP)</ThOrdenavel><ThOrdenavel {...esferas.props('contratacoes')} alinhar="right" className="pr-3 text-right">Contratações</ThOrdenavel><ThOrdenavel {...esferas.props('valor')} alinhar="right" className="text-right">Valor</ThOrdenavel></tr></thead>
              <tbody>{esferas.ordenados.map((e) => <tr key={e.esfera} className="border-t border-gray-100"><td className="py-1 pr-3">{ESFERA[e.esfera] ?? e.esfera}</td><td className="pr-3 text-right tabular-nums">{n(e.contratacoes)}</td><td className="text-right tabular-nums">{reais(e.valor)}</td></tr>)}</tbody>
            </table>
            <table className="w-full text-xs" data-testid="contratos-por-uf">
              <thead><tr className="text-left text-gray-500"><ThOrdenavel {...ufs.props('uf')} className="py-1 pr-3">UF do órgão</ThOrdenavel><ThOrdenavel {...ufs.props('contratacoes')} alinhar="right" className="pr-3 text-right">Contratações</ThOrdenavel><ThOrdenavel {...ufs.props('valor')} alinhar="right" className="text-right">Valor</ThOrdenavel></tr></thead>
              <tbody>{ufs.ordenados.map((u) => <tr key={u.uf} className="border-t border-gray-100"><td className="py-1 pr-3">{u.uf}</td><td className="pr-3 text-right tabular-nums">{n(u.contratacoes)}</td><td className="text-right tabular-nums">{reais(u.valor)}</td></tr>)}</tbody>
            </table>
          </div>
          <details>
            <summary className="cursor-pointer text-xs text-primario-600">Contratações mais recentes ({Math.min((c.recentes ?? []).length, LINHAS)} de {n(c.contratacoes)})</summary>
            <ul className="mt-2 space-y-1 text-xs" data-testid="contratos-recentes">
              {(c.recentes ?? []).slice(0, LINHAS).map((r) => (
                <li key={r.contratacao}>
                  {dataBr(r.data)} · {r.orgao ?? 'órgão não detalhado'}{r.orgao_detalhado ? '' : ' (unidade de compra)'}{r.uf ? ` · ${r.uf}` : ''}{r.esfera ? ` · ${ESFERA[r.esfera] ?? r.esfera}` : ''}{r.modalidade ? ` · ${r.modalidade}` : ''} ·{' '}
                  <span className="tabular-nums">{reais(r.valor)}</span>
                  {r.objeto ? <span className="block text-gray-500">{r.objeto}</span> : null}
                </li>
              ))}
            </ul>
          </details>
        </>
      )}
      <Rodape c={c} nota="Só o CNPJ de matriz; contratos em nome de filial e os anteriores à Lei 14.133 não entram." />
    </div>
  )
}

/**
 * Operadoras com contratação de órgão sediado neste município. O município é o do órgão comprador, não o local de entrega; a ordem é por valor numa leitura parcial e não é ranking de mercado.
 */
export function ContratosMunicipioBloco({ dados }: BlocoProps<MunicipioCtx>) {
  const c = dados.contratos
  if (!c) return null
  return (
    <div className="space-y-3 text-sm" data-testid="contratos-municipio">
      <p className="rounded border border-aviso-200 bg-aviso-50 p-2 text-xs text-aviso-900" data-testid="contratos-aviso">{c.criterio_municipio.charAt(0).toUpperCase() + c.criterio_municipio.slice(1)}. A ordem é por valor registrado numa leitura parcial: não é ranking de mercado nem prova de que a operadora atende o município. {c.aviso}</p>
      <p data-testid="contratos-municipio-resumo">
        Órgãos sediados em {c.municipio ?? c.ibge}{c.uf ? `/${c.uf}` : ''}: <span className="tabular-nums">{n(c.itens)}</span> {palavra(c.itens, 'item', 'itens')} em <span className="tabular-nums">{n(c.contratacoes)}</span> {palavra(c.contratacoes, 'contratação', 'contratações')}, somando <span className="tabular-nums">{reais(c.valor)}</span> homologados.
      </p>
      <table className="w-full text-xs" data-testid="contratos-fornecedores">
        <thead><tr className="text-left text-gray-500"><th className="py-1 pr-3">Operadora (CNPJ de matriz)</th><th className="pr-3 text-right">Contratações</th><th className="pr-3 text-right">Itens</th><th className="text-right">Valor</th></tr></thead>
        <tbody>
          {c.fornecedores.map((f) => (
            <tr key={f.raiz} className="border-t border-gray-100">
              <td className="py-1 pr-3">{f.cnpj ? <Link className="text-primario-600 hover:underline" to={`/operadora/${f.cnpj}`}>{f.nome ?? f.cnpj}</Link> : (f.nome ?? f.raiz)}</td>
              <td className="pr-3 text-right tabular-nums">{n(f.contratacoes)}</td><td className="pr-3 text-right tabular-nums">{n(f.itens)}</td><td className="text-right tabular-nums">{reais(f.valor)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <Rodape c={c} nota="Quem não aparece pode ainda não ter sido lido." />
    </div>
  )
}
