"""
utils/projection.py
Konversi GeoDataFrame dari TM3 Indonesia ke UTM WGS84.
"""
import geopandas as gpd
from pyproj import CRS

# Tabel meridian tengah tiap zona TM3
_TM3_CENTRAL_MERIDIANS: dict[str, float] = {
    "46.2": 102.0, "47.1": 105.0, "47.2": 108.0,
    "48.1": 111.0, "48.2": 114.0, "49.1": 117.0,
    "49.2": 120.0, "50.1": 123.0, "50.2": 126.0,
    "51.1": 129.0, "51.2": 132.0, "52.1": 135.0,
    "52.2": 138.0, "53.1": 141.0, "53.2": 144.0,
}

_SCALE_FACTOR   = 0.9999
_FALSE_EASTING  = 200_000.0
_FALSE_NORTHING = 1_500_000.0


def get_tm3_crs(zone: str) -> CRS:
    if zone not in _TM3_CENTRAL_MERIDIANS:
        raise ValueError(
            f"Zona TM3 '{zone}' tidak dikenal. "
            f"Pilihan valid: {list(_TM3_CENTRAL_MERIDIANS.keys())}"
        )
    cm = _TM3_CENTRAL_MERIDIANS[zone]
    proj4 = (
        f"+proj=tmerc +lat_0=0 +lon_0={cm} +k={_SCALE_FACTOR} "
        f"+x_0={_FALSE_EASTING} +y_0={_FALSE_NORTHING} "
        f"+ellps=WGS84 +datum=WGS84 +units=m +no_defs"
    )
    return CRS.from_proj4(proj4)


def _tm3_zone_to_utm_epsg(zone: str) -> int:
    """Petakan zona TM3 ke EPSG UTM WGS84 (South, 327xx) yang sesuai."""
    cm = _TM3_CENTRAL_MERIDIANS[zone]
    utm_zone_number = int((cm + 180) / 6) + 1
    # Indonesia mayoritas lintang selatan → UTM South
    return 32700 + utm_zone_number


def reproject_to_utm(gdf: gpd.GeoDataFrame, zone: str) -> gpd.GeoDataFrame:
    """
    Konversi GeoDataFrame dari TM3 ke UTM WGS84.

    - Jika GDF tidak memiliki CRS, diasumsikan TM3 sesuai zona yang dipilih.
    - Konversi via WGS84 sebagai perantara untuk presisi maksimal.
    """
    if gdf is None or gdf.empty:
        raise ValueError("GeoDataFrame kosong.")

    # Tetapkan CRS sumber sebagai TM3 jika belum ada
    if gdf.crs is None:
        gdf = gdf.set_crs(get_tm3_crs(zone))

    # Perantara WGS84
    gdf_wgs = gdf.to_crs(epsg=4326)

    # Konversi ke UTM
    utm_epsg = _tm3_zone_to_utm_epsg(zone)
    return gdf_wgs.to_crs(epsg=utm_epsg)
