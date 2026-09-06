import type { ReactNode } from 'react';

interface SectionHeaderProps {
  title: string;
  description?: string;
  meta?: ReactNode;
  id?: string;
  tone?: 'primary' | 'secondary';
}

export function SectionHeader({
  title,
  description,
  meta,
  id,
  tone = 'primary',
}: SectionHeaderProps) {
  return (
    <div
      className={
        tone === 'secondary'
          ? 'section-header section-header-secondary'
          : 'section-header'
      }
    >
      <div className="section-header-main">
        <h2 className="section-header-title" id={id}>
          {title}
        </h2>
        {description ? (
          <p className="section-header-description">{description}</p>
        ) : null}
      </div>
      {meta != null ? <div className="section-header-meta">{meta}</div> : null}
    </div>
  );
}
