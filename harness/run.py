"""Build every implementation, run it over the corpus, compare, and time it.

The point is not that five languages can each compute a diameter. It is that when you
maintain the same library five times, the implementations drift — and nothing tells you
until something is run side by side against a pinned contract.
"""
import json, os, shutil, statistics, subprocess, sys, time

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
BUILD = os.path.join(ROOT, "build")
SITE = os.path.join(ROOT, "docs", "data")
INT_FIELDS = ["n", "m", "maxDeg", "minDeg", "components", "diameter",
              "triangles", "wiener", "greedyColors"]
FLOAT_FIELDS = ["spectralRadius"]
FLOAT_TOL = 1e-9
REPEATS = 5

IMPLS = [
    {"id": "python", "label": "Python 3", "dir": "impl/python",
     "build": None, "run": [sys.executable, "impl/python/ref.py"],
     "version": [sys.executable, "--version"]},
    {"id": "js", "label": "JavaScript (node)", "dir": "impl/js",
     "build": None, "run": ["node", "impl/js/ref.mjs"],
     "version": ["node", "--version"]},
    {"id": "cpp", "label": "C++ (g++ -O2)", "dir": "impl/cpp",
     "build": ["g++", "-O2", "-std=c++17", "-o", os.path.join(BUILD, "ref_cpp"), "impl/cpp/ref.cpp"],
     "run": [os.path.join(BUILD, "ref_cpp")], "version": ["g++", "--version"]},
    {"id": "rust", "label": "Rust (release)", "dir": "impl/rust",
     "build": ["cargo", "build", "--release", "--quiet", "--manifest-path", "impl/rust/Cargo.toml",
               "--target-dir", os.path.join(BUILD, "rust")],
     "run": [os.path.join(BUILD, "rust", "release", "rosetta")], "version": ["cargo", "--version"]},
    {"id": "java", "label": "Java 21", "dir": "impl/java",
     "build": ["javac", "-d", os.path.join(BUILD, "java"), "impl/java/Ref.java"],
     "run": ["java", "-cp", os.path.join(BUILD, "java"), "Ref"], "version": ["java", "-version"]},
]


def version(cmd):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return (p.stdout + p.stderr).strip().split("\n")[0]
    except Exception:
        return "unknown"


