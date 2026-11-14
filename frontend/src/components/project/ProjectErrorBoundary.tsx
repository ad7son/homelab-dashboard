import { Component } from 'react';
import type { ErrorInfo, ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { PageContainer } from '../layout/PageContainer';
import { PageHeader } from '../layout/PageHeader';

interface ProjectErrorBoundaryProps {
  children: ReactNode;
  onRetry?: () => void;
}

interface ProjectErrorBoundaryState {
  error: Error | null;
}

export class ProjectErrorBoundary extends Component<
  ProjectErrorBoundaryProps,
  ProjectErrorBoundaryState
> {
  state: ProjectErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ProjectErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error('Project page failed to render', error, info.componentStack);
  }

  render() {
    const { error } = this.state;
    if (!error) {
      return this.props.children;
    }
    const message = error.message || 'The project page failed to render.';
    return (
      <PageContainer>
        <PageHeader
          title="This project page could not be loaded"
          description={message}
        />
        {this.props.onRetry ? (
          <button type="button" onClick={this.props.onRetry}>Retry</button>
        ) : null}
        <p>
          <Link to="/">Back to home</Link>
          {' · '}
          <Link to="/settings">Settings</Link>
        </p>
      </PageContainer>
    );
  }
}
