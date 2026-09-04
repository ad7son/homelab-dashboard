import { Server, Settings, X } from 'lucide-react';
import { NavLink } from 'react-router-dom';

interface SidebarProps {
  id: string;
  desktopOpen: boolean;
  mobileOpen: boolean;
  onCloseMobile: () => void;
}

export function Sidebar({
  id,
  desktopOpen,
  mobileOpen,
  onCloseMobile,
}: SidebarProps) {
  const desktopClass = desktopOpen ? 'sidebar-desktop-open' : 'sidebar-desktop-closed';
  const mobileClass = mobileOpen ? 'sidebar-mobile-open' : 'sidebar-mobile-closed';

  return (
    <aside
      id={id}
      className={`sidebar ${desktopClass} ${mobileClass}`}
      aria-label="Application"
    >
      <div className="sidebar-mobile-header">
        <span className="sidebar-mobile-title">Navigation</span>
        <button
          type="button"
          className="sidebar-close-button"
          aria-label="Close navigation"
          onClick={onCloseMobile}
        >
          <X size={20} aria-hidden="true" />
        </button>
      </div>

      <nav className="sidebar-nav" aria-label="Primary">
        <div className="sidebar-section">
          <p className="sidebar-section-label">Infrastructure</p>
          <NavLink
            to="/homelab"
            className={({ isActive }) =>
              isActive
                ? 'sidebar-nav-link sidebar-nav-link-active'
                : 'sidebar-nav-link'
            }
            onClick={onCloseMobile}
          >
            <Server size={18} aria-hidden="true" />
            <span>Home Lab</span>
          </NavLink>
        </div>

        <div className="sidebar-section">
          <p className="sidebar-section-label">System</p>
          <NavLink
            to="/settings"
            end
            className={({ isActive }) =>
              isActive
                ? 'sidebar-nav-link sidebar-nav-link-active'
                : 'sidebar-nav-link'
            }
            onClick={onCloseMobile}
          >
            <Settings size={18} aria-hidden="true" />
            <span>Settings</span>
          </NavLink>
        </div>
      </nav>
    </aside>
  );
}
