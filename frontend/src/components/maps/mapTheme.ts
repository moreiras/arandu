// Tema compartilhado pelos 7 mapas do frontend — basemap, paleta de cores e
// controles canônicos. Extraído porque os 7 arquivos duplicavam praticamente
// o mesmo objeto de estilo/paleta, e isso deixava divergir sem querer (cores
// diferentes para o mesmo conceito, contorno de estado com opacidades
// diferentes, controles em cantos diferentes).
import * as maplibregl from 'maplibre-gl'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url'
import { Protocol } from 'pmtiles'
import { urlCamada } from '../../services/camadasEstaticas'
import { lembrarOrientacao, orientacaoPreferida } from '../../lib/orientacaoMapa'
import { DBIP_ATRIBUICAO_HTML } from '../../lib/atribuicoes'

// Registra o protocolo pmtiles:// uma única vez — o basemap vetorial
// auto-hospedado é lido diretamente de um arquivo .pmtiles estático via
// Range requests (ver docker/nginx-frontend.conf e scripts/build-basemap-tiles.sh),
// sem precisar de um servidor de tiles dedicado.
// O MapLibre 6 monta a URL do WebWorker em tempo de execução, e o Vite não a enxerga: sem isto o arquivo não entra no build e a
// página recebe o index.html no lugar do worker. Todo mapa importa este módulo antes de criar o Map.
maplibregl.setWorkerUrl(workerUrl)
maplibregl.addProtocol('pmtiles', new Protocol().tile)

export const MAP_COLORS = {
  // IPv6/IPv4 — "forte" (próprio/direto) vs "fraco" (cliente/indireto/fora)
  v4Strong: '#1d4ed8', // blue-700
  v4Weak: '#60a5fa', // blue-400
  v6Strong: '#92400e', // amber-900
  v6Weak: '#f97316', // orange-500

  // Prefixos por origem (BR vs não-BR)
  prefixV4Br: '#2563eb', // blue-600
  prefixV6Br: '#f97316', // orange-500
  nonBr: '#64748b', // slate-500

  // Visibilidade de ASN na tabela global
  visibilityBoth: '#16a34a', // green-600
  visibilityV4Only: '#991b1b', // red-800
  visibilityV6Only: '#f97316', // orange-500
  visibilityNone: '#9ca3af', // gray-400

  // PIX / PTT físico
  pixFill: '#fbbf24', // amber-400
  pixStroke: '#92400e', // amber-900

  // Papel do AS num IXP
  asMember: '#1e3a8a', // blue-900
  asDirect: '#14532d', // green-900
  asOrigin: '#6d28d9', // violet-700

  // Outorga SCM
  scmWithoutAsn: '#a855f7', // purple-500
  scmWithAsn: '#64748b', // slate-500

  // Usuários declarados ao SICI (Anatel), por município
  sici: '#dc2626', // red-600

  // Infraestrutura física de fundo (ITU + TeleGeography).
  // Violeta claro para o enlace terrestre; nos cabos submarinos, verde-mar destaca os que
  // conectam o Brasil e um cinza-azulado médio deixa os demais (e os pontos de chegada) como contexto. Os dois têm de se
  // distinguir entre si e do mar do mapa de fundo (o marinho e o cinza 70% da 2.0.9 ficaram
  // pesados e parecidos).
  terrestrialLink: '#c4b5fd', // violet-300
  submarineCableOther: '#607B8B', // cinza 50% (cinza-azulado) — cabos submarinos sem landing point no Brasil
  erbs: '#0d9488', // teal-600 — células de estações do SMP licenciadas
  submarineCableBr: '#20B2AA', // verde-mar (light sea green) — cabos com landing point no Brasil

  // Linhas de transmissão de alta tensão (SIGEL/ANEEL).
  // Violeta mais saturado que terrestrialLink (violet-300) para não se confundir
  // com o enlace terrestre da ITU quando as duas camadas de fundo aparecem juntas.
  powerLine: '#7c3aed', // violet-600

  // Malha rodoviária (IBGE/BC250). Camada opcional só
  // em /mapa (nunca no fundo compartilhado, dado o volume — 124 mil feições),
  // tom terroso para não colidir com as outras camadas de infra física.
  road: '#c2410c', // orange-700
  // Rodovias estaduais — mesmo tom, mais claro, para distinguir das federais
  // quando as duas camadas estão ligadas.
  roadState: '#fb923c', // orange-400

  cnpj: '#0891b2', // cyan-600, usado em texto de tooltip

  // Basemap vetorial: terra/água/rótulos de país e cidade — terra quase
  // branca (contraste mínimo, deixa as camadas de dados serem o foco) e
  // água num azul-acinzentado mais escuro pra continuar legível ao lado
  // da terra clara. Só o preenchimento, sem mexer nos contornos
  // (STATE_OUTLINE_PAINT).
  mapLand: '#fafaf8', // quase branco
  mapWater: '#cbd5e1', // slate-300, mais escuro que a terra
  mapLabel: '#334155', // slate-700

  // Território brasileiro — verde bem claro, só o suficiente pra distinguir
  // do resto dos continentes (mapLand) sem competir com as camadas de dado.
  brazilLand: '#eef6ea',
} as const

