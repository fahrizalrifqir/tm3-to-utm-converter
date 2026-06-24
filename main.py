import geopandas as gpd
import pandas as pd
from pyproj import CRS, Transformer
from shapely.geometry import Polygon
from pathlib import Path

# ==========================================
# KONFIGURASI
# ==========================================

INPUT_FILE = r"input\data.shp"

TM3_ZONE = "48.2"

# ==========================================
# DEFINISI EPSG TM3
# ==========================================

TM3_EPSG = {
    "46.2": 23830,
    "47.1": 23831,
    "47.2": 23832,
    "48.1": 23833,
    "48.2": 23834,
    "49.1": 23835,
    "49.2": 23836,
    "50.1": 23837,
    "50.2": 23838,
    "51.1": 23839,
    "51.2": 23840,
    "52.1": 23841,
    "52.2": 23842,
    "53.1": 23843,
    "53.2": 23844
}

def tm3_to_utm_zone(tm3_zone):
    """
    Menentukan zona UTM berdasarkan zona TM3.
    """
    base_zone = int(float(tm3_zone))

    if ".1" in tm3_zone:
        return base_zone
    else:
        return base_zone

def convert_shp(input_file, tm3_zone):

    epsg_tm3 = TM3_EPSG[tm3_zone]

    utm_zone = tm3_to_utm_zone(tm3_zone)

    epsg_utm = 32700 + utm_zone

    print(f"TM3 EPSG : {epsg_tm3}")
    print(f"UTM EPSG : {epsg_utm}")

    gdf = gpd.read_file(input_file)

    gdf = gdf.set_crs(epsg_tm3)

    gdf_utm = gdf.to_crs(epsg_utm)

    if gdf_utm.geom_type.iloc[0] in ["Polygon", "MultiPolygon"]:

        gdf_utm["Luas_m2"] = gdf_utm.area
        gdf_utm["Luas_Ha"] = gdf_utm.area / 10000

    output_shp = Path("output/hasil_utm.shp")

    gdf_utm.to_file(output_shp)

    print("Berhasil disimpan:")
    print(output_shp)

    if "Luas_Ha" in gdf_utm.columns:
        print()
        print("Total Luas:")
        print(round(gdf_utm["Luas_Ha"].sum(), 4), "Ha")

if __name__ == "__main__":
    convert_shp(INPUT_FILE, TM3_ZONE)
