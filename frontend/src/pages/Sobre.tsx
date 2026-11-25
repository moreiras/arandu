import { SITE } from '../lib/site'
import { TetosDeUso } from '../components/TetosDeUso'
import { CorrecoesNoChangelog } from '../components/ui/CorrecoesNoChangelog'
import { DESCRICAO_SELO, ROTULO_SELO, type Selo } from '../components/entidade/proveniencia'
import { LISTA_UNIVERSOS } from '../lib/universos'

/** Ordem de exibição dos selos, do mais firme ao menos firme. Os textos vêm de `proveniencia.ts` (fonte única, a mesma dos KPIs e do relatório). */
const SELOS: Selo[] = ['fato', 'estimado', 'inferido']

export function Sobre() {
  return (
    <div className="max-w-3xl space-y-8">
      <div>
        <h1 className="text-titulo-1 text-gray-900">{SITE.nome}</h1>
        <p className="text-gray-500 text-sm mt-1">{SITE.nomeExtenso}</p>
      </div>

      <section className="rounded-lg border border-aviso-200 bg-aviso-50 px-5 py-4 space-y-1">
        <p className="text-sm font-semibold text-aviso-800">Versão preliminar</p>
        <p className="text-sm text-aviso-700 leading-relaxed">
          Este site ainda está em desenvolvimento ativo. Algumas seções podem estar incompletas,
          e os dados exibidos podem conter lacunas ou imprecisões. O projeto foi construído com
          uso intensivo de IA generativa (Claude, da Anthropic) — tanto na geração de código
          quanto na automação de partes do pipeline de dados.
        </p>
      </section>

      <section className="space-y-4">
        <p className="text-sm text-gray-600 leading-relaxed">
          O <strong className="text-gray-800">{SITE.nome}</strong> organiza informações públicas sobre rotas, PTTs, ASes,
          operadoras e o território, oferecendo uma visão mais clara da infraestrutura lógica da Internet no país. Não se
          trata apenas de listar dados técnicos, mas de transformar esses dados em conhecimento útil para quem opera,
          pesquisa, planeja ou simplesmente quer entender melhor como a Internet brasileira se conecta. Todo número tem
          fonte e data, e o que é inferido ou estimado vem rotulado como tal.
        </p>
        <p className="text-sm text-gray-600 leading-relaxed">
          O site é mantido pela <strong className="text-gray-800">Internet Bit a Bit</strong>, sem fins lucrativos, e é
          gratuito.
        </p>
      </section>

      <section className="space-y-4">
        <h2 className="text-base font-semibold text-gray-800">O software: {SITE.software}</h2>
        <p className="text-sm text-gray-600 leading-relaxed">
          O {SITE.nome} roda sobre o <strong className="text-gray-800">{SITE.software}</strong>, software livre sob a
          licença GNU Affero General Public License, versão 3 ou posterior (AGPL-3.0-or-later). O código-fonte que esta
          instância roda está em{' '}
          <a href={SITE.codigoFonte} target="_blank" rel="noopener noreferrer" className="text-primario-600 hover:underline break-all">
            {SITE.codigoFonte.replace(/^https?:\/\//, '')}
          </a>
          {' '}(versão {__APP_VERSION__}).
        </p>
        <p className="text-sm text-gray-600 leading-relaxed">
          Em Guarani, <strong className="text-gray-800">Arandu</strong> pode ser entendido como
          sabedoria, conhecimento, entendimento. Ainda em Guarani, <strong className="text-gray-800">Tape</strong>{' '}
          ou <strong className="text-gray-800">Rape</strong> é
          caminho. Juntas, as palavras formam uma ideia simples e forte: o caminho do conhecimento.
        </p>
        <p className="text-sm text-gray-600 leading-relaxed">
          A pronúncia é aproximadamente <strong className="text-gray-800">a-ran-du-ra-PÉ</strong>,
          com acento na última sílaba. Os sons de <em>r</em> em <em>ran</em> e <em>ra</em> são
          suaves, como em "arara" ou "arado", não o <em>r</em> forte de "rua". O final <em>pe</em>{' '}
          soa como "pé".
        </p>
        <p className="text-sm text-gray-600 leading-relaxed">
          O nome foi escolhido porque a Internet também é feita de caminhos. Cada rota anunciada,
          cada Sistema Autônomo, cada ponto de troca de tráfego e cada interconexão ajudam a compor
          a malha invisível que sustenta a comunicação no Brasil. Mas esses caminhos só fazem
          sentido quando podem ser observados, compreendidos e analisados.
        </p>
        <p className="text-sm text-gray-600 leading-relaxed">
          O nome carrega também uma escolha simbólica: poucas marcas são tão brasileiras quanto a presença dos idiomas dos
          povos originários no nosso vocabulário de todo dia. Palavras como abacaxi, mandioca, capivara, tatu, pipoca,
          guaraná e jabuticaba, ou nomes de lugares como Ipanema, Guanabara, Niterói e Aracaju,
          vêm em boa parte do tupi-guarani e atravessam o português falado no país. Batizar o
          projeto com uma expressão dessa origem é uma forma de reconhecer e honrar essa herança, e
          de afirmar, já no nome, que aqui o foco são as redes e a infraestrutura da Internet no
          Brasil.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-base font-semibold text-gray-800">Como funciona</h2>
        <p className="text-sm text-gray-600 leading-relaxed">
          Os dados de fontes públicas são processados em um pipeline offline e publicados
          semanalmente; cada fonte é coletada no seu próprio calendário. Cada publicação gera um
          {' '}<em>snapshot</em> datado. <CorrecoesNoChangelog /> Os dois snapshots mais recentes abrem sem login; os anteriores continuam guardados e abrem com login. Todos os resultados são
          pré-computados — a interface nunca aguarda processamento em tempo real.
        </p>
        <p className="text-sm text-gray-600 leading-relaxed">
          O pipeline coleta tabelas BGP dos looking glasses Telnet dos PTTs do IX.br, baixa
          dumps MRT de múltiplos coletores RouteViews e RIPE RIS para obter uma visão da tabela
          de roteamento global, e cruza essas informações com dados cadastrais do Registro.br,
          LACNIC, PeeringDB e RIPE NCC. Também incorpora outorgas de Serviço de Comunicação
          Multimídia (SCM), Serviço Móvel Pessoal (SMP), Serviço Telefônico Fixo Comutado (STFC)
          e Serviço de Acesso Condicionado (SeAC, TV por assinatura) publicadas pela Anatel,
          cruzando prestadoras licenciadas com os ASes brasileiros identificados.
        </p>
        <p className="text-sm text-gray-600 leading-relaxed">
          Além das outorgas, o pipeline ingere os <strong className="text-gray-800">acessos
          declarados ao SICI</strong> — a declaração mensal obrigatória de toda prestadora à
          Anatel — tanto de banda larga fixa quanto de telefonia móvel: quantos acessos em
          serviço cada CNPJ tem, por município, tecnologia e faixa de velocidade (fixa) ou
          modalidade de cobrança e geração de rede (móvel). Esses números são cruzados com as
          outorgas SCM/SMP e com os ASes identificados, alimentando as páginas de operadora,
          município e a seção de estatísticas de telefonia. Por fim, quatro camadas de
          infraestrutura física completam o mapa: enlaces terrestres de fibra e micro-ondas do{' '}
          <strong className="text-gray-800">ITU BBmaps</strong>, o traçado dos{' '}
          <strong className="text-gray-800">cabos submarinos</strong> e pontos de aterrissagem
          do TeleGeography Submarine Cable Map, as{' '}
          <strong className="text-gray-800">linhas de transmissão de alta tensão</strong> do
          SIGEL/ANEEL e a <strong className="text-gray-800">malha rodoviária nacional</strong> do
          IBGE (BC250) — relevantes porque faixas de domínio de rodovias e linhas de transmissão
          frequentemente carregam cabos OPGW/fibra usados também para telecom, embora nem o SIGEL
          nem o IBGE informem quais trechos especificamente têm essa fibra.
        </p>
        <p className="text-sm text-gray-600 leading-relaxed">
          Além do estado estático da tabela de roteamento, o pipeline analisa a{' '}
          <strong className="text-gray-800">estabilidade BGP</strong> dos ASes brasileiros ao
          longo do tempo. Para cada snapshot, são baixados e processados os arquivos de{' '}
          <em>updates</em> MRT do coletor <code className="font-mono bg-gray-100 px-0.5 rounded text-xs">route-views.saopaulo</code>{' '}
          referentes aos <strong className="text-gray-800">7 dias anteriores</strong> à coleta.
          Esses arquivos registram cada anúncio e retirada de rota ao longo do período, permitindo
          calcular métricas de instabilidade por AS e por prefixo: total de eventos, flaps,
          pico de atividade por hora e sequências repetidas de announce/withdraw. Em uma segunda
          etapa, os ASes mais ruidosos são analisados em detalhe — relendo os arquivos MRT com o
          AS_PATH completo dos eventos — para identificar se o ruído tem origem no próprio AS,
          em um prefixo específico, ou em um upstream instável.
        </p>
      </section>

      <section id="selos" className="space-y-3 scroll-mt-28" data-testid="sobre-selos">
        <h2 className="text-base font-semibold text-gray-800">Como ler os selos: fato, estimado e inferido</h2>
        <p className="text-sm text-gray-600 leading-relaxed">
          Os indicadores trazem, por extenso, a natureza do dado, a fonte e a data de referência (por exemplo, &ldquo;Estimado · APNIC Labs · ref. 2026-11-15&rdquo;).
          O selo diz o quanto o número pode ser tomado como observação direta.
        </p>
        <dl className="space-y-2 text-sm text-gray-700">
          {SELOS.map((k) => (
            <div key={k}><dt className="inline font-semibold">{ROTULO_SELO[k]}:</dt> <dd className="inline" data-selo-def={k}>{DESCRICAO_SELO[k]}</dd></div>
          ))}
        </dl>
      </section>

      <section id="contagens" className="space-y-3 scroll-mt-28" data-testid="sobre-contagens">
        <h2 className="text-base font-semibold text-gray-800">Por que há vários totais</h2>
        <p className="text-sm text-gray-600 leading-relaxed">
          O mesmo nome (&ldquo;ASNs brasileiros&rdquo;, &ldquo;participantes&rdquo;, &ldquo;declarantes&rdquo;, &ldquo;municípios&rdquo;, &ldquo;usuários&rdquo;) pode contar
          conjuntos diferentes. Um total depende de três escolhas: a regra de &ldquo;brasileiro&rdquo; (a delegação da LACNIC ao Brasil ou a lista de alocações do
          Registro.br, que tem alguns ASNs a mais); o que conta como presença (sessão com o route server, cadastro de participantes ou prefixo visto no PTT); e se o número
          é uma união ou uma soma por PTT, com qual denominador. Por isso cada rótulo do site diz o universo, e dois números do mesmo nome com valores diferentes na mesma
          página seriam um defeito. A soma dos usuários estimados por PTT, por exemplo, conta o mesmo usuário em cada PTT onde o seu ASN aparece e não é o total do país.
        </p>
        <dl className="space-y-2 text-sm text-gray-700">
          {LISTA_UNIVERSOS.map((u) => (
            <div key={u.chave} data-universo={u.chave}><dt className="inline font-semibold">{u.rotulo}:</dt> <dd className="inline">{u.definicao}</dd></div>
          ))}
        </dl>
      </section>

      <section id="acesso" className="space-y-3 scroll-mt-28">
        <h2 className="text-base font-semibold text-gray-800">Acesso sem login, limites e como citar</h2>
        <p className="text-sm text-gray-600 leading-relaxed">
          Sem login ficam abertas as páginas de entrada, os dois snapshots mais recentes e a primeira página (até 100 linhas, pela ordem escolhida) das listas, como prévia.
          Páginas avançadas funcionam enquanto durar um orçamento de uso; os snapshots anteriores, as listas completas, o histórico e os contatos exigem login (conta gratuita).
        </p>
        <p className="text-sm text-gray-600 leading-relaxed" data-testid="sobre-citacao">
          O botão &ldquo;Citar este dado&rdquo; gera um texto com os valores mostrados, a data do snapshot e as fontes com as datas de referência, além do endereço permanente.
          Esse endereço fixa o snapshot e <strong>abre sem login enquanto o snapshot estiver entre os dois mais recentes</strong>, em geral cerca de duas semanas, pois os
          snapshots são semanais. Depois disso o endereço exige login; a citação continua valendo por trazer os valores e as fontes.
        </p>
        <TetosDeUso />
      </section>

      <section className="space-y-4">
        <h2 className="text-base font-semibold text-gray-800">Fontes de dados</h2>
        <p className="text-sm text-gray-600">
          Todos os dados utilizados são públicos e de livre acesso. Nenhuma informação privada
          ou proprietária é coletada ou exibida.
        </p>

        <div className="space-y-3">

          <div className="rounded-lg border border-gray-200 p-4 space-y-1">
            <div className="flex items-baseline gap-2">
              <span className="text-sm font-semibold text-gray-800">IX.br — Looking Glass Telnet (PTTs)</span>
              <span className="text-xs text-gray-400">lg.{'{code}'}.ix.br:23</span>
            </div>
            <p className="text-xs text-gray-500">
              Cada PTT do IX.br expõe um servidor Telnet de looking glass na porta 23, no host{' '}
              <code className="font-mono bg-gray-100 px-0.5 rounded">lg.{'{code}'}.ix.br</code>{' '}
              (ex: <code className="font-mono bg-gray-100 px-0.5 rounded">lg.sp.ix.br</code>,{' '}
              <code className="font-mono bg-gray-100 px-0.5 rounded">lg.rj.ix.br</code>). O {SITE.software}
              abre uma sessão Telnet em cada um dos PTTs ativos, executa o comando
              da tabela BGP IPv6 conforme o firmware (FRR ou Quagga) e o{' '}
              <code className="font-mono bg-gray-100 px-0.5 rounded">show ip bgp</code> (IPv4), e extrai a tabela BGP completa
              dos Route Servers — prefixos anunciados, peers diretos, ASNs de origem e estatísticas de
              cobertura por PTT.
            </p>
          </div>

          <div className="rounded-lg border border-gray-200 p-4 space-y-1">
            <div className="flex items-baseline gap-2">
              <span className="text-sm font-semibold text-gray-800">IX.br — Dashboard (membros registrados)</span>
              <a href="https://dashboard.ix.br/generate_json?ixp=sp" target="_blank" rel="noopener noreferrer"
                className="text-xs text-primario-600 hover:underline">dashboard.ix.br/generate_json</a>
            </div>
            <p className="text-xs text-gray-500">
              Lista oficial de participantes cadastrados em cada PTT do IX.br, consultada via endpoint
              público{' '}
              <code className="font-mono bg-gray-100 px-0.5 rounded">dashboard.ix.br/generate_json?ixp={'{code}'}</code>.
              Inclui membros bilaterais que trocam tráfego sem usar os Route Servers e,
              por isso, não aparecem nas tabelas BGP coletadas via Telnet. Usada para identificar
              membros registrados sem peering ativo e exibi-los nas páginas de PTT e AS.
            </p>
          </div>

          <div className="rounded-lg border border-gray-200 p-4 space-y-1">
            <div className="flex items-baseline gap-2">
              <span className="text-sm font-semibold text-gray-800">RouteViews</span>
              <a href="https://archive.routeviews.org/bgpdata/" target="_blank" rel="noopener noreferrer"
                className="text-xs text-primario-600 hover:underline">archive.routeviews.org/bgpdata</a>
            </div>
            <p className="text-xs text-gray-500">
              Projeto da Universidade de Oregon que disponibiliza dumps MRT das tabelas BGP
              globais coletadas de múltiplos pontos de observação ao redor do mundo. Os arquivos
              são baixados e processados para compor a visão da tabela de roteamento global
              (full table), usada como referência para calcular cobertura de prefixos BR.
            </p>
          </div>

          <div className="rounded-lg border border-gray-200 p-4 space-y-1">
            <div className="flex items-baseline gap-2">
              <span className="text-sm font-semibold text-gray-800">RouteViews — Updates MRT (route-views.saopaulo)</span>
              <a href="https://archive.routeviews.org/route-views.saopaulo/bgpdata/" target="_blank" rel="noopener noreferrer"
                className="text-xs text-primario-600 hover:underline">archive.routeviews.org/route-views.saopaulo</a>
            </div>
            <p className="text-xs text-gray-500">
              Arquivos de <em>updates</em> BGP (formato MRT/BGP4MP) do coletor{' '}
              <code className="font-mono bg-gray-100 px-0.5 rounded">route-views.saopaulo</code>,
              com peers latino-americanos. Diferentemente dos dumps de tabela completa (RIBs), os
              arquivos de update registram cada anúncio e retirada de rota ao longo do tempo,
              gerados a cada 15 minutos. O {SITE.software} baixa os updates dos 7 dias anteriores ao
              snapshot e os processa para calcular métricas de estabilidade BGP por AS e por
              prefixo — eventos totais, flaps, atividade horária e diagnóstico de causa raiz para
              os ASes mais ruidosos.
            </p>
          </div>

          <div className="rounded-lg border border-gray-200 p-4 space-y-1">
            <div className="flex items-baseline gap-2">
              <span className="text-sm font-semibold text-gray-800">RIPE RIS</span>
              <a href="https://data.ris.ripe.net/" target="_blank" rel="noopener noreferrer"
                className="text-xs text-primario-600 hover:underline">data.ris.ripe.net</a>
            </div>
            <p className="text-xs text-gray-500">
              Routing Information Service do RIPE NCC. Complementa o RouteViews com dumps MRT
              de coletores adicionais, ampliando a cobertura geográfica da visão global de
              roteamento.
            </p>
          </div>

          <div className="rounded-lg border border-gray-200 p-4 space-y-1">
            <div className="flex items-baseline gap-2">
              <span className="text-sm font-semibold text-gray-800">Registro.br — nicbr-asn-blk</span>
              <a href="https://ftp.registro.br/pub/numeracao/origin/nicbr-asn-blk-latest.txt" target="_blank" rel="noopener noreferrer"
                className="text-xs text-primario-600 hover:underline">ftp.registro.br/…/nicbr-asn-blk-latest.txt</a>
            </div>
            <p className="text-xs text-gray-500">
              Arquivo pipe-delimitado publicado pelo NIC.br no FTP do Registro.br, com mapeamento
              de ASN → nome da organização, CNPJ e blocos IPv6/IPv4 declarados. Formato:{' '}
              <code className="font-mono bg-gray-100 px-0.5 rounded">AS{'{num}'}|Nome|CNPJ|prefixo1|…</code>.
              Usada como referência canônica do espaço de endereçamento BR para calcular cobertura,
              filtrar ASes e identificar prefixos nacionais.
            </p>
          </div>

          <div className="rounded-lg border border-gray-200 p-4 space-y-1">
            <div className="flex items-baseline gap-2">
              <span className="text-sm font-semibold text-gray-800">LACNIC — delegated-lacnic-extended</span>
              <a href="https://ftp.lacnic.net/pub/stats/lacnic/delegated-lacnic-extended-latest" target="_blank" rel="noopener noreferrer"
                className="text-xs text-primario-600 hover:underline">ftp.lacnic.net/…/delegated-lacnic-extended-latest</a>
            </div>
            <p className="text-xs text-gray-500">
              Arquivo de delegações estendido do LACNIC, no formato RIR Statistics Exchange Format
              (RFC 7682). O {SITE.software} extrai as linhas com{' '}
              <code className="font-mono bg-gray-100 px-0.5 rounded">lacnic|BR|asn|…|allocated</code>{' '}
              e{' '}
              <code className="font-mono bg-gray-100 px-0.5 rounded">|assigned</code>{' '}
              para determinar o conjunto autoritativo de ASNs brasileiros. Complementa o
              nicbr-asn-blk do Registro.br, que mapeia prefixos mas pode incluir ASNs estrangeiros
              com blocos BR alocados.
            </p>
          </div>

          <div className="rounded-lg border border-gray-200 p-4 space-y-1">
            <div className="flex items-baseline gap-2">
              <span className="text-sm font-semibold text-gray-800">PeeringDB</span>
              <a href="https://www.peeringdb.com" target="_blank" rel="noopener noreferrer"
                className="text-xs text-primario-600 hover:underline">peeringdb.com</a>
            </div>
            <p className="text-xs text-gray-500">
              Base de dados colaborativa com informações sobre redes e pontos de troca de tráfego
              globais. Usada para enriquecer dados de IXPs externos (membros, localização, tipo),
              identificar presença de ASes em PTTs internacionais e geolocalizar redes estrangeiras.
            </p>
          </div>

          <div className="rounded-lg border border-gray-200 p-4 space-y-1">
            <div className="flex items-baseline gap-2">
              <span className="text-sm font-semibold text-gray-800">RIPE NCC — AS names</span>
              <a href="https://ftp.ripe.net/ripe/asnames/asn.txt" target="_blank" rel="noopener noreferrer"
                className="text-xs text-primario-600 hover:underline">ftp.ripe.net/ripe/asnames/asn.txt</a>
            </div>
            <p className="text-xs text-gray-500">
              Arquivo <code className="font-mono bg-gray-100 px-0.5 rounded">asn.txt</code> compilado
              pelo RIPE NCC a partir dos dados WHOIS dos cinco RIRs, com os nomes descritivos de
              aproximadamente 121 mil ASes globais. Atualizado diariamente. Usado para exibir o nome
              associado a cada número de sistema autônomo em toda a interface.
            </p>
          </div>

          <div className="rounded-lg border border-gray-200 p-4 space-y-1">
            <div className="flex items-baseline gap-2">
              <span className="text-sm font-semibold text-gray-800">APNIC Labs — estimativas de usuários</span>
              <a href="https://stats.labs.apnic.net/aspop" target="_blank" rel="noopener noreferrer"
                className="text-xs text-primario-600 hover:underline">stats.labs.apnic.net</a>
            </div>
            <p className="text-xs text-gray-500">
              Estimativas de número de usuários de Internet por AS, derivadas de medições ativas
              do APNIC Labs. Usadas para contextualizar o alcance de cada rede e calcular
              percentuais de população atendida por PTT.
            </p>
          </div>

          <div className="rounded-lg border border-gray-200 p-4 space-y-1">
            <div className="flex items-baseline gap-2">
              <span className="text-sm font-semibold text-gray-800">MANRS — participantes do programa de operadores</span>
              <a href="https://manrs.org/netops/participants/" target="_blank" rel="noopener noreferrer"
                className="text-xs text-primario-600 hover:underline">manrs.org</a>
            </div>
            <p className="text-xs text-gray-500">
              Lista pública de organizações participantes do programa de operadores de rede do MANRS. Os termos do MANRS permitem divulgar dados de outras redes só de forma
              agregada: o {SITE.nome} mostra apenas a participação de ASNs e usuários do Brasil por porte e UF (recortes com menos de 5 participantes ficam ocultos) e nunca
              lista organizações nem marca ASNs. Provided by the MANRS with support from the Global Cyber Alliance. O MANRS e a GCA não endossam este uso.
            </p>
          </div>

          <div className="rounded-lg border border-gray-200 p-4 space-y-1">
            <div className="flex items-baseline gap-2">
              <span className="text-sm font-semibold text-gray-800">RPKI — Routinator (NLnet Labs)</span>
              <a href="https://routinator.docs.nlnetlabs.nl/en/stable/" target="_blank" rel="noopener noreferrer"
                className="text-xs text-primario-600 hover:underline">routinator.docs.nlnetlabs.nl</a>
            </div>
            <p className="text-xs text-gray-500">
              ROAs (Route Origin Authorizations) coletados via Routinator, validador RPKI open
              source do NLnet Labs. Usados para indicar o estado de validação RPKI de cada
              prefixo: válido, inválido ou não coberto.
            </p>
          </div>

          <div className="rounded-lg border border-gray-200 p-4 space-y-1">
            <div className="flex items-baseline gap-2">
              <span className="text-sm font-semibold text-gray-800">DB-IP City Lite</span>
              <a href="https://db-ip.com" target="_blank" rel="noopener noreferrer"
                className="text-xs text-primario-600 hover:underline">IP Geolocation by DB-IP</a>
            </div>
            <p className="text-xs text-gray-500">
              Base de geolocalização de IPs do DB-IP, sob licença Creative Commons Atribuição 4.0 (com dados do GeoNames).
              Usada para associar o estado e o município a prefixos BR declarados no Registro.br, alimentando o mapa de
              prefixos. O {SITE.nome} não serve a posição de cada prefixo ou IP: só agregados por ASN e município.
            </p>
          </div>

          <div className="rounded-lg border border-gray-200 p-4 space-y-1">
            <div className="flex items-baseline gap-2">
              <span className="text-sm font-semibold text-gray-800">Anatel — Outorgas SCM</span>
              <a href="https://www.anatel.gov.br/dadosabertos/paineis_de_dados/outorga_e_licenciamento/" target="_blank" rel="noopener noreferrer"
                className="text-xs text-primario-600 hover:underline">anatel.gov.br</a>
            </div>
            <p className="text-xs text-gray-500">
              Base de prestadoras autorizadas a operar o Serviço de Comunicação Multimídia (SCM)
              publicada pela Anatel como dados abertos. Permite cruzar CNPJ de operadoras com
              ASes brasileiros, exibir situação da outorga e localizar geograficamente as
              prestadoras no mapa.
            </p>
          </div>

          <div className="rounded-lg border border-gray-200 p-4 space-y-1">
            <div className="flex items-baseline gap-2">
              <span className="text-sm font-semibold text-gray-800">Anatel — Outorgas SMP</span>
              <a href="https://www.anatel.gov.br/dadosabertos/paineis_de_dados/outorga_e_licenciamento/" target="_blank" rel="noopener noreferrer"
                className="text-xs text-primario-600 hover:underline">anatel.gov.br</a>
            </div>
            <p className="text-xs text-gray-500">
              Mesma base de outorgas da Anatel usada para SCM, filtrada pelo código de serviço
              010 — Serviço Móvel Pessoal. Universo pequeno (dezenas de CNPJs: grandes operadoras
              móveis, MVNOs e prestadoras de M2M), geolocalizado e cruzado com os ASes
              brasileiros identificados, da mesma forma que as outorgas SCM. Cruzado também com o
              dataset de <a href="https://dados.gov.br/dados/conjuntos-dados/empresas-credenciadas-de-rede-virtual-do-servico-movel-pessoal-telefonia-movel"
              target="_blank" rel="noopener noreferrer" className="text-primario-600 hover:underline">
              Empresas Credenciadas de Rede Virtual</a>, que identifica quais operadoras são MVNO
              puro (sem outorga própria, credenciadas a uma Prestadora Origem/host) — essas
              credenciadas passam a aparecer mesmo sem outorga SMP própria.
            </p>
          </div>

          <div className="rounded-lg border border-gray-200 p-4 space-y-1">
            <div className="flex items-baseline gap-2">
              <span className="text-sm font-semibold text-gray-800">Anatel — Outorgas STFC</span>
              <a href="https://www.anatel.gov.br/dadosabertos/paineis_de_dados/outorga_e_licenciamento/" target="_blank" rel="noopener noreferrer"
                className="text-xs text-primario-600 hover:underline">anatel.gov.br</a>
            </div>
            <p className="text-xs text-gray-500">
              Mesma base de outorgas usada para SCM/SMP, filtrada pelo código de serviço 171 —
              Serviço Telefônico Fixo Comutado. Universo bem maior que SMP (~1.700 CNPJs),
              incluindo pequenos provedores de VoIP e telefonia fixa, geolocalizado e cruzado
              com os ASes brasileiros identificados.
            </p>
          </div>

          <div className="rounded-lg border border-gray-200 p-4 space-y-1">
            <div className="flex items-baseline gap-2">
              <span className="text-sm font-semibold text-gray-800">Anatel — Outorgas SeAC</span>
              <a href="https://www.anatel.gov.br/dadosabertos/paineis_de_dados/outorga_e_licenciamento/" target="_blank" rel="noopener noreferrer"
                className="text-xs text-primario-600 hover:underline">anatel.gov.br</a>
            </div>
            <p className="text-xs text-gray-500">
              Mesma base de outorgas usada para SCM/SMP/STFC, filtrada pelo código de serviço
              750 — Serviço de Acesso Condicionado (nome oficial da TV por assinatura no Brasil,
              Lei 12.485/2011). ~1.400 CNPJs outorgados, geolocalizados e cruzados com os ASes
              brasileiros identificados.
            </p>
          </div>

          <div className="rounded-lg border border-gray-200 p-4 space-y-1">
            <div className="flex items-baseline gap-2">
              <span className="text-sm font-semibold text-gray-800">Anatel — Acessos declarados ao SICI</span>
              <a href="https://www.anatel.gov.br/dadosabertos/paineis_de_dados/acessos/" target="_blank" rel="noopener noreferrer"
                className="text-xs text-primario-600 hover:underline">anatel.gov.br/dadosabertos/.../acessos</a>
            </div>
            <p className="text-xs text-gray-500">
              O SICI (Sistema de Coleta de Informações) é a declaração mensal obrigatória de toda
              prestadora de telecomunicações à Anatel. O {SITE.software} baixa incrementalmente (via
              HTTP Range, sem repetir o download do ZIP completo a cada semana) as bases de
              acessos de banda larga fixa e de telefonia móvel: quantidade de acessos em serviço
              por CNPJ, município, tecnologia, meio de acesso, velocidade contratada (fixa) ou
              modalidade de cobrança e geração de rede — 2G a 5G (móvel), e tipo de cliente
              (PF/PJ). É dado mensal, então só é reprocessado quando a Anatel publica um mês novo.
            </p>
          </div>

          <div className="rounded-lg border border-gray-200 p-4 space-y-1">
            <div className="flex items-baseline gap-2">
              <span className="text-sm font-semibold text-gray-800">ITU BBmaps — Enlaces Terrestres</span>
              <a href="https://bbmaps.itu.int/geoserver/itu-geocatalogue/wfs" target="_blank" rel="noopener noreferrer"
                className="text-xs text-primario-600 hover:underline">bbmaps.itu.int</a>
            </div>
            <p className="text-xs text-gray-500">
              Transmission Networks Geocatalogue da União Internacional de Telecomunicações
              (ITU): enlaces terrestres de fibra óptica e micro-ondas, cobertura global, servidos
              via WFS sem autenticação. Usado como camada de fundo no mapa, exibindo a
              infraestrutura de transmissão terrestre por trás dos PTTs e ASes.
            </p>
          </div>

          <div className="rounded-lg border border-gray-200 p-4 space-y-1">
            <div className="flex items-baseline gap-2">
              <span className="text-sm font-semibold text-gray-800">TeleGeography — Submarine Cable Map</span>
              <a href="https://www.submarinecablemap.com" target="_blank" rel="noopener noreferrer"
                className="text-xs text-primario-600 hover:underline">submarinecablemap.com</a>
            </div>
            <p className="text-xs text-gray-500">
              Traçado e metadados (proprietários, ano de entrada em operação, comprimento) de
              cabos submarinos e seus pontos de aterrissagem, publicados pela TeleGeography sob
              licença Creative Commons Attribution-ShareAlike 4.0 (CC BY-SA 4.0). A atribuição é
              mantida visível na UI sempre que a camada é exibida no mapa.
            </p>
          </div>

          <div className="rounded-lg border border-gray-200 p-4 space-y-1">
            <div className="flex items-baseline gap-2">
              <span className="text-sm font-semibold text-gray-800">SIGEL/ANEEL — Linhas de Transmissão</span>
              <a href="https://sigel.aneel.gov.br" target="_blank" rel="noopener noreferrer"
                className="text-xs text-primario-600 hover:underline">sigel.aneel.gov.br</a>
            </div>
            <p className="text-xs text-gray-500">
              Sistema de Informações Georreferenciadas do Setor Elétrico da ANEEL: traçado das
              linhas de transmissão de alta tensão da rede básica nacional (operada pelo ONS),
              com tensão e extensão quando disponíveis. Relevante porque essas linhas
              frequentemente carregam cabos OPGW (fibra óptica no cabo para-raios) usados também
              para telecom — mas o SIGEL não indica quais linhas especificamente têm OPGW, então
              a camada representa só a malha de alta tensão, sem afirmar essa presença.
            </p>
          </div>

          <div className="rounded-lg border border-gray-200 p-4 space-y-1">
            <div className="flex items-baseline gap-2">
              <span className="text-sm font-semibold text-gray-800">IBGE — Malha Rodoviária (BC250)</span>
              <a href="https://www.ibge.gov.br/geociencias/cartas-e-mapas/bases-cartograficas-continuas.html"
                target="_blank" rel="noopener noreferrer"
                className="text-xs text-primario-600 hover:underline">ibge.gov.br</a>
            </div>
            <p className="text-xs text-gray-500">
              Base Cartográfica Contínua 1:250.000 (BC250) do IBGE: trechos de rodovia federais,
              estaduais, municipais e particulares, com jurisdição, revestimento e sigla (quando
              aplicável). Relevante porque faixas de domínio de rodovia frequentemente carregam
              cabos de fibra óptica lançados por concessionárias ou operadoras — mas o IBGE não
              indica quais trechos têm fibra, então a camada representa só a malha viária em si,
              sem afirmar essa presença. Camada opcional em /mapa, com filtro por jurisdição e
              pavimentação (não exibida por padrão, dado o volume de dados).
            </p>
          </div>

          <div className="rounded-lg border border-gray-200 p-4 space-y-1">
            <div className="flex items-baseline gap-2">
              <span className="text-sm font-semibold text-gray-800">BrasilAPI + OpenStreetMap Nominatim</span>
              <a href="https://brasilapi.com.br/docs#tag/CNPJ" target="_blank" rel="noopener noreferrer"
                className="text-xs text-primario-600 hover:underline">brasilapi.com.br/docs#CNPJ</a>
              <span className="text-xs text-gray-400">/</span>
              <a href="https://nominatim.openstreetmap.org/search" target="_blank" rel="noopener noreferrer"
                className="text-xs text-primario-600 hover:underline">nominatim.openstreetmap.org/search</a>
            </div>
            <p className="text-xs text-gray-500">
              Para ASes brasileiros com CNPJ identificado, a BrasilAPI fornece o endereço
              cadastral da organização. O Nominatim (geocodificador do OpenStreetMap) converte
              esse endereço em coordenadas geográficas, alimentando o mapa de ASes BR.
            </p>
          </div>

        </div>
      </section>

      <section className="space-y-3">
        <h2 className="text-base font-semibold text-gray-800">Por que os mapas estão com o sul para cima?</h2>
        <p className="text-sm text-gray-600 leading-relaxed">
          Não estão de ponta-cabeça — não existe "certo" ali. Norte para cima é uma convenção,
          não um fato físico: a Terra não tem topo. A orientação virou padrão a partir dos
          mapas europeus dos séculos 15 e 16, e o hábito se consolidou por repetição, não por
          necessidade técnica. Em maio de 2025 o IBGE publicou um{' '}
          <a href="https://agenciabrasil.ebc.com.br/geral/noticia/2025-05/ibge-lanca-mapa-mundi-invertido-com-sul-no-topo"
            target="_blank" rel="noopener noreferrer" className="text-primario-600 hover:underline">
            mapa-múndi oficial com o sul no topo
          </a>, justamente para tornar essa convenção visível. O {SITE.nome} segue a mesma lógica
          por padrão; um clique no ícone de bússola, no canto do mapa, alterna entre sul e norte
          para cima.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-base font-semibold text-gray-800">Tecnologia</h2>
        <p className="text-sm text-gray-600 leading-relaxed">
          O backend é escrito em <strong className="text-gray-700">Python</strong>, com um
          pipeline de coleta e processamento modular e uma API REST construída com{' '}
          <strong className="text-gray-700">FastAPI</strong>. Os dados são armazenados como
          arquivos JSON comprimidos — sem banco de dados relacional — o que simplifica o
          deployment e facilita a replicação do pipeline.
        </p>
        <p className="text-sm text-gray-600 leading-relaxed">
          O frontend é uma SPA em <strong className="text-gray-700">React</strong> com{' '}
          <strong className="text-gray-700">TypeScript</strong> e{' '}
          <strong className="text-gray-700">Tailwind CSS</strong>. As visualizações de grafos
          usam <strong className="text-gray-700">D3.js</strong>, os mapas Hilbert do espaço de
          endereçamento são renderizados em <strong className="text-gray-700">Canvas</strong>, e
          os mapas geográficos usam <strong className="text-gray-700">MapLibre GL</strong>. Toda a
          infraestrutura roda em contêineres <strong className="text-gray-700">Docker</strong>{' '}
          com <strong className="text-gray-700">nginx</strong> como proxy reverso.
        </p>
        <p className="text-sm text-gray-600 leading-relaxed">
          O projeto foi desenvolvido com uso intensivo de IA generativa —
          o assistente <strong className="text-gray-700">Claude</strong> (Anthropic) foi
          utilizado em praticamente todas as etapas: escrita de código, modelagem de dados,
          depuração, documentação e revisão de lógica. Isso acelerou significativamente o
          desenvolvimento, mas também significa que o código deve ser lido com atenção crítica.
        </p>
      </section>

      <section id="contato" className="space-y-3 scroll-mt-28">
        <h2 className="text-base font-semibold text-gray-800">Contato</h2>
        <p className="text-sm text-gray-600">
          Correções de dados, dúvidas e problemas de acessibilidade:{' '}
          <a href={`mailto:${SITE.contato}`} className="text-primario-600 hover:underline">{SITE.contato}</a>.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-base font-semibold text-gray-800">API</h2>
        <p className="text-sm text-gray-600">
          A API REST pública está disponível em{' '}
          <a
            href={`${SITE.url}/api/v1`}
            target="_blank"
            rel="noopener noreferrer"
            className="text-primario-600 hover:underline font-mono text-xs"
          >
            {SITE.url}/api/v1
          </a>
          . Documentação interativa (Swagger UI) em{' '}
          <a
            href="/api/v1/docs"
            target="_blank"
            rel="noopener noreferrer"
            className="text-primario-600 hover:underline font-mono text-xs"
          >
            /api/v1/docs
          </a>.
        </p>
        <div className="bg-gray-900 rounded-lg p-4 font-mono text-xs text-gray-300 space-y-1.5">
          <div className="text-gray-500"># Snapshots</div>
          <div><span className="text-ok-400">GET</span> /api/v1/brasil/snapshots</div>
          <div><span className="text-ok-400">GET</span> /api/v1/brasil/snapshots/{'{date}'}</div>
          <div><span className="text-ok-400">GET</span> /api/v1/snapshots <span className="text-gray-500">(com login)</span></div>
          <div className="text-gray-500 pt-1"># PTTs</div>
          <div><span className="text-ok-400">GET</span> /api/v1/ixps</div>
          <div><span className="text-ok-400">GET</span> /api/v1/ixps/{'{code}'}</div>
          <div><span className="text-ok-400">GET</span> /api/v1/ixps/{'{code}'}/peers</div>
          <div><span className="text-ok-400">GET</span> /api/v1/ixps/{'{code}'}/geo</div>
          <div><span className="text-ok-400">GET</span> /api/v1/external-ixps</div>
          <div><span className="text-ok-400">GET</span> /api/v1/external-ixps/{'{code}'}</div>
          <div className="text-gray-500 pt-1"># ASes</div>
          <div><span className="text-ok-400">GET</span> /api/v1/asns</div>
          <div><span className="text-ok-400">GET</span> /api/v1/asns/{'{asn}'}</div>
          <div><span className="text-ok-400">GET</span> /api/v1/asns/{'{asn}'}/geo</div>
          <div><span className="text-ok-400">GET</span> /api/v1/asns/names</div>
          <div className="text-gray-500 pt-1"># Prefixos</div>
          <div><span className="text-ok-400">GET</span> /api/v1/prefixes</div>
          <div><span className="text-ok-400">GET</span> /api/v1/prefixes/{'{prefix}'}</div>
          <div className="text-gray-500 pt-1"># Outorgas da Anatel (SCM, SMP, STFC, SeAC)</div>
          <div><span className="text-ok-400">GET</span> /api/v1/outorgas?servico=SCM,SMP</div>
          <div><span className="text-ok-400">GET</span> /api/v1/outorgas/{'{cnpj}'}</div>
          <div><span className="text-ok-400">GET</span> /api/v1/outorgas/stats?servico=SCM</div>
          <div><span className="text-ok-400">GET</span> /api/v1/outorgas/map?servico=SMP</div>
          <div className="text-gray-500 pt-1"># Perfis consolidados</div>
          <div><span className="text-ok-400">GET</span> /api/v1/operadoras/{'{cnpj}'}</div>
          <div><span className="text-ok-400">GET</span> /api/v1/municipios/{'{ibge}'}</div>
          <div><span className="text-ok-400">GET</span> /api/v1/ufs</div>
          <div><span className="text-ok-400">GET</span> /api/v1/ufs/{'{uf}'}</div>
          <div className="text-gray-500 pt-1"># Acessos declarados ao SICI (servico=fixa|movel)</div>
          <div><span className="text-ok-400">GET</span> /api/v1/acessos/stats?servico=movel</div>
          <div><span className="text-ok-400">GET</span> /api/v1/acessos/operadoras</div>
          <div><span className="text-ok-400">GET</span> /api/v1/acessos/municipios</div>
          <div className="text-gray-500 pt-1"># Infraestrutura física (mapa)</div>
          <div><span className="text-ok-400">GET</span> /api/v1/map/terrestrial-links</div>
          <div><span className="text-ok-400">GET</span> /api/v1/map/submarine-cables</div>
          <div><span className="text-ok-400">GET</span> /api/v1/map/submarine-landing-points</div>
          <div><span className="text-ok-400">GET</span> /api/v1/map/power-transmission-lines</div>
          <div><span className="text-ok-400">GET</span> /api/v1/map/rodovias</div>
          <div className="text-gray-500 pt-1"># RPKI</div>
          <div><span className="text-ok-400">GET</span> /api/v1/rpki/summary</div>
          <div className="text-gray-500 pt-1"># Espaço de endereçamento</div>
          <div><span className="text-ok-400">GET</span> /api/v1/hilbert/v6</div>
          <div><span className="text-ok-400">GET</span> /api/v1/hilbert/v4</div>
          <div><span className="text-ok-400">GET</span> /api/v1/hilbert/v4/detail</div>
          <div className="text-gray-500 pt-1"># CDNs</div>
          <div><span className="text-ok-400">GET</span> /api/v1/cdns/presence</div>
          <div className="text-gray-500 pt-1"># Query genérica</div>
          <div><span className="text-ok-400">GET</span> /api/v1/schema</div>
          <div><span className="text-primario-400">POST</span> /api/v1/query/{'{collection}'}</div>
          <div><span className="text-ok-400">GET</span> /api/v1/query/{'{collection}'}?corpo={'{JSON}'}</div>
          <div className="text-gray-500 pt-1"># Infra</div>
          <div><span className="text-ok-400">GET</span> /health</div>
        </div>
      </section>

    </div>
  )
}
