import { AliasPanorama } from './features/panorama/AliasPanorama'
import { StrictMode, lazy, Suspense } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Navigate, Routes, Route } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'

import { queryClient } from './services/queryClient'
import { carregarCamadasEstaticas } from './services/camadasEstaticas'
import { AppLayout } from './components/layout/AppLayout'
import { aplicarLeituraSalva } from './components/layout/LeituraConfortavel'
import { AuthProvider } from './auth/AuthContext'
import { ProtectedRoute } from './auth/ProtectedRoute'
import { LoginModal } from './components/LoginModal'
import { Login } from './pages/Login'
import './index.css'

// Hashes das camadas estáticas dos mapas (cabos, enlaces, linhas): pedido uma vez, antes de qualquer mapa montar.
void carregarCamadasEstaticas()

// Lazy imports — cada página vira um chunk separado, carregado só quando necessário.
const HomePage       = lazy(() => import('./pages/HomePage').then(m => ({ default: m.HomePage })))
const Dashboard      = lazy(() => import('./pages/Dashboard').then(m => ({ default: m.Dashboard })))
const OperadorasPage = lazy(() => import('./pages/OperadorasPage').then(m => ({ default: m.OperadorasPage })))
const RedirecionaServico = lazy(() => import('./pages/OperadorasPage').then(m => ({ default: m.RedirecionaServico })))
const EstadosPage    = lazy(() => import('./pages/EstadosPage').then(m => ({ default: m.EstadosPage })))
const UFPage         = lazy(() => import('./pages/UFPage').then(m => ({ default: m.UFPage })))
const PrefixoPage    = lazy(() => import('./pages/PrefixoPage').then(m => ({ default: m.PrefixoPage })))
const FontesPage     = lazy(() => import('./pages/FontesPage').then(m => ({ default: m.FontesPage })))
const DadosPage      = lazy(() => import('./pages/DadosPage').then(m => ({ default: m.DadosPage })))
const ExplorarPage   = lazy(() => import('./pages/ExplorarPage').then(m => ({ default: m.ExplorarPage })))
const IXPPage        = lazy(() => import('./pages/IXPPage').then(m => ({ default: m.IXPPage })))
const ASNPage        = lazy(() => import('./pages/ASNPage').then(m => ({ default: m.ASNPage })))
const FacilitiesPage = lazy(() => import('./pages/FacilitiesPage').then(m => ({ default: m.FacilitiesPage })))
const FacilityPage   = lazy(() => import('./pages/FacilityPage').then(m => ({ default: m.FacilityPage })))
const ExternalIXPPage = lazy(() => import('./pages/ExternalIXPPage').then(m => ({ default: m.ExternalIXPPage })))
const CDNPage        = lazy(() => import('./pages/CDNPage').then(m => ({ default: m.CDNPage })))
const CDNCapPage     = lazy(() => import('./pages/CDNCapPage').then(m => ({ default: m.CDNCapPage })))
const RankingsPage    = lazy(() => import('./pages/RankingsPage').then(m => ({ default: m.RankingsPage })))
const CommunitiesPage = lazy(() => import('./pages/CommunitiesPage').then(m => ({ default: m.CommunitiesPage })))
const SegurancaRoteamentoPage = lazy(() => import('./pages/SegurancaRoteamentoPage').then(m => ({ default: m.SegurancaRoteamentoPage })))
const QualidadePage = lazy(() => import('./pages/QualidadePage').then(m => ({ default: m.QualidadePage })))
const RegulatorioPage = lazy(() => import('./pages/RegulatorioPage').then(m => ({ default: m.RegulatorioPage })))
const MercadoIpv4Page = lazy(() => import('./pages/MercadoIpv4Page').then(m => ({ default: m.MercadoIpv4Page })))
const UsoInternetPage = lazy(() => import('./pages/UsoInternetPage').then(m => ({ default: m.UsoInternetPage })))
const MudancasPage    = lazy(() => import('./pages/MudancasPage').then(m => ({ default: m.MudancasPage })))
const PanoramaTecnico = lazy(() => import('./pages/PanoramaTecnico').then(m => ({ default: m.PanoramaTecnico })))
const PanoramaMercado = lazy(() => import('./pages/PanoramaMercado').then(m => ({ default: m.PanoramaMercado })))
const PanoramaIpv6    = lazy(() => import('./pages/PanoramaIpv6').then(m => ({ default: m.PanoramaIpv6 })))
const Estatisticas   = lazy(() => import('./pages/Estatisticas').then(m => ({ default: m.Estatisticas })))
const Comparar       = lazy(() => import('./pages/Comparar').then(m => ({ default: m.Comparar })))
const Snapshots      = lazy(() => import('./pages/Snapshots').then(m => ({ default: m.Snapshots })))
const Sobre          = lazy(() => import('./pages/Sobre').then(m => ({ default: m.Sobre })))
const Localizador    = lazy(() => import('./pages/Localizador').then(m => ({ default: m.Localizador })))
const IXPs           = lazy(() => import('./pages/IXPs').then(m => ({ default: m.IXPs })))
const ASes           = lazy(() => import('./pages/ASes').then(m => ({ default: m.ASes })))
const Mapa           = lazy(() => import('./pages/Mapa').then(m => ({ default: m.Mapa })))
const Privacidade    = lazy(() => import('./pages/Privacidade').then(m => ({ default: m.Privacidade })))
const RelatorioPage = lazy(() => import('./pages/RelatorioPage').then(m => ({ default: m.RelatorioPage })))
const GrupoPage      = lazy(() => import('./pages/GrupoPage').then(m => ({ default: m.GrupoPage })))
const MunicipiosPage = lazy(() => import('./pages/MunicipiosPage').then(m => ({ default: m.MunicipiosPage })))
const Perfil         = lazy(() => import('./pages/Perfil').then(m => ({ default: m.Perfil })))
const UsoAceitavel   = lazy(() => import('./pages/UsoAceitavel').then(m => ({ default: m.UsoAceitavel })))
const MapaDoSite     = lazy(() => import('./pages/MapaDoSite').then(m => ({ default: m.MapaDoSite })))
const Acessibilidade = lazy(() => import('./pages/Acessibilidade').then(m => ({ default: m.Acessibilidade })))
const GruposPage     = lazy(() => import('./pages/GruposPage').then(m => ({ default: m.GruposPage })))
const OperadoraPage  = lazy(() => import('./pages/OperadoraPage').then(m => ({ default: m.OperadoraPage })))
const MunicipioPage  = lazy(() => import('./pages/MunicipioPage').then(m => ({ default: m.MunicipioPage })))
const BGP            = lazy(() => import('./pages/BGP').then(m => ({ default: m.BGP })))
function PageLoader() {
  return (
    <div className="flex justify-center items-center h-64">
      <span className="text-gray-400 text-sm">Carregando…</span>
    </div>
  )
}

