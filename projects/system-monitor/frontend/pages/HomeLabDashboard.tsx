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
import { GpuCard } from '../components/metrics/GpuCard';
import { DiskIoCard } from '../components/metrics/DiskIoCard';
import { ProjectHealthSection } from '../components/health/ProjectHealthSection';
import { useSystemOverview } from '../hooks/useSystemOverview';
import { useProjectHealth } from '../hooks/useProjectHealth';
import { usePageScrollPosition } from '../hooks/usePageScrollPosition';

export function HomeLabDashboard() {
  const { data, loading, error, lastUpdated, status, refresh, samples } =
    useSystemOverview();
  const [monitoringMode, setMonitoringMode] = useState<MonitoringMode>('live');
  const [refreshToken, setRefreshToken] = useState(0);
  const health = useProjectHealth(refreshToken);
  usePageScrollPosition((data !== null || !loading) && !health.loading);

  // 同時刷新主機資訊、歷史圖表與實際功能健康報告。
  const refreshPage = () => {
    refresh();
    setRefreshToken((token) => token + 1);
  };

  if (loading && !data) {
    return (
      <PageContainer>
        <HomeLabLoadState mode="loading" />
        <ProjectHealthSection health={health} />
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
        <ProjectHealthSection health={health} />
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

      {status === 'stale' || status === 'unstable' || status === 'offline' ? (
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
              <GpuCard gpu={data.gpu} />
              <DiskIoCard diskIo={data.disk_io} />
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

      <ProjectHealthSection health={health} />
    </PageContainer>
  );
}