// Contorno de fronteira (país) e de estado — usado tanto no basemap
// compartilhado (boundary-country, abaixo) quanto nos 9 mapas que desenham
// os estados a partir de br-states.geojson (ver BR_STATES_URL nesses
// arquivos). Um pouco mais forte que o padrão do OpenMapTiles pra ficar
// legível mesmo com as camadas de dado por cima — pedido do usuário.
export const STATE_OUTLINE_PAINT = {
  'line-color': '#475569', // slate-600
  'line-width': 0.9,
  'line-opacity': 0.7,
} as const

/** Raio-padrão de marcador pontual (ASNs no mapa da home, outorgas SCM, etc.):
 *  pequeno e discreto em zoom nacional, cresce ao aproximar. Reused para manter
 *  os pontos de todos os mapas com o mesmo peso visual. */
export const MARKER_RADIUS_EXPR: maplibregl.ExpressionSpecification = [
  'interpolate', ['linear'], ['zoom'], 3, 3, 7, 5, 12, 9,
]

/** Opacidade-padrão do mesmo marcador — translúcido o bastante pra sobreposições
 *  não virarem uma mancha sólida em áreas densas (grande SP, por exemplo). */
export const MARKER_OPACITY = 0.75

export const MAP_DEFAULT_CENTER: [number, number] = [-52, -14]
export const MAP_DEFAULT_ZOOM = 3.5
// Sul para cima: com basemap vetorial os rótulos (nossos e do basemap) ficam
// upright independente da rotação (text-rotation-alignment viewport por padrão),
// então girar 180° não inverte texto nenhum — só a geografia.
export const MAP_DEFAULT_BEARING = 180
/** Ângulo inicial dos mapas: o padrão (sul para cima) ou a escolha lembrada de quem usa. */
export const bearingInicial = (): number => orientacaoPreferida()

/** Basemap vetorial auto-hospedado (PMTiles/OpenMapTiles) + globo, canônico
 * para todos os mapas. Style mínimo, propositalmente: só terra/água,
 * fronteiras de país e rótulos de país/cidade — as camadas de dados (SCM,
 * ASN, IXP, etc.) são todas nossas, feitas à parte em cada mapa, então não
 * precisamos do restante de um style completo (ruas, edifícios, POIs).
 * "current.pmtiles" é o ponteiro pra versão vigente, promovido só depois de
 * validado (ver scripts/validate-basemap-tiles.sh) — nunca aponta pra uma
 * versão que não passou no smoke test. */
