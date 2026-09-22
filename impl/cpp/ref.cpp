// C++ implementation of the GTea Rosetta contract.
// stdin: "<id> <graph6>" per line. stdout: one JSON object per line.
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <deque>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

static const int ITERS = 1000;

static void decode(const std::string& s, int& n, std::vector<std::vector<int>>& adj) {
    std::vector<long long> b;
    b.reserve(s.size());
    for (unsigned char c : s) b.push_back((long long)c - 63);
    size_t p;
    if (b[0] == 63) { n = (int)((b[1] << 12) | (b[2] << 6) | b[3]); p = 4; }
    else { n = (int)b[0]; p = 1; }
    adj.assign(n, {});
    size_t bit = 0;
    for (int j = 1; j < n; ++j) {
        for (int i = 0; i < j; ++i) {
            long long byte = b[p + bit / 6];
            if ((byte >> (5 - (bit % 6))) & 1) { adj[i].push_back(j); adj[j].push_back(i); }
            ++bit;
        }
    }
    for (auto& a : adj) std::sort(a.begin(), a.end());
}

static std::vector<long long> bfs(int n, const std::vector<std::vector<int>>& adj, int src) {
    std::vector<long long> dist(n, -1);
    dist[src] = 0;
    std::deque<int> q{src};
    while (!q.empty()) {
        int v = q.front(); q.pop_front();
        for (int w : adj[v]) if (dist[w] < 0) { dist[w] = dist[v] + 1; q.push_back(w); }
    }
    return dist;
}

static std::string analyse(const std::string& id, const std::string& s) {
    int n; std::vector<std::vector<int>> adj;
    decode(s, n, adj);

    long long m = 0, maxDeg = 0, minDeg = n ? (long long)adj[0].size() : 0;
    for (int v = 0; v < n; ++v) {
        long long d = (long long)adj[v].size();
        m += d;
        maxDeg = std::max(maxDeg, d);
        minDeg = std::min(minDeg, d);
    }
    m /= 2;

    std::vector<char> seen(n, 0);
    long long components = 0;
    for (int v = 0; v < n; ++v) {
        if (seen[v]) continue;
        ++components;
        auto d = bfs(n, adj, v);
        for (int w = 0; w < n; ++w) if (d[w] >= 0) seen[w] = 1;
    }

    long long diameter = -1, wiener = -1;
    if (components == 1) {
        diameter = 0;
        long long total = 0;
        for (int v = 0; v < n; ++v) {
            auto d = bfs(n, adj, v);
            for (int w = 0; w < n; ++w) { diameter = std::max(diameter, d[w]); total += d[w]; }
        }
        wiener = total / 2;
    }

    long long triangles = 0;
    for (int v = 0; v < n; ++v)
        for (int w : adj[v]) {
            if (w <= v) continue;
            for (int u : adj[w])
                if (u > w && std::binary_search(adj[v].begin(), adj[v].end(), u)) ++triangles;
        }

    std::vector<long long> color(n, -1);
    for (int v = 0; v < n; ++v) {
        std::vector<long long> used;
        for (int w : adj[v]) if (color[w] >= 0) used.push_back(color[w]);
        std::sort(used.begin(), used.end());
        long long c = 0;
        while (std::binary_search(used.begin(), used.end(), c)) ++c;
        color[v] = c;
    }
    long long greedy = n ? *std::max_element(color.begin(), color.end()) + 1 : 0;

    std::vector<double> x(n, 1.0 / std::sqrt((double)n));
    double rho = 0.0;
    bool dead = false;
    for (int it = 0; it < ITERS; ++it) {
        std::vector<double> y(n, 0.0);
        for (int v = 0; v < n; ++v) { double t = 0.0; for (int w : adj[v]) t += x[w]; y[v] = t; }
        double nr = 0.0;
        for (double t : y) nr += t * t;
        nr = std::sqrt(nr);
        if (nr < 1e-12) { dead = true; break; }
        for (double& t : y) t /= nr;
        x.swap(y);
    }
    if (!dead)
        for (int v = 0; v < n; ++v) { double t = 0.0; for (int w : adj[v]) t += x[w]; rho += x[v] * t; }

    char buf[512];
    std::snprintf(buf, sizeof buf,
        "{\"id\":\"%s\",\"n\":%d,\"m\":%lld,\"maxDeg\":%lld,\"minDeg\":%lld,\"components\":%lld,"
        "\"diameter\":%lld,\"triangles\":%lld,\"wiener\":%lld,\"greedyColors\":%lld,"
        "\"spectralRadius\":%.17g}",
        id.c_str(), n, m, maxDeg, minDeg, components, diameter, triangles, wiener, greedy, rho);
    return buf;
}

int main() {
    std::ios::sync_with_stdio(false);
    std::string line;
    while (std::getline(std::cin, line)) {
        std::istringstream ss(line);
        std::string id, g6;
        if (!(ss >> id >> g6)) continue;
        std::cout << analyse(id, g6) << "\n";
    }
    return 0;
}
