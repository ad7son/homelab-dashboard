import { lazy } from 'react'
import type { ProjectFrontendModule } from '@shell/plugins/loader'
import './styles.css'

const OverviewPage = lazy(() =>
  import('./pages/OverviewPage').then((module) => ({
    default: module.OverviewPage,
  })),
)

const ProjectHealthPage = lazy(() =>
  import('./pages/ProjectHealthPage').then((module) => ({ default: module.ProjectHealthPage })),
)

const systemMonitorModule: ProjectFrontendModule = {
  routes: [
    { index: true, element: <OverviewPage /> },
    { path: 'health/:projectId', element: <ProjectHealthPage /> },
  ],
}

export default systemMonitorModule
