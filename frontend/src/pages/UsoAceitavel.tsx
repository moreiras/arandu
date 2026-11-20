// SPDX-License-Identifier: AGPL-3.0-or-later
// Copyright (C) 2026 Antonio M. Moreiras / Internet Bit a Bit
// Este arquivo faz parte do Arandurape.
// Licença: GNU Affero General Public License v3 ou posterior.
// Texto completo: https://www.gnu.org/licenses/agpl-3.0.html
import { SITE } from '../lib/site'

/** Política de Uso Aceitável. Texto proposto, em revisão pelo mantenedor. */
export function UsoAceitavel() {
  return (
    <div className="max-w-3xl space-y-8">
      <div>
        <h1 className="text-titulo-1 text-gray-900">Política de Uso Aceitável</h1>
        <p className="text-gray-500 text-sm mt-1">Proposta de novembro de 2026 · em revisão</p>
        <p className="text-sm text-gray-600 leading-relaxed mt-3">
          O {SITE.nome} é aberto para consulta, estudo e trabalho. Estas regras valem para o site, a API e o servidor MCP, e
          existem para que ele continue disponível para todos.
        </p>
      </div>

      <section className="space-y-3">
        <h2 className="text-base font-semibold text-gray-800">1. O que você pode fazer</h2>
        <p className="text-sm text-gray-600 leading-relaxed">
          Consultar, pesquisar, ensinar, operar redes, escrever matérias e construir ferramentas com os dados, respeitando a
          licença de cada fonte (veja <a href="/fontes" className="text-primario-600 hover:underline">Fontes e licenças</a>) e
          citando a fonte e a data do snapshot.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-base font-semibold text-gray-800">2. O que não é permitido</h2>
        <ul className="text-sm text-gray-600 leading-relaxed list-disc list-inside space-y-1.5">
          <li>
            <strong>Coleta extensiva:</strong> copiar de forma sistemática a base do sistema (varrer todos os ASNs,
            prefixos, operadoras ou municípios, paginar listas até o fim, raspar páginas) para reconstruí-la, redistribuí-la
            ou revendê-la. Se você precisa de volume, fale conosco antes.
          </li>
          <li>
            <strong>Spam:</strong> usar dados do sistema para enviar mensagens não solicitadas, em massa ou não.
          </li>
          <li>
            <strong>Atividades maliciosas ou ilegais:</strong> preparar ou executar ataques, invasões, fraudes ou
            assédio; violar direitos de terceiros ou a lei.
          </li>
          <li>
            <strong>Burlar limites ou sobrecarregar o serviço:</strong> criar várias contas, compartilhar chave de MCP ou
            contornar o limite de uso.
          </li>
        </ul>
      </section>

      <section className="space-y-3">
        <h2 className="text-base font-semibold text-gray-800">3. Sua conta e sua chave</h2>
        <p className="text-sm text-gray-600 leading-relaxed">
          A chave de MCP é pessoal e intransferível. Você responde pelo que é feito com ela; se ela vazar, revogue-a no
          perfil. O uso é registrado conforme a <a href="/privacidade" className="text-primario-600 hover:underline">Política
          de Privacidade</a>.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-base font-semibold text-gray-800">4. Se as regras forem violadas</h2>
        <p className="text-sm text-gray-600 leading-relaxed">
          O uso acima dos limites recebe resposta de limite (HTTP 429), sem suspensão. Violação desta política pode levar à{' '}
          <strong>revogação da chave e do acesso à conta</strong>, sem aviso prévio quando houver risco para o serviço ou
          para terceiros. Para contestar ou tirar dúvidas:{' '}
          <a href={`mailto:${SITE.contatoPrivacidade}`} className="text-primario-600 hover:underline">{SITE.contatoPrivacidade}</a>.
        </p>
      </section>
    </div>
  )
}
