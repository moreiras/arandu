// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { useState } from 'react'
import { Link } from 'react-router-dom'
import type { BlocoProps } from '../entidade/registry'
import type { OperadoraCtx } from '../operadora/contexto'
import type { UfCtx } from '../uf/contexto'
import type { CadastroMeta, CadastroOperadora } from '../../types/api'

const inteiro = (v?: number | null) => (v == null ? '—' : Math.round(v).toLocaleString('pt-BR'))
const dataBr = (d?: string | null) => (d ? d.split('-').reverse().join('/') : '—')
const PORTE: Record<string, string> = { micro: 'microempresa', pequeno: 'empresa de pequeno porte', demais: 'demais portes', nao_informado: 'porte não informado' }
const LINHAS = 15

function Rodape({ m }: { m: CadastroMeta }) {
  return <p className="text-xs text-gray-500">Receita Federal, dados abertos do CNPJ (dump de {m.dump_reference}); snapshot {m.snapshot_date}. {m.limites}</p>
}

function Dados({ c }: { c: CadastroOperadora }) {
  const e = c.estabelecimentos
  const m = c.matriz
  return (
    <dl className="grid grid-cols-2 sm:grid-cols-4 gap-x-6 gap-y-2 text-sm" data-testid="cadastro-dados">
      <div><dt className="text-xs text-gray-500">Matriz</dt><dd>{m ? `${m.municipio ?? '—'}${m.uf ? `/${m.uf}` : ''}` : '—'}{m?.situacao && m.situacao !== 'ativa' ? ` (${m.situacao})` : ''}</dd></div>
      <div><dt className="text-xs text-gray-500">Início da atividade</dt><dd>{dataBr(m?.inicio)}</dd></div>
      <div><dt className="text-xs text-gray-500">Estabelecimentos</dt><dd className="tabular-nums">{inteiro(e.ativos)} ativos, {inteiro(e.baixados)} baixados</dd></div>
      <div><dt className="text-xs text-gray-500">Filiais ativas</dt><dd className="tabular-nums">{inteiro(e.filiais_ativas)}</dd></div>
      <div><dt className="text-xs text-gray-500">Porte</dt><dd>{c.porte ? PORTE[c.porte] ?? c.porte : '—'}{c.mei ? ' (MEI)' : c.simples ? ' (Simples)' : ''}</dd></div>
      <div><dt className="text-xs text-gray-500">Capital social</dt><dd className="tabular-nums">{c.capital_social != null ? `R$ ${inteiro(c.capital_social)}` : '—'}</dd></div>
      <div className="col-span-2"><dt className="text-xs text-gray-500">Atividade principal</dt><dd>{m?.cnae_descricao ?? m?.cnae ?? '—'}</dd></div>
    </dl>
  )
}

