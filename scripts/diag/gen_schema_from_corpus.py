import json, sys, os, glob, itertools
from collections import defaultdict

def infer_type(v):
    if v is None: return "null"
    if isinstance(v, bool): return "boolean"
    if isinstance(v, int): return "integer"
    if isinstance(v, float): return "number"
    if isinstance(v, list): return "array"
    if isinstance(v, dict): return "object"
    return "string"

def merge_types(a, b):
    if a == b: return a
    if isinstance(a, list):
        s = set(a)
    else:
        s = set([a])
    if isinstance(b, list):
        s |= set(b)
    else:
        s |= set([b])
    return sorted(s)

def main():
    repo = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    paths = sorted(glob.glob(os.path.join(repo, "processed_brcorpus", "brcorpus_*.jsonl")))
    if not paths:
        print("ERRO: nenhum processed_brcorpus/brcorpus_*.jsonl encontrado", file=sys.stderr)
        sys.exit(2)
    types = defaultdict(lambda: None)
    seen = 0
    for p in paths:
        with open(p, "r", encoding="utf-8") as fh:
            for line in fh:
                line=line.strip()
                if not line: continue
                try:
                    obj=json.loads(line)
                except Exception:
                    continue
                for k,v in obj.items():
                    t = infer_type(v)
                    types[k] = t if types[k] is None else merge_types(types[k], t)
                seen += 1
                if seen >= 1000: break
        if seen >= 1000: break

    props = {}
    for k,t in sorted(types.items()):
        if t is None: continue
        props[k] = {"type": t}

    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "funkbr processed_brcorpus record",
        "type": "object",
        "additionalProperties": True,
        "properties": props,
        "required": []  # não impomos required aqui; mantemos flexível
    }

    out = os.path.join(repo, "schema.json")
    with open(out, "w", encoding="utf-8") as w:
        json.dump(schema, w, ensure_ascii=False, indent=2, sort_keys=True)
    print(f"ok: schema gerado/atualizado em {out} (amostra={seen} linhas)")

if __name__ == "__main__":
    main()
