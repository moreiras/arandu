// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { SITE } from '../lib/site'

/**
 * `/acessibilidade`: o nível buscado, o que foi feito e verificado, as limitações conhecidas e como
 * relatar um problema. A NBR 17225 não exige a página; ela existe para o usuário saber o que esperar.
 */
export function Acessibilidade() {
  return (
    <div className="max-w-3xl space-y-6">
      <div>
        <h1 className="text-titulo-1 text-gray-900">Acessibilidade</h1>
        <p className="mt-1 text-sm text-gray-600">Como o {SITE.nome} trata a acessibilidade, o que já foi verificado e o que ainda não atende.</p>
      </div>

      <section className="space-y-2">
        <h2 className="text-titulo-3 text-gray-800">Objetivo</h2>
        <p className="text-sm text-gray-700">
          O site busca a <strong>conformidade regular</strong> da norma ABNT NBR 17225:2025 (Acessibilidade em conteúdo e aplicações web), que equivale
          aos níveis A e AA da WCAG 2.2. É um objetivo em andamento: a lista de limitações abaixo diz onde ainda não chegamos.
        </p>
      </section>

      <section className="space-y-2">
        <h2 className="text-titulo-3 text-gray-800">O que o site oferece</h2>
        <ul className="list-disc space-y-1 pl-5 text-sm text-gray-700">
          <li>Link "Pular para o conteúdo" no início de cada página, títulos de página únicos e regiões com nome (menu, conteúdo, rodapé).</li>
          <li>Navegação por teclado: abas com as setas, ordenação das tabelas por botão, explicações (ⓘ) que abrem no foco e fecham com Esc.</li>
          <li>Explicações que abrem também no toque, e não só com o mouse; textos de método recolhidos em "Como ler".</li>
          <li>Gráficos com "Ver dados (tabela)", com os mesmos números em texto.</li>
          <li>Controle <strong>Leitura confortável</strong> no topo da página: mais espaço entre linhas, letras, palavras e parágrafos, lembrado neste navegador.</li>
          <li>Texto corrido com entrelinha de 1,5 e linhas de até 80 caracteres; contraste mínimo de 4,5:1 no texto.</li>
          <li>Sem animação para quem pede movimento reduzido no sistema; o zoom do navegador não é bloqueado; o site funciona a partir de 320 px de largura.</li>
          <li>Aviso do tempo de uso avançado visível em todas as larguras; o login, gratuito, desliga esse limite.</li>
        </ul>
      </section>

      <section className="space-y-2">
        <h2 className="text-titulo-3 text-gray-800">Como verificamos</h2>
        <p className="text-sm text-gray-700">
          Verificação automática (axe-core, regras WCAG 2.0, 2.1 e 2.2 nos níveis A e AA) nas páginas do menu e em uma página de cada tipo de entidade,
          em tela larga e em tela de telefone (360 px), além de testes de componente para teclado, foco e explicações. A verificação automática não substitui
          o teste com pessoas e com leitores de tela, que ainda não foi feito.
        </p>
      </section>

      <section className="space-y-2">
        <h2 className="text-titulo-3 text-gray-800">Limitações conhecidas</h2>
        <ul className="list-disc space-y-1 pl-5 text-sm text-gray-700">
          <li><strong>Mapas e curvas de Hilbert:</strong> a navegação e o detalhe por ponto ou bloco dependem do mouse ou do toque. Os mesmos dados estão nas
            tabelas e na busca de cada página (município, PTT, AS), mas não há equivalente completo do desenho em texto.</li>
          <li><strong>Documentação interativa da API (Swagger):</strong> é de terceiros e tem problemas de acessibilidade conhecidos; a página API e MCP traz os
            exemplos em texto.</li>
          <li><strong>Login:</strong> acontece nas páginas do Google, do LinkedIn ou do PeeringDB, fora do controle do site. O site não usa senha nem teste cognitivo próprio.</li>
          <li>Algumas tabelas antigas ainda não têm explicação por coluna; estão sendo migradas para a tabela padrão do site.</li>
        </ul>
      </section>

      <section className="space-y-2">
        <h2 className="text-titulo-3 text-gray-800">Relatar um problema</h2>
        <p className="text-sm text-gray-700">
          Encontrou uma barreira? Escreva para <a href={`mailto:${SITE.contato}`} className="text-primario-700 underline">{SITE.contato}</a> dizendo a
          página, o que tentou fazer e, se puder, o navegador e a tecnologia assistiva usados.
        </p>
      </section>
    </div>
  )
}
