import { SITE } from '../lib/site'
import { TabelaRetencao } from '../components/privacidade/TabelaRetencao'

// TODO(mantenedor) (PT-13 / D10): a tabela de retenção abaixo é gerada das constantes do código (`scripts/gen_retencao.py` →
// `lib/retencao.gen.json`) e continua DESLIGADA: inserir conteúdo na política é decisão e redação do mantenedor. Para ligar, mude a
// constante para `true` (a tabela aparece depois da seção 2.4) e, se quiser outro texto nas células, ajuste `gen_retencao.py` e rode
// `python3 scripts/gen_retencao.py`.
const EXIBIR_TABELA_RETENCAO = false

// TODO(mantenedor) (PT-13 / D10): o texto vigente diverge do código nos pontos abaixo. Nada foi alterado no que o público vê; as redações
// são PROPOSTAS, nesta ordem de seção.
// (a) Seção 2, parágrafo "Também registramos logs de acesso...": proposta de substituição:
//     "O servidor web registra, a cada acesso, o endereço IP, a URL acessada e o horário, para operação e segurança do serviço. Esse
//     registro tem rotação por tamanho e não tem prazo fixo de retenção. Os registros da própria aplicação, descritos nas seções 2.2
//     e 2.3, não guardam o endereço IP."
// (b) Seção 2.3, "ficam apenas contagens por dia e por classe de rota, por até 12 meses": proposta:
//     "ficam apenas contagens por dia, conta, origem da chamada (site, API ou MCP) e classe de rota, por até 12 meses. O identificador
//     interno da conta só é retirado dessas contagens quando a conta é excluída."
// (c) Seção 2.3, "o limite diário de chamadas do MCP": proposta: "os tetos de chamadas do MCP por minuto, por hora e por dia".
// (d) Nova seção 2.5 (não existe; localStorage não é citado): proposta:
//     "2.5 Armazenamento no navegador: o site guarda no armazenamento local do seu navegador (localStorage) a sua preferência de leitura
//     confortável, as buscas recentes da barra de busca e a orientação do mapa. Esses dados ficam só no seu navegador, não são enviados
//     ao servidor e deixam de existir quando você limpa os dados do site."
// (e) CONFLITO a decidir: `POST /auth/log` (api/auth/storage.py, `log_access`) grava, para quem tem login, linha com data, IP, `conta_id` e
//     caminho da página em `data/auth/access_AAAA-MM.log`, retido por 3 meses (RETENCAO_LOG_MESES). Isso contradiz "registros da aplicação
//     não guardam IP" (D10) e a frase "Não guardamos o endereço IP nesse registro" da 2.3 (que trata de outro registro, `uso_conta`).
//     Prática não muda (D10); o mantenedor decide se a política descreve esse registro. Proposta: acrescentar à seção 2.3:
//     "Para quem tem conta, as páginas visitadas no site também são registradas com data e hora, identificador interno da conta,
//     endereço IP e caminho da página, por 3 meses."
export function Privacidade() {
  return (
    <div className="max-w-3xl space-y-8">
      <div>
        <h1 className="text-titulo-1 text-gray-900">Política de Privacidade</h1>
        <p className="text-gray-500 text-sm mt-1">
          Vigente desde junho de 2026 · Atualizada em novembro de 2026 (registro de uso por conta e chave de MCP; em revisão) · Conforme a Lei nº 13.709/2018 (LGPD)
        </p>
      </div>

      <section className="space-y-3">
        <h2 className="text-base font-semibold text-gray-800">1. Quem trata seus dados</h2>
        <p className="text-sm text-gray-600 leading-relaxed">
          O {SITE.nome} é operado pela <strong>Internet Bit a Bit</strong> (
          <a href={`mailto:${SITE.contatoPrivacidade}`} className="text-primario-600 hover:underline">
            {SITE.contatoPrivacidade}
          </a>
          ), responsável pelo tratamento dos dados pessoais coletados neste site.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-base font-semibold text-gray-800">2. Dados coletados</h2>
        <p className="text-sm text-gray-600 leading-relaxed">
          Quando você faz login via provedor de identidade (Google, LinkedIn ou PeeringDB),
          coletamos:
        </p>
        <ul className="text-sm text-gray-600 leading-relaxed list-disc list-inside space-y-1">
          <li>Endereço de e-mail</li>
          <li>Nome associado à conta</li>
          <li>Provedor utilizado no login</li>
          <li>Data do primeiro acesso e do acesso mais recente</li>
        </ul>
        <p className="text-sm text-gray-600 leading-relaxed mt-2">
          Também registramos logs de acesso contendo endereço IP, URL acessada e horário, com o
          objetivo de monitorar o uso do serviço.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-base font-semibold text-gray-800">2.1 Navegação sem login</h2>
        <p className="text-sm text-gray-600 leading-relaxed">
          Para quem navega sem login, o site usa um <strong>cookie de sessão</strong> (anon_sid, 24 horas)
          e uma <strong>identificação técnica do navegador</strong>, da qual guardamos apenas um{' '}
          <em>hash</em> irreversível, para contabilizar o tempo de uso das páginas avançadas e
          manter esse limite mesmo quando o cookie é bloqueado. Em acessos sem cookie, pode ser usado um
          hash do endereço IP combinado com o navegador. Esses dados não identificam a pessoa, não são
          compartilhados e são apagados após 24 horas.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-base font-semibold text-gray-800">2.2 Registro de uso do serviço</h2>
        <p className="text-sm text-gray-600 leading-relaxed">
          O {SITE.nome} <strong>mantém registros de uso da plataforma</strong>, em dois níveis: um registro
          anônimo, descrito abaixo, e, para quem tem conta, um registro associado à conta, descrito na seção 2.3.
          Para entender como o serviço é usado, dimensionar a infraestrutura e orientar melhorias, o
          registro anônimo anota, a cada chamada à interface de dados (API) e ao servidor MCP, apenas:
        </p>
        <ul className="text-sm text-gray-600 leading-relaxed list-disc list-inside space-y-1">
          <li>a rota ou a ferramenta consultada (sem os parâmetros da consulta);</li>
          <li>data e hora, código de resposta, volume de dados enviado e tempo de resposta;</li>
          <li>o tipo de acesso (navegação sem login, com login ou rede autorizada);</li>
          <li>
            um <strong>identificador técnico</strong> obtido por <em>hash</em> do endereço IP e do
            navegador combinados com um valor secreto e aleatório que <strong>muda todos os dias</strong>.
          </li>
        </ul>
        <p className="text-sm text-gray-600 leading-relaxed">
          O registro anônimo <strong>não guarda o endereço IP</strong>, e-mail, nome, cookies nem o conteúdo das
          consultas, e o identificador não permite recuperar o IP nem reconhecer a mesma pessoa em
          dias diferentes. Não é usado para publicidade nem compartilhado. Os registros são mantidos por
          até <strong>90 dias</strong> e depois apagados.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-base font-semibold text-gray-800">2.3 Registro de uso associado à conta</h2>
        <p className="text-sm text-gray-600 leading-relaxed">
          Quando você usa o site, a API ou o servidor MCP com login (cookie de sessão) ou com uma chave de MCP,
          registramos o uso <strong>associado à sua conta</strong>, por um identificador interno
          (não o seu e-mail):
        </p>
        <ul className="text-sm text-gray-600 leading-relaxed list-disc list-inside space-y-1">
          <li>a rota ou a ferramenta consultada (sem os parâmetros da consulta);</li>
          <li>data e hora, código de resposta, volume de dados enviado e tempo de resposta;</li>
          <li>a origem da chamada (site, API ou MCP).</li>
        </ul>
        <p className="text-sm text-gray-600 leading-relaxed">
          A finalidade é o controle de acesso e a prevenção de abuso (inclusive o limite diário de chamadas do
          MCP e a <a href="/uso-aceitavel" className="text-primario-600 hover:underline">Política de Uso Aceitável</a>)
          e o registro do perfil de uso das funcionalidades protegidas. Não guardamos o endereço IP nesse registro, que
          não é usado para publicidade nem compartilhado. O registro detalhado é mantido por <strong>90 dias</strong>; depois,
          ficam apenas contagens por dia e por classe de rota, por até <strong>12 meses</strong>. Você vê um resumo do seu
          uso no perfil.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-base font-semibold text-gray-800">2.4 Chave de MCP</h2>
        <p className="text-sm text-gray-600 leading-relaxed">
          A chave de MCP é gerada <strong>a seu pedido</strong>, no perfil, e mostrada <strong>uma única vez</strong>.
          Guardamos <strong>apenas um código de verificação irreversível (hash)</strong> dela: não é possível recuperá-la, e
          quem perde a chave gera outra. Guardamos também a data de criação, o dia do último uso e um rótulo opcional.
          Você pode <strong>revogar</strong> a chave a qualquer momento, e a revogação vale em poucos segundos. A chave
          nunca aparece em registros do serviço.
        </p>
      </section>

      {EXIBIR_TABELA_RETENCAO && (
        <section className="space-y-3">
          <TabelaRetencao />
        </section>
      )}

      <section className="space-y-3">
        <h2 className="text-base font-semibold text-gray-800">3. Finalidade e base legal</h2>
        <p className="text-sm text-gray-600 leading-relaxed">
          Seus dados são tratados com base no <strong>consentimento</strong> (LGPD, art. 7º, I),
          expresso ao realizar o login. As finalidades são:
        </p>
        <ul className="text-sm text-gray-600 leading-relaxed list-disc list-inside space-y-1">
          <li>Controle de acesso às funcionalidades protegidas do site e registro do perfil de uso das mesmas</li>
          <li>
            Envio de comunicações sobre o serviço, como atualizações, novos recursos e
            informações técnicas
          </li>
          <li>
            Envio de comunicações comerciais, incluindo ofertas de produtos ou serviços próprios
            e de parceiros
          </li>
        </ul>
        <p className="text-sm text-gray-600 leading-relaxed mt-2">
          O consentimento pode ser revogado a qualquer momento mediante solicitação ao e-mail de
          contato indicado abaixo.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-base font-semibold text-gray-800">4. Compartilhamento</h2>
        <p className="text-sm text-gray-600 leading-relaxed">
          Seus dados <strong>não são vendidos</strong>. Podem ser compartilhados com fornecedores
          ou parceiros que atuem em nome do {SITE.nome} para viabilizar a operação do serviço e as
          demais finalidades descritas nesta política — como serviços de infraestrutura, envio de
          comunicações e ferramentas de análise — sempre mediante obrigação de confidencialidade e
          em conformidade com a LGPD.
        </p>
        <p className="text-sm text-gray-600 leading-relaxed">
          Os provedores de login (Google, LinkedIn, PeeringDB) recebem apenas as informações
          necessárias para autenticar sua identidade, conforme suas próprias políticas de
          privacidade.
        </p>
        <p className="text-sm text-gray-600 leading-relaxed">
          A Cloudflare, que entrega o site, mede visitas e desempenho das páginas com o Cloudflare Web
          Analytics, que não usa cookies.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-base font-semibold text-gray-800">5. Retenção</h2>
        <p className="text-sm text-gray-600 leading-relaxed">
          Os dados da conta são armazenados por <strong>tempo indeterminado</strong>, enquanto o serviço
          estiver em operação, ou até que você solicite a exclusão. Os registros de uso seguem os prazos das seções
          2.2 e 2.3. A exclusão da conta, <strong>solicitada pelo perfil ou por e-mail</strong>, <strong>não é imediata</strong>:
          é efetivada em até <strong>30 dias</strong> do pedido. Nesse período a conta fica desativada (sem acesso e com a chave
          de MCP revogada), para que o uso anterior continue registrado e o serviço possa prevenir abusos. Concluído o
          prazo, apagamos os dados da conta, a chave de MCP e o registro detalhado de uso ligado a ela; as contagens por dia
          deixam de ter qualquer ligação com você.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-base font-semibold text-gray-800">6. Seus direitos</h2>
        <p className="text-sm text-gray-600 leading-relaxed">
          Conforme a LGPD, você tem direito a:
        </p>
        <ul className="text-sm text-gray-600 leading-relaxed list-disc list-inside space-y-1">
          <li>Confirmar a existência do tratamento e acessar seus dados</li>
          <li>Corrigir dados incompletos, inexatos ou desatualizados</li>
          <li>Solicitar a exclusão dos seus dados</li>
          <li>Revogar o consentimento (o que pode implicar o fim do acesso às funcionalidades protegidas)</li>
          <li>Obter informações sobre o compartilhamento realizado</li>
        </ul>
        <p className="text-sm text-gray-600 leading-relaxed mt-2">
          Para exercer qualquer um desses direitos, envie um e-mail para{' '}
          <a href={`mailto:${SITE.contatoPrivacidade}`} className="text-primario-600 hover:underline">
            {SITE.contatoPrivacidade}
          </a>
          .
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-base font-semibold text-gray-800">7. Contato</h2>
        <p className="text-sm text-gray-600 leading-relaxed">
          Para dúvidas sobre esta política ou sobre o tratamento dos seus dados:{' '}
          <a href={`mailto:${SITE.contatoPrivacidade}`} className="text-primario-600 hover:underline">
            {SITE.contatoPrivacidade}
          </a>
        </p>
      </section>
    </div>
  )
}
