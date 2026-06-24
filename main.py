import streamlit as st
import geopandas as gpd
import pandas as pd
import tempfile, os, zipfile, io
from streamlit_folium import st_folium

from utils.shp_reader import read_shp
from utils.dwg_reader import read_dwg
from utils.pdf_reader import read_pdf
from utils.projection import reproject_to_tm3
from utils.exporter import export_shp, export_csv

# ── page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="TM3 Universal Converter",
    page_icon="🗺️",
    layout="wide",
)

# ── header ───────────────────────────────────────────────────────────────────
st.title("🗺️ TM3 Universal Converter")
st.caption(
    "Konversi file SHP / DWG / PDF / CSV koordinat ke sistem proyeksi **TM3 Indonesia**, "
    "hitung luas (Ha), dan ekspor hasil."
)
st.divider()

# ── sidebar – zona TM3 ───────────────────────────────────────────────────────
ZONA_LIST = [
    "46.2","47.1","47.2","48.1","48.2",
    "49.1","49.2","50.1","50.2","51.1",
    "51.2","52.1","52.2","53.1","53.2",
]

with st.sidebar:
    st.header("⚙️ Pengaturan")
    tm3_zone = st.selectbox("Zona TM3", ZONA_LIST, index=6)
    st.info(
        "TM3 (Transverse Mercator 3°) adalah sistem proyeksi resmi BPN Indonesia "
        "dengan lebar zona 3°."
    )
    st.markdown("---")
    st.markdown("**Format input yang didukung:**")
    st.markdown(
        "- `.zip` — **ZIP Shapefile** (berisi .shp, .dbf, .shx, .prj)\n"
        "- `.dxf` — AutoCAD DXF\n"
        "- `.pdf` — PDF tabel koordinat\n"
        "- `.csv` — Koordinat teks"
    )

# ── file uploader ─────────────────────────────────────────────────────────────
st.subheader("1. Upload File")
uploaded = st.file_uploader(
    "Pilih file koordinat / peta",
    type=["zip", "dxf", "dwg", "pdf", "csv"],
    accept_multiple_files=False,
    help=(
        "Shapefile: ZIP berisi .shp + .dbf + .shx (+ .prj). "
        "DXF/DWG: export dari AutoCAD ke .dxf terlebih dahulu."
    ),
)

# ── process ───────────────────────────────────────────────────────────────────
gdf = None

if uploaded:
    ext = os.path.splitext(uploaded.name)[1].lower()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = os.path.join(tmpdir, uploaded.name)
        with open(tmp_path, "wb") as fp:
            fp.write(uploaded.read())

        try:
            if ext == ".zip":
                # ZIP Shapefile
                gdf = read_shp(tmp_path)
                src_format = "ZIP Shapefile"

            elif ext in (".dxf", ".dwg"):
                gdf = read_dwg(tmp_path)
                src_format = "DWG/DXF"

            elif ext == ".pdf":
                gdf = read_pdf(tmp_path)
                src_format = "PDF (tabel koordinat)"

            elif ext == ".csv":
                gdf = read_shp(tmp_path, is_csv=True)
                src_format = "CSV"

            else:
                st.warning("Format file tidak dikenali. Mohon upload ZIP, DXF, PDF, atau CSV.")

        except Exception as e:
            st.error(f"❌ Gagal membaca file: {e}")
            gdf = None

    if gdf is not None:
        st.success(f"✅ File berhasil dibaca sebagai **{src_format}** — {len(gdf)} fitur ditemukan.")

# ── proses reproyeksi ─────────────────────────────────────────────────────────
if gdf is not None:
    st.subheader("2. Reproyeksi ke TM3")
    if st.button("🔄 Proses Konversi", type="primary"):
        with st.spinner("Memproyeksikan koordinat ke TM3…"):
            try:
                gdf_tm3 = reproject_to_tm3(gdf, tm3_zone)
                st.session_state["gdf_tm3"] = gdf_tm3
                st.session_state["gdf_wgs"] = gdf_tm3.to_crs(epsg=4326)
                st.success(f"✅ Reproyeksi selesai — CRS: `{gdf_tm3.crs}`")
            except Exception as e:
                st.error(f"❌ Gagal reproyeksi: {e}")

# ── tampilkan hasil ───────────────────────────────────────────────────────────
if "gdf_tm3" in st.session_state:
    gdf_tm3: gpd.GeoDataFrame = st.session_state["gdf_tm3"]
    gdf_wgs: gpd.GeoDataFrame = st.session_state["gdf_wgs"]

    st.divider()
    st.subheader("3. Hasil Konversi")

    col1, col2 = st.columns(2)

    # ── tabel atribut + luas ──────────────────────────────────────────────────
    with col1:
        st.markdown("**Tabel Atribut & Luas**")

        df_display = gdf_tm3.drop(columns="geometry", errors="ignore").copy()
        if gdf_tm3.geom_type.isin(["Polygon", "MultiPolygon"]).any():
            df_display["Luas_m2"] = gdf_tm3.geometry.area.round(2)
            df_display["Luas_Ha"]  = (gdf_tm3.geometry.area / 10_000).round(4)

        st.dataframe(df_display, use_container_width=True)

        total_ha = df_display.get("Luas_Ha", pd.Series([0])).sum()
        if total_ha:
            st.metric("Total Luas", f"{total_ha:,.4f} Ha")

    # ── preview peta ─────────────────────────────────────────────────────────
    with col2:
        st.markdown("**Preview Peta (WGS84)**")
        try:
            import folium
            centroid = gdf_wgs.geometry.unary_union.centroid
            m = folium.Map(location=[centroid.y, centroid.x], zoom_start=13,
                           tiles="CartoDB positron")
            folium.GeoJson(
                gdf_wgs,
                style_function=lambda _: {
                    "fillColor": "#3b82f6", "color": "#1d4ed8",
                    "weight": 2, "fillOpacity": 0.35,
                },
                tooltip=folium.GeoJsonTooltip(fields=list(df_display.columns[:3]))
            ).add_to(m)
            st_folium(m, use_container_width=True, height=420)
        except Exception as e:
            st.warning(f"Preview peta tidak tersedia: {e}")

    # ── ekspor ───────────────────────────────────────────────────────────────
    st.divider()
    st.subheader("4. Ekspor Hasil")
    ecol1, ecol2 = st.columns(2)

    with ecol1:
        shp_bytes = export_shp(gdf_tm3)
        st.download_button(
            "⬇️ Download SHP (ZIP)",
            data=shp_bytes,
            file_name="hasil_tm3.zip",
            mime="application/zip",
        )

    with ecol2:
        csv_bytes = export_csv(gdf_tm3)
        st.download_button(
            "⬇️ Download CSV Koordinat",
            data=csv_bytes,
            file_name="koordinat_tm3.csv",
            mime="text/csv",
        )