function P({ children }: { children: React.ReactNode }) {
  return <ProtectedRoute>{children}</ProtectedRoute>
}

aplicarLeituraSalva()
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <LoginModal />
          <Suspense fallback={<PageLoader />}>
            <Routes>
              {/* Página de login — fora do AppLayout */}
              <Route path="login" element={<Login />} />

              <Route element={<AppLayout />}>
                {/* Rotas públicas */}
                <Route index element={<HomePage />} />
                <Route path="inicio-classico" element={<Navigate to="/" replace />} />{/* alias de rota: redireciona para a home */}
                <Route path="panorama/tecnico" element={<P><PanoramaTecnico /></P>} />
                <Route path="panorama/mercado" element={<P><PanoramaMercado /></P>} />
                <Route path="panorama/ipv6" element={<P><PanoramaIpv6 /></P>} />
                <Route path="visao-geral" element={<AliasPanorama de="visao-geral" antiga={<P><Dashboard /></P>} />} />
                <Route path="fontes" element={<FontesPage />} />
                <Route path="dados" element={<DadosPage />} />
                <Route path="sobre" element={<Sobre />} />
                <Route path="privacidade" element={<Privacidade />} />
                <Route path="uso-aceitavel" element={<UsoAceitavel />} />
                <Route path="acessibilidade" element={<Acessibilidade />} />
                <Route path="mapa-do-site" element={<MapaDoSite />} />
                <Route path="perfil" element={<Perfil />} />
                <Route path="municipios" element={<P><MunicipiosPage /></P>} />
                <Route path="grupo/:id" element={<P><GrupoPage /></P>} />
                <Route path="relatorio/:tipo/:id" element={<P><RelatorioPage /></P>} />
                <Route path="ixps" element={<IXPs />} />
                <Route path="ases" element={<ASes />} />
                <Route path="scms" element={<RedirecionaServico servico="scm" />} />
                <Route path="smps" element={<RedirecionaServico servico="smp" />} />
                <Route path="stfcs" element={<RedirecionaServico servico="stfc" />} />
                <Route path="seacs" element={<RedirecionaServico servico="seac" />} />
                <Route path="operadoras" element={<OperadorasPage />} />
                <Route path="grupos" element={<GruposPage />} />
                <Route path="operadora/:cnpj" element={<P><OperadoraPage /></P>} />
                <Route path="prefixo/*" element={<P><PrefixoPage /></P>} />
                <Route path="explorar" element={<P><ExplorarPage /></P>} />
                <Route path="estados" element={<EstadosPage />} />
                <Route path="uf/:uf" element={<P><UFPage /></P>} />
                <Route path="municipio/:ibge" element={<P><MunicipioPage /></P>} />

                {/* Rotas protegidas */}
                <Route path="ixp/:code" element={<P><IXPPage /></P>} />
                <Route path="ixp-externo/:code" element={<P><ExternalIXPPage /></P>} />
                <Route path="instalacoes" element={<P><FacilitiesPage /></P>} />
                <Route path="instalacao/:id" element={<P><FacilityPage /></P>} />
                <Route path="asn/:asn" element={<P><ASNPage /></P>} />
                <Route path="cdns" element={<P><CDNPage /></P>} />
                <Route path="cdncap/:slug" element={<P><CDNCapPage /></P>} />
                <Route path="estatisticas" element={<AliasPanorama de="estatisticas" antiga={<P><Estatisticas /></P>} />} />
                <Route path="rankings" element={<P><RankingsPage /></P>} />
                <Route path="communities" element={<P><CommunitiesPage /></P>} />
                <Route path="uso-da-internet" element={<P><UsoInternetPage /></P>} />
                <Route path="mercado-ipv4" element={<P><MercadoIpv4Page /></P>} />
                <Route path="regulatorio" element={<P><RegulatorioPage /></P>} />
                <Route path="qualidade" element={<P><QualidadePage /></P>} />
                <Route path="seguranca-de-roteamento" element={<P><SegurancaRoteamentoPage /></P>} />
                <Route path="mudancas" element={<P><MudancasPage /></P>} />
                <Route path="comparar" element={<P><Comparar /></P>} />
                <Route path="snapshots" element={<P><Snapshots /></P>} />
                <Route path="localizador" element={<P><Localizador /></P>} />
                <Route path="mapa" element={<P><Mapa /></P>} />
                <Route path="bgp"  element={<P><BGP /></P>} />

                <Route
                  path="*"
                  element={
                    <div className="text-center py-24">
                      <div className="text-4xl mb-3">404</div>
                      <p className="text-gray-500 text-sm">Página não encontrada.</p>
                    </div>
                  }
                />
              </Route>
            </Routes>
          </Suspense>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
)
