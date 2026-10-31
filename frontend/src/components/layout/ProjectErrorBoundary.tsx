import { Component } from 'react';
import type { ErrorInfo, ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { PageContainer } from './PageContainer';
import { PageHeader } from './PageHeader';

interface ProjectErrorBoundaryProps {
  children: ReactNode;
  resetKey: string;
  onReset?: () => void;
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

  componentDidUpdate(previous: ProjectErrorBoundaryProps): void {
    if (previous.resetKey !== this.props.resetKey && this.state.error) {
      this.setState({ error: null });
      this.props.onReset?.();
    }
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
        <p>
          <Link to="/">Back to home</Link>
          {' · '}
          <Link to="/settings">Settings</Link>
        </p>
      </PageContainer>
    );
  }
}
