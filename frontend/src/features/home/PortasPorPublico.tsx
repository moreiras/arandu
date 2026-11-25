// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from '../../components/layout/LinkDatado'

export interface PortaPublico {
  id: 'tecnico' | 'regulador' | 'jornalista' | 'politicas' | 'empresa'
  titulo: string
  /** A pergunta-tipo da lente, em texto: o leitor se reconhece pela pergunta, não pelo rótulo do perfil. */
  pergunta: string
  links: ReadonlyArray<{ to: string; rotulo: string }>
}

/**
 * Cinco portas por lente de leitura (PT-27, home 5.3): técnico, regulação, jornalismo, política pública e empresa. Cada porta tem uma pergunta e três
 * caminhos para páginas que já existem (`menu.ts`; `rotas.test.ts` confere). O título descreve o que a pessoa faz, não um vínculo institucional do site
 * com quem regula ou fiscaliza. A linha "Também" e o menu continuam: a lente não esconde página. Experimento a medir com pesquisa de uso: se atrapalhar
 * a tarefa "achar minha cidade", a seção sai e a Home segue sem ela.
 */
export const PORTAS: readonly PortaPublico[] = [
  { id: 'tecnico', titulo: 'Opero uma rede', pergunta: 'Meu AS está visível e protegido?',
    links: [{ to: '/ases', rotulo: 'Procurar um AS' }, { to: '/panorama/tecnico', rotulo: 'Panorama técnico' }, { to: '/seguranca-de-roteamento', rotulo: 'Segurança de roteamento' }] },
  { id: 'regulador', titulo: 'Acompanho a regulação', pergunta: 'Quem declara e quem tem outorga?',
    links: [{ to: '/regulatorio', rotulo: 'Regulatório' }, { to: '/operadoras?servico=scm', rotulo: 'Operadoras (SCM)' }, { to: '/qualidade', rotulo: 'Qualidade e reclamações' }] },
  { id: 'jornalista', titulo: 'Escrevo sobre o tema', pergunta: 'Que número posso citar?',
    links: [{ to: '/mudancas', rotulo: 'O que mudou' }, { to: '/fontes', rotulo: 'Fontes e como citar' }, { to: '/estados', rotulo: 'Estados' }] },
  { id: 'politicas', titulo: 'Formulo política pública', pergunta: 'Onde falta conexão?',
    links: [{ to: '/estados', rotulo: 'Estados' }, { to: '/municipios', rotulo: 'Municípios' }, { to: '/uso-da-internet', rotulo: 'Uso da Internet (Cetic.br)' }] },
  { id: 'empresa', titulo: 'Sou empresa ou provedor', pergunta: 'Onde crescer e com quem interligar?',
    links: [{ to: '/localizador', rotulo: 'Localizador de Redes' }, { to: '/ixps', rotulo: 'PTTs do IX.br' }, { to: '/grupos', rotulo: 'Grupos econômicos' }] },
]

/** Páginas que não cabem numa lente só: ficam à vista, para a persona não esconder página. */
export const TAMBEM: ReadonlyArray<{ to: string; rotulo: string }> = [
  { to: '/comparar', rotulo: 'Comparar' }, { to: '/explorar', rotulo: 'Explorar dados' }, { to: '/mapa', rotulo: 'Mapa' },
  { to: '/dados', rotulo: 'API e MCP' }, { to: '/snapshots', rotulo: 'Snapshots' }, { to: '/sobre', rotulo: 'Sobre' },
]

const LINK = 'inline-flex min-h-6 items-center py-0.5 text-primario-700 underline underline-offset-2 hover:text-primario-900'

export function PortasPorPublico() {
  return (
    <section aria-labelledby="portas-titulo">
      <h2 id="portas-titulo" className="text-titulo-3 text-gray-900">Por onde começar</h2>
      <ul className="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {PORTAS.map((p) => (
          <li key={p.id} className="rounded-lg border border-gray-200 bg-white p-4 hover:border-primario-400" data-testid={`porta-${p.id}`}>
            <h3 className="text-base font-semibold text-gray-900">{p.titulo}</h3>
            <p className="mt-0.5 text-sm text-gray-600">{p.pergunta}</p>
            <ul className="mt-2 space-y-0.5 text-sm">
              {p.links.map((l) => <li key={l.to + l.rotulo}><Link to={l.to} className={LINK}>{l.rotulo}</Link></li>)}
            </ul>
          </li>
        ))}
      </ul>
      <p className="mt-3 text-sm text-gray-600" data-testid="portas-tambem">
        Também:{' '}
        {TAMBEM.map((l, i) => <span key={l.to}>{i > 0 && ' · '}<Link to={l.to} className={LINK}>{l.rotulo}</Link></span>)}
      </p>
      <p className="mt-1 text-xs text-gray-600">Atalhos por perfil. Tudo está também no menu e na busca.</p>
    </section>
  )
}
