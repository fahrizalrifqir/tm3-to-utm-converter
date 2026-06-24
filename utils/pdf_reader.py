"""
utils/pdf_reader.py
Membaca tabel koordinat dari file PDF dan mengubahnya menjadi GeoDataFrame.

Strategi:
  1. Ekstrak tabel dari semua halaman dengan pdfplumber.
  2. Cari kolom yang mengandung koordinat (X/Y, Bujur/Lintang, Easting/Northing).
  3. Bentuk GeoDataFrame Point (atau Polygon jika ada kolom bidang).
"""
import geopandas as gpd
import pandas as pd
import pdfplumber
from shapely.geometry import Point, Polygon


# Kandidat nama kolom (case-insensitive)
_LON_HINTS = ["x", "longitude", "bujur", "easting",  "e", "lon", "long"]
_LAT_HINTS = ["y", "latitude",  "lintang","northing", "n", "lat"]
_ID_HINTS  = ["id_bidang", "bidang", "no", "no_bidang", "parcel", "id", "kode"]


def read_pdf(path: str) -> gpd.GeoDataFrame:
    """
    Ekstrak tabel koordinat dari PDF dan kembalikan GeoDataFrame (EPSG:4326).
    """
    frames = _extract_tables(path)

    if not frames:
        raise ValueError(
            "Tidak ada tabel koordinat yang ditemukan di PDF.\n"
            "Pastikan PDF berisi tabel dengan kolom X/Y atau Bujur/Lintang."
        )

    # Gabungkan semua tabel
    df = pd.concat(frames, ignore_index=True)
    df = _clean_df(df)

    lon_col = _find_col(df, _LON_HINTS)
    lat_col = _find_col(df, _LAT_HINTS)

    if lon_col is None or lat_col is None:
        raise ValueError(
            f"Kolom koordinat tidak ditemukan. Kolom tersedia: {list(df.columns)}\n"
            "Ganti nama kolom CSV/PDF Anda menjadi: X/Y, Longitude/Latitude, "
            "Bujur/Lintang, atau Easting/Northing."
        )

    df[lon_col] = pd.to_numeric(df[lon_col], errors="coerce")
    df[lat_col] = pd.to_numeric(df[lat_col], errors="coerce")
    df = df.dropna(subset=[lon_col, lat_col])

    if df.empty:
        raise ValueError("Semua nilai koordinat tidak valid setelah parsing.")

    id_col = _find_col(df, _ID_HINTS)

    if id_col and df[id_col].nunique() < len(df):
        # Beberapa titik per bidang → buat Polygon
        gdf = _build_polygons(df, lon_col, lat_col, id_col)
    else:
        geom = [Point(xy) for xy in zip(df[lon_col], df[lat_col])]
        gdf  = gpd.GeoDataFrame(df, geometry=geom, crs="EPSG:4326")

    return gdf


# ─── ekstraksi tabel ──────────────────────────────────────────────────────────

def _extract_tables(path: str) -> list[pd.DataFrame]:
    frames = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for tbl in tables:
                if not tbl or len(tbl) < 2:
                    continue
                header = [str(c).strip() if c else f"col_{i}"
                          for i, c in enumerate(tbl[0])]
                rows   = tbl[1:]
                df = pd.DataFrame(rows, columns=header)
                frames.append(df)

    # Jika tidak ada tabel terstruktur, coba ekstrak teks per halaman
    if not frames:
        frames = _parse_text_fallback(path)

    return frames


def _parse_text_fallback(path: str) -> list[pd.DataFrame]:
    """
    Fallback: coba baca teks mentah dan parse baris yang mengandung angka koordinat.
    Berguna untuk PDF yang discan tapi punya text layer.
    """
    import re
    rows = []
    pattern = re.compile(
        r"(\d+)\s+"                       # no titik
        r"([+-]?\d+\.?\d*)\s+"            # X / bujur
        r"([+-]?\d+\.?\d*)"               # Y / lintang
    )
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for line in text.splitlines():
                m = pattern.search(line)
                if m:
                    rows.append({
                        "No":  m.group(1),
                        "X":   m.group(2),
                        "Y":   m.group(3),
                    })
    if rows:
        return [pd.DataFrame(rows)]
    return []


# ─── helper ───────────────────────────────────────────────────────────────────

def _clean_df(df: pd.DataFrame) -> pd.DataFrame:
    """Bersihkan whitespace dan baris kosong."""
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    df = df.dropna(how="all")
    for col in df.columns:
        if df[col].dtype == object:
            df[col] = df[col].astype(str).str.strip()
    return df


def _find_col(df: pd.DataFrame, hints: list) -> str | None:
    lower = {c.lower(): c for c in df.columns}
    for h in hints:
        if h in lower:
            return lower[h]
    return None


def _build_polygons(
    df: pd.DataFrame, lon_col: str, lat_col: str, id_col: str
) -> gpd.GeoDataFrame:
    rows = []
    for bid, grp in df.groupby(id_col, sort=False):
        coords = list(zip(grp[lon_col], grp[lat_col]))
        if len(coords) >= 3:
            geom = Polygon(coords)
        else:
            geom = Point(coords[0]) if coords else None
        if geom is None:
            continue
        meta = {c: grp[c].iloc[0] for c in grp.columns if c not in [lon_col, lat_col]}
        meta["geometry"] = geom
        rows.append(meta)
    return gpd.GeoDataFrame(rows, crs="EPSG:4326")
