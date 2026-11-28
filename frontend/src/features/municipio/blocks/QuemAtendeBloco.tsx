// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useState } from 'react'
import { Link } from '../../../components/layout/LinkDatado'
import { SeloMarca } from '../../../components/ui/SeloMarca'
import { palavra } from '../../../lib/sintese'
import type { BlocoProps } from '../../entidade/registry'
import type { MunicipioCtx } from '../contexto'
import { fmt, fmtCnpj } from '../ui'
import { quemAtende, type LinhaQuemAtende } from '../quemAtende'
import { ListaPtts, nomeDosPtts } from './RegiaoBlocos'

const pct = (v: number) => `${v.toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`
/** Empresário individual e MEI chegam da API com o rótulo "Empresário individual": o nome já traz o CNPJ mascarado, então aqui não há link nem CNPJ completo. */
const ehPessoaNatural = (nome: string) => /^empres[aá]rio individual/i.test(nome.trim())
const ehCnpjCompleto = (c: string) => /^\d{14}$/.test((c ?? '').replace(/\D/g, '')) && !/[*]/.test(c)

function Nome({ l }: { l: LinhaQuemAtende }) {
  const rotulo = l.semNome ? `CNPJ ${fmtCnpj(l.cnpj)}` : l.nome
  return (
    <>
      {ehCnpjCompleto(l.cnpj) && !ehPessoaNatural(l.nome)
        ? <Link to={`/operadora/${l.cnpj}`} className="text-primario-600 hover:underline font-medium">{rotulo}</Link>
        : <span className="font-medium text-gray-800">{rotulo}</span>}
      {l.nomeDoAsn && <span title="o SICI informa &quot;Nenhum Informado&quot; como nome da operadora; aqui vai o nome do ASN ligado ao CNPJ"> (*)</span>}
      {l.semNome && <span title="o SICI não informa o nome desta operadora e não há ASN ligado ao CNPJ"> (*)</span>}
      <div className="text-xs text-gray-400 font-mono">{!ehPessoaNatural(l.nome) && fmtCnpj(l.cnpj)}{l.marca && <span className="font-sans"> · marca {l.marca} (inferido)</span>}</div>
    </>
  )
}

