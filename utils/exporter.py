"""
utils/exporter.py
Ekspor GeoDataFrame ke:
  - ZIP berisi Shapefile lengkap (.shp, .dbf, .shx, .prj)
  - CSV koordinat titik sudut polygon (atau titik langsung)
"""
import geopandas as gpd
import pandas as pd
import tempfile, os, zipfile, io
from shapely.geometry import mapping


# ── SHP → ZIP ─────────────────────────────────────────────────────────────────

def export_shp(gdf: gpd.GeoDataFrame) -> bytes:
    """
    Simpan GeoDataFrame sebagai Shapefile dan kembalikan sebagai bytes ZIP.

    Return
    ------
    bytes : konten file ZIP yang berisi .shp, .dbf, .shx, .prj
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        shp_path = os.path.join(tmpdir, "hasil_tm3.shp")
        gdf_out  = _prepare_for_export(gdf)
        gdf_out.to_file(shp_path, driver="ESRI Shapefile", encoding="utf-8")

        # Kemas semua komponen ke dalam satu ZIP
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for fname in os.listdir(tmpdir):
                fpath = os.path.join(tmpdir, fname)
                zf.write(fpath, arcname=fname)

        zip_buffer.seek(0)
        return zip_buffer.read()


# ── CSV koordinat ─────────────────────────────────────────────────────────────

def export_csv(gdf: gpd.GeoDataFrame) -> bytes:
    """
    Ekspor koordinat menjadi CSV.

    - Untuk Polygon/MultiPolygon : daftar titik sudut per fitur
    - Untuk Point                : satu baris per titik
    - Untuk LineString           : daftar titik per segmen

    Return
    ------
    bytes : konten CSV dalam encoding UTF-8
    """
    rows = []
    attr_cols = [c for c in gdf.columns if c != "geometry"]

    for idx, row in gdf.iterrows():
        geom = row.geometry
        attrs = {c: row[c] for c in attr_cols}

        if geom is None or geom.is_empty:
            continue

        coords = _extract_coords(geom)
        for i, (x, y) in enumerate(coords, start=1):
            entry = {"FID": idx, "No_Titik": i, "X_TM3": round(x, 3), "Y_TM3": round(y, 3)}
            entry.update(attrs)
            rows.append(entry)

    df = pd.DataFrame(rows)
    return df.to_csv(index=False).encode("utf-8")


# ─── helper ───────────────────────────────────────────────────────────────────

def _prepare_for_export(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Bersihkan GDF sebelum ditulis ke Shapefile:
    - Potong nama kolom menjadi maks 10 karakter (batasan DBF)
    - Ubah tipe kompleks menjadi string
    """
    gdf = gdf.copy()
    rename_map = {}
    for col in gdf.columns:
        if col == "geometry":
            continue
        new_name = col[:10]
        if new_name != col:
            rename_map[col] = new_name
        # Ubah list/dict ke string agar bisa ditulis ke DBF
        if gdf[col].dtype == object:
            gdf[col] = gdf[col].astype(str)
    if rename_map:
        gdf = gdf.rename(columns=rename_map)
    return gdf


def _extract_coords(geom) -> list[tuple[float, float]]:
    """Kembalikan daftar (x, y) dari sembarang geometri Shapely."""
    gtype = geom.geom_type

    if gtype == "Point":
        return [(geom.x, geom.y)]

    elif gtype in ("LineString", "LinearRing"):
        return list(geom.coords)

    elif gtype == "Polygon":
        return list(geom.exterior.coords)

    elif gtype.startswith("Multi") or gtype == "GeometryCollection":
        coords = []
        for part in geom.geoms:
            coords.extend(_extract_coords(part))
        return coords

    return []
