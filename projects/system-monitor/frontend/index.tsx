import { lazy } from 'react'
import type { ProjectFrontendModule } from '@shell/modules/types'
import './styles.css'

const HomeLabDashboard = lazy(() =>
  import('./pages/HomeLabDashboard').then((module) => ({
    default: module.HomeLabDashboard,
  })),
)
const ServicesPage = lazy(() =>
  import('./pages/ServicesPage').then((module) => ({
    default: module.ServicesPage,
  })),
)

const systemMonitorModule: ProjectFrontendModule = {
  routes: [
    { index: true, element: <HomeLabDashboard /> },
    { path: 'services', element: <ServicesPage /> },
  ],
}

export default systemMonitorModule
