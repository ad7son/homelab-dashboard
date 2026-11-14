import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { RouterProvider } from 'react-router-dom'
import './styles.css'
import { createBrowserRouter } from 'react-router-dom'
import { createPlatformRoutes } from './router'
import { loadDiscoveredProjects } from './plugins/loader'

const router = createBrowserRouter(createPlatformRoutes(loadDiscoveredProjects()))

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
)
