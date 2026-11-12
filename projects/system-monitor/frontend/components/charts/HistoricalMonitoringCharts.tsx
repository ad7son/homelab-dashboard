import { useMemo } from 'react';
import type { HistoricalMetricSample, HistoricalRange } from '../../types/history';
import { SelectedMetricChart } from './SelectedMetricChart';
import type { MonitoringMetric } from '../../types/monitoring';
import {
  formatHistoryAxisTime,
  formatHistoryTooltipTime,
  hasValidHistoricalTemperature,
  historicalSamplesToChartPoints,
} from './chartUtils';

interface HistoricalMonitoringChartsProps {
  range: HistoricalRange;
  samples: HistoricalMetricSample[];
  metric: MonitoringMetric;
}

export function HistoricalMonitoringCharts({ range, samples, metric }: HistoricalMonitoringChartsProps) {
  const chartPoints = useMemo(
    () => historicalSamplesToChartPoints(samples, range),
    [samples, range],
  );
  const temperatureAvailable = hasValidHistoricalTemperature(samples);

  return (
    <SelectedMetricChart
      metric={metric}
      data={chartPoints}
      formatAxisTime={(timestamp) => formatHistoryAxisTime(timestamp, range)}
      formatTooltipTime={formatHistoryTooltipTime}
      unavailable={metric === 'temperature' && !temperatureAvailable && samples.length > 0}
      unavailableMessage="Temperature data unavailable"
      emptyMessage="No historical data available for this range."
    />
  );
}
