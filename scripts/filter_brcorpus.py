#!/usr/bin/env python3
import argparse, os, sys, json, re
from datetime import date

PT_TOKENS = set([
    " de ", " da ", " do ", " das ", " dos ", " pra ", " pro ", " na ", " no ", " em ",
    " não ", " nao ", " você ", " voce ", " que ", " com ", " sem ", " por ", " uma ", " um ",
])
def pt_hint(text: str) -> bool:
    if not text:
        return False
    t = " " + text.lower() + " "
    if any(tok in t for tok in PT_TOKENS): return True
    # sinais comuns de português
    if re.search(r"[ãõçáéíóúàêô]", t): return True
    return False

def load_seeds(path: str):
    seeds = set()
    if not path: return seeds
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if s: seeds.add(s.lower())
    except FileNotFoundError:
        pass
    return seeds

def iter_jsonl(path):
    if os.path.isdir(path):
        for root, _, files in os.walk(path):
            for fn in files:
                if fn.endswith(".jsonl"):
                    with open(os.path.join(root, fn), "r", encoding="utf-8", errors="ignore") as f:
                        for line in f:
                            line = line.strip()
                            if line:
                                yield line
    else:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if line:
                    yield line

def main():
    p = argparse.ArgumentParser(description="Filtro BR paralelo para corpus, sem sobrescrever saída atual.")
    p.add_argument("--input", required=True, help="Arquivo JSONL ou diretório contendo .jsonl")
    p.add_argument("--output-dir", default="processed_brcorpus", help="Diretório de saída novo")
    p.add_argument("--seeds", default="", help="Arquivo com uma artista por linha para dar +1 em match exato")
    p.add_argument("--min-score", type=int, default=2, help="Pontuação mínima para aceitar no corpus BR")
    p.add_argument("--dry-run", action="store_true", help="Somente contar, não escrever arquivos")
    args = p.parse_args()

    seeds = load_seeds(args.seeds)
    os.makedirs(args.output_dir, exist_ok=True)
    today = date.today().isoformat()
    out_path = os.path.join(args.output_dir, f"brcorpus_{today}.jsonl")

    total = 0
    accepted = 0

    out_f = None
    if not args.dry_run:
        out_f = open(out_path, "w", encoding="utf-8")

    for line in iter_jsonl(args.input):
        total += 1
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            # pula linhas inválidas
            continue

        artist_country = (obj.get("artist_country_primary") or obj.get("artist_country") or "").upper()
        isrc = (obj.get("isrc") or "").upper()
        title = (obj.get("track_name") or obj.get("title") or "") + " " + (obj.get("album_name") or "")

        score = 0
        if artist_country == "BR":
            score += 1
        if isrc.startswith("BR"):
            score += 1
        if pt_hint(title):
            score += 1

        # seeds opcionais por nome de artista
        artist_name = (obj.get("artist_name") or obj.get("primary_artist") or "")
        if artist_name and artist_name.lower() in seeds:
            score += 1

        obj["country_score"] = 1 if artist_country == "BR" else 0
        obj["isrc_score"] = 1 if isrc.startswith("BR") else 0
        obj["pt_hint"] = 1 if pt_hint(title) else 0
        obj["seed_match"] = 1 if artist_name and artist_name.lower() in seeds else 0
        obj["accept_in_brcorpus"] = 1 if score >= args.min_score else 0

        if obj["accept_in_brcorpus"]:
            accepted += 1
            if out_f:
                out_f.write(json.dumps(obj, ensure_ascii=False) + "\n")

    if out_f:
        out_f.close()

    print(f"Total lidas: {total}")
    print(f"Aceitas BR:  {accepted}")
    if not args.dry_run:
        print(f"Saída:       {out_path}")
    else:
        print("Dry-run: nada foi escrito.")

if __name__ == "__main__":
    main()
