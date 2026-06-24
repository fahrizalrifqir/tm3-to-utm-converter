"""
utils/shp_reader.py
Membaca Shapefile dari ZIP (.zip berisi .shp, .dbf, .shx, .prj)
atau CSV koordinat menjadi GeoDataFrame.
"""
import geopandas as gpd
import pandas as pd
import zipfile, tempfile, os
from shapely.geometry import Point, Polygon, LineString


def read_shp(path: str, is_csv: bool = False) -> gpd.GeoDataFrame:
    """
    Membaca file ZIP-Shapefile atau CSV dan mengembalikan GeoDataFrame.

    Parameter
    ---------
    path    : path ke file .zip (berisi shapefile) atau .csv
    is_csv  : True jika file adalah CSV koordinat

    Return
    ------
    GeoDataFrame dengan CRS WGS84 (EPSG:4326).
    """
    if is_csv:
        return _read_csv(path)
    return _read_shapefile(path)


# ─── shapefile ────────────────────────────────────────────────────────────────

def _read_shapefile(path: str) -> gpd.GeoDataFrame:
    # ZIP berisi shapefile → ekstrak dulu
    if path.lower().endswith(".zip"):
        return _read_shp_from_zip(path)

    # File .shp langsung (tetap didukung sebagai fallback)
    gdf = gpd.read_file(path)
    return _normalize_crs(gdf)


def _read_shp_from_zip(zip_path: str) -> gpd.GeoDataFrame:
    """Ekstrak ZIP ke tempdir, temukan .shp, lalu baca dengan geopandas."""
    with tempfile.TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            shp_files = [n for n in names if n.lower().endswith(".shp")]
            if not shp_files:
                raise ValueError(
                    "ZIP tidak mengandung file .shp.\n"
                    "Pastikan ZIP berisi: nama.shp, nama.dbf, nama.shx "
                    "(dan opsional nama.prj)."
                )
            zf.extractall(tmpdir)

        # Ambil .shp pertama — dukung nested folder di dalam ZIP
        shp_path = os.path.join(tmpdir, shp_files[0])
        gdf = gpd.read_file(shp_path)

    return _normalize_crs(gdf)


def _normalize_crs(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Pastikan GDF dalam WGS84 (EPSG:4326)."""
    if gdf.crs is None:
        gdf = gdf.set_crs(epsg=4326)
    elif gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)
    return gdf


# ─── CSV koordinat ────────────────────────────────────────────────────────────

def _read_csv(path: str) -> gpd.GeoDataFrame:
    df = pd.read_csv(path)

    lon_col = _find_col(df, ["longitude", "lon", "x", "bujur", "long", "easting"])
    lat_col = _find_col(df, ["latitude",  "lat", "y", "lintang", "northing"])

    if lon_col is None or lat_col is None:
        raise ValueError(
            "Kolom koordinat tidak ditemukan. "
            "Pastikan CSV memiliki kolom seperti: longitude/latitude, x/y, "
            "bujur/lintang, atau easting/northing."
        )

    df[lon_col] = pd.to_numeric(df[lon_col], errors="coerce")
    df[lat_col] = pd.to_numeric(df[lat_col], errors="coerce")
    df = df.dropna(subset=[lon_col, lat_col])

    id_col = _find_col(df, ["id_bidang", "bidang", "no_bidang", "parcel_id", "id"])
    if id_col:
        gdf = _build_polygons_from_points(df, lon_col, lat_col, id_col)
    else:
        geometry = [Point(xy) for xy in zip(df[lon_col], df[lat_col])]
        gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")

    return gdf


def _build_polygons_from_points(
    df: pd.DataFrame, lon_col: str, lat_col: str, id_col: str
) -> gpd.GeoDataFrame:
    rows = []
    for bid, grp in df.groupby(id_col):
        coords = list(zip(grp[lon_col], grp[lat_col]))
        if len(coords) >= 3:
            geom = Polygon(coords)
        elif len(coords) == 2:
            geom = LineString(coords)
        else:
            geom = Point(coords[0])
        meta = {c: grp[c].iloc[0] for c in grp.columns if c not in [lon_col, lat_col]}
        meta["geometry"] = geom
        rows.append(meta)
    return gpd.GeoDataFrame(rows, crs="EPSG:4326")


# ─── helper ───────────────────────────────────────────────────────────────────

def _find_col(df: pd.DataFrame, candidates: list) -> str | None:
    lower_cols = {c.lower(): c for c in df.columns}
    for cand in candidates:
        if cand in lower_cols:
            return lower_cols[cand]
    return None
