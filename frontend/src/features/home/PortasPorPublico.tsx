// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from 'react-router-dom'

/**
 * Três portas por público (EXPERIMENTO, a medir com pesquisa de uso). Cada porta tem três caminhos para páginas que já existem.
 * Se a pesquisa mostrar que as portas atrapalham a tarefa "achar minha cidade", a seção sai e a home segue sem ela.
 */
export const PORTAS = [
  { id: 'tecnico', titulo: 'Sou técnico de rede', texto: 'Roteamento, interconexão e segurança.', cor: 'text-v4-700 border-v4-200 hover:border-v4-400',
    links: [{ to: '/ases', rotulo: 'Procurar um AS' }, { to: '/ixps', rotulo: 'Ver os PTTs do IX.br' }, { to: '/seguranca-de-roteamento', rotulo: 'RPKI, ROV e ASPA' }] },
  { id: 'gestor', titulo: 'Tenho ou quero um provedor', texto: 'Mercado, concorrentes e onde crescer.', cor: 'text-mercado-700 border-mercado-200 hover:border-mercado-400',
    links: [{ to: '/operadoras?servico=scm', rotulo: 'Ver operadoras e assinantes' }, { to: '/localizador', rotulo: 'Achar minha cidade' }, { to: '/ixps', rotulo: 'Avaliar entrar num PTT' }] },
  { id: 'regulador', titulo: 'Estudo ou formulo política', texto: 'Território, concentração e qualidade.', cor: 'text-primario-700 border-primario-200 hover:border-primario-400',
    links: [{ to: '/estados', rotulo: 'Comparar estados' }, { to: '/regulatorio', rotulo: 'Outorgas e FUST' }, { to: '/qualidade', rotulo: 'Qualidade e reclamações' }] },
] as const

export function PortasPorPublico() {
  return (
    <section aria-labelledby="portas-titulo">
      <h2 id="portas-titulo" className="text-titulo-3 text-gray-900">Por onde começar</h2>
      <ul className="mt-3 grid gap-3 md:grid-cols-3">
        {PORTAS.map((p) => (
          <li key={p.id} className={`rounded-lg border bg-white p-4 ${p.cor.split(' ').filter((c) => c.startsWith('border') || c.startsWith('hover')).join(' ')}`} data-testid={`porta-${p.id}`}>
            <h3 className={`text-base font-semibold ${p.cor.split(' ')[0]}`}>{p.titulo}</h3>
            <p className="text-sm text-gray-500 mt-0.5">{p.texto}</p>
            <ul className="mt-2 space-y-1 text-sm">
              {p.links.map((l) => <li key={l.to + l.rotulo}><Link to={l.to} className="text-primario-700 hover:underline">{l.rotulo} →</Link></li>)}
            </ul>
          </li>
        ))}
      </ul>
    </section>
  )
}
