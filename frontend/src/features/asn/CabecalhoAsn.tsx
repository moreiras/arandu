// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Migalhas } from '../../components/layout/Migalhas'
import { Link } from '../../components/layout/LinkDatado'
import { EntityHeader } from '../../components/entidade'
import { AcoesEntidade } from '../../components/entidade/AcoesEntidade'
import { ContactsReveal } from '../../components/ContactsReveal'
import { OutorgaBadge } from '../../components/OutorgaBadge'
import { EmpresasRelacionadasSection } from '../../components/socios/EmpresasRelacionadasSection'
import { fetchASNContacts, fetchEmpresasRelacionadas } from '../../services/api'
import { useQuery } from '@tanstack/react-query'
import { useActiveDate } from '../../hooks/useSnapshot'
import type { ASNDocument, AsnCadastro, AsnRecuperacao } from '../../types/api'
import { fmtCnpj } from './Outorgas'

/** Link para a página do grupo econômico (cruzamento de sócios), como na Operadora. Usa a mesma consulta (e o cache)
 * da seção de empresas relacionadas; sem grupo, não mostra nada. */
function LinkGrupo({ cnpj }: { cnpj: string }) {
  const date = useActiveDate()
  const q = useQuery({ queryKey: ['empresas-relacionadas', cnpj, date], queryFn: () => fetchEmpresasRelacionadas(cnpj, date ?? undefined), retry: false })
  const id = q.data?.grupo_id
  if (!id) return null
  const n = (q.data?.mesmo_grupo?.length ?? 0) + 1
  return (
    <div className="text-sm">
      <Link to={`/grupo/${encodeURIComponent(id)}`} className="font-medium text-primario-700 hover:underline">Grupo econômico{n > 1 ? ` (${n} empresas)` : ''} →</Link>
      <span className="ml-2 text-xs text-gray-500">indicadores técnicos e de mercado somados das empresas do grupo</span>
    </div>
  )
}

const dia = (iso?: string | null) => (iso ? iso.slice(0, 10) : null)

/**
 * Fatos cadastrais e de numeração do ASN (PT-26, ASN 5.3), sem causa: a situação do CNPJ na Receita só aparece quando não é ATIVA (com o motivo
 * que a Receita informa e a data da leitura); o ASN em recuperação pelo Registro.br aparece com a janela. Nenhum dos dois prova que o AS está sem
 * uso nem irregular. Município e atividade principal vêm do mesmo cadastro, sem endereço.
 */
export function FatosCadastrais({ cadastro, recuperacao }: { cadastro?: AsnCadastro | null; recuperacao?: AsnRecuperacao | null }) {
  const situacao = (cadastro?.descricao_situacao_cadastral ?? '').trim()
  const naoAtiva = situacao !== '' && situacao.toUpperCase() !== 'ATIVA'
  if (!cadastro && !recuperacao) return null
  return (
    <div className="text-xs text-gray-600 space-y-0.5" data-testid="asn-fatos-cadastrais">
      {cadastro?.cnae_fiscal_descricao && <div>Atividade principal (CNAE): {cadastro.cnae_fiscal_descricao.toLowerCase()} <span className="text-gray-400">(fato, Receita)</span></div>}
      {cadastro?.municipio && (
        <div>Sede: {cadastro.codigo_municipio_ibge ? <Link to={`/municipio/${cadastro.codigo_municipio_ibge}`} className="text-primario-600 hover:underline">{cadastro.municipio}{cadastro.uf ? ` (${cadastro.uf})` : ''}</Link> : `${cadastro.municipio}${cadastro.uf ? ` (${cadastro.uf})` : ''}`}</div>
      )}
      {naoAtiva && (
        <div data-testid="asn-situacao-cadastral">
          Situação cadastral do CNPJ na Receita: <strong>{situacao.toLowerCase()}</strong>{cadastro?.lido_em ? ` (cadastro lido em ${dia(cadastro.lido_em)})` : ''} <span className="text-gray-400">(fato)</span>.
          {cadastro?.descricao_motivo_situacao_cadastral ? ` Motivo informado pela Receita: ${cadastro.descricao_motivo_situacao_cadastral.toLowerCase()}.` : ''}
          {' '}A situação do CNPJ não prova que o AS esteja sem uso.
        </div>
      )}
      {recuperacao && (
        <div data-testid="asn-recuperacao">
          ASN em recuperação pelo Registro.br (janela {recuperacao.inicio} a {recuperacao.fim}) <span className="text-gray-400">(fato)</span>. A lista não informa o motivo.
        </div>
      )}
    </div>
  )
}

