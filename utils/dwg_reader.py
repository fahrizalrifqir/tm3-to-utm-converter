"""
utils/dwg_reader.py
Membaca file DXF (atau DWG yang sudah dikonversi ke DXF) menjadi GeoDataFrame.

Catatan:
  - Format DWG biner tidak bisa dibaca langsung. Jika user upload .dwg,
    mereka perlu mengkonversinya ke .dxf via AutoCAD / ODA File Converter /
    LibreOffice terlebih dahulu. Kode ini siap menerima .dxf.
  - Library yang digunakan: ezdxf
"""
import geopandas as gpd
from shapely.geometry import Point, LineString, Polygon, MultiPolygon
from shapely.ops import unary_union
import ezdxf
from ezdxf.math import Vec3


def read_dwg(path: str) -> gpd.GeoDataFrame:
    """
    Membaca file DXF dan mengekstrak entitas geometri (LINE, LWPOLYLINE,
    POLYLINE, SPLINE, CIRCLE, INSERT) menjadi GeoDataFrame WGS84.

    File .dwg biner TIDAK didukung langsung; pengguna harus menyimpannya
    sebagai .dxf dari AutoCAD atau ODA File Converter.
    """
    if path.lower().endswith(".dwg"):
        raise ValueError(
            "File .dwg biner tidak bisa dibaca langsung.\n"
            "Silakan konversi ke .dxf terlebih dahulu menggunakan:\n"
            "  • AutoCAD: Save As → DXF\n"
            "  • ODA File Converter (gratis): https://www.opendesign.com/guestfiles/oda_file_converter"
        )

    doc = ezdxf.readfile(path)
    msp = doc.modelspace()

    rows = []
    for entity in msp:
        geom = _entity_to_geom(entity)
        if geom is None or geom.is_empty:
            continue
        row = {
            "layer": entity.dxf.layer,
            "type":  entity.dxftype(),
            "geometry": geom,
        }
        # Tambahkan atribut teks jika ada
        if hasattr(entity.dxf, "text"):
            row["text"] = entity.dxf.text
        rows.append(row)

    if not rows:
        raise ValueError("Tidak ada geometri yang dapat dibaca dari file DXF.")

    gdf = gpd.GeoDataFrame(rows, crs="EPSG:4326")
    return gdf


# ─── konverter entitas ────────────────────────────────────────────────────────

def _entity_to_geom(entity):
    t = entity.dxftype()

    try:
        if t == "LINE":
            s = entity.dxf.start
            e = entity.dxf.end
            return LineString([(s.x, s.y), (e.x, e.y)])

        elif t in ("LWPOLYLINE", "POLYLINE"):
            pts = _polyline_points(entity)
            if len(pts) < 2:
                return None
            closed = getattr(entity.dxf, "flags", 0) & 1 or entity.is_closed if hasattr(entity, "is_closed") else False
            if closed and len(pts) >= 3:
                return Polygon(pts)
            return LineString(pts)

        elif t == "SPLINE":
            pts = [(p.x, p.y) for p in entity.control_points]
            if len(pts) >= 3:
                return Polygon(pts) if entity.closed else LineString(pts)
            return None

        elif t == "CIRCLE":
            c = entity.dxf.center
            r = entity.dxf.radius
            return Point(c.x, c.y).buffer(r, resolution=32)

        elif t == "ARC":
            # Aproksimasi busur sebagai LineString
            import math
            c  = entity.dxf.center
            r  = entity.dxf.radius
            a1 = math.radians(entity.dxf.start_angle)
            a2 = math.radians(entity.dxf.end_angle)
            if a2 < a1:
                a2 += 2 * math.pi
            pts = [
                (c.x + r * math.cos(a), c.y + r * math.sin(a))
                for a in [a1 + (a2 - a1) * i / 32 for i in range(33)]
            ]
            return LineString(pts)

        elif t == "POINT":
            p = entity.dxf.location
            return Point(p.x, p.y)

        elif t in ("HATCH",):
            polys = []
            for boundary in entity.paths:
                pts = [(v[0], v[1]) for v in boundary.vertices] if hasattr(boundary, "vertices") else []
                if len(pts) >= 3:
                    polys.append(Polygon(pts))
            if polys:
                return unary_union(polys)

    except Exception:
        pass

    return None


def _polyline_points(entity) -> list:
    if entity.dxftype() == "LWPOLYLINE":
        return [(p[0], p[1]) for p in entity.get_points()]
    else:  # POLYLINE
        return [(v.dxf.location.x, v.dxf.location.y) for v in entity.vertices]
