import { Suspense, useEffect, useState } from 'react';
import { useLocation, useRoutes } from 'react-router-dom';
import type { RouteObject } from 'react-router-dom';
import type { DiscoveredProject, ProjectFrontendModule } from '../../plugins/loader';
import { NotFoundPage } from '../../pages/NotFoundPage';
import { ProjectLoadingPage } from '../../pages/ProjectLoadingPage';
import { ProjectErrorBoundary } from './ProjectErrorBoundary';

interface LoadedProject {
  project: DiscoveredProject;
  attempt: number;
  module: ProjectFrontendModule | null;
  error: Error | null;
}

/** 專案子路由不依賴側邊欄項目，詳情頁可直接開啟。 */
function ProjectRoutes({ module }: { module: ProjectFrontendModule }) {
  const routes: RouteObject[] = module.routes.map((route) =>
    route.index
      ? { index: true, element: route.element }
      : { path: route.path, element: route.element },
  );
  routes.push({ path: '*', element: <NotFoundPage /> });
  return useRoutes(routes);
}

function ProjectContent({ result }: { result: LoadedProject | null }) {
  if (result?.error) throw result.error;
  return result?.module
    ? <ProjectRoutes module={result.module} />
    : <ProjectLoadingPage />;
}

/** 延後載入專案，忽略離開後的回應；重試重新呼叫專案入口。 */
export function ProjectOutlet({ project }: { project: DiscoveredProject }) {
  const { pathname } = useLocation();
  const [attempt, setAttempt] = useState(0);
  const [result, setResult] = useState<LoadedProject | null>(null);

  useEffect(() => {
    let active = true;
    void Promise.resolve().then(() => project.loadFrontend()).then(
      (module) => {
        if (active) setResult({ project, attempt, module, error: null });
      },
      (failure: unknown) => {
        if (active) setResult({ project, attempt, module: null,
          error: failure instanceof Error ? failure : new Error(String(failure)) });
      },
    );
    return () => { active = false; };
  }, [project, attempt]);

  const current = result?.project === project && result.attempt === attempt ? result : null;
  return (
    <ProjectErrorBoundary key={`${project.manifest.id}:${pathname}:${attempt}`}
      onRetry={() => setAttempt((value) => value + 1)}>
      <Suspense fallback={<ProjectLoadingPage />}>
        <ProjectContent result={current} />
      </Suspense>
    </ProjectErrorBoundary>
  );
}
