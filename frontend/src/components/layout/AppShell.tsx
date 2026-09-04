import { Outlet } from 'react-router-dom';
import { GlobalHeader } from './GlobalHeader';

export function AppShell() {
  return (
    <div className="app-shell">
      <GlobalHeader />
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}
