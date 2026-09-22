const $ = s => document.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const FIELD_LABEL = {
  n: 'vertices', m: 'edges', maxDeg: 'max degree', minDeg: 'min degree',
  components: 'components', diameter: 'diameter', triangles: 'triangles',
  wiener: 'Wiener index', greedyColors: 'greedy colours', spectralRadius: 'spectral radius',
};

const r = await fetch('data/results.json').then(x => x.json()).catch(() => null);
if (!r) {
  $('#main').innerHTML = `<p class="loading">No run found. Execute <code>python harness/run.py</code> first.</p>`;
} else {
  render(r);
}

function render(r) {
  const live = Object.keys(r.rows);
  const totalChecks = r.corpus_size * (r.fields.int.length + r.fields.float.length);
  const dis = Object.values(r.per_field).reduce((a, v) => a + v.disagreed, 0);
  const worst = r.float_spreads?.[0];

  $('#main').innerHTML = `
    ${headline(r, live, totalChecks, dis)}
    ${matrix(r, live)}
    ${fields(r)}
    ${timing(r, live)}
    ${drift(r, worst)}
    ${explorer(r, live)}
  `;
  wireExplorer(r, live);
}

function headline(r, live, totalChecks, dis) {
  const claim = dis === 0
    ? `<b>${live.length}</b> implementations, <b>${r.corpus_size}</b> graphs,
       <b>${totalChecks.toLocaleString()}</b> comparisons, <b>zero</b> disagreements.`
    : `<b>${dis}</b> disagreement${dis === 1 ? '' : 's'} across
       <b>${totalChecks.toLocaleString()}</b> comparisons.`;
  return `<div class="headline">
    <p class="claim">${claim}</p>
    <p class="sub">Python, JavaScript, C++, Rust and Java each implement the same eight graph
    quantities against one pinned contract — including a greedy colouring fixed to a specific
    vertex order and a power iteration specified down to the iteration count, so that any
    difference is a bug rather than a defensible choice.</p>
    <p class="stamp">last run ${esc(r.generated)}</p>
  </div>`;
}

function matrix(r, live) {
  const head = `<tr><th>agrees with →</th>${live.map(i => `<th>${esc(r.impls[i].label)}</th>`).join('')}</tr>`;
  const body = live.map(a => {
    const tds = live.map(b => {
      const p = r.pair_agree[`${a}|${b}`];
      if (!p) return '<td>—</td>';
      if (a === b) return `<td class="self">${p.total}</td>`;
      const full = p.same === p.total;
      return `<td class="${full ? 'agree' : 'differ'}">${p.same}/${p.total}</td>`;
    }).join('');
    return `<tr><th>${esc(r.impls[a].label)}</th>${tds}</tr>`;
  }).join('');
  return `<section><h2>Who agrees with whom</h2>
    <p class="lede">Graphs on which two implementations produce identical results for every
    integer quantity and a spectral radius within ${r.fields.float_tol}.</p>
    <table class="grid"><thead>${head}</thead><tbody>${body}</tbody></table></section>`;
}

function fields(r) {
  const rows = Object.entries(r.per_field).map(([f, v]) => {
    const ok = v.disagreed === 0;
    return `<tr><th>${esc(FIELD_LABEL[f] || f)}</th>
      <td>${v.checked}</td>
      <td class="${ok ? 'agree' : 'differ'}">${v.disagreed}</td></tr>`;
  }).join('');
  return `<section><h2>By quantity</h2>
    <p class="lede">Each row is one quantity, checked on every graph in the corpus across every
    implementation that ran.</p>
    <table class="grid"><thead><tr><th>Quantity</th><th>Graphs checked</th><th>Disagreements</th></tr></thead>
    <tbody>${rows}</tbody></table></section>`;
}

function timing(r, live) {
  const ms = live.map(i => r.impls[i]);
  const max = Math.max(...ms.map(m => m.median_ms));
  const bars = live.map(i => {
    const m = r.impls[i];
    const sw = (m.startup_ms / max) * 100, cw = (m.compute_ms / max) * 100;
    return `<div class="name">${esc(m.label)}</div>
      <div class="track">
        <div class="seg-start" style="width:${sw.toFixed(1)}%"></div>
        <div class="seg-comp" style="width:${cw.toFixed(1)}%"></div>
      </div>
      <div class="val">${m.compute_ms} ms</div>`;
  }).join('');
  return `<section><h2>What it costs</h2>
    <p class="lede">Median of five runs over the whole corpus. Process startup is measured
    separately with an empty input and shown apart from compute, because at this corpus size
    the JVM and node spend more time starting than working — reporting only the total would
    make them look slower than they are.</p>
    <div class="bars">${bars}</div>
    <div class="legend"><span><i class="a"></i>startup</span><span><i class="b"></i>compute</span></div>
  </section>`;
}

function drift(r, worst) {
  if (!worst) return '';
  const rows = r.float_spreads.slice(0, 8).map(s =>
    `<tr><th>${esc(s.graph)}</th><td>${s.spread.toExponential(3)}</td></tr>`).join('');
  return `<section><h2>Where the languages actually differ</h2>
    <p class="lede">Every integer quantity matches exactly. The spectral radius does not, and
    cannot: five languages summing the same doubles in the same order still land on slightly
    different bits, because each is free to use wider intermediate precision or fuse a
    multiply-add. The widest spread across the whole corpus is
    <code>${worst.spread.toExponential(3)}</code> — around ${Math.round(worst.spread / 2.22e-16)} units
    in the last place, which is what "the same algorithm" means in floating point.</p>
    <table class="grid"><thead><tr><th>Graph</th><th>Spread across implementations</th></tr></thead>
    <tbody>${rows}</tbody></table></section>`;
}

function explorer(r, live) {
  const ids = Object.keys(r.rows[live[0]] || {});
  return `<section><h2>Look at one graph</h2>
    <p class="lede">Every implementation's full output for a single graph, side by side.</p>
    <div class="picker">
      <select id="pick">${ids.map(i => `<option value="${esc(i)}">${esc(i)}</option>`).join('')}</select>
      <span class="drift" id="g6"></span>
    </div>
    <div id="cmp"></div></section>`;
}

function wireExplorer(r, live) {
  const sel = $('#pick');
  if (!sel) return;
  const draw = () => {
    const gid = sel.value;
    const fs = [...r.fields.int, ...r.fields.float];
    const head = `<tr><th>Quantity</th>${live.map(i => `<th>${esc(r.impls[i].label)}</th>`).join('')}</tr>`;
    const body = fs.map(f => {
      const vals = live.map(i => r.rows[i][gid]?.[f]);
      const nums = vals.filter(v => typeof v === 'number');
      const same = f === 'spectralRadius'
        ? (Math.max(...nums) - Math.min(...nums)) <= r.fields.float_tol
        : new Set(vals).size <= 1;
      const tds = vals.map(v => `<td class="${same ? '' : 'differ'}">${
        typeof v === 'number' && f === 'spectralRadius' ? v.toFixed(12) : esc(v)}</td>`).join('');
      return `<tr><th>${esc(FIELD_LABEL[f] || f)}</th>${tds}</tr>`;
    }).join('');
    $('#cmp').innerHTML = `<table class="grid"><thead>${head}</thead><tbody>${body}</tbody></table>`;
    const dis = r.disagreements.find(d => d.graph === gid);
    $('#g6').innerHTML = dis ? `graph6 <code>${esc(dis.g6)}</code>` : '';
  };
  sel.onchange = draw;
  draw();
}
