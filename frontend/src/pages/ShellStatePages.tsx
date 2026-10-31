import { Link } from 'react-router-dom';
import { PageContainer } from '../components/layout/PageContainer';
import { PageHeader } from '../components/layout/PageHeader';

export function ProjectLoadingState() {
  return (
    <PageContainer>
      <PageHeader title="Loading" description="Loading project page." />
    </PageContainer>
  );
}

export function EmptyProjectsPage() {
  return (
    <PageContainer>
      <PageHeader
        title="No projects enabled"
        description="Add a project under projects/ and refresh the shell."
      />
    </PageContainer>
  );
}

export function DiscoveryErrorPage({ message }: { message: string }) {
  return (
    <PageContainer>
      <PageHeader title="Projects could not be loaded" description={message} />
      <p>The shell is still available. Fix the project manifest and refresh.</p>
      <p>
        <Link to="/settings">Open Settings</Link>
      </p>
    </PageContainer>
  );
}