export function createBaseMapStyle(): maplibregl.StyleSpecification {
  const tilesUrl = new URL('/tiles/current.pmtiles', window.location.origin).href
  return {
    version: 8,
    projection: { type: 'globe' },
    glyphs: '/tiles/_assets/fonts/{fontstack}/{range}.pbf',
    sources: {
      basemap: {
        type: 'vector',
        url: `pmtiles://${tilesUrl}`,
        // Exigido pela licença do schema OpenMapTiles usado pelo Planetiler
        // (CC-BY) além do crédito de dados do OpenStreetMap (ODbL).
        attribution:
          '© <a href="https://www.openmaptiles.org/">OpenMapTiles</a> © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      },
      // A camada 'place' do tileset (acima) só tem dado vindo do OSM, que é
      // recortado pra América do Sul (ver scripts/build-basemap-tiles.sh) —
      // fora dali não existe NENHUM rótulo de país/cidade, mesmo cobrindo o
      // mundo todo com --bounds pro resto (água/terra/fronteira, que vêm de
      // fontes globais do próprio Planetiler). Rótulos de país/cidade em
      // qualquer lugar do globo vêm de um arquivo próprio nosso (Natural
      // Earth 1:110m, domínio público, ~60 KB), independente do tileset.
      'world-places': { type: 'geojson', data: '/world-places.geojson' },
      // Contorno dos estados (IBGE) reaproveitado aqui só pra pintar o
      // território do Brasil com uma cor de fundo distinta — o contorno em
      // si (linha) continua sendo desenhado por cada mapa via BR_STATES_URL
      // (ver mapTheme.ts STATE_OUTLINE_PAINT), pra não duplicar a camada.
      'brazil-land': { type: 'geojson', data: '/br-states.geojson' },
      // Capitais, cidades-sede de PTT do IX.br e metrópoles regionais —
      // rótulos próprios (Natural Earth não tem granularidade suficiente
      // dentro do Brasil; ver world-places.geojson, que teve Brasília/Rio/SP
      // removidos daqui pra não duplicar com place-capital abaixo).
      'br-places': { type: 'geojson', data: '/br-places.geojson' },
      // Infraestrutura física de fundo — servida pela própria API (dado dinâmico,
      // coletado semanalmente junto do snapshot), não um arquivo estático do frontend.
      // Ver api/routes/map.py.
      'infra-terrestrial': { type: 'geojson', data: urlCamada('itu_transmission', '/api/v1/map/terrestrial-links') },
      'infra-submarine-cables': { type: 'geojson', data: urlCamada('submarine_cables', '/api/v1/map/submarine-cables') },
      'infra-submarine-landing-points': { type: 'geojson', data: urlCamada('submarine_landing_points', '/api/v1/map/submarine-landing-points') },
      'infra-power-lines': { type: 'geojson', data: urlCamada('power_transmission_lines', '/api/v1/map/power-transmission-lines') },
    },
    layers: [
      { id: 'background', type: 'background', paint: { 'background-color': MAP_COLORS.mapLand } },
      // Fundo do território brasileiro, levemente esverdeado — antes da água
      // pra que rios/lagos (camada 'water' abaixo) continuem aparecendo por
      // cima, na cor de água padrão.
      {
        id: 'brazil-land-fill', type: 'fill', source: 'brazil-land',
        paint: { 'fill-color': MAP_COLORS.brazilLand },
      },
      {
        id: 'water', type: 'fill', source: 'basemap', 'source-layer': 'water',
        paint: { 'fill-color': MAP_COLORS.mapWater },
      },
      {
        id: 'boundary-country', type: 'line', source: 'basemap', 'source-layer': 'boundary',
        // 'has' antes do '<=' evita comparar contra null quando a feature não
        // tem admin_level (ex.: linhas de fronteira marítima/disputada) — sem
        // essa guarda, o worker de tiles lança "Expected number, found null"
        // e o tile inteiro (água/terra/rótulos) some do mapa nesse zoom.
        filter: ['all', ['has', 'admin_level'], ['<=', ['get', 'admin_level'], 2]],
        paint: STATE_OUTLINE_PAINT,
      },
      // Enlaces terrestres (ITU) — camada de fundo discreta, sem interação por padrão.
      // Só a categoria "Operacional" é exibida; planejado/proposto/em construção fica
      // disponível na propriedade `status` para quem quiser filtrar, mas não é exibido
      // por padrão (evita sugerir infraestrutura que ainda não existe).
      {
        id: 'infra-terrestrial-links', type: 'line', source: 'infra-terrestrial',
        filter: ['==', ['get', 'status'], 'Operational'],
        // round: junções e pontas sem quina visível — o traçado já vem em muitos
        // segmentos curtos, e um miter-join (padrão) marcaria cada vértice.
        layout: { 'line-join': 'round', 'line-cap': 'round' },
        paint: {
          'line-color': MAP_COLORS.terrestrialLink,
          'line-width': 0.7,
          'line-opacity': 0.55,
        },
      },
      // Cabos submarinos (TeleGeography, CC BY-SA 4.0) — destacados mesmo em zoom
      // afastado, ao contrário do terrestre. Azul claro para os que tocam o Brasil
      // (calculado na publicação, ver build_infra_maps em snapshot_builder.py),
      // violeta claro para os demais — mesma cor do enlace terrestre, por ser
      // também "contexto". A geometria já vem suavizada por spline Catmull-Rom
      // na publicação; round join/cap evita qualquer quina residual nas junções.
      {
        id: 'infra-submarine-cables', type: 'line', source: 'infra-submarine-cables',
        layout: { 'line-join': 'round', 'line-cap': 'round' },
        paint: {
          'line-color': [
            'case', ['==', ['get', 'touches_brazil'], true],
            MAP_COLORS.submarineCableBr,
            MAP_COLORS.submarineCableOther,
          ],
          'line-width': 1.5,
          'line-opacity': 0.85,
        },
      },
      {
        id: 'infra-submarine-landing-points', type: 'circle', source: 'infra-submarine-landing-points',
        paint: {
          'circle-radius': 2.5,
          'circle-color': MAP_COLORS.submarineCableOther,   // pontos de chegada no cinza dos demais cabos
          'circle-opacity': 0.85,
        },
      },
      // Linhas de transmissão de alta tensão (SIGEL/ANEEL) — camada de fundo discreta,
      // mesmo tratamento do enlace terrestre da ITU (sem interação por padrão). Contexto
      // de possível uso para OPGW, nunca uma afirmação de que a linha o carrega: o SIGEL
      // não informa quais linhas têm OPGW (dado comercial das transmissoras).
      {
        id: 'infra-power-lines', type: 'line', source: 'infra-power-lines',
        layout: { 'line-join': 'round', 'line-cap': 'round' },
        paint: {
          'line-color': MAP_COLORS.powerLine,
          'line-width': 0.6,
          'line-opacity': 0.4,
        },
      },
      {
        id: 'place-country', type: 'symbol', source: 'world-places',
        filter: ['==', ['get', 'class'], 'country'],
        minzoom: 0,
        layout: {
          'text-field': ['get', 'name_pt'],
          'text-font': ['Noto Sans Regular'],
          'text-size': 12,
          'text-transform': 'uppercase',
          'text-letter-spacing': 0.05,
        },
        paint: {
          'text-color': MAP_COLORS.mapLabel,
          'text-halo-color': '#ffffff',
          'text-halo-width': 1.2,
        },
      },
      // Capitais (estaduais + Brasília), cidades-sede de PTT do IX.br e
      // metrópoles regionais — nessa ordem de prioridade de colisão (a
      // primeira camada listada "ganha" o espaço quando os rótulos disputam
      // o mesmo lugar na tela). minzoom crescente evita poluir o mapa em
      // zoom nacional: capitais aparecem cedo, metrópoles só ao aproximar.
      {
        id: 'place-capital', type: 'symbol', source: 'br-places',
        filter: ['==', ['get', 'kind'], 'capital'],
        minzoom: 2,
        layout: {
          'text-field': ['get', 'name'],
          'text-font': ['Noto Sans Regular'],
          'text-size': ['case', ['==', ['get', 'national'], true], 12, 10.5],
        },
        paint: {
          'text-color': MAP_COLORS.mapLabel,
          'text-halo-color': '#ffffff',
          'text-halo-width': 1.3,
        },
      },
      {
        id: 'place-ptt', type: 'symbol', source: 'br-places',
        filter: ['==', ['get', 'kind'], 'ptt'],
        minzoom: 4,
        layout: {
          'text-field': ['get', 'name'],
          'text-font': ['Noto Sans Regular'],
          'text-size': 9.5,
        },
        paint: {
          'text-color': MAP_COLORS.mapLabel,
          'text-halo-color': '#ffffff',
          'text-halo-width': 1.2,
        },
      },
      {
        id: 'place-metro', type: 'symbol', source: 'br-places',
        filter: ['==', ['get', 'kind'], 'metro'],
        minzoom: 5,
        layout: {
          'text-field': ['get', 'name'],
          'text-font': ['Noto Sans Regular'],
          'text-size': 9,
        },
        paint: {
          'text-color': MAP_COLORS.mapLabel,
          'text-halo-color': '#ffffff',
          'text-halo-width': 1.1,
        },
      },
      {
        id: 'place-city', type: 'symbol', source: 'world-places',
        filter: ['==', ['get', 'class'], 'city'],
        minzoom: 2,
        layout: {
          'text-field': ['get', 'name_pt'],
          'text-font': ['Noto Sans Regular'],
          'text-size': 10,
          'symbol-sort-key': ['get', 'rank'],
        },
        paint: {
          'text-color': MAP_COLORS.mapLabel,
          'text-halo-color': '#ffffff',
          'text-halo-width': 1.2,
        },
      },
    ],
  }
}

/** Botão de bússola que alterna entre norte (0°) e sul (`MAP_DEFAULT_BEARING`)
 * a cada clique — diferente do compassClickHandler padrão do MapLibre, que só
 * reseta pra norte (então um segundo clique não fazia nada). Reaproveita as
 * classes CSS do NavigationControl (`maplibregl-ctrl-compass`/`-icon`) pra
 * ficar visualmente idêntico ao controle nativo. */
export class BearingToggleControl implements maplibregl.IControl {
  private map?: maplibregl.Map
  private icon!: HTMLSpanElement

  onAdd(map: maplibregl.Map): HTMLElement {
    this.map = map
    const container = document.createElement('div')
    container.className = 'maplibregl-ctrl maplibregl-ctrl-group'
    const button = document.createElement('button')
    button.type = 'button'
    button.className = 'maplibregl-ctrl-compass'
    button.setAttribute('aria-label', 'Girar mapa (norte/sul)')
    button.title = 'Girar mapa (norte/sul)'
    button.addEventListener('click', this.onClick)
    this.icon = document.createElement('span')
    this.icon.className = 'maplibregl-ctrl-icon'
    this.icon.setAttribute('aria-hidden', 'true')
    button.appendChild(this.icon)
    container.appendChild(button)
    map.on('rotate', this.updateIcon)
    this.updateIcon()
    return container
  }

  onRemove(): void {
    this.map?.off('rotate', this.updateIcon)
    this.map = undefined
  }

  private onClick = () => {
    if (!this.map) return
    const bearing = ((this.map.getBearing() % 360) + 360) % 360
    // Alterna pro cardeal mais distante do atual — clique sempre "vira" pro
    // outro lado, mesmo que o usuário tenha girado o mapa manualmente antes.
    const target = bearing > 90 && bearing < 270 ? 0 : MAP_DEFAULT_BEARING
    lembrarOrientacao(target)
    this.map.easeTo({ bearing: target, duration: 300 })
  }

  private updateIcon = () => {
    if (this.map) this.icon.style.transform = `rotate(${this.map.getBearing()}deg)`
  }
}

/** NavigationControl (zoom, top-right) + bússola norte/sul + AttributionControl
 * (compacto, bottom-right) — o mapa ainda precisa ser criado com
 * `attributionControl: false`, já que isso é opção do construtor do `Map`,
 * não dá pra centralizar aqui. `dbip`: o mapa exibe ou usa a geolocalização do DB-IP, cuja licença pede o link na página
 * (`lib/atribuicoes.ts`). */
export function addStandardControls(map: maplibregl.Map, opcoes: { dbip?: boolean } = {}): void {
  map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right')
  map.addControl(new BearingToggleControl(), 'top-right')
  map.addControl(new maplibregl.AttributionControl({ compact: true, customAttribution: opcoes.dbip ? DBIP_ATRIBUICAO_HTML : undefined }), 'bottom-right')
}
