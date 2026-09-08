import { Navigate, createBrowserRouter } from 'react-router-dom';
import { AppShell } from '../components/layout/AppShell';
import { HomeLabDashboard } from '../pages/HomeLabDashboard';
import { NotFoundPage } from '../pages/NotFoundPage';
import { ServicesPage } from '../pages/ServicesPage';
import { SettingsPage } from '../pages/SettingsPage';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <AppShell />,
    children: [
      { index: true, element: <Navigate to="/homelab" replace /> },
      { path: 'homelab', element: <HomeLabDashboard /> },
      { path: 'homelab/services', element: <ServicesPage /> },
      { path: 'settings', element: <SettingsPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]);
