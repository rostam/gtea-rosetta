//! Rust implementation of the GTea Rosetta contract.
//! stdin: "<id> <graph6>" per line. stdout: one JSON object per line.

use std::collections::VecDeque;
use std::io::{self, BufRead, Write};

const ITERS: usize = 1000;

fn decode(s: &str) -> (usize, Vec<Vec<usize>>) {
    let b: Vec<i64> = s.bytes().map(|c| c as i64 - 63).collect();
    let (n, p) = if b[0] == 63 {
        (((b[1] << 12) | (b[2] << 6) | b[3]) as usize, 4usize)
    } else {
        (b[0] as usize, 1usize)
    };
    let mut adj = vec![Vec::new(); n];
    let mut bit = 0usize;
    for j in 1..n {
        for i in 0..j {
            let byte = b[p + bit / 6];
            if (byte >> (5 - (bit % 6))) & 1 == 1 {
                adj[i].push(j);
                adj[j].push(i);
            }
            bit += 1;
        }
    }
    for a in adj.iter_mut() {
        a.sort_unstable();
    }
    (n, adj)
}

fn bfs(n: usize, adj: &[Vec<usize>], src: usize) -> Vec<i64> {
    let mut dist = vec![-1i64; n];
    dist[src] = 0;
    let mut q = VecDeque::new();
    q.push_back(src);
    while let Some(v) = q.pop_front() {
        for &w in &adj[v] {
            if dist[w] < 0 {
                dist[w] = dist[v] + 1;
                q.push_back(w);
            }
        }
    }
    dist
}

fn analyse(id: &str, s: &str) -> String {
    let (n, adj) = decode(s);
    let degs: Vec<usize> = adj.iter().map(|a| a.len()).collect();
    let m: usize = degs.iter().sum::<usize>() / 2;

    let mut seen = vec![false; n];
    let mut components = 0;
    for v in 0..n {
        if seen[v] {
            continue;
        }
        components += 1;
        for (w, d) in bfs(n, &adj, v).iter().enumerate() {
            if *d >= 0 {
                seen[w] = true;
            }
        }
    }

    let (mut diameter, mut wiener) = (-1i64, -1i64);
    if components == 1 {
        diameter = 0;
        let mut total = 0i64;
        for v in 0..n {
            for d in bfs(n, &adj, v) {
                if d > diameter {
                    diameter = d;
                }
                total += d;
            }
        }
        wiener = total / 2;
    }

    let mut triangles = 0i64;
    for v in 0..n {
        for &w in &adj[v] {
            if w <= v {
                continue;
            }
            for &u in &adj[w] {
                if u > w && adj[v].binary_search(&u).is_ok() {
                    triangles += 1;
                }
            }
        }
    }

    let mut color = vec![-1i64; n];
    for v in 0..n {
        let mut used: Vec<i64> = adj[v].iter().map(|&w| color[w]).filter(|&c| c >= 0).collect();
        used.sort_unstable();
        let mut c = 0i64;
        while used.binary_search(&c).is_ok() {
            c += 1;
        }
        color[v] = c;
    }
    let greedy = if n > 0 { color.iter().max().unwrap() + 1 } else { 0 };

    let mut x = vec![1.0f64 / (n as f64).sqrt(); n];
    let mut rho = 0.0f64;
    let mut dead = false;
    for _ in 0..ITERS {
        let mut y = vec![0.0f64; n];
        for v in 0..n {
            let mut t = 0.0f64;
            for &w in &adj[v] {
                t += x[w];
            }
            y[v] = t;
        }
        let nr = y.iter().map(|t| t * t).sum::<f64>().sqrt();
        if nr < 1e-12 {
            dead = true;
            break;
        }
        for t in y.iter_mut() {
            *t /= nr;
        }
        x = y;
    }
    if !dead {
        for v in 0..n {
            let mut t = 0.0f64;
            for &w in &adj[v] {
                t += x[w];
            }
            rho += x[v] * t;
        }
    }

    format!(
        "{{\"id\":\"{}\",\"n\":{},\"m\":{},\"maxDeg\":{},\"minDeg\":{},\"components\":{},\
\"diameter\":{},\"triangles\":{},\"wiener\":{},\"greedyColors\":{},\"spectralRadius\":{:.17}}}",
        id, n, m,
        degs.iter().max().unwrap_or(&0),
        degs.iter().min().unwrap_or(&0),
        components, diameter, triangles, wiener, greedy, rho
    )
}

fn main() {
    let stdin = io::stdin();
    let stdout = io::stdout();
    let mut out = io::BufWriter::new(stdout.lock());
    for line in stdin.lock().lines() {
        let line = line.unwrap();
        let t = line.trim();
        if t.is_empty() {
            continue;
        }
        let mut it = t.splitn(2, char::is_whitespace);
        let id = it.next().unwrap();
        let g6 = it.next().unwrap_or("").trim();
        writeln!(out, "{}", analyse(id, g6)).unwrap();
    }
}
