import { useState } from 'react';
import {
  MonitoringSection,
  type MonitoringMode,
} from '../components/charts/MonitoringSection';
import { ConnectionBanner } from '../components/homelab/ConnectionBanner';
import { HomeLabHeader } from '../components/homelab/HomeLabHeader';
import { HomeLabLoadState } from '../components/homelab/HomeLabLoadState';
import { PageContainer } from '@shell/components/layout/PageContainer';
import { SectionHeader } from '@shell/components/layout/SectionHeader';
import { CpuCard } from '../components/metrics/CpuCard';
import { MemoryCard } from '../components/metrics/MemoryCard';
import { NetworkCard } from '../components/metrics/NetworkCard';
import { StorageCard } from '../components/metrics/StorageCard';
import { ServicesSection } from '../components/services/ServicesSection';
import { useSystemOverview } from '../hooks/useSystemOverview';
import { useServices } from '../hooks/useServices';

export function HomeLabDashboard() {
  const { data, loading, error, lastUpdated, status, refresh, samples } =
    useSystemOverview();
  const [monitoringMode, setMonitoringMode] = useState<MonitoringMode>('live');
  const services = useServices();
  const [refreshToken, setRefreshToken] = useState(0);

  // 頁首統一刷新主機、服務與目前啟用的歷史圖表；不重設所選指標或時間範圍。
  const refreshPage = () => {
    refresh();
    services.refresh();
    setRefreshToken((token) => token + 1);
  };

  if (loading && !data) {
    return (
      <PageContainer>
        <HomeLabLoadState mode="loading" />
      </PageContainer>
    );
  }

  if (!data && !loading) {
    return (
      <PageContainer>
        <HomeLabHeader
          status={status}
          lastUpdated={lastUpdated}
          onRefresh={refreshPage}
        />
        <HomeLabLoadState mode="failed" error={error} onRetry={refresh} />
      </PageContainer>
    );
  }

  if (!data) {
    return null;
  }

  return (
    <PageContainer>
      <HomeLabHeader
        status={status}
        lastUpdated={lastUpdated}
        onRefresh={refreshPage}
      />

      {status === 'unstable' || status === 'offline' ? (
        <ConnectionBanner status={status} lastUpdated={lastUpdated} />
      ) : null}

      {/* 桌面版左右各半：狀態卡與單一可切換圖表並列。 */}
      <section className="machine-state" aria-labelledby="machine-state-heading">
        <SectionHeader id="machine-state-heading" title="Machine State" />
        <div className="monitor-overview-grid">
          <div className="current-status">
            <div className="metrics-grid">
              <CpuCard cpu={data.cpu} samples={samples} />
              <MemoryCard memory={data.memory} samples={samples} />
              <StorageCard disks={data.disks} />
              <NetworkCard network={data.network} />
            </div>
          </div>

          <MonitoringSection
            samples={samples}
            mode={monitoringMode}
            onModeChange={setMonitoringMode}
            refreshToken={refreshToken}
          />
        </div>
      </section>

      <ServicesSection services={services} />
    </PageContainer>
  );
}
