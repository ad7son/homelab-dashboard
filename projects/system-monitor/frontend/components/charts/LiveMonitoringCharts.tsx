import { useMemo } from 'react';
import type { RealtimeSample } from '../../types/realtime';
import { SelectedMetricChart } from './SelectedMetricChart';
import type { MonitoringMetric } from '../../types/monitoring';
import { hasValidSeriesValues, toChartPoints } from './chartUtils';

interface LiveMonitoringChartsProps {
  samples: RealtimeSample[];
  metric: MonitoringMetric;
}

export function LiveMonitoringCharts({ samples, metric }: LiveMonitoringChartsProps) {
  const chartPoints = useMemo(() => toChartPoints(samples), [samples]);
  const temperatureAvailable = hasValidSeriesValues(chartPoints, 'cpuTemperatureCelsius');

  return (
    <SelectedMetricChart
      metric={metric}
      data={chartPoints}
      unavailable={metric === 'temperature' && !temperatureAvailable && samples.length > 0}
      unavailableMessage="Temperature data unavailable"
    />
  );
}
