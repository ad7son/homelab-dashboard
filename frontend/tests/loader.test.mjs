import test from 'node:test';
import assert from 'node:assert/strict';
import { loadShell, manifest } from './helpers.mjs';

const { loadProjects, loadDiscoveredProjects } = await loadShell('plugins/loader.ts');
const key = (id) => `/projects/${id}/project.json`;
const frontend = (id) => `/projects/${id}/frontend/index.tsx`;

test('discovery is lazy, sorts enabled projects and tolerates disabled projects without an entry', async () => {
  let loads = 0;
  const load = async () => { loads++; return {default: {routes: []}}; };
  const projects = loadProjects({
    [key('beta')]: manifest('beta'), [key('alpha')]: manifest('alpha'),
    [key('disabled')]: manifest('disabled', {enabled: false}),
  }, {[frontend('beta')]: load, [frontend('alpha')]: load});
  assert.deepEqual(projects.map(project => project.manifest.id), ['alpha', 'beta']);
  assert.equal(loads, 0);
  assert.deepEqual(await projects[0].loadFrontend(), {routes: []});
  assert.equal(loads, 1);
});

test('a missing entry or invalid disabled manifest fails the whole discovery batch', () => {
  assert.throws(() => loadProjects({[key('alpha')]: manifest()}, {}), /missing frontend/);
  assert.throws(() => loadProjects({[key('alpha')]: manifest('alpha', {enabled: false, schemaVersion: 2})}, {}), /schemaVersion/);
  assert.deepEqual(loadProjects({}, {}), []);
});

test('enabled projects cannot share current or legacy route and API prefixes', () => {
  const entries = {[frontend('alpha')]: async () => ({}), [frontend('beta')]: async () => ({})};
  for (const overrides of [{routeBase: '/alpha'}, {legacyRouteBases: ['/alpha']},
    {apiPrefix: '/api/alpha'}, {legacyApiPrefix: '/api/alpha'}]) {
    assert.throws(() => loadProjects({[key('alpha')]: manifest(), [key('beta')]: manifest('beta', overrides)}, entries), /duplicate/);
  }
});

test('module load failure can be retried and malformed module exports are rejected', async () => {
  let attempts = 0;
  const [project] = loadProjects({[key('alpha')]: manifest()}, {
    [frontend('alpha')]: async () => {
      if (++attempts === 1) throw new Error('network unavailable');
      return {default: {routes: []}};
    },
  });
  await assert.rejects(project.loadFrontend(), /network unavailable/);
  assert.deepEqual(await project.loadFrontend(), {routes: []});
  const [broken] = loadProjects({[key('alpha')]: manifest()}, {
    [frontend('alpha')]: async () => ({default: {routes: 'wrong'}}),
  });
  await assert.rejects(broken.loadFrontend(), /default-export/);
});

test('discovery reports configuration errors rather than presenting a successful empty registry', (context) => {
  const original = console.error;
  console.error = () => {};
  context.after(() => { console.error = original; });
  const result = loadDiscoveredProjects({[key('alpha')]: manifest('alpha', {schemaVersion: 2})}, {});
  assert.deepEqual(result.projects, []);
  assert.match(result.error, /schemaVersion/);
});
