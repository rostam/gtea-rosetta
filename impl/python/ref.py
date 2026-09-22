"""Python implementation of the GTea Rosetta contract. stdin: graph6, stdout: JSON lines."""
import json
import math
import sys
from collections import deque

ITERS = 1000


def decode(s):
    b = [ord(c) - 63 for c in s]
    if b[0] == 63:
        n = (b[1] << 12) | (b[2] << 6) | b[3]
        p = 4
    else:
        n = b[0]
        p = 1
    adj = [[] for _ in range(n)]
    bit = 0
    for j in range(1, n):
        for i in range(j):
            if (b[p + bit // 6] >> (5 - bit % 6)) & 1:
                adj[i].append(j)
                adj[j].append(i)
            bit += 1
    for a in adj:
        a.sort()
    return n, adj


def bfs(n, adj, src):
    dist = [-1] * n
    dist[src] = 0
    q = deque([src])
    while q:
        v = q.popleft()
        for w in adj[v]:
            if dist[w] < 0:
                dist[w] = dist[v] + 1
                q.append(w)
    return dist


def analyse(gid, s):
    n, adj = decode(s)
    m = sum(len(a) for a in adj) // 2
    degs = [len(a) for a in adj]

    seen = [False] * n
    comps = 0
    for v in range(n):
        if not seen[v]:
            comps += 1
            for w, d in enumerate(bfs(n, adj, v)):
                if d >= 0:
                    seen[w] = True

    diameter, wiener = -1, -1
    if comps == 1:
        diameter = 0
        total = 0
        for v in range(n):
            d = bfs(n, adj, v)
            diameter = max(diameter, max(d))
            total += sum(d)
        wiener = total // 2

    nbr = [set(a) for a in adj]
    triangles = 0
    for v in range(n):
        for w in adj[v]:
            if w <= v:
                continue
            for u in adj[w]:
                if u > w and u in nbr[v]:
                    triangles += 1

    color = [-1] * n
    for v in range(n):
        used = {color[w] for w in adj[v] if color[w] >= 0}
        c = 0
        while c in used:
            c += 1
        color[v] = c
    greedy = max(color) + 1 if n else 0

    x = [1.0 / math.sqrt(n)] * n
    rho = 0.0
    for _ in range(ITERS):
        y = [0.0] * n
        for v in range(n):
            t = 0.0
            for w in adj[v]:
                t += x[w]
            y[v] = t
        norm = math.sqrt(sum(t * t for t in y))
        if norm < 1e-12:
            x = None
            break
        x = [t / norm for t in y]
    if x is not None:
        for v in range(n):
            t = 0.0
            for w in adj[v]:
                t += x[w]
            rho += x[v] * t

    return {"id": gid, "n": n, "m": m, "maxDeg": max(degs), "minDeg": min(degs),
            "components": comps, "diameter": diameter, "triangles": triangles,
            "wiener": wiener, "greedyColors": greedy, "spectralRadius": rho}


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        gid, g6 = line.split(None, 1)
        print(json.dumps(analyse(gid, g6.strip())))


if __name__ == "__main__":
    main()
