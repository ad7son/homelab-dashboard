import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import ts from 'typescript';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

// 以現有 TypeScript 編譯器載入原始碼，不另引入測試框架或複製實作。
const root = new URL('../../projects/system-monitor/frontend/', import.meta.url);
const loaded = new Map();
async function moduleUrl(url) {
  const key = url.href;
  if (loaded.has(key)) return loaded.get(key);
  const source = await readFile(url, 'utf8');
  let output = url.pathname.endsWith('.json') ? `export default ${source}` : ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2023, jsx: ts.JsxEmit.ReactJSX },
    fileName: url.pathname,
  }).outputText;
  const imports = [...output.matchAll(/from\s+['"]([^'"]+)['"]/g)];
  for (const match of imports) {
    const specifier = match[1];
    let target;
    if (specifier.startsWith('.')) {
      const path = new URL(specifier, url);
      if (!/\.(ts|tsx|json)$/.test(path.pathname)) {
        try { await readFile(new URL(path.href + '.ts')); path.pathname += '.ts'; }
        catch { path.pathname += '.tsx'; }
      }
      target = await moduleUrl(path);
    } else {
      target = import.meta.resolve(specifier);
    }
    output = output.replaceAll(`'${specifier}'`, JSON.stringify(target)).replaceAll(`"${specifier}"`, JSON.stringify(target));
  }
  const target = 'data:text/javascript;base64,' + Buffer.from(output).toString('base64');
  loaded.set(key, target);
  return target;
}
async function load(name) { return import(await moduleUrl(new URL(name, root))); }
const { parseOverview, sampleStatus } = await load('utils/overview.ts');
const { mergeRealtimeSample } = await load('utils/realtimeSamples.ts');
const { historicalSamplesToChartPoints } = await load('components/charts/chartUtils.ts');
const { averageRecentMetric } = await load('utils/realtimeAverages.ts');
const { formatBytes, formatNullable, formatPercent } = await load('utils/format.ts');
const { CpuCard } = await load('components/metrics/CpuCard.tsx');
const { MemoryCard } = await load('components/metrics/MemoryCard.tsx');
const api = await load('api.ts');

const now = 1794614400000;
function payload() {
  return {
    info: { updated_at_ms: now - 3000, cpu_physical_cores: 4, memory_total_bytes: 1024, gpu_name: 'GPU', gpu_device_count: 1 },
    metrics: { timestamp_ms: now, cpu_usage_percent: 0, memory_usage_percent: null, memory_used_bytes: null,
      network_download_bytes_per_second: 0, gpu_status: 'unsupported', disk_io_status: 'warming_up' },
  };
}

test('new overview maps info/metrics and preserves real zeroes, nulls and timestamp', () => {
  const result = parseOverview(payload());
  assert.equal(result.timestamp_ms, now);
  assert.equal(result.cpu.usage_percent, 0);
  assert.equal(result.cpu.physical_cores, 4);
  assert.equal(result.memory.total, 1024);
  assert.equal(result.memory.usage_percent, null);
  assert.equal(result.network.download_rate, 0);
  assert.equal(result.gpu.status, 'unsupported');
});
test('old or malformed overview is rejected instead of crashing a card later', () => {
  for (const value of [null, {}, {cpu: {}}, {info: {}, metrics: {}}, { ...payload(), metrics: { timestamp_ms: NaN } }]) {
    assert.throws(() => parseOverview(value));
  }
});
test('repeated DB timestamps and out-of-order samples do not create fake realtime points', () => {
  const result = parseOverview(payload());
  const first = mergeRealtimeSample([], result, now);
  assert.equal(mergeRealtimeSample(first, result, now + 3000).length, 1);
  assert.equal(mergeRealtimeSample(first, {...result, timestamp_ms: now - 3000}, now).length, 1);
  const next = mergeRealtimeSample(first, {...result, timestamp_ms: now + 3000}, now + 3000);
  assert.deepEqual(next.map(point => point.timestamp), [now, now + 3000]);
  assert.deepEqual(mergeRealtimeSample(next, result, now + 304000), []);
});
test('a successful response can still contain stale or future-clock data', () => {
  assert.equal(sampleStatus(now, now + 15000), 'online');
  assert.equal(sampleStatus(now, now + 15001), 'stale');
  assert.equal(sampleStatus(now + 60000, now), 'stale');
});
test('history gaps follow response interval and never fill missing metrics with zero', () => {
  const sample = { timestamp_ms: now, cpu_usage_percent: null, memory_usage_percent: 0 };
  const raw = historicalSamplesToChartPoints([sample, {...sample, timestamp_ms: now + 9000}], '1h', 3);
  assert.equal(raw.length, 3);
  assert.equal(raw[0].cpuUsagePercent, null);
  assert.equal(raw[0].memoryUsagePercent, 0);
  const bucketed = historicalSamplesToChartPoints([sample, {...sample, timestamp_ms: now + 600000}], '24h', 300);
  assert.equal(bucketed.length, 2);
});
test('30 second averages exclude missing values and expired samples', () => {
  const points = [{ timestamp: now - 31000, cpuUsagePercent: 100 }, {timestamp: now, cpuUsagePercent: 0}, {timestamp: now - 3000, cpuUsagePercent: null}];
  assert.equal(averageRecentMetric(points, 'cpuUsagePercent', 30000, now), 0);
  assert.equal(averageRecentMetric(points, 'cpuUsagePercent', 30000, now + 31000), null);
});
test('null CPU and memory render N/A without false progress bars', () => {
  const result = parseOverview(payload());
  const cpu = renderToStaticMarkup(createElement(CpuCard, {cpu: {...result.cpu, usage_percent: null}, samples: []}));
  const memory = renderToStaticMarkup(createElement(MemoryCard, {memory: result.memory, samples: []}));
  for (const html of [cpu, memory]) {
    assert.ok(html.includes('N/A'));
    assert.ok(!html.includes('role="progressbar"'));
    assert.ok(!html.includes('NaN'));
  }
  const zero = renderToStaticMarkup(createElement(CpuCard, {cpu: result.cpu, samples: []}));
  assert.ok(zero.includes('0.0%'));
  assert.ok(zero.includes('role="progressbar"'));
});
test('formatting handles sub-byte rates, zero and unavailable readings', () => {
  assert.equal(formatBytes(0), '0 B');
  assert.equal(formatBytes(0.5), '1 B');
  assert.equal(formatBytes(-1), 'N/A');
  assert.equal(formatNullable(null, formatPercent), 'N/A');
});
test('API consumes actual new overview and history contracts', async (context) => {
  const original = globalThis.fetch;
  context.after(() => { globalThis.fetch = original; });
  globalThis.fetch = async (url) => new Response(JSON.stringify(String(url).includes('/history')
    ? {range: '1h', start_ms: now - 3600000, end_ms: now, interval_seconds: 3, samples: []}
    : payload()), {status: 200});
  assert.equal((await api.getSystemOverview()).timestamp_ms, now);
  const history = await api.getHistoricalMetrics('1h');
  assert.equal(history.start_ms, now - 3600000);
  assert.equal(history.interval_seconds, 3);
});
test('503 and malformed history responses surface useful errors', async (context) => {
  const original = globalThis.fetch;
  context.after(() => { globalThis.fetch = original; });
  globalThis.fetch = async () => new Response('{}', {status: 503});
  await assert.rejects(api.getSystemOverview(), /採集器/);
  globalThis.fetch = async () => new Response('{"samples":[]}', {status: 200});
  await assert.rejects(api.getHistoricalMetrics('1h'), /格式/);
});
