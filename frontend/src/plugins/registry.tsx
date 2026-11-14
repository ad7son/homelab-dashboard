import { createContext, useContext } from 'react';
import type { ReactNode } from 'react';
import type { ProjectDiscoveryResult } from './loader';

const ProjectRegistryContext = createContext<ProjectDiscoveryResult | null>(null);

export function ProjectRegistryProvider({
  value,
  children,
}: {
  value: ProjectDiscoveryResult;
  children: ReactNode;
}) {
  return (
    <ProjectRegistryContext.Provider value={value}>
      {children}
    </ProjectRegistryContext.Provider>
  );
}

// 專案清單的 Provider 與 hook 共用同一個 Context。
// oxlint-disable-next-line react/only-export-components
export function useProjectRegistry(): ProjectDiscoveryResult {
  const value = useContext(ProjectRegistryContext);
  if (value == null) {
    throw new Error('Project registry is missing from the shell');
  }
  return value;
}
