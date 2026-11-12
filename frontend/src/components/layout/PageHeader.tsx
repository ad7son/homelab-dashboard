import type { ReactNode } from 'react';

interface PageHeaderProps {
  className?: string;
  title: string;
  icon?: ReactNode;
  description?: ReactNode;
  actions?: ReactNode;
}

export function PageHeader({ title, icon, description, actions, className }: PageHeaderProps) {
  return (
    <header className={['page-header', className].filter(Boolean).join(' ')}>
      <div className="page-header-main">
        <h1 className="page-header-title">{icon}{title}</h1>
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
