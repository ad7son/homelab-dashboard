import { lazy } from 'react'
import type { ProjectFrontendModule } from '@shell/modules/types'
import './styles.css'

const HomeLabDashboard = lazy(() =>
  import('./pages/HomeLabDashboard').then((module) => ({
    default: module.HomeLabDashboard,
  })),
)

const systemMonitorModule: ProjectFrontendModule = {
  routes: [
    { index: true, element: <HomeLabDashboard /> },
  ],
}

export default systemMonitorModule
