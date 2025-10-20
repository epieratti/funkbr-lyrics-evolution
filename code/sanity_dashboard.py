import os, glob, csv, time, statistics as st, argparse
p=argparse.ArgumentParser(); p.add_argument("--out", default="reports/sanity"); a=p.parse_args()
os.makedirs(a.out, exist_ok=True)
rows=[]; sizes=[]
today=time.strftime("%Y%m%d")
for fn in sorted(glob.glob("data/raw/*")):
    sz=os.path.getsize(fn); m=time.strftime("%F %T", time.localtime(os.path.getmtime(fn)))
    rows.append({"arquivo":os.path.basename(fn),"bytes":sz,"data_mod":m,"hoje":"SIM" if today in fn else "NAO"})
    if today in fn and fn.endswith(".jsonl"): sizes.append(sz)
out=os.path.join(a.out,"sanity_min_raw.csv")
with open(out,"w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=["arquivo","bytes","data_mod","hoje"]); w.writeheader(); w.writerows(rows)
open(os.path.join(a.out,"README.txt"),"w").write(
    f"jsonl_hoje={len(sizes)}, zerados={sum(1 for s in sizes if s==0)}, media_bytes={round(st.mean(sizes),1) if sizes else 0}\n"
)
print("ok:", out)
