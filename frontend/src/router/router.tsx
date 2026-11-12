import { lazy, Suspense, useMemo, useState } from 'react';
import { Navigate, createBrowserRouter, useLocation, useRoutes } from 'react-router-dom';
import type { RouteObject } from 'react-router-dom';
import { ProjectErrorBoundary } from '../components/layout/ProjectErrorBoundary';
import { AppShell } from '../components/layout/AppShell';
import {
  buildProjectNavigation,
  loadDiscoveredProjects,
} from '../modules/loadProjects';
import { ProjectRegistryProvider, useProjectRegistry } from '../modules/ProjectRegistry';
import type { DiscoveredProject } from '../modules/types';
import { NotFoundPage } from '../pages/NotFoundPage';
import { SettingsPage } from '../pages/SettingsPage';
import {
  DiscoveryErrorPage,
  EmptyProjectsPage,
  ProjectLoadingState,
} from '../pages/ShellStatePages';

const discovery = loadDiscoveredProjects();

function HomeIndex() {
  const { projects, error } = useProjectRegistry();
  if (error) {
    return <DiscoveryErrorPage message={error} />;
  }
  const first = buildProjectNavigation(projects)[0]?.links[0];
  if (!first) {
    return <EmptyProjectsPage />;
  }
  return <Navigate to={first.to} replace />;
}

function LegacyRedirect({ fromBase, toBase }: { fromBase: string; toBase: string }) {
  const location = useLocation();
  const suffix = location.pathname.startsWith(fromBase)
    ? location.pathname.slice(fromBase.length)
    : '';
  const normalizedSuffix = suffix === '/' ? '' : suffix;
  const target = `${toBase}${normalizedSuffix}${location.search}${location.hash}`;
  const current = `${location.pathname}${location.search}${location.hash}`;
  if (target === current) {
    return <NotFoundPage />;
  }
  return <Navigate to={target} replace />;
}

function ProjectPage({
  project,
}: {
  project: DiscoveredProject;
}) {
  const { pathname } = useLocation();
  const [attempt, setAttempt] = useState(0);
  const LazyPage = useMemo(
    () => lazy(() => loadProjectRoutes(project)),
    [project, attempt],
  );

  return (
    <ProjectErrorBoundary
      resetKey={pathname}
      onReset={() => setAttempt((value) => value + 1)}
    >
      <Suspense fallback={<ProjectLoadingState />}>
        <LazyPage />
      </Suspense>
    </ProjectErrorBoundary>
  );
}

/** 模組路由獨立於側欄項目，讓詳情頁不必新增導覽連結也能直接開啟。 */
async function loadProjectRoutes(project: DiscoveredProject) {
  const projectModule = await project.loadFrontend();
  const routes: RouteObject[] = projectModule.routes.map((route) =>
    route.index
      ? { index: true, element: route.element }
      : { path: route.path, element: route.element },
  );
  routes.push({ path: '*', element: <NotFoundPage /> });
  return {
    default: function LoadedProjectRoutes() {
      return useRoutes(routes);
    },
  };
}

function projectRoutes(projects: readonly DiscoveredProject[]): RouteObject[] {
  return projects.map((project) => ({
    path: `${project.manifest.routeBase.replace(/^\//, '')}/*`,
    element: <ProjectPage project={project} />,
  }));
}

function legacyRoutes(projects: readonly DiscoveredProject[]): RouteObject[] {
  const routes: RouteObject[] = [];
  for (const project of projects) {
    for (const legacyBase of project.manifest.legacyRouteBases) {
      const legacyPath = legacyBase.replace(/^\//, '');
      routes.push({
        path: legacyPath,
        element: (
          <LegacyRedirect fromBase={legacyBase} toBase={project.manifest.routeBase} />
        ),
      });
      routes.push({
        path: `${legacyPath}/*`,
        element: (
          <LegacyRedirect fromBase={legacyBase} toBase={project.manifest.routeBase} />
        ),
      });
    }
  }
  return routes;
}

export const router = createBrowserRouter([
  {
    path: '/',
    element: (
      <ProjectRegistryProvider value={discovery}>
        <AppShell />
      </ProjectRegistryProvider>
    ),
    children: [
      { index: true, element: <HomeIndex /> },
      { path: 'settings', element: <SettingsPage /> },
      ...projectRoutes(discovery.projects),
      ...legacyRoutes(discovery.projects),
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]);
