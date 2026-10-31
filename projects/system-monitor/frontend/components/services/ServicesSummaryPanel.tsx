import type { ServicesSummary } from '../../types/services';

interface ServicesSummaryPanelProps {
  summary: ServicesSummary;
}

export function ServicesSummaryPanel({ summary }: ServicesSummaryPanelProps) {
  const allActive =
    summary.total > 0 && summary.active === summary.total;

  return (
    <section
      className="services-summary"
      aria-labelledby="services-summary-heading"
    >
      <div className="services-summary-header">
        <h2 id="services-summary-heading" className="services-summary-title">
          Summary
        </h2>
        {allActive ? (
          <p className="services-summary-note">
            All monitored services are active
          </p>
        ) : null}
      </div>

      <dl className="services-summary-grid">
        <div className="services-summary-item">
          <dt>Total</dt>
          <dd>{summary.total}</dd>
        </div>
        <div className="services-summary-item services-summary-active">
          <dt>Active</dt>
          <dd>{summary.active}</dd>
        </div>
        <div className="services-summary-item">
          <dt>Inactive</dt>
          <dd>{summary.inactive}</dd>
        </div>
        <div className="services-summary-item services-summary-failed">
          <dt>Failed</dt>
          <dd>{summary.failed}</dd>
        </div>
        <div className="services-summary-item services-summary-unavailable">
          <dt>Unavailable</dt>
          <dd>{summary.unavailable}</dd>
        </div>
        <div className="services-summary-item">
          <dt>Unknown</dt>
          <dd>{summary.unknown}</dd>
        </div>
      </dl>
    </section>
  );
}
