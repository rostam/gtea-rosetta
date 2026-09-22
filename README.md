# GTea Rosetta

The same graph algorithms implemented five times — Python, JavaScript, C++, Rust, Java —
run against one pinned contract and compared, quantity by quantity.

**[See the last run →](https://rostam.github.io/gtea-rosetta/)**

There are five graph libraries in this account:
[GraphTea](https://github.com/rostam/GraphTea) (Java),
[CGTea](https://github.com/rostam/CGTea) (C++),
[rust_gtea](https://github.com/rostam/rust_gtea) (Rust),
[WASMTea](https://github.com/rostam/WASMTea) (Rust/WASM) and
[GSearchTea](https://github.com/rostam/GSearchTea) (Flink). They were ported from one
another and have drifted apart since, and nothing anywhere checks that they still agree.
This is the harness that would catch it.

## The result

**5 implementations · 110 graphs · 1,100 comparisons · 0 disagreements** on every
integer quantity.

The one place they genuinely differ is the spectral radius, and it cannot be fixed. Five
languages summing the same doubles in the same specified order still land on different
bits, because each is free to use wider intermediate precision or fuse a multiply-add.
The widest spread across the corpus is about **3.6 × 10⁻¹⁵** — roughly 16 units in the
last place. That is what "the same algorithm" means in floating point, and the dashboard
shows it rather than rounding it away.

## The contract

Every implementation is a filter: graph6 on stdin, one JSON object per line on stdout.
Eight quantities — order, size, degrees, components, diameter, triangles, Wiener index,
greedy colouring, spectral radius.

Two of them are pinned deliberately so that disagreement can only mean a bug:

- **Greedy colouring** is fixed to vertex order 0, 1, …, n−1. It is *not* the chromatic
  number. Every implementation must return the same count.
- **Power iteration** is specified down to the starting vector, the iteration count
  (1000), the summation order, and the bail-out threshold.

Full contract in [`spec/spec.md`](spec/spec.md).

## Running it

```bash
python3 harness/run.py
```

It builds what needs building, runs each implementation five times over the corpus,
separates process startup from compute (at this corpus size the JVM and node spend more
time starting than working — reporting only wall time would libel them), compares
everything against everything, and writes `docs/data/results.json`.

An implementation whose toolchain is missing is reported as unavailable rather than
failing the run. [CI](.github/workflows/rosetta.yml) runs the whole thing weekly and
fails the build on any disagreement.

## What it costs

Compute time over the 110-graph corpus, median of five runs, startup excluded:

| | compute |
| --- | ---: |
| Rust (release) | 9.2 ms |
| C++ (g++ -O2) | 10.1 ms |
| JavaScript (node 24) | 76.5 ms |
| Java 21 | 77.0 ms |
| Python 3.12 | 176.9 ms |

Three tiers, and the pairs inside each tier are close enough to be a tie. The corpus is
small on purpose — this is a conformance harness first and a benchmark second.

## Adding an implementation

Write something that satisfies the contract, drop it in `impl/<lang>/`, and add an entry
to `IMPLS` in `harness/run.py` with its build and run commands. Pointing one of those
entries at a real GTea build instead of the reference implementation here is the whole
reason the harness exists.

## Layout

```
spec/spec.md       the contract
spec/corpus.json   110 graphs: sampled from nauty-geng plus 18 named graphs
impl/{python,js,cpp,rust,java}/
harness/run.py     build, run, time, compare
docs/              the dashboard
```
