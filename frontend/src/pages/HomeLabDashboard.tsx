import { RealtimeMonitoring } from '../components/charts/RealtimeMonitoring';
import { HomeLabHeader } from '../components/homelab/HomeLabHeader';
import { PageContainer } from '../components/layout/PageContainer';
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
        <div className="loading-state">Loading system overview…</div>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <HomeLabHeader
        system={data?.system ?? null}
        status={status}
        lastUpdated={lastUpdated}
        onRefresh={refresh}
      />

      {error && (
        <div className={`connection-banner connection-${status}`}>
          Connection {status}: {error}
        </div>
      )}

      {data ? (
        <>
          <section className="metrics-grid">
            <CpuCard cpu={data.cpu} />
            <MemoryCard memory={data.memory} />
            <StorageCard disks={data.disks} />
            <NetworkCard network={data.network} />
          </section>

          <RealtimeMonitoring samples={samples} />

          <section className="details-grid">
            <SystemInfoSection system={data.system} />
            <CpuDetails cpu={data.cpu} />
          </section>

          <StorageList disks={data.disks} />
        </>
      ) : (
        <div className="empty-state">
          Unable to load system data. Waiting for connection…
        </div>
      )}
    </PageContainer>
  );
}
