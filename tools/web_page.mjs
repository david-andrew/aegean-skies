// Where a browser tool opens a built page. A single-file page (`sloppy build --target wasm`)
// opens from disk. A page whose program is a separate file (`--wasm-file`: index.html and
// index.wasm, as the Pages site is built) must come over http, so this serves its folder from
// this same process, on 127.0.0.1 and a free port, with the types a browser needs (application/wasm
// lets it compile while it downloads). The server ends with the tool (close(), or process exit):
// nothing is left running.
import {createServer} from 'node:http';
import {readFileSync, statSync, createReadStream} from 'node:fs';
import {dirname, basename, join, resolve, normalize, extname, sep} from 'node:path';

const TYPES = {'.html': 'text/html; charset=utf-8', '.wasm': 'application/wasm', '.js': 'text/javascript',
  '.json': 'application/json', '.png': 'image/png', '.svg': 'image/svg+xml', '.ico': 'image/x-icon',
  '.webmanifest': 'application/manifest+json', '.bin': 'application/octet-stream', '.css': 'text/css'};

// true when the page's program is a separate file beside it (`--wasm-file`)
export const separateModule = (page) =>
  /<script[^>]*id="sloppy-wasm"[^>]*data-src="/.test(readFileSync(page, 'latin1').slice(0, 400000));

// the module's bytes, from either kind of page
export const pageModule = (page) => {
  const html = readFileSync(page, 'latin1');
  const tag = html.match(/<script[^>]*id="sloppy-wasm"[^>]*>/);
  if (!tag) throw Error(`${page}: no #sloppy-wasm element (built with Sloppy 0.35 or later?)`);
  const src = tag[0].match(/data-src="([^"?]+)/);
  if (src) return readFileSync(join(dirname(page), src[1]));
  const start = tag.index + tag[0].length, end = html.indexOf('</script>', start);
  return Buffer.from(html.slice(start, end).trim(), 'base64');
};

// { url, close }: the address to navigate to (query appended by the caller) and how to stop serving
export const openPage = async (page) => {
  const file = resolve(page);
  if (!separateModule(file)) return {url: 'file://' + file, close: async () => {}};
  const root = dirname(file);
  const server = createServer((req, res) => {
    const path = normalize(join(root, decodeURIComponent(new URL(req.url, 'http://x').pathname)));
    let info = null;
    try { info = path.startsWith(root + sep) && statSync(path).isFile() ? statSync(path) : null; } catch { info = null; }
    if (!info) { res.writeHead(404); res.end(); return; }
    // (cached as GitHub Pages has it: ten minutes, then revalidated by its tag)
    const tag = `"${info.size.toString(16)}-${Math.floor(info.mtimeMs).toString(16)}"`;
    const head = {'Content-Type': TYPES[extname(path)] ?? 'application/octet-stream', 'Cache-Control': 'max-age=600', 'ETag': tag};
    if (req.headers['if-none-match'] === tag) { res.writeHead(304, head); res.end(); return; }
    res.writeHead(200, {...head, 'Content-Length': info.size});
    createReadStream(path).pipe(res);
  });
  await new Promise((done) => server.listen(0, '127.0.0.1', done));
  server.unref();
  return {url: `http://127.0.0.1:${server.address().port}/${basename(file)}`,
    close: () => new Promise((done) => { server.closeAllConnections(); server.close(() => done()); })};
};
