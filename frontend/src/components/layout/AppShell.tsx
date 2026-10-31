import { useEffect, useMemo, useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { buildProjectNavigation } from '../../modules/loadProjects';
import { useProjectRegistry } from '../../modules/ProjectRegistry';
import type { ProjectNavLink } from '../../modules/types';
import { GlobalHeader } from './GlobalHeader';
import { Sidebar } from './Sidebar';

const SIDEBAR_ID = 'a7las-sidebar';
const MENU_BUTTON_ID = 'a7las-sidebar-menu-button';
const MOBILE_MEDIA_QUERY = '(max-width: 768px)';

function documentTitleForPath(
  pathname: string,
  links: readonly ProjectNavLink[],
  discoveryError: string | null,
): string {
  if (pathname === '/settings') {
    return 'Settings · A7LAS';
  }
  const ranked = [...links].sort((left, right) => right.to.length - left.to.length);
  const match = ranked.find((link) =>
    link.end
      ? pathname === link.to
      : pathname === link.to || pathname.startsWith(`${link.to}/`),
  );
  if (match) {
    return `${match.documentTitle} · A7LAS`;
  }
  if (pathname === '/') {
    if (discoveryError) {
      return 'Projects could not be loaded · A7LAS';
    }
    if (links[0]) {
      return `${links[0].documentTitle} · A7LAS`;
    }
    return 'No projects enabled · A7LAS';
  }
  return 'Page Not Found · A7LAS';
}

export function AppShell() {
  const { pathname } = useLocation();
  const { projects, error } = useProjectRegistry();
  const links = useMemo(
    () => buildProjectNavigation(projects).flatMap((section) => section.links),
    [projects],
  );
  const [desktopOpen, setDesktopOpen] = useState(true);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(() =>
    typeof window !== 'undefined'
      ? window.matchMedia(MOBILE_MEDIA_QUERY).matches
      : false,
  );

  useEffect(() => {
    document.title = documentTitleForPath(pathname, links, error);
  }, [pathname, links, error]);

  useEffect(() => {
    const mediaQuery = window.matchMedia(MOBILE_MEDIA_QUERY);
    const syncViewport = () => {
      const mobile = mediaQuery.matches;
      setIsMobile(mobile);
      if (!mobile) {
        setMobileOpen(false);
      }
    };

    syncViewport();
    mediaQuery.addEventListener('change', syncViewport);
    return () => mediaQuery.removeEventListener('change', syncViewport);
  }, []);

  useEffect(() => {
    if (!mobileOpen) return;

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setMobileOpen(false);
      }
    };

    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [mobileOpen]);

  useEffect(() => {
    if (!(mobileOpen && isMobile)) return;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [mobileOpen, isMobile]);

  const closeMobile = () => {
    setMobileOpen(false);
  };

  const toggleSidebar = () => {
    if (isMobile) {
      setMobileOpen((open) => !open);
    } else {
      setDesktopOpen((open) => !open);
    }
  };

  const sidebarExpanded = isMobile ? mobileOpen : desktopOpen;

  return (
    <div className="app-shell">
      <GlobalHeader
        menuButtonId={MENU_BUTTON_ID}
        sidebarId={SIDEBAR_ID}
        sidebarExpanded={sidebarExpanded}
        onToggleSidebar={toggleSidebar}
      />

      <div className="app-body">
        <div
          className={
            mobileOpen
              ? 'sidebar-overlay sidebar-overlay-visible'
              : 'sidebar-overlay'
          }
          onClick={closeMobile}
          aria-hidden="true"
        />

        <Sidebar
          id={SIDEBAR_ID}
          desktopOpen={desktopOpen}
          mobileOpen={mobileOpen}
          onCloseMobile={closeMobile}
        />

        <main className="app-main">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
