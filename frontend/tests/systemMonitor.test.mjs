import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import ts from 'typescript';
import { createElement } from 'react';
import { MemoryRouter } from 'react-router-dom';
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
    if (specifier.startsWith('.') || specifier.startsWith('@shell/')) {
      const path = specifier.startsWith('@shell/')
        ? new URL('../src/' + specifier.slice(7), import.meta.url) : new URL(specifier, url);
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
const { parseOverview, getOverview } = await load('api/overview.ts');
const { sampleStatus } = await load('hooks/useOverview.ts');
const { getHistory, parseHistory } = await load('api/history.ts');
const { getProjectHealth } = await load('api/health.ts');
const { requestJson } = await load('api/client.ts');
const { mergeRealtimeSample } = await load('utils/realtimeSamples.ts');
const { historicalSamplesToChartPoints } = await load('components/charts/chartUtils.ts');
const { averageRecentMetric } = await load('utils/realtimeAverages.ts');
const { formatBytes, formatNullable, formatPercent } = await load('utils/format.ts');
const { CpuCard } = await load('components/metrics/CpuCard.tsx');
const { MemoryCard } = await load('components/metrics/MemoryCard.tsx');
const { OverviewPage } = await load('pages/OverviewPage.tsx');
const { OverviewHeader } = await load('components/OverviewHeader.tsx');
const { GpuCard } = await load('components/metrics/GpuCard.tsx');
const { DiskIoCard } = await load('components/metrics/DiskIoCard.tsx');

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
  assert.equal((await getOverview()).timestamp_ms, now);
  const history = await getHistory('1h');
  assert.equal(history.start_ms, now - 3600000);
  assert.equal(history.interval_seconds, 3);
});
test('503 and malformed history responses surface useful errors', async (context) => {
  const original = globalThis.fetch;
  context.after(() => { globalThis.fetch = original; });
  globalThis.fetch = async () => new Response('{}', {status: 503});
  await assert.rejects(getOverview(), /採集器/);
  globalThis.fetch = async () => new Response('{"samples":[]}', {status: 200});
  await assert.rejects(getHistory('1h'), /格式/);
});


const { ProjectHealthSection } = await load('components/health/ProjectHealthSection.tsx');
const { FeatureDiagnostics } = await load('components/health/FeatureDiagnostics.tsx');
const feature = {
  id: 'query', name: 'Query', description: 'Actual query results', criteria: 'Last execution',
  status: 'unknown', message: 'Never executed', checked_at_ms: now, last_success_at_ms: null,
  duration_ms: null, source: 'platform event log', raw_data: {last_event: null}, error: null,
};

test('health overview automatically renders other registered projects', () => {
  const projects = [
    {project_id: 'system-monitor', project_name: 'System Monitor', checked_at_ms: now, features: [feature]},
    {project_id: 'new-project', project_name: 'New Project', checked_at_ms: now, features: []},
  ];
  const html = renderToStaticMarkup(createElement(MemoryRouter, null,
    createElement(ProjectHealthSection, {health: {projects, data: null, error: null, loading: false, refresh() {}}})));
  assert.ok(html.includes('New Project'));
  assert.ok(html.includes('/system-monitor/health/new-project'));
  assert.ok(html.includes('尚未宣告監測功能'));
  assert.ok(!html.includes('尚未啟用'));
});
test('diagnostics point at the shared API and show unknown execution time honestly', () => {
  const html = renderToStaticMarkup(createElement(FeatureDiagnostics, {
    feature, report: {project_id: 'new-project', project_name: 'New Project', checked_at_ms: now, features: [feature]},
    onRefresh() {}, refreshing: false,
  }));
  assert.ok(html.includes('/api/project-health/new-project'));
  assert.ok(html.includes('尚無執行紀錄'));
  assert.ok(!html.includes('/feature-health'));
});

test('initial overview keeps header, all cards, chart controls and health summary without data', () => {
  const html = renderToStaticMarkup(createElement(MemoryRouter, null, createElement(OverviewPage)));
  for (const label of ['System Monitor', 'Machine State', 'CPU', 'Memory', 'GPU', 'Disk I/O',
    'Monitoring metric', 'Live', 'History', 'Project Health', 'Summary', 'Loading host data']) {
    assert.ok(html.includes(label), `missing ${label}`);
  }
  assert.ok(!html.includes('connection-banner'));
  assert.ok(!html.includes('homelab-load-state'));
  assert.ok(!html.includes('role="progressbar"'));
});