/** Cabeçalho da página de ASN: nome, selos (Brasil/IPv6/IPv4), CNPJ com outorgas, ASNs do mesmo CNPJ, nomes alternativos, PeeringDB e contatos. */
export function CabecalhoAsn({ doc }: { doc: ASNDocument & { cadastro?: AsnCadastro | null; recuperacao?: AsnRecuperacao | null } }) {
  // credenciamento de rede virtual no SMP sem outorga própria: selo "MVNO", nunca "SMP" (REL-E3)
  const credenciada = !doc.has_smp && !!doc.smp?.some((r) => r.rede_virtual?.papel === 'credenciada')
  return (
    <EntityHeader
      trilha={<Migalhas grupo="rede" itens={[{ rotulo: 'ASes', to: '/ases' }, { rotulo: `AS${doc.asn}`, mono: true }]} />}
      nome={`AS${doc.asn}`}
      selos={[
        ...(doc.is_br ? [{ rotulo: 'Brasil', tom: 'verde' as const }] : []),
        ...(doc.has_ipv6 ? [{ rotulo: 'IPv6', tom: 'laranja' as const }] : []),
        ...((doc.global_prefixes_v4?.length ?? 0) > 0 ? [{ rotulo: 'IPv4', tom: 'azul' as const }] : []),
      ]}
      descricao={doc.name}
      snapshot={doc.snapshot_date}
      acoes={<AcoesEntidade tipo="asn" id={String(doc.asn)} />}
    >
      {doc.cnpj && (
        <div className="mt-1 space-y-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-gray-400 text-sm">CNPJ:{' '}
              <Link to={`/operadora/${doc.cnpj}`} className="font-mono text-gray-500 hover:text-primario-600 hover:underline">
                {fmtCnpj(doc.cnpj)}
              </Link>
            </span>
            {doc.has_scm && <OutorgaBadge label="SCM" />}
            {doc.has_smp && <OutorgaBadge label="SMP" />}
            {!doc.has_smp && credenciada && <OutorgaBadge label="MVNO" />}
            {doc.has_stfc && <OutorgaBadge label="STFC" />}
            {doc.has_seac && <OutorgaBadge label="SeAC" />}
            {!doc.has_scm && !doc.has_smp && !credenciada && !doc.has_stfc && !doc.has_seac && (
              <span className="text-xs font-medium bg-gray-100 text-gray-500 rounded px-1.5 py-0.5">sem outorga Anatel</span>
            )}
          </div>

          {!doc.has_scm && !doc.has_smp && !credenciada && !doc.has_stfc && !doc.has_seac && (
            <p className="text-xs text-gray-500" data-testid="asn-sem-outorga">
              Sem outorga própria na base de outorgas da Anatel (SCM, SMP, STFC e SeAC; snapshot {doc.snapshot_date}) <span className="text-gray-400">(fato)</span>. O selo diz só que o CNPJ não consta nessa base; não indica irregularidade.
            </p>
          )}
          <FatosCadastrais cadastro={doc.cadastro} recuperacao={doc.recuperacao} />

          {doc.same_cnpj_asns && doc.same_cnpj_asns.length > 0 && (
            <div className="text-xs text-gray-500">
              Outros ASNs do mesmo CNPJ:{' '}
              {doc.same_cnpj_asns.map((o, i) => (
                <span key={o.asn}>
                  {i > 0 && ', '}
                  <Link to={`/asn/${o.asn}`} className="text-primario-600 underline underline-offset-2" title={o.name}>AS{o.asn}</Link>
                </span>
              ))}
            </div>
          )}

          <LinkGrupo cnpj={doc.cnpj} />
          <EmpresasRelacionadasSection cnpj={doc.cnpj} title="Outras empresas relacionadas" compact />

          {doc.alt_names && doc.alt_names.length > 0 && (
            <div className="text-xs text-gray-400 leading-snug">
              {doc.alt_names.map((a, i) => (
                <span key={i}>
                  {i > 0 && ' · '}
                  {a.name} <span className="text-gray-300">({a.source})</span>
                </span>
              ))}
            </div>
          )}

          {doc.is_br && doc.pdb_registered !== false && (
            <div className="text-xs pt-0.5">
              <a
                href={`https://www.peeringdb.com/asn/${doc.asn}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-tecnico-600 hover:underline"
              >
                Ver perfil no PeeringDB ↗
              </a>
            </div>
          )}

          <ContactsReveal
            available={doc.contacts_available}
            fetchContacts={() => fetchASNContacts(doc.asn)}
          />
        </div>
      )}
    </EntityHeader>
  )
}
