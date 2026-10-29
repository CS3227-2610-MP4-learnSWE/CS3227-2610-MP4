"""Run the battery against the clean reference and every planted bug. Writes selfcheck_results.json."""
import json, os, subprocess, sys, importlib.util
here = os.path.dirname(os.path.abspath(__file__))
ref = os.path.join(here, "reference")
sys.path.insert(0, ref)
os.environ.pop("MUTANT", None)
spec = importlib.util.spec_from_file_location("refmain", os.path.join(ref, "main.py"))
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
names = list(mod.MUTANTS)
def run(mutant, slow=True):
    env = dict(os.environ); env.pop("MUTANT", None)
    if mutant: env["MUTANT"] = mutant
    cmd = [sys.executable, os.path.join(here, "edge_cases.py"), ref] + (["--slow", "main:do_save"] if slow else [])
    p = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=900)
    return json.loads(p.stdout)
out = {}
clean = run("")
out["__clean__"] = {"total": len(clean), "failed": [r["id"] for r in clean if r["result"] != "pass"]}
clean2 = run("", slow=False)
out["__clean_noslow__"] = {"total": len(clean2), "failed": [r["id"] for r in clean2 if r["result"] != "pass"]}
for n in names:
    rs = run(n)
    out[n] = [r["id"] for r in rs if r["result"] != "pass"]
    print(n, out[n], file=sys.stderr, flush=True)
json.dump(out, open(os.path.join(here, "selfcheck_results.json"), "w"), indent=1)
caught = sum(1 for n in names if out[n])
print(f"clean failures: {out['__clean__']['failed']}; mutants caught {caught}/{len(names)}; missed: {[n for n in names if not out[n]]}")
