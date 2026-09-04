import { Menu } from 'lucide-react';

interface GlobalHeaderProps {
  menuButtonId: string;
  sidebarId: string;
  sidebarExpanded: boolean;
  onToggleSidebar: () => void;
}

export function GlobalHeader({
  menuButtonId,
  sidebarId,
  sidebarExpanded,
  onToggleSidebar,
}: GlobalHeaderProps) {
  return (
    <header className="global-header">
      <button
        id={menuButtonId}
        type="button"
        className="global-header-menu-button"
        aria-label="Toggle navigation"
        aria-expanded={sidebarExpanded}
        aria-controls={sidebarId}
        onClick={onToggleSidebar}
      >
        <Menu size={20} aria-hidden="true" />
      </button>
      <div className="global-header-brand">
        <span className="global-header-wordmark" aria-label="A7LAS">
          A<span className="global-header-wordmark-accent">7</span>LAS
        </span>
        <span className="global-header-subtitle">Personal Operating Space</span>
      </div>
    </header>
  );
}
