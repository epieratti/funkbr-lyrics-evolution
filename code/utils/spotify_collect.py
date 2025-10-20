from typing import Iterable, Dict, List
from itertools import islice
from spotipy import Spotify

def _chunked(it, n: int):
    it = iter(it)
    while True:
        chunk = list(islice(it, n))
        if not chunk:
            break
        yield chunk

def fetch_artist_catalog(sp: Spotify, artist_id: str, market: str = "BR") -> List[Dict]:
    # 1) /v1/artists/{id}/albums  (Spotipy usa "country" em vez de "market")
    albums, seen = [], set()
    resp = sp.artist_albums(artist_id, include_groups="album,single,appears_on,compilation",
                            country=market, limit=50)
    while True:
        for a in resp.get("items", []):
            if a["id"] in seen:
                continue
            seen.add(a["id"])
            albums.append(a)
        if resp.get("next"):
            resp = sp.next(resp)
        else:
            break

    # 2) /v1/albums?ids=... (UPC/label/release_date)
    album_meta: Dict[str, Dict] = {}
    for batch in _chunked([a["id"] for a in albums], 20):
        det = sp.albums(batch)
        for a in det.get("albums", []):
            ext = (a.get("external_ids") or {})
            album_meta[a["id"]] = {
                "upc": ext.get("upc"),
                "label": a.get("label"),
                "release_date": a.get("release_date"),
                "release_date_precision": a.get("release_date_precision"),
                "album_type": a.get("album_type"),
            }

    # 3) /v1/albums/{id}/tracks (todas as faixas do álbum)
    pairs = []  # (album, track)
    for alb in albums:
        tr = sp.album_tracks(alb["id"], market=market, limit=50)
        items = tr.get("items", [])
        while tr.get("next"):
            tr = sp.next(tr)
            items.extend(tr.get("items", []))
        for t in items:
            pairs.append((alb, t))

    # 4) /v1/tracks?ids=... (ISRC, popularity, duração, explicit, url)
    ids = [t.get("id") for _, t in pairs if t.get("id")]
    track_meta: Dict[str, Dict] = {}
    for batch in _chunked(ids, 50):
        det = sp.tracks(batch)
        for trk in det.get("tracks", []):
            ext = (trk.get("external_ids") or {})
            track_meta[trk["id"]] = {
                "isrc": ext.get("isrc"),
                "duration_ms": trk.get("duration_ms"),
                "explicit": trk.get("explicit"),
                "popularity": trk.get("popularity"),
                "spotify_url": (trk.get("external_urls") or {}).get("spotify"),
            }

    # 5) /v1/audio-features?ids=...
    features: Dict[str, Dict] = {}
    for batch in _chunked(ids, 100):
        feats = sp.audio_features(batch) or []
        for f in feats:
            if not f:
                continue
            features[f["id"]] = {
                "danceability": f.get("danceability"),
                "energy": f.get("energy"),
                "tempo": f.get("tempo"),
                "key": f.get("key"),
                "mode": f.get("mode"),
                "loudness": f.get("loudness"),
                "time_signature": f.get("time_signature"),
                "acousticness": f.get("acousticness"),
                "instrumentalness": f.get("instrumentalness"),
                "liveness": f.get("liveness"),
                "speechiness": f.get("speechiness"),
                "valence": f.get("valence"),
            }

    rows: List[Dict] = []
    for alb, t in pairs:
        tm = track_meta.get(t.get("id"), {})
        af = features.get(t.get("id"), {})
        rows.append({
            "artist_id": (alb.get("artists") or [{}])[0].get("id"),
            "artist_name": (alb.get("artists") or [{}])[0].get("name"),
            "album_id": alb.get("id"),
            "album_name": alb.get("name"),
            "album_upc": album_meta.get(alb["id"], {}).get("upc"),
            "album_label": album_meta.get(alb["id"], {}).get("label"),
            "album_type": album_meta.get(alb["id"], {}).get("album_type"),
            "album_release_date": album_meta.get(alb["id"], {}).get("release_date"),
            "album_release_date_precision": album_meta.get(alb["id"], {}).get("release_date_precision"),
            "track_id": t.get("id"),
            "track_name": t.get("name"),
            "disc_number": t.get("disc_number"),
            "track_number": t.get("track_number"),
            "duration_ms": tm.get("duration_ms"),
            "explicit": tm.get("explicit"),
            "isrc": tm.get("isrc"),
            "track_popularity": tm.get("popularity"),
            "spotify_url": tm.get("spotify_url"),
            "audio_features": af,
            "market": market,
        })
    return rows
