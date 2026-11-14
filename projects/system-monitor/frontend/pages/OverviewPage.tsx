import { useState } from 'react';
import { MonitoringSection, type MonitoringMode } from '../components/charts/MonitoringSection';
import { OverviewHeader } from '../components/OverviewHeader';
import { PageContainer } from '@shell/components/layout/PageContainer';
import { SectionHeader } from '@shell/components/layout/SectionHeader';
import { CpuCard } from '../components/metrics/CpuCard';
import { MemoryCard } from '../components/metrics/MemoryCard';
import { GpuCard } from '../components/metrics/GpuCard';
import { DiskIoCard } from '../components/metrics/DiskIoCard';
import { ProjectHealthSection } from '../components/health/ProjectHealthSection';
import { useOverview } from '../hooks/useOverview';
import { useHistory } from '../hooks/useHistory';
import { useProjectHealth } from '../hooks/useProjectHealth';
import { usePageScrollPosition } from '../hooks/usePageScrollPosition';

/** 固定保留完整畫面，各區塊獨立處理載入、缺值與錯誤。 */
export function OverviewPage() {
  const overview = useOverview();
  const [monitoringMode, setMonitoringMode] = useState<MonitoringMode>('live');
  const [refreshToken, setRefreshToken] = useState(0);
  const health = useProjectHealth(refreshToken);
  const history = useHistory({ enabled: monitoringMode === 'history', refreshToken });
  usePageScrollPosition(true);

  const refreshPage = () => {
    void overview.refresh();
    setRefreshToken((token) => token + 1);
  };
  const emptyMessage = overview.loading ? 'Loading host data…'
    : overview.error ? 'Host data unavailable' : 'No host data available';

  return (
    <PageContainer>
      <OverviewHeader status={overview.status} lastUpdated={overview.lastUpdated}
        loading={overview.loading} error={overview.error} onRefresh={refreshPage} />
      <section className="machine-state" aria-labelledby="machine-state-heading">
        <SectionHeader id="machine-state-heading" title="Machine State" />
        <div className="monitor-overview-grid">
          <div className="current-status">
            <div className="metrics-grid">
              <CpuCard cpu={overview.data?.cpu} samples={overview.samples} emptyMessage={emptyMessage} />
              <MemoryCard memory={overview.data?.memory} samples={overview.samples} emptyMessage={emptyMessage} />
              <GpuCard gpu={overview.data?.gpu} emptyMessage={emptyMessage} />
              <DiskIoCard diskIo={overview.data?.disk_io} emptyMessage={emptyMessage} />
            </div>
          </div>
          <MonitoringSection samples={overview.samples} mode={monitoringMode}
            onModeChange={setMonitoringMode} history={history} emptyMessage={emptyMessage} />
        </div>
      </section>
      <ProjectHealthSection health={health} />
    </PageContainer>
  );
}
