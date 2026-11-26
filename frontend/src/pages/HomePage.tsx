// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { Link } from '../components/layout/LinkDatado'
import { SITE } from '../lib/site'
import { SearchBar } from '../components/layout/SearchBar'
import { BrasilEmNumeros } from '../features/home/BrasilEmNumeros'
import { Destaques } from '../features/home/Destaques'
import { OQueMudou } from '../features/home/OQueMudou'
import { PortasPorPublico } from '../features/home/PortasPorPublico'
import { SinteseHome } from '../features/home/BlocoSinteseHome'
import { CartogramaUfs, METRICAS_NORMALIZADAS } from '../features/estados/CartogramaUfs'
import { ApresentacaoRecolhida, ProvenienciaCompacta } from '../components/ui'
import { useFontes, useUfs } from '../hooks/entidades'

const EXEMPLOS = ['Vivo', 'São Paulo', 'AS28573', 'RPKI', '2804::/32']

/**
 * Home: o que é, para quem é e por onde começar, em um olhar. Busca grande, "o Brasil em números" (cartões), resumo em texto (PT-22, depois dos cartões por PT-30), cinco portas por lente de leitura (PT-27, experimento),
 * cartograma por UF com indicador normalizado, destaques do snapshot e o que mudou. A rota `/inicio-classico` redireciona para cá.
 */
export function HomePage() {
  const { fontes } = useFontes()
  const ufs = useUfs()
  return (
    <ApresentacaoRecolhida>
    <div className="space-y-8">
      <section aria-labelledby="home-titulo" className="pt-2">
        <h1 id="home-titulo" className="text-titulo-1 text-gray-900">{SITE.nomeExtenso}</h1>
        <p className="mt-1 text-base text-gray-600 max-w-2xl">
          Como a Internet se organiza no país, das rotas BGP aos acessos em cada município.
        </p>
        <div className="mt-4 max-w-2xl"><SearchBar grande exemplos={EXEMPLOS} /></div>
      </section>

      <BrasilEmNumeros />
      <SinteseHome />
      <PortasPorPublico />

      <div className="grid gap-6 lg:grid-cols-2 items-start">
        {ufs.data?.items?.length ? (
          <div>
            <CartogramaUfs ufs={ufs.data.items} metricas={METRICAS_NORMALIZADAS} titulo="O Brasil por estado" compacto />
            <p className="mt-2 text-sm"><Link to="/estados" className="text-primario-700 hover:underline">Ver todos os estados →</Link></p>
          </div>
        ) : <p className="text-sm text-gray-500" role="status">{ufs.isLoading ? 'Carregando o cartograma…' : 'O cartograma por estado não está disponível agora.'}</p>}
        <Destaques fontes={fontes} />
      </div>

      <OQueMudou />
      <div className="text-xs text-gray-500">
        <ProvenienciaCompacta bloco={{ fontes: ['anatel_sici', 'registro_br', 'fulltable_routeviews'] }} fontes={fontes} />
      </div>
    </div>
    </ApresentacaoRecolhida>
  )
}
