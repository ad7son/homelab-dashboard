import type { ReactNode } from 'react';

interface PageHeaderProps {
  title: string;
  description?: ReactNode;
  actions?: ReactNode;
}

export function PageHeader({ title, description, actions }: PageHeaderProps) {
  return (
    <header className="page-header">
      <div className="page-header-main">
        <h1 className="page-header-title">{title}</h1>
        {description != null && description !== '' && (
          <div className="page-header-description">{description}</div>
        )}
      </div>
      {actions != null && (
        <div className="page-header-actions">{actions}</div>
      )}
    </header>
  );
}
