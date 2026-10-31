import { Settings, X } from 'lucide-react';
import { NavLink } from 'react-router-dom';
import { resolveProjectIcon } from '../../modules/icons';
import { buildProjectNavigation } from '../../modules/loadProjects';
import { useProjectRegistry } from '../../modules/ProjectRegistry';

interface SidebarProps {
  id: string;
  desktopOpen: boolean;
  mobileOpen: boolean;
  onCloseMobile: () => void;
}

function navClassName({ isActive }: { isActive: boolean }): string {
  return isActive ? 'sidebar-nav-link sidebar-nav-link-active' : 'sidebar-nav-link';
}

export function Sidebar({
  id,
  desktopOpen,
  mobileOpen,
  onCloseMobile,
}: SidebarProps) {
  const { projects, error } = useProjectRegistry();
  const sections = buildProjectNavigation(projects);
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
        {error ? (
          <div className="sidebar-section">
            <p className="sidebar-section-label">Projects</p>
            <p className="sidebar-nav-link">Unavailable</p>
          </div>
        ) : (
          sections.map((section) => (
            <div className="sidebar-section" key={section.section}>
              <p className="sidebar-section-label">{section.section}</p>
              {section.links.map((link) => {
                const Icon = resolveProjectIcon(link.icon);
                return (
                  <NavLink
                    key={link.to}
                    to={link.to}
                    end={link.end}
                    className={navClassName}
                    onClick={onCloseMobile}
                  >
                    <Icon size={18} aria-hidden="true" />
                    <span>{link.label}</span>
                  </NavLink>
                );
              })}
            </div>
          ))
        )}

        <div className="sidebar-section">
          <p className="sidebar-section-label">System</p>
          <NavLink
            to="/settings"
            end
            className={navClassName}
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
