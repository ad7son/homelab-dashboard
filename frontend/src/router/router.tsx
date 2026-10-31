import { lazy, Suspense, useMemo, useState } from 'react';
import { Navigate, createBrowserRouter, useLocation } from 'react-router-dom';
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
  itemPath,
}: {
  project: DiscoveredProject;
  itemPath: string;
}) {
  const { pathname } = useLocation();
  const [attempt, setAttempt] = useState(0);
  const LazyPage = useMemo(
    () => lazy(() => loadProjectPage(project, itemPath)),
    [project, itemPath, attempt],
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

async function loadProjectPage(project: DiscoveredProject, itemPath: string) {
  const projectModule = await project.loadFrontend();
  const route = projectModule.routes.find((entry) =>
    itemPath === '' ? entry.index === true : entry.path === itemPath,
  );
  if (route == null) {
    throw new Error(
      `Project '${project.manifest.name}' has no page for '${itemPath || '/'}'.`,
    );
  }
  const element = route.element;
  return {
    default: function LoadedProjectPage() {
      return element;
    },
  };
}

function projectRoutes(projects: readonly DiscoveredProject[]): RouteObject[] {
  return projects.map((project) => ({
    path: project.manifest.routeBase.replace(/^\//, ''),
    children: project.manifest.nav.items.map((item) =>
      item.path === ''
        ? {
            index: true as const,
            element: <ProjectPage project={project} itemPath="" />,
          }
        : {
            path: item.path,
            element: <ProjectPage project={project} itemPath={item.path} />,
          },
    ),
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
