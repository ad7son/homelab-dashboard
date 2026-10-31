import type { MonitoredService } from '../../types/services';
import {
  formatLocalDateTime,
  formatServiceSubState,
  formatServiceUptime,
} from '../../utils/format';
import { ServiceStatusBadge } from './ServiceStatusBadge';

interface ServiceCardProps {
  service: MonitoredService;
}

export function ServiceCard({ service }: ServiceCardProps) {
  const subStateLabel = formatServiceSubState(service.sub_state);
  const uptimeLabel =
    service.status === 'active' && service.uptime_seconds != null
      ? formatServiceUptime(service.uptime_seconds)
      : null;

  const detailParts: string[] = [];
  if (subStateLabel) {
    detailParts.push(subStateLabel);
  }
  if (uptimeLabel) {
    detailParts.push(`Uptime ${uptimeLabel}`);
  }

  return (
    <article className="service-card">
      <div className="service-card-header">
        <h3 className="service-card-title">{service.display_name}</h3>
        <ServiceStatusBadge status={service.status} />
      </div>

      {service.description ? (
        <p className="service-card-description">{service.description}</p>
      ) : null}

      {detailParts.length > 0 ? (
        <p className="service-card-primary-meta">{detailParts.join(' · ')}</p>
      ) : null}

      <dl className="service-card-meta">
        <div>
          <dt>Unit</dt>
          <dd>{service.unit}</dd>
        </div>
        <div>
          <dt>Main PID</dt>
          <dd>{service.main_pid != null ? service.main_pid : 'N/A'}</dd>
        </div>
        {service.status === 'active' &&
        service.started_at_timestamp_ms != null ? (
          <div>
            <dt>Started</dt>
            <dd>{formatLocalDateTime(service.started_at_timestamp_ms)}</dd>
          </div>
        ) : null}
      </dl>
    </article>
  );
}
