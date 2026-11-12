import { SectionHeader } from '@shell/components/layout/SectionHeader';
import type { UseServicesResult } from '../../hooks/useServices';
import { ServiceCard } from './ServiceCard';
import { ServicesLoadState } from './ServicesLoadState';
import { ServicesStaleBanner } from './ServicesStaleBanner';
import { ServicesSummaryPanel } from './ServicesSummaryPanel';

/**
 * 顯示 Monitor 頁面統一管理的服務資料；保留失敗重試與舊資料提示。
 * 一般刷新由頁首觸發，區塊本身不重複提供刷新按鈕與更新時間。
 */
export function ServicesSection({ services }: { services: UseServicesResult }) {
  const { data, loading, error, lastUpdated, refresh } = services;

  return (
    <section className="services-list-section" aria-labelledby="services-list-heading">
      <SectionHeader
        id="services-list-heading"
        title="Monitored Services"
      />

      {!data ? (
        <ServicesLoadState
          mode={loading ? 'loading' : 'failed'}
          error={error}
          onRetry={refresh}
        />
      ) : (
        <>
          {error ? (
            <ServicesStaleBanner lastUpdated={lastUpdated} error={error} />
          ) : null}
          <ServicesSummaryPanel summary={data.summary} />
          <div className="services-grid">
            {data.services.map((service) => (
              <ServiceCard key={service.key} service={service} />
            ))}
          </div>
        </>
      )}
    </section>
  );
}
