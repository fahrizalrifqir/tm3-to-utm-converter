import streamlit as st

st.set_page_config(page_title="TM3 Universal Converter", layout="wide")
st.title("TM3 Universal Converter")

st.info("Starter project generated. Implement parsers in utils/*.py")

uploaded = st.file_uploader(
    "Upload Data",
    type=["zip", "shp", "dwg", "pdf", "csv"]
)

tm3_zone = st.selectbox(
    "Zona TM3",
    ["46.2","47.1","47.2","48.1","48.2","49.1","49.2","50.1","50.2","51.1","51.2","52.1","52.2","53.1","53.2"]
)

if st.button("Proses"):
    st.success("Project template siap dikembangkan.")
