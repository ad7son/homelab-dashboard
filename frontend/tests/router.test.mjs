import test from 'node:test';
import assert from 'node:assert/strict';
import { createElement } from 'react';
import { matchRoutes, MemoryRouter } from 'react-router-dom';
import { renderToStaticMarkup } from 'react-dom/server';
import { loadShell, manifest } from './helpers.mjs';

const { createPlatformRoutes } = await loadShell('router.tsx');
const { loadProjects } = await loadShell('plugins/loader.ts');
const { ProjectRegistryProvider } = await loadShell('plugins/registry.tsx');
const { HomePage } = await loadShell('pages/HomePage.tsx');
const { ProjectErrorBoundary } = await loadShell('components/project/ProjectErrorBoundary.tsx');
const [project] = loadProjects({'/projects/alpha/project.json': manifest('alpha', {legacyRouteBases: ['/old']})},
  {'/projects/alpha/frontend/index.tsx': async () => ({default: {routes: []}})});
const routes = createPlatformRoutes({projects: [project], error: null});

function render(element, value = {projects: [], error: null}, path = '/') {
  return renderToStaticMarkup(createElement(MemoryRouter, {initialEntries: [path]},
    createElement(ProjectRegistryProvider, {value}, element)));
}

test('platform routes keep settings, project children, aliases and 404 reachable', () => {
  for (const [path, expected] of [['/settings', 'settings'], ['/alpha/jobs/one', 'alpha/*'],
    ['/old', 'old'], ['/old/jobs', 'old/*'], ['/missing', '*']]) {
    assert.equal(matchRoutes(routes, path).at(-1).route.path, expected);
  }
});

test('legacy redirect preserves nested paths, query strings and hashes', () => {
  const route = matchRoutes(routes, '/old/jobs').at(-1).route;
  // 以路由元件的實際輸出驗證 Navigate 的目標，沒有另外複製轉址邏輯。
  const element = route.element;
  let redirect;
  function Inspect() {
    redirect = element.type(element.props);
    return null;
  }
  render(createElement(Inspect), undefined, '/old/jobs?range=1h#details');
  assert.equal(redirect.props.to, '/alpha/jobs?range=1h#details');
});

test('home distinguishes no enabled projects from invalid configuration', () => {
  assert.match(render(createElement(HomePage)), /No projects enabled/);
  const html = render(createElement(HomePage), {projects: [], error: 'Broken manifest'});
  assert.match(html, /Broken manifest/);
  assert.match(html, /Open Settings/);
});

test('project errors retain shell navigation links and expose a retry callback', () => {
  let retries = 0;
  const boundary = new ProjectErrorBoundary({children: 'content', onRetry: () => retries++});
  boundary.state = ProjectErrorBoundary.getDerivedStateFromError(new Error('Module failed'));
  const content = boundary.render();
  const html = render(content);
  assert.match(html, /Module failed/);
  assert.match(html, /Retry/);
  assert.match(html, /Back to home/);
  assert.match(html, /Settings/);
  const button = content.props.children.find(child => child?.type === 'button');
  button.props.onClick();
  assert.equal(retries, 1);
});
