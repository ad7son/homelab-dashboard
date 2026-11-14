import { Navigate, useLocation } from 'react-router-dom';
import type { RouteObject } from 'react-router-dom';
import { AppShell } from './components/AppShell';
import { ProjectOutlet } from './components/project/ProjectOutlet';
import { ProjectRegistryProvider } from './plugins/registry';
import type { ProjectDiscoveryResult } from './plugins/loader';
import { HomePage } from './pages/HomePage';
import { NotFoundPage } from './pages/NotFoundPage';
import { SettingsPage } from './pages/SettingsPage';

// 轉址元件只供本路由組裝使用，保留在同一檔案。
// oxlint-disable-next-line react/only-export-components
function LegacyRedirect({ fromBase, toBase }: { fromBase: string; toBase: string }) {
  const location = useLocation();
  const suffix = location.pathname.startsWith(fromBase)
    ? location.pathname.slice(fromBase.length) : '';
  const target = `${toBase}${suffix === '/' ? '' : suffix}${location.search}${location.hash}`;
  const current = `${location.pathname}${location.search}${location.hash}`;
  return target === current ? <NotFoundPage /> : <Navigate to={target} replace />;
}

/** 組裝路由但不建立瀏覽器實例，啟動與測試可使用相同路由定義。 */
export function createPlatformRoutes(discovery: ProjectDiscoveryResult): RouteObject[] {
  const projects = discovery.projects;
  const projectRoutes: RouteObject[] = projects.map((project) => ({
    path: `${project.manifest.routeBase.replace(/^\//, '')}/*`,
    element: <ProjectOutlet project={project} />,
  }));
  const legacyRoutes: RouteObject[] = projects.flatMap((project) =>
    project.manifest.legacyRouteBases.flatMap((legacyBase) => {
      const element = <LegacyRedirect fromBase={legacyBase} toBase={project.manifest.routeBase} />;
      const path = legacyBase.replace(/^\//, '');
      return [{ path, element }, { path: `${path}/*`, element }];
    }),
  );
  return [{
    path: '/',
    element: <ProjectRegistryProvider value={discovery}><AppShell /></ProjectRegistryProvider>,
    children: [
      { index: true, element: <HomePage /> },
      { path: 'settings', element: <SettingsPage /> },
      ...projectRoutes,
      ...legacyRoutes,
      { path: '*', element: <NotFoundPage /> },
    ],
  }];
}
