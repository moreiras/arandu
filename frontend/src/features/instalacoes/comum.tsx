// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from '../../components/layout/LinkDatado'
import type { CadastroInferido, FacilityMeta, FacilityResumo } from '../../types/api'
import { palavra } from '../../lib/sintese'

export const n = (v: number | null | undefined) => (v == null ? '—' : v.toLocaleString('pt-BR'))
export const dataCurta = (iso: string | null | undefined) => (iso ? iso.slice(0, 10) : '—')

/** Velocidade de porta em Mbps → texto (10000 → "10 Gbps"). */
export function fmtMbps(mbps: number | null | undefined): string {
  if (!mbps) return '—'
  if (mbps >= 1000) return `${(mbps / 1000).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} Gbps`
  return `${mbps} Mbps`
}

/** Nome vindo do cadastro do PeeringDB é texto de terceiros: escapa antes de ir para HTML de popup do mapa (fonte única em `lib/html`). */
export { escapar } from '../../lib/html'

const COR_CADASTRO: Record<string, string> = {
  recente: 'bg-ok-50 text-ok-800 border-ok-200',
  parado: 'bg-aviso-50 text-aviso-800 border-aviso-200',
  antigo: 'bg-gray-100 text-gray-700 border-gray-300',
}
const ROTULO_CADASTRO: Record<string, string> = { recente: 'cadastro com atividade em até 12 meses', parado: 'sem atividade no cadastro há 1 a 3 anos', antigo: 'sem atividade no cadastro há mais de 3 anos' }

/**
 * Cadastro com atividade ou parado: leitura INFERIDA das datas do cadastro no PeeringDB, a mais recente entre o registro da instalação e os vínculos de rede,
 * exibidas como vêm. Mede a manutenção do cadastro, não a operação da instalação nem da empresa: o `title` diz isso; o selo nunca usa "ativa" ou "abandonada".
 */
export function SeloCadastro({ c }: { c: CadastroInferido | null | undefined }) {
  if (!c || !c.classe) return <span className="text-xs text-gray-400">sem data</span>
  const datas = c.registro_atualizado !== undefined || c.vinculo_atualizado !== undefined
  const detalhe = datas ? `registro: ${dataCurta(c.registro_atualizado)} · último vínculo de rede: ${dataCurta(c.vinculo_atualizado)}` : dataCurta(c.ultima_atualizacao)
  return (
    <span
      className={`inline-block rounded border px-1.5 py-0.5 text-xs ${COR_CADASTRO[c.classe]}`}
      title={`Inferido: data mais recente do cadastro em ${dataCurta(c.ultima_atualizacao)}, ${n(c.dias)} dias antes da coleta. Mede a manutenção do registro no PeeringDB, não a operação da instalação nem da empresa.`}
      data-testid="selo-cadastro"
    >
      {ROTULO_CADASTRO[c.classe]} · {detalhe}
    </span>
  )
}

/** Atribuição ao PeeringDB e rótulo de dado autodeclarado, com a data da coleta. */
export function AtribuicaoPeeringDb({ meta }: { meta: Pick<FacilityMeta, 'coletado_em' | 'fonte' | 'limites'> }) {
  return (
    <div className="space-y-0.5" data-testid="atribuicao-peeringdb">
      <p className="text-xs text-gray-500">{meta.limites}</p>
      <p className="text-xs text-gray-400">
        Dado autodeclarado no <a href="https://www.peeringdb.com" target="_blank" rel="noreferrer" className="text-primario-600 hover:underline">PeeringDB</a>
        {' '}(<a href="https://www.peeringdb.com/aup" target="_blank" rel="noreferrer" className="hover:underline">AUP</a>). Coletado em {dataCurta(meta.coletado_em ?? meta.fonte?.coletado_em)}.
      </p>
    </div>
  )
}

/** Linha de tabela de instalações (bloco do PTT, do ASN e lista). */
export function LinkInstalacao({ f }: { f: Pick<FacilityResumo, 'id' | 'nome'> }) {
  return <Link to={`/instalacao/${f.id}`} className="text-primario-600 hover:underline">{f.nome ?? `Instalação ${f.id}`}</Link>
}

export const localDe = (f: Pick<FacilityResumo, 'cidade' | 'uf' | 'pais'>) => [f.cidade, f.uf ?? (f.pais && f.pais !== 'BR' ? f.pais : undefined)].filter(Boolean).join(' / ') || '—'

/** PTTs de uma instalação na lista: até 3 com código (IX.br, depois externos) e "+n outros" para o resto, com o texto acessível dizendo quantos o site não acompanha. O nome da cidade vai como texto do link e o código como complemento. */
export function PttsDaInstalacao({ f, nomes }: { f: Pick<FacilityResumo, 'ptts_detalhe' | 'n_ptts'>; nomes?: Record<string, string> }) {
  const ptts = f.ptts_detalhe ?? []
  const comCodigo = ptts.filter((p) => p.code)
  const visiveis = comCodigo.slice(0, 3)
  const sobra = ptts.length - visiveis.length
  const naoAcompanhados = ptts.filter((p) => !p.code).length
  if (ptts.length === 0) return <span className="text-gray-500">—</span>
  return (
    <span className="inline-flex flex-wrap gap-x-1.5 items-baseline">
      {visiveis.map((p) => (
        <Link key={p.ix_id} to={p.tipo === 'ixbr' ? `/ixp/${p.code}` : `/ixp-externo/${p.code}`} className="inline-block min-h-6 leading-6 text-primario-600 hover:underline">
          {p.tipo === 'ixbr' && nomes?.[p.code!] ? `${nomes[p.code!]} (${p.code!.toUpperCase()})` : p.code!.toUpperCase()}
        </Link>
      ))}
      {sobra > 0 && <span className="text-gray-600" title={`${sobra} ${palavra(sobra, 'PTT a mais', 'PTTs a mais')}${naoAcompanhados ? `, ${naoAcompanhados} do PeeringDB que o site não acompanha` : ''}`}>+{sobra} outro{sobra > 1 ? 's' : ''}<span className="sr-only">{`: ${sobra} PTT${sobra > 1 ? 's' : ''} a mais${naoAcompanhados ? `, ${naoAcompanhados} do PeeringDB que o site não acompanha` : ''}`}</span></span>}
    </span>
  )
}

/** Link de um PTT: IX.br em /ixp/{code}, externo em /ixp-externo/{code}; PTT sem cadastro no Arandurapé vira só texto. */
export function PttRotulo({ p }: { p: { ix_id: number; code?: string; nome?: string; tipo: string } }) {
  const rotulo = p.nome ?? (p.code ? p.code.toUpperCase() : `PTT ${p.ix_id} no PeeringDB`)
  if (!p.code) return <span className="text-gray-600">{rotulo}</span>
  return <Link to={p.tipo === 'ixbr' ? `/ixp/${p.code}` : `/ixp-externo/${p.code}`} className="text-primario-600 hover:underline">{p.tipo === 'ixbr' ? p.code.toUpperCase() : rotulo}</Link>
}
