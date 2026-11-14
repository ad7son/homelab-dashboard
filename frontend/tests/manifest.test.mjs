import test from 'node:test';
import assert from 'node:assert/strict';
import { loadShell, manifest } from './helpers.mjs';

const { validateManifest } = await loadShell('plugins/manifest.ts');
function validate(value) {
  return validateManifest(value, value?.id ?? 'alpha', 'project.json');
}

test('manifest applies defaults and preserves independent project package names', () => {
  const result = validate(manifest());
  assert.equal(result.enabled, true);
  assert.deepEqual(result.legacyRouteBases, []);
  assert.equal(result.legacyApiPrefix, null);
  assert.equal(result.nav.items[0].end, false);
  assert.equal(result.pythonPackage, 'src');
});

test('manifest rejects invalid identity, unknown fields and unsupported schema', () => {
  for (const value of [null, [], manifest('Alpha'), manifest('alpha', {schemaVersion: 2}),
    manifest('alpha', {unexpected: true}), manifest('alpha', {pythonPackage: 'class'})]) {
    assert.throws(() => validate(value));
  }
  assert.throws(() => validateManifest(manifest(), 'beta', 'project.json'), /directory/);
});

test('platform paths and unsafe paths cannot be claimed by a project', () => {
  for (const routeBase of ['/settings', '/settings/private', '/', '/alpha/../beta', '/alpha%2Fbeta']) {
    assert.throws(() => validate(manifest('alpha', {routeBase})));
  }
  for (const apiPrefix of ['/api', '/api/health', '/api/project-health', '/api/project-health/alpha', '/api/logs']) {
    assert.throws(() => validate(manifest('alpha', {apiPrefix})));
  }
});

test('legacy aliases are validated and root API compatibility is exclusive to System Monitor', () => {
  assert.equal(validate(manifest('system-monitor', {legacyApiPrefix: '/api'})).legacyApiPrefix, '/api');
  assert.throws(() => validate(manifest('alpha', {legacyApiPrefix: '/api'})));
  for (const legacyRouteBases of [['/alpha'], ['/alpha/child'], ['/old', '/old'], ['/settings']]) {
    assert.throws(() => validate(manifest('alpha', {legacyRouteBases})));
  }
});

test('navigation rejects duplicate paths, invalid icons, empty items and invalid booleans', () => {
  const nav = manifest().nav;
  for (const changed of [{...nav, items: []}, {...nav, order: true},
    {...nav, items: [nav.items[0], nav.items[0]]},
    {...nav, items: [{...nav.items[0], icon: 'unknown'}]},
    {...nav, items: [{...nav.items[0], path: '../escape'}]},
    {...nav, items: [{...nav.items[0], end: 'yes'}]}]) {
    assert.throws(() => validate(manifest('alpha', {nav: changed})));
  }
});
