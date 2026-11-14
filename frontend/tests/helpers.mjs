import { readFile } from 'node:fs/promises';
import ts from 'typescript';

// 以現有 TypeScript 編譯器載入原始碼，不另引入測試框架或複製實作。
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
export async function loadSource(url) {
  return import(await moduleUrl(url));
}

export function loadShell(name) {
  return loadSource(new URL('../src/' + name, import.meta.url));
}

export function manifest(id = 'alpha', overrides = {}) {
  return {
    schemaVersion: 1, id, name: id, pythonPackage: 'src',
    routeBase: '/' + id, apiPrefix: '/api/' + id,
    nav: {section: 'Projects', order: 10, items: [
      {path: '', label: id, icon: 'activity', documentTitle: id},
    ]},
    ...overrides,
  };
}
