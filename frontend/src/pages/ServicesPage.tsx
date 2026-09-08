import { ServiceCard } from '../components/services/ServiceCard';
import { ServicesHeader } from '../components/services/ServicesHeader';
import { ServicesLoadState } from '../components/services/ServicesLoadState';
import { ServicesStaleBanner } from '../components/services/ServicesStaleBanner';
import { ServicesSummaryPanel } from '../components/services/ServicesSummaryPanel';
import { PageContainer } from '../components/layout/PageContainer';
import { SectionHeader } from '../components/layout/SectionHeader';
import { useServices } from '../hooks/useServices';

export function ServicesPage() {
  const { data, loading, refreshing, error, lastUpdated, refresh } =
    useServices();

  if (loading && !data) {
    return (
      <PageContainer>
        <ServicesHeader
          lastUpdated={lastUpdated}
          refreshing={false}
          refreshDisabled
          onRefresh={refresh}
        />
        <ServicesLoadState mode="loading" />
      </PageContainer>
    );
  }

  if (!data && !loading) {
    return (
      <PageContainer>
        <ServicesHeader
          lastUpdated={lastUpdated}
          refreshing={refreshing}
          onRefresh={refresh}
        />
        <ServicesLoadState mode="failed" error={error} onRetry={refresh} />
      </PageContainer>
    );
  }

  if (!data) {
    return null;
  }

  return (
    <PageContainer>
      <ServicesHeader
        lastUpdated={lastUpdated}
        refreshing={refreshing}
        onRefresh={refresh}
      />

      {error ? (
        <ServicesStaleBanner lastUpdated={lastUpdated} error={error} />
      ) : null}

      <ServicesSummaryPanel summary={data.summary} />

      <section
        className="services-list-section"
        aria-labelledby="services-list-heading"
      >
        <SectionHeader
          id="services-list-heading"
          title="Monitored Services"
          description="Configured Home Lab units in deployment order"
        />
        <div className="services-grid">
          {data.services.map((service) => (
            <ServiceCard key={service.key} service={service} />
          ))}
        </div>
      </section>
    </PageContainer>
  );
}
