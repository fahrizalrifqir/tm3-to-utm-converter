"""
utils/projection.py
Reproyeksi GeoDataFrame ke sistem koordinat TM3 Indonesia (Transverse Mercator 3°).

TM3 adalah proyeksi resmi BPN (Badan Pertanahan Nasional) Indonesia.
Setiap zona memiliki meridian tengah tersendiri dengan lebar 3°.
Datum: WGS84 (ITRF/GRS80)
"""
import geopandas as gpd
from pyproj import CRS


# ── Tabel meridian tengah tiap zona TM3 ──────────────────────────────────────
# Zona format: "XX.Y" → central meridian (°E)
# Referensi: SNI 19-6726-2002 / Juknis BPN
_TM3_CENTRAL_MERIDIANS: dict[str, float] = {
    "46.2": 102.0,
    "47.1": 105.0,
    "47.2": 108.0,
    "48.1": 111.0,
    "48.2": 114.0,
    "49.1": 117.0,
    "49.2": 120.0,
    "50.1": 123.0,
    "50.2": 126.0,
    "51.1": 129.0,
    "51.2": 132.0,
    "52.1": 135.0,
    "52.2": 138.0,
    "53.1": 141.0,
    "53.2": 144.0,
}

# Parameter standar TM3 BPN
_SCALE_FACTOR  = 0.9999       # faktor skala (k₀)
_FALSE_EASTING = 200_000.0    # False Easting (m)
_FALSE_NORTHING = 1_500_000.0 # False Northing (m)  — bisa 0 untuk proyeksi murni


def get_tm3_crs(zone: str) -> CRS:
    """
    Kembalikan objek CRS pyproj untuk zona TM3 yang diberikan.

    Parameter
    ---------
    zone : str
        Kode zona TM3, mis. "49.2"

    Return
    ------
    pyproj.CRS
    """
    if zone not in _TM3_CENTRAL_MERIDIANS:
        raise ValueError(
            f"Zona TM3 '{zone}' tidak dikenal. "
            f"Pilihan valid: {list(_TM3_CENTRAL_MERIDIANS.keys())}"
        )

    cm = _TM3_CENTRAL_MERIDIANS[zone]

    # Definisi proj4 TM3 BPN
    proj4 = (
        f"+proj=tmerc "
        f"+lat_0=0 "
        f"+lon_0={cm} "
        f"+k={_SCALE_FACTOR} "
        f"+x_0={_FALSE_EASTING} "
        f"+y_0={_FALSE_NORTHING} "
        f"+ellps=WGS84 "
        f"+datum=WGS84 "
        f"+units=m "
        f"+no_defs"
    )

    return CRS.from_proj4(proj4)


def reproject_to_tm3(gdf: gpd.GeoDataFrame, zone: str) -> gpd.GeoDataFrame:
    """
    Proyeksikan GeoDataFrame ke TM3 zona yang ditentukan.

    Jika GDF tidak memiliki CRS, diasumsikan WGS84 (EPSG:4326).

    Parameter
    ---------
    gdf  : GeoDataFrame sumber (sembarang CRS)
    zone : kode zona TM3, mis. "49.2"

    Return
    ------
    GeoDataFrame baru dengan CRS TM3 dan koordinat dalam meter.
    """
    if gdf is None or gdf.empty:
        raise ValueError("GeoDataFrame kosong, tidak ada yang diproyeksikan.")

    # Pastikan ada CRS
    if gdf.crs is None:
        gdf = gdf.set_crs(epsg=4326)

    # Konversi ke WGS84 jika belum
    if gdf.crs.to_epsg() != 4326:
        gdf = gdf.to_crs(epsg=4326)

    tm3_crs = get_tm3_crs(zone)
    gdf_tm3 = gdf.to_crs(tm3_crs)

    return gdf_tm3
