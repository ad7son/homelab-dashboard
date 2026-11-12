import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import ts from 'typescript';

async function load(file) {
  const source = await readFile(new URL('../../projects/system-monitor/frontend/components/health/' + file, import.meta.url), 'utf8');
  const { outputText } = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2023 },
  });
  return import('data:text/javascript;base64,' + Buffer.from(outputText).toString('base64'));
}
const { formatDiagnosticResponse } = await load('diagnosticData.ts');
const { summarizeFeatures } = await load('healthData.ts');

test('complete responses retain all features, errors, zeroes and nested fields', () => {
  const report = { features: [
    { id: 'cpu', raw_data: { usage_percent: 0, temperature: null, nested: [1, 2] }, error: null },
    { id: 'history-write', error: { type: 'OSError', message: 'full', traceback: 'line 1\nline 2' } },
  ] };
  const text = formatDiagnosticResponse(JSON.stringify(report));
  assert.ok(text.includes('\n'));
  assert.deepEqual(JSON.parse(text), report);
});
test('non-JSON errors remain verbatim', () => {
  assert.equal(formatDiagnosticResponse('<html>Gateway error</html>'), '<html>Gateway error</html>');
});
test('counts reflect changing real reports including unavailable hardware', () => {
  const features = [{ status: 'healthy' }, { status: 'issues' }, { status: 'unavailable' }, { status: 'unknown' }];
  assert.deepEqual(summarizeFeatures(features), { healthy: 1, issues: 1, unavailable: 1, unknown: 1 });
  features[1].status = 'healthy';
  assert.deepEqual(summarizeFeatures(features), { healthy: 2, issues: 0, unavailable: 1, unknown: 1 });
});
