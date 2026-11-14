import test from 'node:test';
import assert from 'node:assert/strict';
import { loadShell, manifest } from './helpers.mjs';

const { buildProjectNavigation, documentTitleForPath } = await loadShell('plugins/navigation.ts');
const { validateManifest } = await loadShell('plugins/manifest.ts');
function project(id, overrides = {}) {
  return {manifest: validateManifest(manifest(id, overrides), id, 'project.json')};
}

test('navigation groups sections, uses the lowest group order and joins child paths', () => {
  const projects = [project('alpha'), project('beta', {
    nav: {section: 'Projects', order: 5, items: [{path: 'jobs', label: 'Jobs', icon: 'bot', documentTitle: 'Jobs'}]},
  }), project('gamma', {nav: {section: 'First', order: 1, items: [manifest('gamma').nav.items[0]]}})];
  const sections = buildProjectNavigation(projects);
  assert.deepEqual(sections.map(section => section.section), ['First', 'Projects']);
  assert.equal(sections[1].order, 5);
  assert.deepEqual(sections[1].links.map(link => link.to), ['/alpha', '/beta/jobs']);
  assert.equal(projects[0].manifest.nav.order, 10);
});

test('page titles use the longest matching path and respect exact links', () => {
  const links = [{to: '/alpha', end: false, documentTitle: 'Alpha'},
    {to: '/alpha/jobs', end: false, documentTitle: 'Jobs'},
    {to: '/exact', end: true, documentTitle: 'Exact'}];
  assert.equal(documentTitleForPath('/alpha/jobs/one', links, null), 'Jobs · A7LAS');
  assert.equal(documentTitleForPath('/exact/child', links, null), 'Page Not Found · A7LAS');
  assert.equal(documentTitleForPath('/alphabet', links, null), 'Page Not Found · A7LAS');
  assert.equal(documentTitleForPath('/settings', links, null), 'Settings · A7LAS');
  assert.equal(documentTitleForPath('/', [], null), 'No projects enabled · A7LAS');
  assert.equal(documentTitleForPath('/', [], 'invalid manifest'), 'Projects could not be loaded · A7LAS');
});