/** "Quem atende e como se conecta" (PT-26, município 5.2): operadoras do fixo por CNPJ, com ASN, sessão direta em PTT e PTTs só indiretos. */
export function QuemAtendeBloco({ dados }: BlocoProps<MunicipioCtx>) {
  const regiao = dados.regiao
  const [todas, setTodas] = useState(false)
  const q = quemAtende(dados.fixo?.operadores ?? [], regiao, dados.indicadores?.mudancas_cnpj)
  const nomePtt = nomeDosPtts(regiao?.ptts_nomes ?? {})
  const linhas = todas && q.demais ? [...q.linhas, ...q.demais.linhas] : q.linhas
  const nota = linhas.some((l) => l.nomeDoAsn || l.semNome) || (!todas && !!q.demais && q.demais.linhas.some((l) => l.nomeDoAsn || l.semNome))
  const indicador = (rotulo: string, v: number, id: string) => (
    <div data-testid={id}>
      <dt className="text-xs text-gray-500">{rotulo}</dt>
      <dd className="text-lg font-semibold tabular-nums">{pct(v)}</dd>
      <dd><SeloMarca selo="inferido" legivel /></dd>
    </div>
  )
  return (
    <div className="space-y-3" data-testid="quem-atende">
      <dl className="grid grid-cols-1 md:grid-cols-3 gap-3">
        {indicador('Fixo em operadora com ASN ligado', q.pctComAsn, 'qa-asn')}
        {indicador('Fixo em operadora com sessão direta em PTT do IX.br', q.pctDireta, 'qa-direta')}
        {indicador('Fixo em operadora vista só de forma indireta', q.pctSoIndireta, 'qa-indireta')}
      </dl>
      <p className="text-xs text-gray-500">
        Parcelas do total de {fmt(q.total)} acessos fixos declarados. As duas últimas estão contidas na primeira; a diferença é a parcela em operadora com ASN
        sem PTT visto{q.indeterminadas > 0 ? ' ou sem leitura' : ''}.
        {q.listaCortada && ` A lista de provedores da região veio cortada: ${fmt(q.indeterminadas)} ${palavra(q.indeterminadas, 'operadora ficou', 'operadoras ficaram')} sem leitura de PTT e ${palavra(q.indeterminadas, 'não entra', 'não entram')} nas duas últimas parcelas.`}
      </p>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <caption className="sr-only">Operadoras do fixo no município, por acessos declarados, com ASN e PTTs</caption>
          <thead>
            <tr className="text-left text-xs text-gray-400 border-b border-gray-100">
              <th scope="col" className="px-2 py-1">Operadora</th>
              <th scope="col" className="px-2 py-1 text-right">Fixo local</th>
              <th scope="col" className="px-2 py-1">ASN</th>
              <th scope="col" className="px-2 py-1">Sessão direta em PTT (IX.br)</th>
              <th scope="col" className="px-2 py-1">Só indireto, via</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {linhas.map((l) => (
              <tr key={l.cnpj} data-testid="qa-linha">
                <td className="px-2 py-1"><Nome l={l} /></td>
                <td className="px-2 py-1 text-right tabular-nums whitespace-nowrap">{fmt(l.acessos)} <span className="text-gray-500">({pct(l.share)})</span></td>
                <td className="px-2 py-1">
                  {l.asns.length === 0 ? <span className="text-gray-600">sem ASN</span> : (
                    <span className="flex flex-wrap gap-1">
                      {l.asns.slice(0, 3).map((a) => <Link key={a} to={`/asn/${a}`} className="text-xs px-1.5 py-0.5 rounded bg-primario-50 text-primario-700 border border-primario-100">AS{a}</Link>)}
                      {l.asns.length > 3 && <span className="text-xs text-gray-400">+{l.asns.length - 3}</span>}
                    </span>
                  )}
                </td>
                <td className="px-2 py-1">{l.situacao === 'sem_asn' || l.situacao === 'indeterminada' ? <span className="text-gray-500">n/d</span> : l.diretos.length ? <ListaPtts codigos={l.diretos} nome={nomePtt} /> : <span className="text-gray-600">nenhum</span>}</td>
                <td className="px-2 py-1">{l.situacao === 'sem_asn' || l.situacao === 'indeterminada' ? <span className="text-gray-500">n/d</span> : l.indiretos.length ? <ListaPtts codigos={l.indiretos} nome={nomePtt} /> : <span className="text-gray-600">nenhum</span>}</td>
              </tr>
            ))}
            {!todas && q.demais && (
              <tr data-testid="qa-demais">
                <td className="px-2 py-1 font-medium text-gray-800">Demais ({fmt(q.demais.n)})</td>
                <td className="px-2 py-1 text-right tabular-nums whitespace-nowrap">{fmt(q.demais.acessos)} <span className="text-gray-500">({pct(q.demais.share)})</span></td>
                <td className="px-2 py-1 text-gray-600" colSpan={3}>
                  {fmt(q.demais.comAsn)} com ASN, {fmt(q.demais.n - q.demais.comAsn)} sem ASN; {fmt(q.demais.comSessaoDireta)} com sessão direta em PTT
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      {q.demais && (
        <button type="button" className="text-xs text-primario-600 hover:underline" onClick={() => setTodas(!todas)} aria-expanded={todas}>
          {todas ? 'Agrupar as operadoras menores' : `Mostrar as ${fmt(q.demais.n)} operadoras menores`}
        </button>
      )}
      {nota && <p className="text-xs text-gray-500">(*) O SICI informa &quot;Nenhum Informado&quot; ou não informa nome; quando há ASN ligado ao CNPJ, aparece o nome do ASN.</p>}
      <p className="text-xs text-gray-500">
        Sessão direta em PTT é um fato do cadastro de participantes do IX.br e não mede qualidade de rede. &quot;Só indireto&quot;: o PTT recebe rotas originadas por um ASN da
        operadora por meio de outro ASN. Não há leitura de trânsito por operadora: o trânsito inferido da região está no bloco de trânsito, mais abaixo.
      </p>
    </div>
  )
}