test('missing host data keeps each card with a placeholder and an appropriate reason', () => {
  for (const Component of [CpuCard, MemoryCard, GpuCard, DiskIoCard]) {
    const html = renderToStaticMarkup(createElement(Component, {
      samples: [], emptyMessage: 'Host data unavailable',
    }));
    assert.ok(html.includes('—'));
    assert.ok(html.includes('Host data unavailable'));
    assert.ok(!html.includes('0.0%'));
    assert.ok(!html.includes('role="progressbar"'));
    assert.ok(!html.includes('monitoring not supported'));
  }
});

test('header owns connection errors and still shows the last real sampling time', () => {
  const html = renderToStaticMarkup(createElement(OverviewHeader, {
    status: 'stale', lastUpdated: new Date(now), loading: false,
    error: 'Connection failed', onRefresh() {},
  }));
  assert.ok(html.includes('Stale'));
  assert.ok(html.includes('Sampled at'));
  assert.ok(html.includes('role="alert"'));
  assert.ok(html.includes('Connection failed'));
  assert.ok(html.includes('Refresh System Monitor'));
});

test('HTTP client distinguishes a timeout from caller cancellation and avoids an already cancelled fetch', async (context) => {
  const original = globalThis.fetch;
  context.after(() => { globalThis.fetch = original; });
  let calls = 0;
  globalThis.fetch = (_url, { signal }) => {
    calls++;
    return new Promise((_resolve, reject) => {
      signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')), { once: true });
    });
  };
  await assert.rejects(requestJson('/timeout', { timeoutMs: 5 }), /timed out/);
  const controller = new AbortController();
  const pending = requestJson('/cancel', { signal: controller.signal });
  controller.abort();
  await assert.rejects(pending, { name: 'AbortError' });
  assert.equal(calls, 2);
  await assert.rejects(requestJson('/already-cancelled', { signal: controller.signal }), { name: 'AbortError' });
  assert.equal(calls, 2);
});

test('history validation rejects malformed individual samples before they reach the chart', () => {
  const body = { range: '1h', start_ms: now - 3600000, end_ms: now, interval_seconds: 3,
    samples: [{ timestamp_ms: now }] };
  for (const samples of [[null], [{timestamp_ms: 'wrong'}], body.samples]) {
    assert.throws(() => parseHistory({...body, samples}), /格式/);
  }
  const valid = {timestamp_ms: now, cpu_usage_percent: 0, cpu_temperature_celsius: null,
    memory_usage_percent: null, network_download_bytes_per_second: 0,
    network_upload_bytes_per_second: null, gpu_usage_percent: null,
    disk_read_bytes_per_second: null, disk_write_bytes_per_second: null};
  assert.equal(parseHistory({...body, samples: [valid]}).samples[0].cpu_usage_percent, 0);
});

test('health API handles list and detail, rejects malformed diagnostics and mismatched project IDs', async (context) => {
  const original = globalThis.fetch;
  context.after(() => { globalThis.fetch = original; });
  const report = {project_id: 'new-project', project_name: 'New Project', checked_at_ms: now, features: [feature]};
  globalThis.fetch = async () => new Response(JSON.stringify({projects: [report]}));
  assert.equal((await getProjectHealth())[0].features[0].duration_ms, null);
  globalThis.fetch = async () => new Response(JSON.stringify(report));
  assert.equal((await getProjectHealth('new-project'))[0].project_id, 'new-project');
  await assert.rejects(getProjectHealth('other-project'), /格式/);
  for (const broken of [null, {...feature, error: undefined}, {...feature, message: 123}]) {
    globalThis.fetch = async () => new Response(JSON.stringify({...report, features: [broken]}));
    await assert.rejects(getProjectHealth('new-project'), /格式/);
  }
  globalThis.fetch = async () => new Response('{}', {status: 404});
  await assert.rejects(getProjectHealth('missing'), /找不到/);
});
