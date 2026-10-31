import { lazy } from 'react'
import type { ProjectFrontendModule } from '@shell/modules/types'
import './styles.css'

const ProjectShowcasePage = lazy(() =>
  import('./pages/ProjectShowcasePage').then((module) => ({
    default: module.ProjectShowcasePage,
  })),
)

const projectShowcaseModule: ProjectFrontendModule = {
  routes: [{ index: true, element: <ProjectShowcasePage /> }],
}

export default projectShowcaseModule
