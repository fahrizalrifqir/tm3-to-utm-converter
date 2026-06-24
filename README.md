# TM3 to UTM Converter

Python tool untuk mengonversi data spasial berkoordinat **TM3 Indonesia** menjadi **UTM**, menghitung luas polygon, dan mengekspor hasil ke format GIS.

## Fitur

- Konversi TM3 → UTM
- Mendukung input:
  - Shapefile (.shp)
  - CSV koordinat
  - PDF tabel koordinat
  - DXF (hasil konversi DWG)
- Menghitung luas (m² dan hektar)
- Export:
  - Shapefile (.shp)
  - GeoJSON (.geojson)
  - CSV ringkasan luasan

## Instalasi

```bash
git clone https://github.com/username/tm3-to-utm-converter.git
cd tm3-to-utm-converter
pip install -r requirements.txt
