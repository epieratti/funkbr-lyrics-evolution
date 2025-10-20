import csv, os, sys, re, unicodedata, collections
from typing import Dict, List, Tuple
import pandas as pd
from statistics import mean, median

# ---------- helpers ----------
def norm(s: str) -> str:
    if s is None: return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.lower()
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

NOISE = re.compile(
    r"\b(deluxe|deluxo|expanded|expandido|expandida|remaster|remasterizado|"
    r"remasterizada|edicao especial|edi[cç][aã]o especial|special edition|"
    r"clean|explicit|acoustic|ao vivo|live|anniversary|vers[aã]o|version)\b",
    flags=re.IGNORECASE
)

def strip_noise(name: str) -> str:
    s = unicodedata.normalize("NFKD", name or "")
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"[\(\)\[\]\{\}\-–—_:;!?.]+", " ", s)
    s = NOISE.sub(" ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def year_of(date_str: str) -> int:
    try:
        return int((date_str or "")[:4])
    except Exception:
        return -1

PREC_RANK = {"day": 3, "month": 2, "year": 1, None: 0, "": 0}

def choose_rep(cands: pd.DataFrame, family: str) -> str:
    """
    cands: linhas de um mesmo grupo (um artista, uma chave base)
    family: 'album' (inclui compilation) ou 'single'
    Retorna o album_id escolhido.
    """
    # 1) score de popularidade (média das tracks)
    def pop_avg(g):
        vals = [float(x) for x in g["track_popularity"].dropna().tolist()]
        if len(vals) >= 1:
            return mean(vals)
        return float("-inf")

    cands = cands.copy()
    # métricas por album_id
    agg = cands.groupby("album_id").agg(
        pop_avg=("track_popularity", lambda s: mean([float(x) for x in s.dropna().tolist()]) if len(s.dropna()) else float("-inf")),
        pop_med=("track_popularity", lambda s: median([float(x) for x in s.dropna().tolist()]) if len(s.dropna()) else float("-inf")),
        release_precision=("album_release_precision", "first"),
        release_date=("album_release_date", "first"),
        album_name=("album_name","first"),
        album_type=("album_type","first"),
        artist_id=("artist_id","first"),
    ).reset_index()

    # 1) popularidade média (se -inf, cai pro próximo)
    agg["score1"] = agg["pop_avg"]

    # 2) precisão
    agg["score2"] = agg["release_precision"].map(PREC_RANK).fillna(0)

    # 3) data (mais antigo melhor): transformar em chave crescente negativa para sort reverso
    agg["score3"] = agg["release_date"].fillna("9999-12-31")

    # 4) nome mais curto
    agg["score4"] = agg["album_name"].fillna("").apply(lambda s: len(strip_noise(s)))

    # 5) tipo (apenas na família album): album>compilation>single
    type_rank = {"album":3, "compilation":2, "single":1}
    agg["score5"] = agg["album_type"].map(type_rank).fillna(0) if family=="album" else 0

    # sort por prioridade (desc/pop; desc/precision; asc/data; asc/nome; desc/tipo; determinismo por id)
    agg = agg.sort_values(
        by=["score1","score2", "score3","score4","score5","album_id"],
        ascending=[False, True, True, True, False, True]
    )

    return agg.iloc[0]["album_id"]

def main():
    import glob
    paths = sorted(glob.glob("data/raw/*_albums_tracks_enriched.csv"))
    if not paths:
        print("Nenhum CSV *_albums_tracks_enriched.csv encontrado em data/raw/")
        return 2
    src = paths[-1]
    print("Lendo:", src)

    df = pd.read_csv(src)
    # Normalizações auxiliares
    df["release_year"] = df["album_release_date"].astype(str).str.slice(0,4).apply(lambda y: int(y) if y.isdigit() else -1)
    df["norm_album_base"] = df["album_name"].astype(str).apply(strip_noise).apply(norm)

    # ------------- Família ÁLBUNS (album/compilation) -------------
    fam_album = df[df["album_type"].isin(["album","compilation"])].copy()
    fam_album["grp_key"] = (
        fam_album["artist_id"].astype(str) + " | " +
        fam_album["norm_album_base"] + " | " +
        fam_album["release_year"].astype(str) + " | " +
        fam_album["album_total_tracks"].astype(str)
    )

    keep_album_ids = set()
    for key, block in fam_album.groupby("grp_key"):
        aid = choose_rep(block, family="album")
        keep_album_ids.add(aid)

    # ------------- Família SINGLES -------------
    fam_single = df[df["album_type"].isin(["single"])].copy()

    # obter track 1 por álbum
    t1 = fam_single[fam_single["track_number"].fillna(0).astype(int)==1].copy()
    t1["norm_track1"] = t1["track_name"].astype(str).apply(strip_noise).apply(norm)
    fam_single = fam_single.merge(
        t1[["album_id","norm_track1"]],
        on="album_id", how="left", suffixes=("","")
    )
    fam_single["grp_key"] = (
        fam_single["artist_id"].astype(str) + " | " +
        fam_single["norm_track1"].fillna("") + " | " +
        fam_single["release_year"].astype(str)
    )

    keep_single_album_ids = set()
    for key, block in fam_single.groupby("grp_key"):
        aid = choose_rep(block, family="single")
        keep_single_album_ids.add(aid)

    keep_all = keep_album_ids | keep_single_album_ids
    out = df[df["album_id"].isin(keep_all)].copy()

    # (opcional) remover linhas 100% duplicadas
    out = out.drop_duplicates()

    dst = src.replace("_enriched.csv", "_dedup.csv")
    out.to_csv(dst, index=False, encoding="utf-8")
    print("OK ->", dst, "| linhas:", len(out))

if __name__ == "__main__":
    sys.exit(main())
