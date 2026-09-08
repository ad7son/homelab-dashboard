import {
  Ban,
  CheckCircle2,
  CircleOff,
  HelpCircle,
  XCircle,
} from 'lucide-react';
import type { ServiceStatus } from '../../types/services';

const STATUS_META: Record<
  ServiceStatus,
  { label: string; Icon: typeof CheckCircle2 }
> = {
  active: { label: 'Active', Icon: CheckCircle2 },
  inactive: { label: 'Inactive', Icon: CircleOff },
  failed: { label: 'Failed', Icon: XCircle },
  unavailable: { label: 'Unavailable', Icon: Ban },
  unknown: { label: 'Unknown', Icon: HelpCircle },
};

interface ServiceStatusBadgeProps {
  status: ServiceStatus;
}

export function ServiceStatusBadge({ status }: ServiceStatusBadgeProps) {
  const { label, Icon } = STATUS_META[status];

  return (
    <span className={`service-status-badge service-status-${status}`}>
      <Icon size={14} aria-hidden="true" />
      <span className="service-status-label">{label}</span>
    </span>
  );
}