def main():
    os.makedirs(BUILD, exist_ok=True)
    os.makedirs(SITE, exist_ok=True)
    corpus = json.load(open(os.path.join(ROOT, "spec", "corpus.json")))["graphs"]
    stdin_text = "".join(f"{g['id']} {g['g6']}\n" for g in corpus)
    print(f"corpus: {len(corpus)} graphs\n")

    results, meta = {}, {}
    for impl in IMPLS:
        name = impl["label"]
        if shutil.which(impl["run"][0]) is None and not os.path.exists(impl["run"][0]):
            if impl["build"] is None:
                print(f"{name}: interpreter not found, skipped")
                meta[impl["id"]] = {"label": name, "status": "unavailable"}
                continue
        if impl["build"]:
            t0 = time.time()
            p = subprocess.run(impl["build"], cwd=ROOT, capture_output=True, text=True)
            if p.returncode != 0:
                print(f"{name}: BUILD FAILED\n{p.stderr[:600]}")
                meta[impl["id"]] = {"label": name, "status": "build-failed",
                                    "error": p.stderr[:600]}
                continue
            print(f"{name}: built in {time.time()-t0:.1f}s")

        # Startup dominates at this corpus size for the VM languages, so measure it
        # separately with an empty stdin and report both numbers.
        starts = []
        for _ in range(REPEATS):
            t0 = time.perf_counter()
            subprocess.run(impl["run"], cwd=ROOT, input="", capture_output=True, text=True)
            starts.append(time.perf_counter() - t0)
        startup = statistics.median(starts)

        times = []
        out = None
        ok = True
        for r in range(REPEATS):
            t0 = time.perf_counter()
            p = subprocess.run(impl["run"], cwd=ROOT, input=stdin_text,
                               capture_output=True, text=True)
            dt = time.perf_counter() - t0
            if p.returncode != 0:
                print(f"{name}: RUN FAILED\n{p.stderr[:600]}")
                meta[impl["id"]] = {"label": name, "status": "run-failed",
                                    "error": p.stderr[:600]}
                ok = False
                break
            times.append(dt)
            out = p.stdout
        if not ok:
            continue

        rows = {}
        bad = 0
        for line in out.strip().split("\n"):
            if not line.strip():
                continue
            try:
                d = json.loads(line)
                rows[d["id"]] = d
            except Exception:
                bad += 1
        results[impl["id"]] = rows
        med = statistics.median(times)
        meta[impl["id"]] = {
            "label": name, "status": "ok",
            "version": version(impl["version"]),
            "median_ms": round(med * 1000, 1),
            "best_ms": round(min(times) * 1000, 1),
            "startup_ms": round(startup * 1000, 1),
            "compute_ms": round(max(0.0, med - startup) * 1000, 1),
            "graphs": len(rows), "unparsable_lines": bad,
        }
        m_ = meta[impl["id"]]
        print(f"{name}: {len(rows)}/{len(corpus)} graphs, {m_['median_ms']} ms total "
              f"= {m_['startup_ms']} ms startup + {m_['compute_ms']} ms compute  [{m_['version']}]")

    # --- compare -------------------------------------------------------------
    live = [i for i in results]
    print(f"\ncomparing {len(live)} implementations across {len(INT_FIELDS)+len(FLOAT_FIELDS)} quantities")

    disagreements = []
    per_field = {f: {"checked": 0, "disagreed": 0} for f in INT_FIELDS + FLOAT_FIELDS}
    pair_agree = {}

    for g in corpus:
        gid = g["id"]
        present = [i for i in live if gid in results[i]]
        for f in INT_FIELDS:
            vals = {i: results[i][gid].get(f) for i in present}
            per_field[f]["checked"] += 1
            if len(set(vals.values())) > 1:
                per_field[f]["disagreed"] += 1
                disagreements.append({"graph": gid, "g6": g["g6"], "field": f, "values": vals})
        for f in FLOAT_FIELDS:
            vals = {i: results[i][gid].get(f) for i in present}
            per_field[f]["checked"] += 1
            nums = [v for v in vals.values() if isinstance(v, (int, float))]
            if nums and (max(nums) - min(nums)) > FLOAT_TOL:
                per_field[f]["disagreed"] += 1
                disagreements.append({"graph": gid, "g6": g["g6"], "field": f, "values": vals,
                                      "spread": max(nums) - min(nums)})

    for a in live:
        for b in live:
            same = 0
            total = 0
            for g in corpus:
                gid = g["id"]
                if gid not in results[a] or gid not in results[b]:
                    continue
                total += 1
                eq = all(results[a][gid].get(f) == results[b][gid].get(f) for f in INT_FIELDS)
                if eq:
                    for f in FLOAT_FIELDS:
                        x, y = results[a][gid].get(f), results[b][gid].get(f)
                        if not (isinstance(x, (int, float)) and isinstance(y, (int, float))
                                and abs(x - y) <= FLOAT_TOL):
                            eq = False
                if eq:
                    same += 1
            pair_agree[f"{a}|{b}"] = {"same": same, "total": total}

    # widest float spread, which is the honest measure of cross-language drift
    spreads = []
    for g in corpus:
        gid = g["id"]
        nums = [results[i][gid]["spectralRadius"] for i in live
                if gid in results[i] and isinstance(results[i][gid].get("spectralRadius"), (int, float))]
        if len(nums) > 1:
            spreads.append((max(nums) - min(nums), gid))
    spreads.sort(reverse=True)

    report = {
        "generated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "corpus_size": len(corpus),
        "fields": {"int": INT_FIELDS, "float": FLOAT_FIELDS, "float_tol": FLOAT_TOL},
        "impls": meta,
        "pair_agree": pair_agree,
        "per_field": per_field,
        "disagreements": disagreements[:200],
        "float_spreads": [{"graph": g, "spread": s} for s, g in spreads[:12]],
        "rows": {i: results[i] for i in live},
    }
    json.dump(report, open(os.path.join(SITE, "results.json"), "w"), separators=(",", ":"))

    total_dis = sum(v["disagreed"] for v in per_field.values())
    print(f"\ndisagreements: {total_dis}")
    for f, v in per_field.items():
        flag = "  <-- " if v["disagreed"] else ""
        print(f"   {f:15s} {v['disagreed']:4d} / {v['checked']}{flag}")
    if spreads:
        print(f"\nwidest spectralRadius spread across languages: {spreads[0][0]:.3e} on {spreads[0][1]}")
    print(f"\nwrote docs/data/results.json")


if __name__ == "__main__":
    # Always exits 0: this script reports, it does not judge. CI decides whether a
    # disagreement should fail the build, in a separate step that reads results.json.
    main()
