import type { ReactNode } from 'react';
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { ChartPoint } from './chartUtils';
import { formatChartAxisTime, formatChartTooltipTime } from './chartUtils';

export interface ChartSeries {
  dataKey: keyof ChartPoint;
  name: string;
  color: string;
}

interface RealtimeChartProps {
  title: string;
  data: ChartPoint[];
  series: ChartSeries[];
  yDomain?: [number | 'auto', number | 'auto'];
  yTickFormatter?: (value: number) => string;
  formatValue?: (value: number) => string;
  yAxisWidth?: number;
  emptyMessage?: string;
  unavailable?: boolean;
  unavailableMessage?: string;
  showLegend?: boolean;
}

interface TooltipPayloadItem {
  dataKey?: string | number;
  name?: string;
  value?: number | null;
  color?: string;
}

interface ChartTooltipProps {
  active?: boolean;
  label?: number | string;
  payload?: TooltipPayloadItem[];
  formatValue?: (value: number) => string;
}

function ChartTooltip({
  active,
  label,
  payload,
  formatValue,
}: ChartTooltipProps) {
  if (!active || !payload || payload.length === 0) {
    return null;
  }

  const timestamp = typeof label === 'number' ? label : Number(label);

  return (
    <div className="realtime-chart-tooltip">
      <div className="realtime-chart-tooltip-time">
        {Number.isFinite(timestamp)
          ? formatChartTooltipTime(timestamp)
          : String(label)}
      </div>
      <ul className="realtime-chart-tooltip-list">
        {payload.map((item) => {
          const value = item.value;
          const display =
            value == null || Number.isNaN(value)
              ? 'N/A'
              : formatValue
                ? formatValue(value)
                : String(value);

          return (
            <li key={String(item.dataKey)} style={{ color: item.color }}>
              <span>{item.name}: </span>
              <strong>{display}</strong>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export function RealtimeChart({
  title,
  data,
  series,
  yDomain,
  yTickFormatter,
  formatValue,
  yAxisWidth = 44,
  emptyMessage = 'Collecting realtime data…',
  unavailable = false,
  unavailableMessage = 'Data unavailable',
  showLegend = false,
}: RealtimeChartProps) {
  let body: ReactNode;

  if (unavailable) {
    body = (
      <div className="realtime-chart-empty">{unavailableMessage}</div>
    );
  } else if (data.length < 2) {
    body = <div className="realtime-chart-empty">{emptyMessage}</div>;
  } else {
    body = (
      <ResponsiveContainer width="100%" height="100%">
        <LineChart
          data={data}
          margin={{ top: 8, right: 8, left: 0, bottom: 0 }}
        >
          <CartesianGrid
            stroke="var(--color-border)"
            strokeDasharray="3 3"
            vertical={false}
          />
          <XAxis
            dataKey="timestamp"
            type="number"
            domain={['dataMin', 'dataMax']}
            tickFormatter={formatChartAxisTime}
            tick={{ fill: 'var(--color-text-subtle)', fontSize: 11 }}
            tickLine={false}
            axisLine={{ stroke: 'var(--color-border)' }}
            minTickGap={48}
          />
          <YAxis
            domain={yDomain}
            width={yAxisWidth}
            tickFormatter={yTickFormatter}
            tick={{ fill: 'var(--color-text-subtle)', fontSize: 11 }}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip
            content={<ChartTooltip formatValue={formatValue} />}
            cursor={{ stroke: 'var(--color-border-strong)' }}
          />
          {showLegend && (
            <Legend
              wrapperStyle={{ fontSize: 12, color: 'var(--color-text-muted)' }}
            />
          )}
          {series.map((item) => (
            <Line
              key={item.dataKey}
              type="monotone"
              dataKey={item.dataKey}
              name={item.name}
              stroke={item.color}
              strokeWidth={2}
              dot={false}
              connectNulls={false}
              isAnimationActive={false}
              activeDot={{ r: 3 }}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    );
  }

  return (
    <article className="realtime-chart-card">
      <h3 className="realtime-chart-title">{title}</h3>
      <div className="realtime-chart-body">{body}</div>
    </article>
  );
}
