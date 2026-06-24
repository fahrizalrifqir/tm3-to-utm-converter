"""
utils/exporter.py
Ekspor GeoDataFrame ke ZIP Shapefile dan CSV koordinat UTM.
"""
import geopandas as gpd
import pandas as pd
import tempfile, os, zipfile, io


def export_shp(gdf: gpd.GeoDataFrame) -> bytes:
    """Simpan GDF sebagai Shapefile dan kembalikan sebagai bytes ZIP."""
    with tempfile.TemporaryDirectory() as tmpdir:
        shp_path = os.path.join(tmpdir, "hasil_utm.shp")
        gdf_out = _prepare_for_export(gdf)
        gdf_out.to_file(shp_path, driver="ESRI Shapefile", encoding="utf-8")

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for fname in os.listdir(tmpdir):
                zf.write(os.path.join(tmpdir, fname), arcname=fname)

        zip_buffer.seek(0)
        return zip_buffer.read()


def export_csv(gdf: gpd.GeoDataFrame) -> bytes:
    """Ekspor koordinat titik sudut sebagai CSV."""
    rows = []
    attr_cols = [c for c in gdf.columns if c != "geometry"]

    for idx, row in gdf.iterrows():
        geom = row.geometry
        attrs = {c: row[c] for c in attr_cols}

        if geom is None or geom.is_empty:
            continue

        coords = _extract_coords(geom)
        for i, coord in enumerate(coords, start=1):
            x, y = coord[0], coord[1]  # abaikan Z jika ada (shapefile 3D)
            entry = {"FID": idx, "No_Titik": i, "X_UTM": round(x, 3), "Y_UTM": round(y, 3)}
            entry.update(attrs)
            rows.append(entry)

    df = pd.DataFrame(rows)
    return df.to_csv(index=False).encode("utf-8")


# ─── helper ───────────────────────────────────────────────────────────────────

def _prepare_for_export(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Bersihkan GDF: potong nama kolom maks 10 karakter (batasan DBF)."""
    gdf = gdf.copy()
    rename_map = {}
    for col in gdf.columns:
        if col == "geometry":
            continue
        if len(col) > 10:
            rename_map[col] = col[:10]
        if gdf[col].dtype == object:
            gdf[col] = gdf[col].astype(str)
    if rename_map:
        gdf = gdf.rename(columns=rename_map)
    return gdf


def _extract_coords(geom) -> list:
    """Kembalikan daftar (x, y[, z]) dari sembarang geometri Shapely."""
    t = geom.geom_type
    if t == "Point":
        return [geom.coords[0]]
    elif t in ("LineString", "LinearRing"):
        return list(geom.coords)
    elif t == "Polygon":
        return list(geom.exterior.coords)
    elif t.startswith("Multi") or t == "GeometryCollection":
        coords = []
        for part in geom.geoms:
            coords.extend(_extract_coords(part))
        return coords
    return []
