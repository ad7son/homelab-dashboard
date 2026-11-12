import { lazy } from 'react'
import type { ProjectFrontendModule } from '@shell/modules/types'
import './styles.css'

const HomeLabDashboard = lazy(() =>
  import('./pages/HomeLabDashboard').then((module) => ({
    default: module.HomeLabDashboard,
  })),
)

const ProjectHealthPage = lazy(() =>
  import('./pages/ProjectHealthPage').then((module) => ({ default: module.ProjectHealthPage })),
)

const systemMonitorModule: ProjectFrontendModule = {
  routes: [
    { index: true, element: <HomeLabDashboard /> },
    { path: 'health/:projectId', element: <ProjectHealthPage /> },
  ],
}

export default systemMonitorModule
