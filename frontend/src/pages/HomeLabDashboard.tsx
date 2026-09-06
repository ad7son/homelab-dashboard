import { RealtimeMonitoring } from '../components/charts/RealtimeMonitoring';
import { ConnectionBanner } from '../components/homelab/ConnectionBanner';
import { HomeLabHeader } from '../components/homelab/HomeLabHeader';
import { HomeLabLoadState } from '../components/homelab/HomeLabLoadState';
import { PageContainer } from '../components/layout/PageContainer';
import { SectionHeader } from '../components/layout/SectionHeader';
import { CpuCard } from '../components/metrics/CpuCard';
import { MemoryCard } from '../components/metrics/MemoryCard';
import { NetworkCard } from '../components/metrics/NetworkCard';
import { StorageCard } from '../components/metrics/StorageCard';
import { CpuDetails } from '../components/sections/CpuDetails';
import { StorageList } from '../components/sections/StorageList';
import { SystemInfoSection } from '../components/sections/SystemInfo';
import { useSystemOverview } from '../hooks/useSystemOverview';

export function HomeLabDashboard() {
  const { data, loading, error, lastUpdated, status, refresh, samples } =
    useSystemOverview();

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
          system={null}
          status={status}
          lastUpdated={lastUpdated}
          onRefresh={refresh}
        />
        <HomeLabLoadState
          mode="failed"
          error={error}
          onRetry={refresh}
        />
      </PageContainer>
    );
  }

  if (!data) {
    return null;
  }

  return (
    <PageContainer>
      <HomeLabHeader
        system={data.system}
        status={status}
        lastUpdated={lastUpdated}
        onRefresh={refresh}
      />

      {status === 'unstable' || status === 'offline' ? (
        <ConnectionBanner status={status} lastUpdated={lastUpdated} />
      ) : null}

      <section
        className="current-status"
        aria-labelledby="current-status-heading"
      >
        <SectionHeader
          id="current-status-heading"
          title="Current Status"
          description="Live system health at a glance"
        />
        <div className="metrics-grid">
          <CpuCard cpu={data.cpu} samples={samples} />
          <MemoryCard memory={data.memory} samples={samples} />
          <StorageCard disks={data.disks} />
          <NetworkCard network={data.network} />
        </div>
      </section>

      <RealtimeMonitoring samples={samples} />

      <section
        className="system-details"
        aria-labelledby="system-details-heading"
      >
        <SectionHeader
          id="system-details-heading"
          title="System Details"
          tone="secondary"
        />
        <div className="details-grid">
          <SystemInfoSection system={data.system} />
          <CpuDetails cpu={data.cpu} />
        </div>
      </section>

      <StorageList disks={data.disks} />
    </PageContainer>
  );
}
