import { useMemo } from 'react';
import type { RealtimeSample } from '../../utils/realtimeSamples';
import { SelectedMetricChart } from './SelectedMetricChart';
import type { MonitoringMetric } from './metrics';
import { hasValidSeriesValues, toChartPoints } from './chartUtils';

interface LiveMonitoringChartsProps {
  samples: RealtimeSample[];
  metric: MonitoringMetric;
  emptyMessage?: string;
}

export function LiveMonitoringCharts({ samples, metric, emptyMessage }: LiveMonitoringChartsProps) {
  const chartPoints = useMemo(() => toChartPoints(samples), [samples]);
  const temperatureAvailable = hasValidSeriesValues(chartPoints, 'cpuTemperatureCelsius');

  return (
    <SelectedMetricChart
      metric={metric}
      data={chartPoints}
      emptyMessage={emptyMessage}
      unavailable={metric === 'temperature' && !temperatureAvailable && samples.length > 0}
      unavailableMessage="Temperature data unavailable"
    />
  );
}
