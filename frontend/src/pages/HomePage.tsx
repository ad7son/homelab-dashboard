import { Link, Navigate } from 'react-router-dom';
import { useProjectRegistry } from '../plugins/registry';
import { buildProjectNavigation } from '../plugins/navigation';
import { PageContainer } from '../components/layout/PageContainer';
import { PageHeader } from '../components/layout/PageHeader';

/** 首頁導向第一個專案；設定失敗或沒有專案時仍保留平台外殼。 */
export function HomePage() {
  const { projects, error } = useProjectRegistry();
  if (error) {
    return (
      <PageContainer>
        <PageHeader title="Projects could not be loaded" description={error} />
        <p>The shell is still available. Fix the project manifest and refresh.</p>
        <p><Link to="/settings">Open Settings</Link></p>
      </PageContainer>
    );
  }
  const first = buildProjectNavigation(projects)[0]?.links[0];
  if (first) return <Navigate to={first.to} replace />;
  return (
    <PageContainer>
      <PageHeader title="No projects enabled"
        description="Add a project under projects/ and refresh the shell." />
    </PageContainer>
  );
}
