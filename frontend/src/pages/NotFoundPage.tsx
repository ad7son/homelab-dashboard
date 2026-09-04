import { Link } from 'react-router-dom';
import { PageContainer } from '../components/layout/PageContainer';
import { PageHeader } from '../components/layout/PageHeader';

export function NotFoundPage() {
  return (
    <PageContainer>
      <PageHeader title="Page not found" />
      <p>
        <Link to="/homelab">Back to Home Lab</Link>
      </p>
    </PageContainer>
  );
}
