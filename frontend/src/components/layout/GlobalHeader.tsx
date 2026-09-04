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
      <span className="global-header-brand">A7LAS</span>
    </header>
  );
}
