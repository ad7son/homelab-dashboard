import type { CpuInfo } from '../../types/system';
import { formatFrequency, formatNullable } from '../../utils/format';

interface CpuDetailsProps {
  cpu: CpuInfo;
}

function formatLoad(value: number): string {
  return value.toFixed(2);
}

export function CpuDetails({ cpu }: CpuDetailsProps) {
  const load = cpu.load_average;

  return (
    <section className="detail-section">
      <h2>CPU Details</h2>
      <dl className="detail-grid">
        <div>
          <dt>Physical Cores</dt>
          <dd>{cpu.physical_cores}</dd>
        </div>
        <div>
          <dt>Logical Cores</dt>
          <dd>{cpu.logical_cores}</dd>
        </div>
        <div>
          <dt>Current Frequency</dt>
          <dd>{formatNullable(cpu.frequency, formatFrequency)}</dd>
        </div>
        <div>
          <dt>Load Average (1 min)</dt>
          <dd>{load ? formatLoad(load.load_1) : 'N/A'}</dd>
        </div>
        <div>
          <dt>Load Average (5 min)</dt>
          <dd>{load ? formatLoad(load.load_5) : 'N/A'}</dd>
        </div>
        <div>
          <dt>Load Average (15 min)</dt>
          <dd>{load ? formatLoad(load.load_15) : 'N/A'}</dd>
        </div>
      </dl>
    </section>
  );
}