/** Presença física da operadora: onde há estabelecimento ativo (Receita) × onde ela declara acessos (SICI). Duas fontes que medem coisas diferentes: a diferença não prova atendimento. */
export function PresencaFisicaOperadoraBloco({ dados }: BlocoProps<OperadoraCtx>) {
  const c = dados.cadastro
  const [todas, setTodas] = useState(false)
  if (!c) return null
  const r = c.resumo_presenca
  const linhas = [...c.presenca].sort((a, b) => (b.acessos_fixo + b.acessos_movel) - (a.acessos_fixo + a.acessos_movel) || b.ativos - a.ativos || a.municipio.localeCompare(b.municipio))
  const vis = todas ? linhas : linhas.slice(0, LINHAS)
  return (
    <div className="space-y-3 text-sm" data-testid="presenca-fisica">
      <Dados c={c} />
      <p data-testid="presenca-resumo">
        <span className="tabular-nums">{inteiro(r.municipios_com_estabelecimento_ativo)}</span> municípios com estabelecimento ativo e <span className="tabular-nums">{inteiro(r.municipios_com_acessos)}</span> com acessos declarados ao SICI:
        {' '}<span className="tabular-nums">{inteiro(r.com_ambos)}</span> com os dois, <span className="tabular-nums">{inteiro(r.so_acessos)}</span> só com acessos e <span className="tabular-nums">{inteiro(r.so_estabelecimento)}</span> só com estabelecimento.
      </p>
      {linhas.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead><tr className="text-left text-gray-500"><th className="py-1 pr-3">Município</th><th className="pr-3 text-right">Estabelecimentos ativos</th><th className="pr-3 text-right">Acessos fixo</th><th className="text-right">Acessos móvel</th></tr></thead>
            <tbody>
              {vis.map((p) => (
                <tr key={p.ibge} className="border-t border-gray-100">
                  <td className="py-1 pr-3"><Link to={`/municipio/${p.ibge}`} className="text-primario-600 hover:underline">{p.municipio}</Link>/{p.uf}{p.tem_matriz ? <span className="ml-1 text-gray-500">(matriz)</span> : null}</td>
                  <td className="pr-3 text-right tabular-nums">{inteiro(p.ativos)}{p.estabelecimentos > p.ativos ? <span className="text-gray-400"> de {inteiro(p.estabelecimentos)}</span> : null}</td>
                  <td className="pr-3 text-right tabular-nums">{p.acessos_fixo ? inteiro(p.acessos_fixo) : '—'}</td>
                  <td className="text-right tabular-nums">{p.acessos_movel ? inteiro(p.acessos_movel) : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {linhas.length > LINHAS && (
            <button type="button" className="mt-2 text-xs text-primario-600 hover:underline" onClick={() => setTodas((v) => !v)}>
              {todas ? 'mostrar menos' : `mostrar os ${inteiro(linhas.length)} municípios`}
            </button>
          )}
        </div>
      )}
      <Rodape m={c} />
    </div>
  )
}

/** Empresas de telecom da UF: abertas e baixadas por ano (matriz com CNAE 61 principal) e quantas estão ativas. */
export function EmpresasTelecomUfBloco({ dados }: BlocoProps<UfCtx>) {
  const c = dados.cadastro
  if (!c) return null
  const anos = [...new Set([...c.entradas_por_ano.map((e) => e.ano), ...c.baixas_por_ano.map((e) => e.ano)])].sort((a, b) => b - a)
  const ent = new Map(c.entradas_por_ano.map((e) => [e.ano, e.total]))
  const bai = new Map(c.baixas_por_ano.map((e) => [e.ano, e.total]))
  const max = Math.max(1, ...c.entradas_por_ano.map((e) => e.total), ...c.baixas_por_ano.map((e) => e.total))
  return (
    <div className="space-y-3 text-sm" data-testid="empresas-telecom-uf">
      <p><span className="text-2xl font-semibold tabular-nums">{inteiro(c.ativas)}</span> <span className="text-gray-500">empresas de telecom ativas em {c.uf} (matriz com CNAE 61 principal)</span></p>
      {anos.length > 0 && (
        <table className="w-full text-xs">
          <thead><tr className="text-left text-gray-500"><th className="py-1 pr-3">Ano</th><th className="pr-3 text-right">Abertas</th><th className="pr-3 text-right">Baixadas</th><th className="w-1/2" /></tr></thead>
          <tbody>
            {anos.map((a) => (
              <tr key={a} className="border-t border-gray-100">
                <td className="py-1 pr-3 tabular-nums">{a}</td>
                <td className="pr-3 text-right tabular-nums">{inteiro(ent.get(a) ?? 0)}</td>
                <td className="pr-3 text-right tabular-nums">{inteiro(bai.get(a) ?? 0)}</td>
                <td><div className="flex h-2 gap-px" aria-hidden="true"><div className="bg-primario-700" style={{ width: `${(100 * (ent.get(a) ?? 0)) / max / 2}%` }} /><div className="bg-gray-400" style={{ width: `${(100 * (bai.get(a) ?? 0)) / max / 2}%` }} /></div></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <Rodape m={c} />
    </div>
  )
}
