import { createContext, useContext } from 'react';
import type { ReactNode } from 'react';
import type { ProjectDiscoveryResult } from './loadProjects';

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

export function useProjectRegistry(): ProjectDiscoveryResult {
  const value = useContext(ProjectRegistryContext);
  if (value == null) {
    throw new Error('Project registry is missing from the shell');
  }
  return value;
}
