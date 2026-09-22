// Java implementation of the GTea Rosetta contract.
// stdin: "<id> <graph6>" per line. stdout: one JSON object per line.
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.PrintWriter;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

public class Ref {
    static final int ITERS = 1000;

    static int n;
    static int[][] adj;

    static void decode(String s) {
        long[] b = new long[s.length()];
        for (int i = 0; i < s.length(); i++) b[i] = s.charAt(i) - 63;
        int p;
        if (b[0] == 63) { n = (int) ((b[1] << 12) | (b[2] << 6) | b[3]); p = 4; }
        else { n = (int) b[0]; p = 1; }

        List<List<Integer>> tmp = new ArrayList<>();
        for (int i = 0; i < n; i++) tmp.add(new ArrayList<>());
        int bit = 0;
        for (int j = 1; j < n; j++) {
            for (int i = 0; i < j; i++) {
                long by = b[p + bit / 6];
                if (((by >> (5 - (bit % 6))) & 1) == 1) { tmp.get(i).add(j); tmp.get(j).add(i); }
                bit++;
            }
        }
        adj = new int[n][];
        for (int i = 0; i < n; i++) {
            adj[i] = tmp.get(i).stream().mapToInt(Integer::intValue).toArray();
            Arrays.sort(adj[i]);
        }
    }

    static long[] bfs(int src) {
        long[] dist = new long[n];
        Arrays.fill(dist, -1);
        dist[src] = 0;
        ArrayDeque<Integer> q = new ArrayDeque<>();
        q.add(src);
        while (!q.isEmpty()) {
            int v = q.poll();
            for (int w : adj[v]) if (dist[w] < 0) { dist[w] = dist[v] + 1; q.add(w); }
        }
        return dist;
    }

    static String analyse(String id, String s) {
        decode(s);
        long m = 0, maxDeg = 0, minDeg = n > 0 ? adj[0].length : 0;
        for (int v = 0; v < n; v++) {
            long d = adj[v].length;
            m += d; maxDeg = Math.max(maxDeg, d); minDeg = Math.min(minDeg, d);
        }
        m /= 2;

        boolean[] seen = new boolean[n];
        long components = 0;
        for (int v = 0; v < n; v++) {
            if (seen[v]) continue;
            components++;
            long[] d = bfs(v);
            for (int w = 0; w < n; w++) if (d[w] >= 0) seen[w] = true;
        }

        long diameter = -1, wiener = -1;
        if (components == 1) {
            diameter = 0;
            long total = 0;
            for (int v = 0; v < n; v++) {
                long[] d = bfs(v);
                for (int w = 0; w < n; w++) { diameter = Math.max(diameter, d[w]); total += d[w]; }
            }
            wiener = total / 2;
        }

        long triangles = 0;
        for (int v = 0; v < n; v++)
            for (int w : adj[v]) {
                if (w <= v) continue;
                for (int u : adj[w]) if (u > w && Arrays.binarySearch(adj[v], u) >= 0) triangles++;
            }

        long[] color = new long[n];
        Arrays.fill(color, -1);
        for (int v = 0; v < n; v++) {
            long[] used = Arrays.stream(adj[v]).mapToLong(w -> color[w]).filter(c -> c >= 0).sorted().toArray();
            long c = 0;
            while (Arrays.binarySearch(used, c) >= 0) c++;
            color[v] = c;
        }
        long greedy = n > 0 ? Arrays.stream(color).max().getAsLong() + 1 : 0;

        double[] x = new double[n];
        Arrays.fill(x, 1.0 / Math.sqrt(n));
        double rho = 0.0;
        boolean dead = false;
        for (int it = 0; it < ITERS; it++) {
            double[] y = new double[n];
            for (int v = 0; v < n; v++) { double t = 0.0; for (int w : adj[v]) t += x[w]; y[v] = t; }
            double nr = 0.0;
            for (double t : y) nr += t * t;
            nr = Math.sqrt(nr);
            if (nr < 1e-12) { dead = true; break; }
            for (int v = 0; v < n; v++) y[v] /= nr;
            x = y;
        }
        if (!dead)
            for (int v = 0; v < n; v++) { double t = 0.0; for (int w : adj[v]) t += x[w]; rho += x[v] * t; }

        return String.format(java.util.Locale.ROOT,
            "{\"id\":\"%s\",\"n\":%d,\"m\":%d,\"maxDeg\":%d,\"minDeg\":%d,\"components\":%d,"
            + "\"diameter\":%d,\"triangles\":%d,\"wiener\":%d,\"greedyColors\":%d,"
            + "\"spectralRadius\":%.17g}",
            id, n, m, maxDeg, minDeg, components, diameter, triangles, wiener, greedy, rho);
    }

    public static void main(String[] args) throws Exception {
        BufferedReader in = new BufferedReader(new InputStreamReader(System.in));
        PrintWriter out = new PrintWriter(new java.io.BufferedWriter(new java.io.OutputStreamWriter(System.out)));
        String line;
        while ((line = in.readLine()) != null) {
            String t = line.trim();
            if (t.isEmpty()) continue;
            int sp = t.indexOf(' ');
            if (sp < 0) continue;
            out.println(analyse(t.substring(0, sp), t.substring(sp + 1).trim()));
        }
        out.flush();
    }
}
