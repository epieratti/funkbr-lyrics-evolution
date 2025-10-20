#!/usr/bin/env python3
import sys, os, json, re

PT_TOKENS = {
    " não ", " nao ", " você ", " voce ", " pra ", " pro ", " cadê ", " cade ",
    " aí ", " ai ", " favela ", " rebola ", " rebolar ", " bumbum ", " novinha ",
    " senta ", " sentadinha ", " rabetão ", " rabetao ", " baile ", " mandela ",
    " funk ", " proibidão ", " proibidao ", " brega ", " putaria ", " safada ",
    " que ", " com ", " sem ", " de ", " do ", " da ", " no ", " na ", " dos ", " das "
}
ES_TOKENS = {
    " cómo ", " como ", " estás ", " estan ", " mí ", " mi ", " corazón ",
    " tú ", " tu ", " canción ", " llorar ", " besame ", " besáme ",
    " te ", " porqué ", " porque ", " mañana ", " siempre ", " nunca "
}

def norm(t: str) -> str:
    return " " + re.sub(r"\s+", " ", (t or "").lower()).strip() + " "

def pt_hint(text: str) -> bool:
    t = norm(text)
    hits = sum(1 for tok in PT_TOKENS if tok in t)
    return hits >= 1

def es_hint(text: str) -> bool:
    t = norm(text)
    hits = sum(1 for tok in ES_TOKENS if tok in t)
    return hits >= 1

if len(sys.argv) < 2:
    print("uso: postfilter_pt_strict.py caminho/do/brcorpus_YYYY-MM-DD.jsonl", file=sys.stderr)
    sys.exit(2)

inp = sys.argv[1]
if not os.path.isfile(inp):
    print(f"arquivo não encontrado: {inp}", file=sys.stderr)
    sys.exit(2)

base, ext = os.path.splitext(inp)
outp = base + "_pt" + ext

total = 0
kept = 0

with open(inp, "r", encoding="utf-8", errors="ignore") as f, \
     open(outp, "w", encoding="utf-8") as o:
    for line in f:
        line = line.strip()
        if not line:
            continue
        total += 1
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        title = " ".join([
            str(obj.get("track_name") or obj.get("title") or ""),
            str(obj.get("album_name") or "")
        ])
        if pt_hint(title) and not es_hint(title):
            o.write(json.dumps(obj, ensure_ascii=False) + "\n")
            kept += 1

print(f"Total lidas: {total}")
print(f"Aceitas PT estrito: {kept}")
print(f"Saída: {outp}")
