import streamlit as st
import geopandas as gpd
from pathlib import Path
import tempfile
import zipfile
import shutil

st.set_page_config(
    page_title="TM3 to UTM Converter",
    layout="wide"
)

st.title("TM3 → UTM Converter")
st.write("Konversi SHP TM3 ke UTM dan hitung luas.")

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
    "53.2": 23844,
}


def get_utm_epsg(tm3_zone):
    utm_zone = int(float(tm3_zone))
    return 32700 + utm_zone


uploaded_files = st.file_uploader(
    "Upload SHP (.shp .dbf .shx .prj)",
    accept_multiple_files=True
)

tm3_zone = st.selectbox(
    "Zona TM3",
    list(TM3_EPSG.keys()),
    index=4
)

if st.button("Konversi"):

    if not uploaded_files:
        st.error("Upload file SHP terlebih dahulu.")
        st.stop()

    with tempfile.TemporaryDirectory() as tmpdir:

        for file in uploaded_files:
            with open(
                Path(tmpdir) / file.name,
                "wb"
            ) as f:
                f.write(file.getbuffer())

        shp_files = list(Path(tmpdir).glob("*.shp"))

        if not shp_files:
            st.error("File .shp tidak ditemukan.")
            st.stop()

        shp_path = shp_files[0]

        epsg_tm3 = TM3_EPSG[tm3_zone]
        epsg_utm = get_utm_epsg(tm3_zone)

        gdf = gpd.read_file(shp_path)

        gdf = gdf.set_crs(
            epsg_tm3,
            allow_override=True
        )

        gdf_utm = gdf.to_crs(epsg_utm)

        if any(
            gdf_utm.geom_type.isin(
                ["Polygon", "MultiPolygon"]
            )
        ):
            gdf_utm["Luas_m2"] = gdf_utm.area
            gdf_utm["Luas_Ha"] = gdf_utm.area / 10000

        outdir = Path(tmpdir) / "output"
        outdir.mkdir(exist_ok=True)

        out_shp = outdir / "hasil_utm.shp"

        gdf_utm.to_file(
            out_shp,
            driver="ESRI Shapefile"
        )

        zip_path = Path(tmpdir) / "hasil_utm.zip"

        with zipfile.ZipFile(
            zip_path,
            "w",
            zipfile.ZIP_DEFLATED
        ) as z:

            for f in outdir.glob("*"):
                z.write(
                    f,
                    arcname=f.name
                )

        st.success("Konversi berhasil")

        st.write(
            f"TM3 EPSG : {epsg_tm3}"
        )

        st.write(
            f"UTM EPSG : {epsg_utm}"
        )

        if "Luas_Ha" in gdf_utm.columns:

            st.metric(
                "Total Luas (Ha)",
                round(
                    gdf_utm["Luas_Ha"].sum(),
                    4
                )
            )

        with open(zip_path, "rb") as fp:
            st.download_button(
                "Download SHP UTM",
                fp,
                "hasil_utm.zip",
                "application/zip"
            )
            
