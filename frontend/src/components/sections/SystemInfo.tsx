import type { SystemInfo } from '../../types/system';
import { formatUptime } from '../../utils/format';

interface SystemInfoSectionProps {
  system: SystemInfo;
}

export function SystemInfoSection({ system }: SystemInfoSectionProps) {
  return (
    <section className="detail-section">
      <h2>System Information</h2>
      <dl className="detail-grid">
        <div>
          <dt>Hostname</dt>
          <dd>{system.hostname}</dd>
        </div>
        <div>
          <dt>Operating System</dt>
          <dd>{system.operating_system}</dd>
        </div>
        <div>
          <dt>OS Version</dt>
          <dd>{system.os_version ?? 'N/A'}</dd>
        </div>
        <div>
          <dt>Kernel</dt>
          <dd>{system.kernel}</dd>
        </div>
        <div>
          <dt>Architecture</dt>
          <dd>{system.architecture}</dd>
        </div>
        <div>
          <dt>Uptime</dt>
          <dd>{formatUptime(system.uptime)}</dd>
        </div>
      </dl>
    </section>
  );
}
