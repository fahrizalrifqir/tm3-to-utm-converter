"""
utils/shp_reader.py
Membaca Shapefile (.shp) atau CSV koordinat menjadi GeoDataFrame.
"""
import geopandas as gpd
import pandas as pd
from shapely.geometry import Point, Polygon


def read_shp(path: str, is_csv: bool = False) -> gpd.GeoDataFrame:
    """
    Membaca file SHP atau CSV dan mengembalikan GeoDataFrame.

    Parameter
    ---------
    path    : path lengkap ke file .shp atau .csv
    is_csv  : True jika file adalah CSV koordinat

    Return
    ------
    GeoDataFrame dengan CRS WGS84 (EPSG:4326) jika tersedia,
    atau tanpa CRS jika file tidak menyertakan proyeksi.
    """
    if is_csv:
        return _read_csv(path)
    return _read_shapefile(path)


# ─── shapefile ────────────────────────────────────────────────────────────────

def _read_shapefile(path: str) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(path)

    # Jika tidak ada CRS, asumsikan WGS84
    if gdf.crs is None:
        gdf = gdf.set_crs(epsg=4326)

    # Pastikan dalam WGS84 sebelum reproyeksi
    if gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)

    return gdf


# ─── CSV koordinat ────────────────────────────────────────────────────────────

def _read_csv(path: str) -> gpd.GeoDataFrame:
    df = pd.read_csv(path)

    # Deteksi kolom X/Y secara fleksibel
    lon_col = _find_col(df, ["longitude", "lon", "x", "bujur", "long", "easting"])
    lat_col = _find_col(df, ["latitude",  "lat", "y", "lintang", "northing"])

    if lon_col is None or lat_col is None:
        raise ValueError(
            "Kolom koordinat tidak ditemukan. "
            "Pastikan CSV memiliki kolom seperti: longitude/latitude, x/y, bujur/lintang, atau easting/northing."
        )

    df[lon_col] = pd.to_numeric(df[lon_col], errors="coerce")
    df[lat_col] = pd.to_numeric(df[lat_col], errors="coerce")
    df = df.dropna(subset=[lon_col, lat_col])

    # Jika ada kolom 'id' atau 'no_titik', buat polygon dari titik berurutan
    id_col = _find_col(df, ["id_bidang", "bidang", "no_bidang", "parcel_id", "id"])
    if id_col:
        gdf = _build_polygons_from_points(df, lon_col, lat_col, id_col)
    else:
        # Titik lepas
        geometry = [Point(xy) for xy in zip(df[lon_col], df[lat_col])]
        gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")

    return gdf


def _build_polygons_from_points(
    df: pd.DataFrame, lon_col: str, lat_col: str, id_col: str
) -> gpd.GeoDataFrame:
    """Kelompokkan baris berdasarkan id_bidang dan bentuk Polygon."""
    rows = []
    for bid, grp in df.groupby(id_col):
        coords = list(zip(grp[lon_col], grp[lat_col]))
        if len(coords) >= 3:
            geom = Polygon(coords)
        elif len(coords) == 2:
            from shapely.geometry import LineString
            geom = LineString(coords)
        else:
            geom = Point(coords[0])
        meta = {c: grp[c].iloc[0] for c in grp.columns if c not in [lon_col, lat_col]}
        meta["geometry"] = geom
        rows.append(meta)

    gdf = gpd.GeoDataFrame(rows, crs="EPSG:4326")
    return gdf


# ─── helper ───────────────────────────────────────────────────────────────────

def _find_col(df: pd.DataFrame, candidates: list) -> str | None:
    """Cari kolom yang cocok (case-insensitive) dari daftar kandidat."""
    lower_cols = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand in lower_cols:
            return lower_cols[cand]
    return None
