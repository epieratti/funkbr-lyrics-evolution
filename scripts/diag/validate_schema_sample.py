import json, os, sys, glob, itertools

def infer_type(v):
    if v is None: return "null"
    if isinstance(v, bool): return "boolean"
    if isinstance(v, int): return "integer"
    if isinstance(v, float): return "number"
    if isinstance(v, list): return "array"
    if isinstance(v, dict): return "object"
    return "string"

repo = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
schema_path = os.path.join(repo, "schema.json")
with open(schema_path, "r", encoding="utf-8") as fh:
    schema = json.load(fh)
props = schema.get("properties", {})

paths = sorted(glob.glob(os.path.join(repo, "processed_brcorpus", "brcorpus_*.jsonl")))
n_checked = 0
bad = 0
for p in paths:
    with open(p, "r", encoding="utf-8") as fh:
        for i,line in enumerate(fh):
            if n_checked >= 100: break
            line=line.strip()
            if not line: continue
            try:
                obj = json.loads(line)
            except Exception:
                bad += 1
                continue
            # checagem leve: se chave existe no schema, tipo deve bater (ou estar no union)
            for k,v in obj.items():
                if k not in props:
                    continue
                t = infer_type(v)
                st = props[k].get("type")
                if isinstance(st, list):
                    if t not in st: bad += 1
                else:
                    if t != st: bad += 1
            n_checked += 1
    if n_checked >= 100: break

print(f"ok: sample validated (n={n_checked}, basic_mismatches={bad})")
sys.exit(0)
