import type { ComponentProps } from 'react';
import { formatBytesPerSecond, formatPercent, formatTemperature } from '../../utils/format';
import { MetricChart } from './MetricChart';

import { MONITORING_METRICS, type MonitoringMetric } from '../../types/monitoring';

type SelectedMetricChartProps = Omit<ComponentProps<typeof MetricChart>, 'title' | 'series'> & {
  metric: MonitoringMetric;
};

/** 即時與歷史模式共用指標設定，切換選單時只呈現一張圖，網路保留雙序列。 */
export function SelectedMetricChart({ metric, ...props }: SelectedMetricChartProps) {
  const title = MONITORING_METRICS.find((item) => item.value === metric)!.label;
  if (metric === 'network') {
    return <MetricChart {...props} title={title} series={[
      { dataKey: 'networkDownloadBytesPerSecond', name: 'Download', color: 'var(--color-chart-download)' },
      { dataKey: 'networkUploadBytesPerSecond', name: 'Upload', color: 'var(--color-chart-upload)' },
    ]} yAxisWidth={64} yTickFormatter={formatBytesPerSecond} formatValue={formatBytesPerSecond} showLegend />;
  }
  if (metric === 'temperature') {
    return <MetricChart {...props} title={title} series={[
      { dataKey: 'cpuTemperatureCelsius', name: 'Temp', color: 'var(--color-chart-temperature)' },
    ]} yTickFormatter={(value) => `${value}`} formatValue={formatTemperature} />;
  }
  return <MetricChart {...props} title={title} series={[
    metric === 'cpu'
      ? { dataKey: 'cpuUsagePercent', name: 'CPU', color: 'var(--color-chart-cpu)' }
      : { dataKey: 'memoryUsagePercent', name: 'Memory', color: 'var(--color-chart-memory)' },
  ]} yDomain={[0, 100]} yTickFormatter={(value) => `${value}`} formatValue={formatPercent} />;
}
