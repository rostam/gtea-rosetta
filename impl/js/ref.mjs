/* JavaScript implementation of the GTea Rosetta contract. */
import { createInterface } from 'node:readline';

const ITERS = 1000;

function decode(s) {
  const b = [...s].map(c => c.charCodeAt(0) - 63);
  let n, p;
  if (b[0] === 63) { n = (b[1] << 12) | (b[2] << 6) | b[3]; p = 4; }
  else { n = b[0]; p = 1; }
  const adj = Array.from({ length: n }, () => []);
  let bit = 0;
  for (let j = 1; j < n; j++) {
    for (let i = 0; i < j; i++) {
      if ((b[p + ((bit / 6) | 0)] >> (5 - (bit % 6))) & 1) { adj[i].push(j); adj[j].push(i); }
      bit++;
    }
  }
  for (const a of adj) a.sort((x, y) => x - y);
  return { n, adj };
}

function bfs(n, adj, src) {
  const dist = new Int32Array(n).fill(-1);
  dist[src] = 0;
  const q = [src];
  for (let h = 0; h < q.length; h++) {
    const v = q[h];
    for (const w of adj[v]) if (dist[w] < 0) { dist[w] = dist[v] + 1; q.push(w); }
  }
  return dist;
}

function analyse(id, s) {
  const { n, adj } = decode(s);
  const degs = adj.map(a => a.length);
  const m = degs.reduce((a, b) => a + b, 0) / 2;

  const seen = new Uint8Array(n);
  let components = 0;
  for (let v = 0; v < n; v++) {
    if (seen[v]) continue;
    components++;
    const d = bfs(n, adj, v);
    for (let w = 0; w < n; w++) if (d[w] >= 0) seen[w] = 1;
  }

  let diameter = -1, wiener = -1;
  if (components === 1) {
    diameter = 0; let total = 0;
    for (let v = 0; v < n; v++) {
      const d = bfs(n, adj, v);
      for (let w = 0; w < n; w++) { if (d[w] > diameter) diameter = d[w]; total += d[w]; }
    }
    wiener = total / 2;
  }

  const nbr = adj.map(a => new Set(a));
  let triangles = 0;
  for (let v = 0; v < n; v++) {
    for (const w of adj[v]) {
      if (w <= v) continue;
      for (const u of adj[w]) if (u > w && nbr[v].has(u)) triangles++;
    }
  }

  const color = new Int32Array(n).fill(-1);
  for (let v = 0; v < n; v++) {
    const used = new Set();
    for (const w of adj[v]) if (color[w] >= 0) used.add(color[w]);
    let c = 0;
    while (used.has(c)) c++;
    color[v] = c;
  }
  const greedyColors = n ? Math.max(...color) + 1 : 0;

  let x = new Float64Array(n).fill(1 / Math.sqrt(n));
  let rho = 0, dead = false;
  for (let it = 0; it < ITERS; it++) {
    const y = new Float64Array(n);
    for (let v = 0; v < n; v++) { let t = 0; for (const w of adj[v]) t += x[w]; y[v] = t; }
    let nr = 0; for (let v = 0; v < n; v++) nr += y[v] * y[v];
    nr = Math.sqrt(nr);
    if (nr < 1e-12) { dead = true; break; }
    for (let v = 0; v < n; v++) y[v] /= nr;
    x = y;
  }
  if (!dead) for (let v = 0; v < n; v++) { let t = 0; for (const w of adj[v]) t += x[w]; rho += x[v] * t; }

  return { id, n, m, maxDeg: Math.max(...degs), minDeg: Math.min(...degs),
           components, diameter, triangles, wiener, greedyColors, spectralRadius: rho };
}

const rl = createInterface({ input: process.stdin });
const out = [];
for await (const line of rl) {
  const t = line.trim();
  if (!t) continue;
  const sp = t.indexOf(' ');
  out.push(JSON.stringify(analyse(t.slice(0, sp), t.slice(sp + 1).trim())));
}
process.stdout.write(out.join('\n') + '\n');
